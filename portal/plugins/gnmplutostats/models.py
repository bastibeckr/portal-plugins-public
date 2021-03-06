from django.db.models import Model, IntegerField, CharField, DateTimeField, BooleanField
from datetime import datetime


class ProjectSizeInfoModel(Model):
    project_id = CharField(max_length=32, db_index=True, null=True)
    storage_id = CharField(max_length=32, db_index=True)
    size_used_gb = IntegerField()
    last_updated = DateTimeField(default=datetime.now)

    class Meta:
        unique_together = (("project_id", "storage_id",))

    def __str__(self):
        return "{0} using {1}Gb on {2}".format(self.project_id, self.size_used_gb, self.storage_id)


class ProjectScanReceipt(Model):
    project_id = CharField(max_length=32, db_index=True, null=False, unique=True)
    last_scan = DateTimeField(null=True)
    project_status = CharField(max_length=32, null=True)
    project_title = CharField(max_length=1024, blank=True,null=True)
    last_scan_duration = IntegerField(null=True)
    last_scan_error = CharField(max_length=4096, blank=True)

    def __str__(self):
        return "{0} last scanned at {1}".format(self.project_id, self.last_scan)


class CategoryScanInfo(Model):
    category_label = CharField(max_length=256, db_index=True)
    storage_id = CharField(max_length=32, db_index=True)
    last_updated = DateTimeField(default=datetime.now)
    attached = BooleanField()
    size_used_gb = IntegerField()

    class Meta:
        unique_together = (('last_updated','category_label', 'storage_id', 'attached', ))

    def __str__(self):
        return "{0}Gb for {1} on {2} at {3}".format(self.size_used_gb, self.category_label, self.storage_id, self.last_updated)