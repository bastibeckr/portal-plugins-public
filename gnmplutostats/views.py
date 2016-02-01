"""
This is where you can write a lot of the code that responds to URLS - such as a page request from a browser
or a HTTP request from another application.

From here you can follow the Cantemo Portal Developers documentation for specific code, or for generic 
framework code refer to the Django developers documentation. 

"""
import logging

from django.contrib.auth.decorators import login_required
from portal.generic.baseviews import ClassView
from portal.vidispine.iitem import ItemHelper
from portal.vidispine.iexception import NotFoundError
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from vsmixin import VSMixin

log = logging.getLogger(__name__)


class GenericAppView(ClassView):
    """ Show the page. Add your python code here to show dynamic content or feed information in
        to external apps
    """
    def __call__(self):
        # __call__ responds to the incoming request. It will already have a information associated to it, such as self.template and self.request

        log.debug("%s Viewing page" % self.request.user)
        ctx = {}
        
        # return a response to the request
        return self.main(self.request, self.template, ctx)

# setup the object, and decorate so that only logged in users can see it
GenericAppView = GenericAppView._decorate(login_required)


class InvalidPlutoType(StandardError):
    pass


class BaseStatsView(VSMixin, APIView):
    from rest_framework.parsers import JSONParser
    from rest_framework.renderers import JSONRenderer

    recognised_types = {}
    interesting_fields = []

    parser_classes = (JSONParser, )
    renderer_classes = (JSONRenderer, )

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(BaseStatsView, self).dispatch(request, *args, **kwargs)

    def get(self, request, type=""):
        from traceback import format_exc
        try:
            return self.inner_get(request, type=type)
        except StandardError as e:
            return Response({'status': 'error', 'exception': str(e), 'trace': format_exc()},status=400)

    def inner_get(self, request, type=None):
        raise StandardError("inner_get not implemented!")

    def process_facets(self,data):
        if not 'facet' in data:
            raise KeyError("Passed data does not contain facets")

        rtn = {}
        for block in data['facet']:
            rtn[block['field']] = (map(lambda x: {'category': x['fieldValue'], 'value': x['value']}, block['count']))
        return rtn


class GetLibraryStats(BaseStatsView):
    from rest_framework.parsers import JSONParser
    from rest_framework.renderers import JSONRenderer

    recognised_types = {
        'FCS': {
            'names': [
                'FCS Media/Holding',
                'FCS online media',
                'FCS external media'
            ],
            'overlaps': [

            ]
        },
        'Rushes': {
            'names': [
                'Back up Guardian rushes',
                'Rushes/ParentProjectsHeld',
                'Rushes+Masters/DeepArchive'
            ],
            'overlaps': [
                [
                    'Back up Guardian rushes',
                    'Rushes/ParentProjectsHeld',
                ],
                [
                    'Back up Guardian rushes',
                    'Rushes+Masters/DeepArchive',
                ]
            ]
        }
    }

    parser_classes = (JSONParser, )
    renderer_classes = (JSONRenderer, )

    def __init__(self, *args, **kwargs):
        self._agent = None

    def get_library_hits(self,libid):
        from xml.etree.cElementTree import Element,SubElement,tostring,fromstring
        headers, content = self._make_vidispine_request(self._agent,
                                     "GET",
                                     "/API/library/{0};number=0".format(libid),
                                     body="",
                                     headers={'Accept': 'application/xml'})
        #print "checking {0}".format(libid)
        data=fromstring(content)
        #print content

        try:
            return int(data.find('{http://xml.vidispine.com/schema/vidispine}hits').text)
        except AttributeError as e: #normally, this means that there was no hits element
            log.error('No <hits> element returned for library {0}'.format(libid))
            return 0
        except ValueError as e: #normally, this means that we couldn't convert the string to integer
            log.error('Could not convert value "{0}" to integer for library {1}'.format(
                data.find('{http://xml.vidispine.com/schema/vidispine}hits'),
            libid))
            return 0

    def find_min(self, overlap, data):
        """
        Find the overlapping field with the minimum number of hits, i.e. the one that is contained within the others
        :param overlap: overlap definition, a list over overlapping field names
        :param data: data dict, containing fieldname -> count pairs
        :return: fieldname of the minimum
        """
        from pprint import pprint
        pprint(overlap)
        n=9999999999
        min_field = None

        for fieldname in overlap:
            print "checking {0} for min".format(fieldname)
            if data[fieldname]<n:
                min_field = fieldname
                n = data[fieldname]
        return min_field, n

    def process_overlaps(self, type, data, want_total=False):
        """
        Uses any overlap statements in the report definition to make piechart-compatible data
        :param data: data dictionary
        :return: normalised data dict
        """
        if not type in self.recognised_types:
            return data

        for overlap in self.recognised_types[type]['overlaps']:
            min_field, min_val = self.find_min(overlap, data)
            for fieldname in overlap:
                if fieldname != min_field:
                    data[fieldname] -= min_val

        if want_total:
            total = 0
            for k,v in data.items():
                total += v
            data['total'] = total
        return data

    def inner_get(self, request, type=""):
        from portal.plugins.gnmlibrarytool.models import LibraryNickname
        from vsmixin import HttpError
        import httplib2
        from django.http import HttpResponseBadRequest
        import json
        from pprint import pprint

        counts = {}
        self._agent = httplib2.Http()

        if type=='all':
             for lib in LibraryNickname.objects.all():
                try:
                    counts[lib.nickname] = self.get_library_hits(lib.library_id)
                except HttpError as e:
                    log.warning(e)

        elif type in self.recognised_types:
            for libname in self.recognised_types[type]['names']:
                lib = LibraryNickname.objects.get(nickname=libname)
                try:
                    counts[lib.nickname] = self.get_library_hits(lib.library_id)
                except HttpError as e:
                    log.warning(e)
        else:
            return HttpResponseBadRequest("Report type not recognised")

        pprint(counts)
        d = self.process_overlaps(type,counts)

        rtn = {
            'status': 'ok',
            'data': {
                type:
                    []
            }
        }

        #rtn['data'][type] = map(lambda k, v: {'category': k,'value': v}, d.items())
        for k,v in d.items():
            rtn['data'][type].append({'category': k,'value': v})
        return Response(rtn)


class GetStatsView(BaseStatsView):
    recognised_types = {
        'commission': {
            'status_field': 'gnm_commission_status',
            'vs_class': 'collection'
        },
        'project': {
            'status_field': 'gnm_project_status',
            'vs_class': 'collection'
        },
        'master': {
            'status_field': 'gnm_master_generic_status',
            'vs_class': 'item'
        },
    }
    interesting_fields = []

    def inner_get(self, request, type=""):
        from xml.etree.cElementTree import Element,SubElement,tostring
        import httplib2
        import json
        from pprint import pprint

        if not type.lower() in self.recognised_types:
            raise InvalidPlutoType("{0} is not a recognised pluto type".format(type))

        xmlroot = Element('ItemSearchDocument', {'xmlns': 'http://xml.vidispine.com/schema/vidispine'})
        fieldEl = SubElement(xmlroot, 'field')
        nameEl = SubElement(fieldEl,'name')
        nameEl.text = 'gnm_type'
        valueEl = SubElement(fieldEl, 'value')
        valueEl.text=type
        facetEl = SubElement(xmlroot, 'facet', {'count': 'true'})
        ffieldEl = SubElement(facetEl, 'field')
        ffieldEl.text = self.recognised_types[type]['status_field']

        searchDoc = tostring(xmlroot,encoding="UTF-8")
        #print searchDoc

        (headers, content) = self._make_vidispine_request(httplib2.Http(),"PUT","/API/search;number=0",searchDoc,
                                               {'Accept': 'application/json'})
        #print "\nreturned:"
        #print content

        data = json.loads(content)
        pprint(data)

        return Response({'status': 'ok', 'data': self.process_facets(data)})

import threading
import Queue


class MediaProjectAttachmentDataView(BaseStatsView):
    max_threads = 4
    max_collection_size = 10

    interesting_fields = [
        'name',
        'originalFilename',
        'fileSize',
        'duration',
        'gnm_asset_category',
        'gnm_type'
    ]

    class FetchDataThread(VSMixin, threading.Thread):
        def __init__(self,input_queue,output_queue,*args,**kwargs):
            import httplib2
            super(MediaProjectAttachmentDataView.FetchDataThread,self).__init__(*args,**kwargs)
            self._q = input_queue
            self._outq = output_queue
            self.agent = httplib2.Http()

        def make_doc(self, cats, doc_size):
            from xml.etree.cElementTree import Element,SubElement, tostring
            if not isinstance(cats,list):
                cats = [cats]
            docroot = Element('ItemSearchDocument', {'xmlns': 'http://xml.vidispine.com/schema/vidispine'})
            fieldEl = SubElement(docroot,'field')
            nameEl = SubElement(fieldEl, 'name')
            nameEl.text = 'gnm_asset_category'
            for c in cats:
                valueEl = SubElement(fieldEl,'value')
                valueEl.text = unicode(c)

            fieldEl = SubElement(docroot,'field')
            nameEl = SubElement(fieldEl, 'name')
            nameEl.text = '__collection_size'
            valueEl = SubElement(fieldEl,'value')
            valueEl.text = str(doc_size)
            return tostring(docroot,encoding="UTF-8")

        def run(self):
            import json
            from pprint import pprint
            while True:
                data = self._q.get()
                if 'complete' in data:
                    break
                doc = self.make_doc(data['categories'],data['bucket'])
                print doc
                try:
                    headers, content = self._make_vidispine_request(self.agent,"PUT","/API/item;number=0",doc,headers={'Accept': 'application/json'})

                    rtn_data = json.loads(content)
                    pprint(content)
                    data['response'] = rtn_data
                    self._outq.put(data)
                except StandardError as e:
                    log.error(e)
                self._q.task_done()

    def inner_get(self, request, type=None):
        input_queue = Queue.Queue()
        output_queue = Queue.Queue()
        threads = []

        log.info("Starting {0} threads".format(self.max_threads))
        #print "Starting {0} threads".format(self.max_threads)
        for n in range(0,self.max_threads):
            t = self.FetchDataThread(input_queue,output_queue)
            threads.append(t)
            t.start()

        for n in range(0,self.max_collection_size):
            input_queue.put({'categories': ['Rushes'], 'bucket': n})

        log.info("Waiting for data back from Vidispine...")
        #print "Waiting for data back from Vidispine..."

        input_queue.join()

        log.info("Terminating threads...")
        #print "Terminating threads..."
        for n in range(0, self.max_threads):
            input_queue.put({'complete': True})

        result = []
        try:
            while True:
                data = output_queue.get(False)
                data['hits'] = data['response']['hits']
                data['n'] = data['bucket']
                data['bucket'] = "{0} collections".format(data['bucket'])
                del data['response']
                result.append(data)

        except Queue.Empty:
            pass

        return Response({'status': 'ok', 'data': sorted(result, key=lambda x: x['n'])})