from celery import shared_task
from celery.decorators import periodic_task
from celery.schedules import crontab
from django.conf import settings
import re
import logging
from datetime import datetime, timedelta
from django.db.models import Q

logger = logging.getLogger(__name__)
id_validator = re.compile(r'^\w{2}-\d+$')


@shared_task
def calculate_project_size(project_id=None):
    """
    celery task to calculate the size of a single project
    :param project_id:
    :return:
    """
    if project_id is not None and not id_validator.match(project_id):
        raise ValueError("{0} is not a valid vidispine id".format(project_id))

    from projectsizer import update_project_size
    #project ID of None=>unattached
    result = update_project_size(project_id)
    logger.info("{0}: Project size information: {1}".format(project_id, result.storage_sum))
    result.save(project_id)
    logger.info("Done")


@periodic_task(run_every=crontab(hour='21',minute='03'))
def scan_all_projects():
    """
    celery task to update receipts for all projects, ensuring that we have a record of every project
    :return:
    """
    from projectscanner import ProjectScanner

    s = ProjectScanner()
    for projectinfo in s.scan_all():
        projectinfo.save_receipt()


@periodic_task(run_every=timedelta(minutes=30))
def launch_project_sizing():
    """
    celery task to launch the scanning of projects.
    A maximum of GNMPLUTOSTATS_PROJECT_SCAN_LIMIT are triggered at once (default 10); "In production" are highest priority,
    if none of these are applicable then "New", if none of these are applicable then everything else.
    "In Production" projects are scanned at most once a day, "New" are scanned
    at most once a day and everything else is scanned at most once a week.
    The calculate_project_size task is queued on the queue given by GNMPLUTOSTATS_PROJECT_SCAN_QUEUE (default 'celery')
    :return:
    """
    from models import ProjectScanReceipt
    trigger_limit = int(getattr(settings,"GNMPLUTOSTATS_PROJECT_SCAN_LIMIT",10))
    to_trigger = []
    c=0

    logger.info("Gathering projects to measure")

    highest_priority = ProjectScanReceipt.objects.filter(project_status="In Production",last_scan__lt=datetime.now()-timedelta(days=1)).order_by('-last_scan')
    for entry in highest_priority:
        to_trigger.append(entry)
        logger.info("{0}: {1} ({2})".format(c, entry,entry.project_status))
        c+=1
        if c>=trigger_limit:
            break

    if len(to_trigger)<trigger_limit:
        next_priority = ProjectScanReceipt.objects.filter(project_status="New", last_scan__lt=datetime.now()-timedelta(days=1)).order_by('-last_scan')
        for entry in next_priority:
            to_trigger.append(entry)
            logger.info("{0}: {1} ({2})".format(c, entry,entry.project_status))
            c+=1
            if c>=trigger_limit:
                break

    if len(to_trigger)<trigger_limit:
        everything_else = ProjectScanReceipt.objects.filter(~Q(project_status="New") & ~Q(project_status="In Production"),last_scan__lt=datetime.now()-timedelta(days=5))
        for entry in everything_else:
            to_trigger.append(entry)
            logger.info("{0}: {1} ({2})".format(c, entry,entry.project_status))
            c+=1
            if c>=trigger_limit:
                break

    logger.debug("Projects to scan: ".format(to_trigger))
    n=0
    for entry in to_trigger:
        n+=1
        calculate_project_size.apply_async(kwargs={'project_id': entry.project_id},queue=getattr(settings,"GNMPLUTOSTATS_PROJECT_SCAN_QUEUE","celery"))
    return "Triggered {0} projects to scan".format(n)