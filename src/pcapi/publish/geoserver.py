""" Module to Communicate with Geoserver's REST API. This is very COBWEB specific and is
not recomended for people who can avoid custom APIs and standards like WFS which break 
with e.g. spaces in property names or binary blobs."""

import urllib2
from pcapi import config, logtool

log = logtool.getLogger("geoserver", "pcapi.publish")

### Constants -- should be the same in all geoserver installations
# Assuming workspace and datastore are Cobweb as we don't expect to use this feature externally
ADD_LAYER_PATH = '/rest/workspaces/cobweb/datastores/cobweb/featuretypes'
PUBLISH_LAYER_PATH_TPL = '/rest/layers/cobweb:{0}'
COMPANY = 'cobweb'
DEFAULT_AUTHORITY_URL = "http://authority.cobwebproject.eu"
# Realm is used by Basic Auth in Geoserver
REALM = 'GeoServer Realm'

def message_add_layer(layer):
    """ Create the XML message for adding a new layer 
    @param layer(string): the name of the layer to add (same as database table)
    @returns : the XML string
    
    NOTE: if table does not exist in postgis you will get a 
    'no all feature attributes are defined' error because geoserver tries to 
    generate the table and needs more info.
    """
    template =  """<featureType><name>%(name)s</name></featureType>"""
    var = { "name": layer,}
    return template % var

def message_authority(company,identifier, url):
    """ Create the XML message for adding an Authority URL and Identifier to the layer
    
    @param company(string): the name of the company to use. Normally "cobweb"
    @param identifier(string): the identifier. Normally a group or session to associate it.
    @param url(string): the name of a URI for the company. Can be "http://SOME_URI"
    @returns : the XML string

    NOTE: Geoserver does not return anything when this call is made    
    """
    template = """<layer>
<enabled>true</enabled>
<metadata>
<entry key="authorityURLs">[{"name":"%(name)s","href":"%(url)s"}]</entry>
<entry
key="identifiers">[{"authority":"%(name)s","identifier":"%(id)s"}]</entry></metadata>
</layer>
"""
    var = { "name": company, "url": url, "id": identifier } 
    return template % var

def rest_request(endpoint, username, password, method, data, path):
    """ Issue a REST Request with POST or PUT
    
    @param endpoint(string): http(s)://.../geoserver endpoint
    @param username(string): username
    @param password(string): password
    @param method(string): "PUT" or "POST"
    @param data(string): XML message
    @param path(string): url path after endpoint e.g. "/rest/..."     
    """  
    auth_handler = urllib2.HTTPBasicAuthHandler()    
    auth_handler.add_password(realm=REALM,uri=endpoint,user=username,passwd=password)
    opener =  urllib2.build_opener(auth_handler)
    urllib2.install_opener(opener)
    url = endpoint + path
    r = urllib2.Request(url,headers={'Content-type': 'text/xml'} )
    if method == "PUT":
        # without this monkey-patch, urllib will always issue a POST
        r.get_method = lambda: 'PUT' 
    log.debug("Rest request: {0} {1}\n{2}".format(method, url, data))
    res = urllib2.urlopen(r,data)
    return res.read()
    

def publish(table, company, identifier,url=DEFAULT_AUTHORITY_URL):
    """ Create a layer & authority metadata for a postgis table
    
    @param company(string): the company name to add
    @param identifier(string): the identifier. 
        NOTE: This is the same as the PostGIS table!.
    @param url(string): the name of a URI for the company. Can be "http://SOME_URI"
    @returns : the XML string
"""
    log.debug("Publishing {0} as {1} and url {2}".format(COMPANY,identifier,url))
    if ( config.get("geoserver","enable") == "true"):
        endpoint = config.get("geoserver","endpoint")
        username = config.get("geoserver","username")
        password = config.get("geoserver","password")

        data = message_add_layer(identifier)
        msg = rest_request(endpoint, username, password, "POST", data, ADD_LAYER_PATH)
        log.debug("Geoserver add layer reponse: %s" % msg)
        data = message_authority("cobweb",identifier,url)
        # this call returns nothing
        rest_request(endpoint, username, password, "PUT", data, PUBLISH_LAYER_PATH_TPL.format(table))
        return msg
    log.debug("Geoserver support is disabled!")
    return None #no-op

if __name__ == "__main__":
    table = "eo"
    create_msg = message_add_layer(table)
    endpoint = config.get("geoserver","endpoint")
    username = config.get("geoserver","username")
    password = config.get("geoserver","password")
    pub_msg = message_authority("cobweb", "test-id2", DEFAULT_AUTHORITY_URL)
    print "Create: %s" % create_msg
    print "Publish: %s" % pub_msg
    print "test add layer : %s " % \
        rest_request(endpoint, username, password, "POST", create_msg, ADD_LAYER_PATH)
    print "test publish : %s " % \
        rest_request(endpoint, username, password, "PUT", pub_msg, PUBLISH_LAYER_PATH_TPL.format(table))
