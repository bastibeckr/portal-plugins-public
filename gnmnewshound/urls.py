"""

"""
import logging

from django.conf.urls.defaults import *

# This new app handles the request to the URL by responding with the view which is loaded 
# from portal.plugins.gnmnewshound.views.py. Inside that file is a class which responsedxs to the 
# request, and sends in the arguments template - the html file to view.
# name is shortcut name for the urls.

urlpatterns = patterns('portal.plugins.gnmnewshound.views',
    url(r'^$', 'GenericAppView', kwargs={'template': 'gnmnewshound/index.html'}, name='index'),
)
