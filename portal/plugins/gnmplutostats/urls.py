"""

"""
import logging

from django.conf.urls.defaults import *
from views import GetStatsView, GetLibraryStats, ProjectScanReceiptView, ProjectStatInfoList, TotalSpaceByStorage, StorageCapacityView
from views import StorageDashMain, ProjectInfoGraphView,IndexView
# This new app handles the request to the URL by responding with the view which is loaded
# from portal.plugins.gnmplutostats.views.py. Inside that file is a class which responsedxs to the
# request, and sends in the arguments template - the html file to view.
# name is shortcut name for the urls.

urlpatterns = patterns('portal.plugins.gnmplutostats.views',
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^stats/([^\/]+)\/*', GetStatsView.as_view(), name='gnmplutostats_get_stats'),
    url(r'^library_stats/([^\/]+)\/*', GetLibraryStats.as_view(), name='gnmplutostats_library_stats'),
    url(r'^storagedash/$', StorageDashMain.as_view(), name="plutostats_storage_dash"),
    url(r'^projectsize/receipts/', ProjectScanReceiptView.as_view(), name='projectsize_receipts'),
    url(r'^projectsize/all/', ProjectStatInfoList.as_view(), name='projectsize_all'),
    url(r'^projectsize/storage/(?P<storage_id>\w{2}-\d+)$', ProjectStatInfoList.as_view(), name='projectsize_storage'),
    url(r'^projectsize/storage/totals$', TotalSpaceByStorage.as_view(), name='projectsize_storage_totals'),
    url(r'^projectsize/project/(?P<project_id>\w{2}-\d+)$', ProjectStatInfoList.as_view(), name='projectsize_project'),
    url(r'^projectsize/project/graph$', ProjectInfoGraphView.as_view(), name='projectsize_graph'),
    url(r'^system/storage/(?P<storage_id>\w{2}-\d+)$', StorageCapacityView.as_view(), name='system_storage_caps')
)
