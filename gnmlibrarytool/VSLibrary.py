class HttpError(StandardError):
    def __init__(self,response,content):
        self.response=response
        self.content=content

    def __unicode__(self):
        return u"HTTP {0} error".format(self.response.code)


class VSApi(object):
    def __init__(self,host="localhost",port=8080,username="admin",password="",protocol="http",url=None):
        import re

        if protocol != "http" and protocol != "https":
            raise ValueError("protocol is not valid")

        if url is not None:
            parts = re.match(r'([^:]+)://(.*)$',url)
            protocol = parts.group(1)
            host = parts.group(2)

        self.host = host
        try:
            self.port = int(port)
        except StandardError:
            self.port = port

        self.username = username
        self.password = password
        self.protocol = protocol
        self._xmlns = "{http://xml.vidispine.com/schema/vidispine}"

    def _validate_params(self):
        import re

        if re.search(u'[/:]',self.host):
            raise ValueError("host is not valid")
        if not isinstance(self.port,int):
            raise ValueError("port is not valid")
        if self.protocol != "http" and self.protocol != "https":
            raise ValueError("protocol is not valid")

    def request(self,path,method="GET",body=None):
        from httplib2 import Http
        import xml.etree.ElementTree as ET
        h = Http()

        h.add_credentials(self.username,self.password)

        self._validate_params()
        uri = "{0}://{1}:{2}/API/{3}".format(self.protocol,self.host,self.port,path)

        if body is None:
            (response,content) = h.request(uri, method=method, headers={'Accept': 'application/xml'})
        else:
            (response,content) = h.request(uri, method=method, body=body, headers={'Accept': 'application/xml'})

        if int(response['status']) < 200 or int(response['status']) > 299:
            raise HttpError(response, content)

        return ET.fromstring(content)


class VSLibraryCollection(VSApi):
    def __init__(self, host="localhost", port=8080, username="admin", password="", protocol="http", url=None):
        """
        Create a new connection to Vidispine to get library information
        :param host: Host for Vidispine. Defaults to localhost.
        :param port: Port on which Vidispine is running. Defaults to 8080
        :param username: Username to communicate with Vidispine. Default is admin
        :param password: Password for the user
        :param protocol: http (default) or https, to talk to Vidispine
        :return: None
        """
        super(VSLibraryCollection,self).__init__(host,port,username,password,protocol,url)

    def scan(self,autoRefresh=None):
        """
        Scans for libraries in Vidispine as a generator, yielding the library name
        :param autoRefresh: Can be None, True or False.  If True or False then only look for libraries that are (or are not) auto-refreshing.
        """
        #from xml.etree.ElementTree import *
        uri = "library"
        if autoRefresh is not None:
            if autoRefresh:
                uri += ";autoRefresh=true"
            else:
                uri += ";autoRefresh=false"

        doc = self.request(uri,method="GET")
        for node in doc.findall("{0}uri".format(self._xmlns)):
            yield node.text


class VSLibrary(VSApi):
    """
    This class represents a Vidispine library, handling all requisite XML parsing via ElementTree
    """

    def __init__(self, host="localhost", port=8080, username="admin", password="", protocol="http", url=None):
        """
        Create a new connection to Vidispine to get library information
        :param host: Host for Vidispine. Defaults to localhost.
        :param port: Port on which Vidispine is running. Defaults to 8080
        :param username: Username to communicate with Vidispine. Default is admin
        :param password: Password for the user
        :param protocol: http (default) or https, to talk to Vidispine
        :return: None
        """
        super(VSLibrary,self).__init__(host,port,username,password,protocol,url)

        self._document = None
        self._settings = None
        self._storagerule = None

    def get_hits(self, vsid):
        """
        Loads enough of the library definition to get the total number of hits
        :param vsid: ID of the vidispine library.  Raises ValueError if this is not in {site}-{number} format.
        :return: Integer representing number of items referenced by library.  This is a convenience, the same result
        can be obtained by reading the VSlibrary.hits property after calling this method
        """
        import re
        if not re.match(r'^\w{2}\*\d+$',vsid):
            raise ValueError("{0} is not a valid Vidispine library ID".format(vsid))

        self._document = self.request("library/{0};number=0".format(vsid))
        return self.hits

    def populate(self, vsid):
        """
        Load a library definition from Vidispine
        :param vsid: ID of the vidispine library. Raises ValueError if this is not in {site}-{number} format.
        :return: None
        """
        import re
        if not re.match(r'^\w{2}\*\d+$',vsid):
            raise ValueError("{0} is not a valid Vidispine library ID".format(vsid))

        self._document = self.request("library/{0}".format(vsid))
        self._settings = self.request("library/{0}/settings".format(vsid))
        try:
            self._storagerule = self.request("library/{0}/storage-rule".format(vsid))
        except HttpError as e:
            if e.response.code != 404:
                raise e

    def saveSettings(self):
        """
        Saves the current state of the object back into Vidispine. Errors are reported as HttpExceptions
        :return: None
        """
        import xml.etree.ElementTree as ET
        if self._settings is None:
            raise ValueError("No settings loaded")

        self.request("library/{0}/settings".format(self.vsid),method="PUT",
                     body=ET.tostring(self._settings.getroot(),encoding="UTF-8")
        )

    @property
    def hits(self):
        elem = self._document.find("{0}hits".format(self._xmlns))
        if elem is not None:
            return int(elem.text)
        return None

    @property
    def vsid(self):
        elem = self._settings.find("{0}id".format(self._xmlns))
        if elem is not None:
            return elem.text
        return None

    @vsid.setter
    def vsid(self,value):
        import re
        if not re.match(r'^\w{2}\*\d+$',value):
            raise ValueError("{0} is not a valid Vidispine library ID".format(value))
        elem = self._settings.find("{0}id".format(self._xmlns))
        if elem is not None:
            elem.text = value
        else:
            raise KeyError("No settings document or it does not contain <id>")

    @property
    def owner(self):
        elem = self._settings.find("{0}username".format(self._xmlns))
        if elem is not None:
            return elem.text
        return None

    @property
    def updateMode(self):
        elem = self._settings.find("{0}updateMode".format(self._xmlns))
        if elem is not None:
            return elem.text
        return None

    @updateMode.setter
    def updateMode(self,value):
        elem = self._settings.find("{0}updateMode".format(self._xmlns))
        if elem is not None:
            elem.text = value
        else:
            raise KeyError("No settings document or it does not contain <updateMode>")

    @property
    def autoRefresh(self):
        elem = self._settings.find("{0}autoRefresh".format(self._xmlns))
        if elem is not None:
            return elem.text
        return None

    @autoRefresh.setter
    def autoRefresh(self,value):
        if not isinstance(value,bool):
            raise ValueError()

        elem = self._settings.find("{0}autoRefresh".format(self._xmlns))
        if elem is not None:
            if value:
                elem.text = "true"
            else:
                elem.text = "false"
        else:
            raise KeyError("No settings document or it does not contain <autoRefresh>")

    @property
    def query(self):
        """
        Get the query section of the library definition
        :return: ElementTree document representing the library's query
        """
        elem = self._settings.find("{0}query".format(self._xmlns))
        if elem is not None:
            return elem.text
        return None