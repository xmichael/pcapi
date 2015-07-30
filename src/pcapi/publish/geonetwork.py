""" Module to Communicate with Geonetworks's REST API. This is very COBWEB specific and is
not recomended for people who can avoid custom APIs"""

import urllib2, json, base64, threading
from pcapi import config, logtool

log = logtool.getLogger("geoserver", "pcapi.publish")

# make sure this is global for all threads (obviously)
lock = threading.Lock()


class Surveys:
    def __init__ (self, surveys):
        """ API to access the contents of the geonetwork response """
        # raw surveys resposne from geonetwork
        self._surveys = surveys
        # parsed summary of _surveys as an array of
        # [ {"sid", "coordinator", "title"} ...
        self._summary = []

        # create a summary of surveys as an array of [ sid, coordinator uid, title ]
        self.count = int(self._surveys["summary"]["@count"])
        if self.count == 0:
            return # empty surveys -- no point
        if self.count == 1: # geonetwork bug -- object instead of array for count==1
            s = self._surveys["metadata"]
            self._summary =  [ \
                { "sid": s["geonet:info"]["uuid"], 
                  "coordinator" : s["userinfo"].split('|')[0], 
                  "title" : s["title"] } ,]
        if self.count > 1:
            for s in self._surveys["metadata"]:
                self._summary.append( { "sid": s["geonet:info"]["uuid"],
                  "coordinator" : s["userinfo"].split('|')[0],
                  "title" : s["title"] })
        
    def get_summary(self):
        """ Return     # parsed summary of _surveys as an array of
        [ {"sid", "coordinator", "title"} ... 
        """
        return self._summary
        
    def get_raw_surveys(self):
        """ return the parsed geoserver resposne """
        return self._surveys
    
    def get_survey(self, sid):
        """ @returns
                {"coordinator", "title"} of survey
                None: survey id not found
        """
        for s in self._summary:
            if s["sid"] == sid:
                return { "coordinator" : s["coordinator"] , "title": s["title"] }
        return None

    def get_summary_ftopen(self):
        """return summary in a format appropriate for FTOpen i.e.
        {
            "metadata": [ "b29c63ae-adc6-4732", "c8942133-22ce-4f93" ],
            "names": ["Another Woodlands Survey", "Grassland survey"]
        }
        """
        # use a dict/set instead of list to prune crazy GN duplicate values(!)
        
        summary_set = {}
        log.debug("Surveys from GeoNetwork are:")
        log.debug("summary is:")
        log.debug(logtool.pp(self._summary))
        if (self.count == 0):
            return { "msg" : "No surveys found", "error" : 1}
        log.debug("Survey Count (from GN) was stated to be: " + str(self.count))
        for s in self._summary:
            summary_set[ s["sid"] ] = s["title"]
        return { "metadata": summary_set.keys() , "names": summary_set.values() , "error": 0}

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
    @returns : A class that represents all the surveys found or None
    """
    log.debug("Quering surveys for {0}".format(uid))
    endpoint = config.get("geonetwork","endpoint")
    username = config.get("geonetwork","username")
    password = config.get("geonetwork","password")

    # just in case, since urllib2 is not threadsafe according to docs
    with lock:
        msg = msg_get_surveys(uid)
        resj = get_request(endpoint, username, password, msg)
        res = json.loads(resj)

    return Surveys(res)
    
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
    all_surveys = get_surveys(uid)
    print "Original response:"
    print logtool.pp(all_surveys.get_raw_surveys())
    print "Parsed surveys are:"
    print logtool.pp(all_surveys.get_summary())
    print "FTOpen format:"
    print logtool.pp(all_surveys.get_summary_ftopen())
