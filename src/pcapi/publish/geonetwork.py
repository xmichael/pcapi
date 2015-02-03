""" Module to Communicate with Geonetworks's REST API. This is very COBWEB specific and is
not recomended for people who can avoid custom APIs"""

import urllib2, json, base64
from pcapi import config, logtool

log = logtool.getLogger("geoserver", "pcapi.publish")


def msg_get_surveys(uid):
    """ Create the get request for fetching all surveys a users is registered for. 
    @param uid(string): the SAML UUID of the user
    @returns : the GET url to be appended to the endpoint
    """
    res =  "type=survey&to=100&fast=index&_content_type=json&_participant=%s" % uid
    return res
    
class PreemptiveBasicAuthHandler(urllib2.BaseHandler):
    """ Geonetwork basic auth does issue password challenges (!) so we must send out
    the credentials for every request"""
    def __init__(self, password_mgr=None):
            if password_mgr is None:
                    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            self.passwd = password_mgr
            self.add_password = self.passwd.add_password
    def http_request(self,req):
            uri = req.get_full_url()
            user, pw = self.passwd.find_user_password(None,uri)
            #log.debug('ADDING REQUEST HEADER for uri (%s): %s:%s',uri,user,pw)
            if pw is None: return req

            raw = "%s:%s" % (user, pw)
            auth = 'Basic %s' % base64.b64encode(raw).strip()
            req.add_unredirected_header('Authorization', auth)
            return req

def get_request(endpoint, username, password, path):
    """ Issue a GET request
    
    @param endpoint(string): http(s)://.../geoserver endpoint
    @param username(string): username
    @param password(string): password
    @param path(string): request after "?" e.g. "foo=bar&..."     
    """  
    auth_handler = PreemptiveBasicAuthHandler()    
    auth_handler.add_password(realm=None,uri=endpoint,user=username,passwd=password)
    opener =  urllib2.build_opener(auth_handler)
    urllib2.install_opener(opener)
    url = endpoint + path
    log.debug("geonetwork request: GET {0}".format(url))
    r = urllib2.Request(url)
    res = urllib2.urlopen(r)
    return res.read()
    

def get_surveys(uid):
    """ fetching all surveys a users is registered for. 
    @param uid(string): the SAML UUID of the user
    @returns : the surveys as a dictionary
    """
    log.debug("Quering surveys for {0}".format(uid))
    endpoint = config.get("geonetwork","endpoint")
    username = config.get("geonetwork","username")
    password = config.get("geonetwork","password")

    msg = msg_get_surveys(uid)
    resj = get_request(endpoint, username, password, msg)
    res = json.loads(resj)

    surveys = []
    for s in res["metadata"]:
        surveys.append([ s["source"], s["userinfo"], s["title"] ])
    return surveys

if __name__ == "__main__":
    """USAGE: ./geonetwork.py UUID """
    import sys
    if (len(sys.argv) != 2):
        print  """USAGE: python geonetwork.py UUID """
        sys.exit(1)
    #print logs
    def dbg(x):
        print(x)
    log.debug = dbg

    uid = sys.argv[1]
    create_msg = msg_get_surveys(uid)
    endpoint = config.get("geonetwork","endpoint")
    username = config.get("geonetwork","username")
    password = config.get("geonetwork","password")
    msg = msg_get_surveys(uid)
    resj = get_request(endpoint, username, password, msg)
    res = json.loads(resj)
    print "Parsed resposne was:"
    print(logtool.pp(res))
    surveys = get_surveys(uid)
    print "Parsed surveys are:"
    print(logtool.pp(surveys))
