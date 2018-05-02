import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings
import logging
from time import sleep
from datetime import datetime
from .exceptions import HttpError

import xml.etree.cElementTree as ET
logger = logging.getLogger(__name__)


class ProcessResult(object):
    def __init__(self):
        self.storage_sum = {}

    def add_entry(self, storage_id, size_in_bytes):
        if not storage_id in self.storage_sum:
            self.storage_sum[storage_id] = float(size_in_bytes)/1024.0**3
        else:
            self.storage_sum[storage_id] += float(size_in_bytes)/1024.0**3

    def __str__(self):
        return "{0}".format(self.storage_sum)

    def save(self,project_id):
        """
        saves the contents of the ProcessResult to a series of data model entries, one for each storage
        :param project_id: project ID to save against
        :return: the number of rows saved
        """
        from models import ProjectSizeInfoModel
        n=0
        for storage_id,total_size in self.storage_sum.items():
            if total_size is None:
                continue
            (record, created) = ProjectSizeInfoModel.objects.get_or_create(project_id=project_id,
                                                                           storage_id=storage_id,
                                                                           defaults={"size_used_gb": total_size,"last_updated": datetime.now()})
            record.size_used_gb = total_size
            record.last_updated = datetime.now()
            record.save()
            n+=1
        return n


class ResponseProcessor(object):
    xmlns = "{http://xml.vidispine.com/schema/vidispine}"

    def __init__(self, textcontent):
        try:
            self._doc = ET.fromstring(textcontent.encode('ascii','xmlcharrefreplace'))
        except UnicodeDecodeError as e:
            logger.warning(e)
            self._doc = ET.fromstring(textcontent.decode('utf-8').encode('ascii','xmlcharrefreplace'))

    @property
    def total_hits(self):
        """
        total number of items matching the query as provided by Vidispine
        :return:
        """
        return int(self._doc.find("{0}hits".format(self.xmlns)).text)

    @property
    def entries(self):
        """
        number of entries in this batch
        :return:
        """
        return len(self._doc.findall("{0}item".format(self.xmlns)))

    def _get_xml_entry(self, parent_entry, tag_name):
        """
        return the value of the given entry or None
        :param parent_entry:
        :param tag_name:
        :return:
        """
        node = parent_entry.find(tag_name)
        if node is None:
            return None
        else:
            return node.text

    @staticmethod
    def get_right_component(item_entry):
        """
        returns the right component for the "main" content
        :param item_entry:
        :return:
        """
        possible_components = [
            "{0}containerComponent".format(ResponseProcessor.xmlns),
            "{0}binaryComponent".format(ResponseProcessor.xmlns),
        ]

        for c in possible_components:
            if item_entry.find(c) is not None:
                return c
        return None

    def item_size(self, item_entry, process_result, shape_tag="original"):
        """
        get the total size of files of the given shape tag for the given item
        :param item_entry: pointer to an <item> node in the returned document
        :param process_result: ProcessResult instance to update
        :param shape_tag: shape tag to get
        :return:
        """
        for shape_entry in item_entry.findall("{0}shape".format(self.xmlns)):
            entry_shape_tag = self._get_xml_entry(shape_entry, "{0}tag".format(self.xmlns))
            if entry_shape_tag!=shape_tag:
                continue
            component_name = self.get_right_component(shape_entry)
            if component_name is None:
                logger.warning("Original content: {0}".format(ET.tostring(shape_entry)))
                raise RuntimeError("Could not determine the right content type to use")

            try:
                process_result.add_entry(self._get_xml_entry(shape_entry,"{1}/{0}file/{0}storage".format(self.xmlns, component_name)),
                                         self._get_xml_entry(shape_entry,"{1}/{0}file/{0}size".format(self.xmlns, component_name)))
            except TypeError as e:
                logger.warning("Original content: {0}".format(ET.tostring(shape_entry)))
                logger.warning("Value {0} for {1} does not seem to be a number (can't convert to float)"
                               .format(self._get_xml_entry(shape_entry,"{1}/{0}file/{0}size".format(self.xmlns, component_name)),
                                       self._get_xml_entry(shape_entry,"{1}/{0}file/{0}path".format(self.xmlns, component_name)))
                               )

    def page_size(self, process_result,shape_tag="original"):
        """
        get the total size of files of the given shape tag in this page of results
        :param process_result: ProcessResult instance to update
        :param shape_tag: shape tag to get
        :return:
        """
        for item_entry in self._doc.findall("{0}item".format(self.xmlns)):
            self.item_size(item_entry, process_result, shape_tag)


def process_next_page(project_id, process_result, start_at, limit, unattached=False):
    """
    grabs another page of search results and processes them
    :param project_id: project id to search
    :param process_result: ProcessResult object to update
    :param start_at: item number to start at (first item is 1)
    :param limit: page size
    :return: tuple of (process_result, more_pages)
    """
    if project_id is None:
        searchdoc = """<ItemSearchDocument xmlns="http://xml.vidispine.com/schema/vidispine">
	<operator operation="NOT"><field>
		<name>__collection</name>
		<value>*</value>
	</field></operator>
</ItemSearchDocument>"""
    else:
        searchdoc = """<ItemSearchDocument xmlns="http://xml.vidispine.com/schema/vidispine">
        <field>
            <name>__collection</name>
            <value>{0}</value>
        </field>
    </ItemSearchDocument>""".format(project_id)

    response = requests.put("{url}:{port}/API/item;first={start};number={limit}?content=shape".format(
                                url=settings.VIDISPINE_URL,
                                port=settings.VIDISPINE_PORT,
                                start=start_at,
                                limit=limit),
                            auth=HTTPBasicAuth(settings.VIDISPINE_USERNAME,settings.VIDISPINE_PASSWORD),
                            data=searchdoc,headers={'Content-Type': 'application/xml', 'Accept': 'application/xml'})

    if response.status_code==200:
        xmldoc = ResponseProcessor(response.text)
        logger.info("{0}: Got page with {1}/{2} items".format(project_id, xmldoc.entries, xmldoc.total_hits))
        if xmldoc.entries==0:
            logger.info("{0}: all items from project counted".format(project_id))
            return (process_result, False)
        xmldoc.page_size(process_result)
        logger.info("{0}: Running total is {1}".format(project_id, process_result))
        return (process_result, True)
    else:
        raise HttpError(response)


def update_project_size(project_id):
    """
    scans the project at project_id and returns a ProcessResult object containing the final data
    :param project_id: project to scan
    :return: ProcessResult object
    """
    page_size = 40
    page_start=1
    retry_limit=5
    retry_count=0
    result = ProcessResult()

    more_pages = True
    while more_pages:
        try:
            logger.info("{0}: Getting page for items {1} to {2}...".format(project_id,page_start, page_start+page_size))
            (result, more_pages) = process_next_page(project_id, result, start_at=page_start, limit=page_size)
            page_start+=page_size+1
        except HttpError as e:
            logger.error(str(e))
            retry_count+=1
            if retry_count>=retry_limit:
                logger.error("Retried {0} times already, aborting".format(retry_count))
                raise
            if e.status_code>=400 and e.status_code<=500:
                logger.error("Not retrying")
                raise
            logger.info("Retrying after 10s delay")
            sleep(10)
    logger.info("{0}: Completed".format(project_id))
    return result
