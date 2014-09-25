import re
import time
from pcapi import config, logtool
from pcapi.db import tokens
from dropbox import client, session, rest
from db import tokens
from urlparse import urlsplit, urlunsplit

### Static Variables ###
APP_KEY = config.get("dropbox","app_key")
APP_SECRET = config.get("dropbox","app_secret")
ACCESS_TYPE = 'app_folder'  # should be 'dropbox' or 'app_folder' as configured for your app

STATE_CODES = {
    "verify_token": 0,
    "connected": 1,
    "non_authorized": 2
}


# CAPABILITIES that this provider supports
CAPABILITIES = [ "oauth", "search", "synchronize", "delete" ]

log = logtool.getLogger("DropboxProvider", "pcapi")
#########################

class Metadata(object):
    """ metadata of files/dir as returned from dropbox. This is plain filesystem
    metadata and NOT high-level pcapi metadata for records or editors"""

    def __init__ (self, md):
        self.md = md

    def __str__(self):
        return `self.md`

    def mtime(self, fmt=None):
        """ Return last modification time of self.
        Args:
            fmt (optional): format (s. strftime() system call) for the output date
        Returns:
         a date string in format described in "fmt" as in strftime. If no
        format is specified then seconds since unix epoch are returned. This is useful for date comparisons.

        Timezones are ignored (assuming GNT) and invalid mtimes return None
        """

        # Dropbox format. Last 5 characters are for timezone
        try:
            tm = time.strptime(self.md["modified"][:-6],"%a, %d %b %Y %H:%M:%S")
            if not fmt:
                return time.mktime(tm)
                return time.strftime(fmt,tm)
        except ValueError:
            log.exception("ValueError. Should not happen. Could not parse mtime: \n"\
                                + self.md["modified"][:-6])
            return None

    def ls(self):
        """ Contents of directory (or just the file) """
        if self.is_dir():
            return [ x["path"] for x in self.md["contents"] ]
        else:
            return self.md["path"]

    def lsdirs(self):
        """ list only directories """
        if self.is_dir():
            return [ x["path"] for x in self.md["contents"] if x["is_dir"] == True ]
        else:
            return []

    def path(self):
        """ return path of file/dir """
        return self.md["path"]

    def is_dir(self):
        return self.md["is_dir"]


class DropboxProvider(object):
    """ Create and control Dropbox sessions using oAuth protocol. Sessions are stored
    in the database table "tokens".

    Use one of the login or load methods to initialise the class as python
    does not have multiple constructors

    """

    def __init__(self):
        # This is sent to clients to let them know which state this object is in.
        self.state = {
                "url": "",
                "req_key": "",
                "state" : STATE_CODES["verify_token"]
            }


    def login(self, req_key=None, callback=None, async=False):
        """ Create a URL which the browser can use to verify a token and redirect to webapp.

        Args:
            req_key : request key (not secret!), cached by session cookie (optional)
            callback : where to redirect the browser after login
            async: if async polling is used

        Returns:
            None: if connection is already established (from cookie) or
            URL: a URL to authorize the token

        Raises:
            rest.ErrorResponse
        """
        self.sess = session.DropboxSession(APP_KEY, APP_SECRET, access_type=ACCESS_TYPE)
        self.api_client = client.DropboxClient(self.sess)

        #check if user has request token.
        if (req_key):
            log.debug("User has a token: " + req_key)
            # check if a req token has an access pair
            accesspair = tokens.get_access_pair(req_key)
            if not accesspair:
                req_tuple = tokens.get_request_pair(req_key)
                # if we have a req_tuple, assume it is a callback request to obtain access token
                if (req_tuple):
                    log.debug("Assumming callback within login")
                    #only works if request token is verified
                    self.sess.set_request_token(req_tuple[0], req_tuple[1])
                    try:
                        ap = self.sess.obtain_access_token()
                    except rest.ErrorResponse as e:
                        return { "state" : STATE_CODES["connected"], "msg": "Dropbox error: %s" % `e` }
                    accesspair = [ap.key , ap.secret]
                    # and save
                    tokens.save_access_tokens(req_tuple[0], req_tuple[1], accesspair[0], accesspair[1] )
                    log.debug("TOKEN[%s] -> %s" %(req_key, `accesspair`))
            # check if token has credentials associate with it
            if accesspair :
                #ipdb.set_trace()
                self.sess.set_token(*accesspair)

        #if we don't have a sessions get a URL for authn
        if (not self.sess.is_linked()):
            log.debug("Session not linked -- Creating new session")
            self.request_token = self.sess.obtain_request_token()
            # If we are using async include the userid in the callback
            if async:
                url = urlsplit(callback)
                mod_path = '%s/%s' % (url.path, self.request_token.key)
                callback = urlunsplit((url.scheme, url.netloc, mod_path,
                                       url.query, url.fragment))

            url = self.sess.build_authorize_url(self.request_token, callback)
            self.state = { "url" : url , "userid" : self.request_token.key , "state" : STATE_CODES["verify_token"] }
            tokens.save_unverified_request( self.request_token.key, self.request_token.secret )
        else:
            self.state = { "state" : STATE_CODES["connected"], "name": self.account_info()["display_name"]}
        return self.state

    def revoke(self, req_key):
        """ Revoke the request key
            Args: req_key
        """
        tokens.delete_unverified_request(req_key)


    def probe(self, req_key):
        """ Check if req_key has associated access key.
            Only use this when polling for the first time otherwise you may get false positives for
            stored credentials that have expired.
        """
        if tokens.get_access_pair(req_key):
            self.state = { "state" : STATE_CODES["connected"] }
        elif tokens.get_request_pair(req_key):
            self.state = { "state" : STATE_CODES["verify_token"] }
        else:
            self.state = { "state" : STATE_CODES["non_authorized"] }

        return self.state

    def upload(self,name, fp, overwrite=False):
        """ Upload the media file `uuid'
        Args:
            name (str): destination path of file in sandbox with directories
                        created on-the-fly e.g. "/foo.jpg" for apps/pcapi/foo.jpg
            fp (File): the file object to upload.
            overwrite (bool): whether to overwrite the file or save under a new name

        Returns: Dictionary of Metadata of uploaded file.
                 see also https://www.dropbox.com/developers/reference/api#metadata-details

        Raises:
            rest.ErrorResponse
        """
        log.debug("uploading file: " + name)
        #log.debug("with tokens: " + logtool.pp(tokens.dump_tokens()) )
        metadata = self.api_client.put_file(name, fp, overwrite )
        try:
            fp.close()
        except Exception as e:
            log.debug(str(e))
        return Metadata(metadata)

    def exists(self, path):
        """ Check if path exists """
        return True # not used

    def mkdir(self, path):
        """ Wrapper call around create_folder. Returns metadata.
        If folder already exists we have to implement to "new file name" algorithm for
        folders since dropbox does not support creating new folders with different names.
        """
        try:
            metadata = self.api_client.file_create_folder(path)
            return Metadata(metadata)
        except rest.ErrorResponse as e:
            log.debug(e.status)
            if e.status == 503:
                log.debug(e.headers)
                time.sleep(1)
                self.mkdir(path)
            if e.status == 403:
                # File already exists. Find the next filename (XXX) available
                # by calling this function recursively. (Can be much faster
                # by first checking the results of ls before doing the recursion)
                numlist = re.findall(".* \(([0-9]*)\)$",path)
                if numlist:
                    num = numlist[0]
                    newpath = path[:path.rfind(num)-2] + " (%d)" % ( int(num) + 1 )
                else:
                    newpath = path + " (1)"
                log.debug("mkdir(): folder collisions. Trying new name: %s" % newpath)
                return self.mkdir(newpath)
            else:
                raise e

    def move(self, path1, path2):
        """ Wrapper call around create_folder. Returns metadata.
        If folder already exists we have to implement to "new file name" algorithm for
        folders since dropbox does not support creating new folders with different names.
        """
        log.debug("move")
        try:
            metadata = self.api_client.file_move(path1, path2)
            return Metadata(metadata)
        except rest.ErrorResponse as e:
            if e.status == 403:
                # File already exists. Find the next filename (XXX) available
                # by calling this function recursively. (Can be much faster
                # by first checking the results of ls before doing the recursion)
                numlist = re.findall(".* \(([0-9]*)\)$",path2)
                if numlist:
                    num = numlist[0]
                    newpath = path2[:path2.rfind(num)-2] + " (%d)" % ( int(num) + 1 )
                else:
                    newpath = path2 + " (1)"
                log.debug("move(): folder collisions. Trying new name: %s" % newpath)
                return self.move(path1, newpath)
            else:
                raise e

    def search(self, path, word):
        """
        search for paths
        """
        log.debug("search in %s for %s" % (path, word))
        return Metadata(self.api_client.search(path=path, query=word))

    def media(self,path):
        """ Create external dropbox url link for sharing
        Args:
            name (str): destination path of file in sandbox with directories created on-the-fly e.g. "/foo.jpg" for apps/pcapi/foo.jpg

        Returns: Dictionary with url and expiration data e.g. {'url': 'http://www.dropbox.com/s/m/a2mbDa2', 'expires': 'Thu, 16 Sep 2011 01:01:25 +0000'}

        Raises:
            rest.ErrorResponse
        """
        log.debug("Creating share for " + path)
        res = self.api_client.media(path)
        return res

    def account_info(self):
        """ pass-through method """
        return self.api_client.account_info()

    def sync(self, cursor=None):
        """ Converts dropbox's sync response to a json object with modified,
            created and deleted files.
        """
        sync_raw = self.api_client.delta(cursor)
        # If we don't have a cursor create a new one
        updated = []
        deleted = []
        if not cursor:
            return { "cursor" : sync_raw["cursor"] }
        # Else just return { "updated" : ...  , "deleted": .. }
        for f,m in sync_raw["entries"]:
            if m == None:
                deleted.append(f)
            else:
                updated.append(f)
        return { "updated": updated, "deleted": deleted }

    def file_delete(self,path):
        """ Delete file and return parsed metadata"""
        res = self.api_client.file_delete(path)
        return Metadata(res)

    def get_file_httpresponse(self, from_path, rev=None):
        """ Raw response as per REST API.
        """
        http_response =  self.api_client.get_file(from_path, rev)
        return http_response

    def get_file_and_metadata(self, from_path, rev=None):
        """ Pass-through method

        Returns:
            Tuple containing HttpResponse as well as parsed metadata as a dict.
            (s. upstream docs)
        """
        httpres, raw_md = self.api_client.get_file_and_metadata(from_path, rev)
        return httpres, Metadata(raw_md)

    def metadata(self,name):
        """ Return parsed metadata for file or folder (using the Metadata object)
        """
        res = self.api_client.metadata(name)
        return Metadata(res)

    def callback(self, req_key):
        """ Call this when authentication has been established with browser.
        This will save the credentials for future use.
        Supply request_token to lookup object credentials from previous
        authentication.

        Returns:
            the request key (aka cookie to set to browser)

        Raises:
            rest.ErrorResponse: e.g. 'Token is disabled or invalid'
        """
        req_tuple = tokens.get_request_pair(req_key)
        self.sess = session.DropboxSession(APP_KEY, APP_SECRET, access_type=ACCESS_TYPE)
        self.api_client = client.DropboxClient(self.sess)
        self.sess.set_request_token(req_tuple[0], req_tuple[1])
        acc_pair = self.sess.obtain_access_token() #only works if request token is verified
        tokens.save_access_tokens(req_tuple[0], req_tuple[1], acc_pair.key, acc_pair.secret )
        log.debug( "DELETE: saving: " + `(req_tuple[0], req_tuple[1], acc_pair.key, acc_pair.secret )`)
        return req_key
