import csv
import json
import os
import re
import simplekml
import sys
import tempfile
import uuid
import urllib2
import time
import zipfile

from bottle import Response, abort
from StringIO import StringIO
from operator import itemgetter
from wand.image import Image

try:
    import threadpool
except ImportError:
    sys.stderr.write("Error: Can't find threadpool...")

from pcapi import ogr, dbox_provider, fs_provider, logtool, config
from pcapi.form_validator import FormValidator, Editor
from pcapi.cobweb_parser import COBWEBFormParser
from pcapi.exceptions import DBException, FsException
from pcapi.publish import postgis, geonetwork

log = logtool.getLogger("PCAPIRest", "pcapi")
#global number of threads
default_number=20

class Record(object):
    """ Class to store record bodies and metadata in memory for fast access"""
    def __init__(self, content, metadata ):
        self.content = content # as a parsed json (dict)
        self.metadata = metadata # as a dbox_provider.Metadata object

################ Decorators ####################
def authdec():
    def decorator(f):
        def wrapper(*args, **kwargs):
            log.debug('%s( *%s )' % (f.__name__, `args`))
            dbox = dbox_provider.DropboxProvider()
            status = dbox.probe(args[1])
            # check access token *existence*
            if ( status["state"] != dbox_provider.STATE_CODES["connected"] ):
                return { "error": 1 , "msg": "Invalid Session. Relogin"}
            else:
                status = dbox.login(args[1])
                # check access token validity
                if ( status["state"] != dbox_provider.STATE_CODES["connected"] ):
                    return { "error": 1 , "msg": "Bad access token. Relogin!"}
            try:
                wrapper.__doc__ = f.__doc__
                kwargs["dbox"] = dbox
                return f(*args, **kwargs)
            except Exception as e:
                log.exception("Exception: " + str(e))
                return {"error":1 , "msg": str(e)}
    return decorator

class PCAPIRest(object):
    """ REST part of the API. Return values should be direct json """

    def __init__(self, request, response):
        self.request = request
        self.response = response
        self.provider = None
        self.rec_cache = []

    def capabilities(self):
        # TODO: configure under a providerFactory once we have >2 providers
        return { \
          "dropbox" : ["oauth", "search", "synchronize", "delete"], \
          "local" : ["search", "synchronize", "delete"] \
        }

    def auth(self, provider, userid):
        """ Resume session using a *known* userid:
            - If successful, initialiaze PCAPI provider object at "self.provider" and return None
            - otherwise return json response describing error

            Arguments:
                provider (string): provider to use
                userid (string): user id to resume
            Returns:
                Error message or None if successful
        """
        #provider is already initialised; ignore
        if self.provider != None:
            return None
        log.debug("auth: resuming %s %s" % (provider, userid) )
        if (provider == "dropbox"):
            self.provider = dbox_provider.DropboxProvider()
            status = self.provider.probe(userid)
            # check access token *existence*
            if ( status["state"] != dbox_provider.STATE_CODES["connected"] ):
                return { "error": 1 , "msg": "Invalid Dropbox Session. Relogin"}
            else:
                status = self.provider.login(userid)
                # check access token validity
                if ( status["state"] != dbox_provider.STATE_CODES["connected"] ):
                    return { "error": 1 , "msg": "Bad access token. Relogin!"}
        elif (provider == "local"):
            # on auth necessary for local
            try:
                self.provider = fs_provider.FsProvider(userid)
            except FsException as e:
                return {"error": 1, "msg": str(e) }
        else:
            return { "error" : 1, "msg" : "provider %s not supported!" % `provider` }
        return None # Success!


    def create_records_cache(self, provider, path):
        """ Creates an array of Records classed (s.a.) after parsing all records under `path'.
        Assumes a valid session """
        records = []

        # If we are in `/' then get all records
        for d in self.provider.metadata(path).lsdirs():
            recpath = d + "/record.json"
            log.debug(recpath)
            records.append(recpath)
        requests = threadpool.makeRequests(self.records_worker, records, self.append_records_cache, self.handle_exception)

        #insert the requests into the threadpool

        # This is ugly but will need serious refactoring for the local provider.
        # basically: if using local storage then just use one thread to avoid choking on the HD.
        # For dropbox and other remote providers use multi-theading
        if ( provider == "local" ):
            pool = threadpool.ThreadPool(1)
        else:
            pool = threadpool.ThreadPool(min(len(requests), default_number))
        for req in requests:
            pool.putRequest(req)
            log.debug("Work request #%s added." % req.requestID)

        #wait for them to finish (or you could go and do something else)
        pool.wait()
        pool.dismissWorkers(min(len(requests), 20), do_join=True)
        log.debug("workers length: %s" % len(pool.workers))

    def records_worker(self, recpath):
        log.debug("Parsing records -- requesting " + recpath)
        folder = re.split("/+", recpath)[2]
        try:
            buf, meta = self.provider.get_file_and_metadata(recpath)
            rec = json.loads(buf.read())
            record = {}
            record[folder] = rec
            log.debug(record)
        except Exception as e:
            log.exception("Exception: " + str(e))
            #rec = json.loads( json.dumps({}) )
            buf.close()
            return None
        buf.close()
        #return Record(rec, meta)
        return Record(record, meta)

    def append_records_cache(self, request, result):
        log.debug("result is %s" % result)
        if result is not None:
            self.rec_cache.append(result)

    def handle_exception(self, request, exc_info):
        if not isinstance(exc_info, tuple):
            # Something is seriously wrong...
            log.debug(request)
            log.debug(exc_info)
            raise SystemExit
        log.debug( "**** Exception occured in request #%s: %s" % \
          (request.requestID, exc_info))


    def check_init_folders(self, path):
        log.debug("check %s" % path)
        if path == "editors/" or path == "records/":
            log.debug("creating " + path)
            self.provider.mkdir(path)
            return True
        return False

    def assets(self, provider, userid, path, flt):
        """
            Update/Overwrite/Create/Delete/Download records.

        """
        log.debug('records( %s, %s, %s, %s)' % (provider, userid, path, str(flt)) )
        error = self.auth(provider,userid)
        if (error):
            return error

        if self.request.method == "GET":
            self.create_records_cache(provider, "records/")
            records_cache = self.filter_data("media", path, userid)
            if str(flt) == "zip":
                self.response.headers['Content-Type'] = 'application/zip'
                self.response.headers['Content-Disposition'] = 'attachment; filename="download.zip"'
                response_data = None
                log.debug(type(records_cache))
                try:
                    f = open(records_cache, "r")
                    try:
                        # Read the entire contents of a file at once.
                        response_data = f.read()
                    finally:
                        f.close()
                except IOError:
                    pass
                return response_data
            bulk = [ r.content for r in records_cache ]
            return {"records": bulk, "error": 0 }


    def records(self, provider, userid, path, flt, ogc_sync):
        """
            Update/Overwrite/Create/Delete/Download records.

        """
        log.debug('records( %s, %s, %s, %s, %s)' % (provider, userid, path, str(flt), str(ogc_sync) ))
        error = self.auth(provider,userid)
        if (error):
            return error

        path = "/records/" + path
        try:
            recordname_lst = re.findall("/records//?([^/]*)$", path)
            if recordname_lst:
                if self.request.method == "PUT":
                    ## NOTE: Put is *not* currently used by FTOPEN
                    res = self.fs(provider, userid, path)
                    if res['error'] == 0 and ogc_sync:
                        return { "error":1, "msg":"ogc_sync is not supported for PUT. Use GET after uploading the record/assets the normal way"}
                    return res
                if self.request.method == "POST":
                    ## We are in depth 1. Create directory (or rename directory) and then upload record.json
                    md = self.provider.mkdir(path)
                    # check path is different and add a callback to update the record's name
                    if ( md.path() != path ):
                        ### moved a myrecord/record.json to a new folder anothername/record.json
                        newname = md.path()[md.path().rfind("/") + 1:]
                        def proc(fp):
                            j = json.loads(fp.read())
                            j["name"]=newname
                            log.debug("Name collision. Renamed record to: " + newname)
                            return StringIO(json.dumps(j))
                        cb = proc
                    else:
                        cb = None
                    path = md.path() + "/record.json"
                    res = self.fs(provider, userid, path, cb)

                    # Sync to PostGIS database after processing with self.fs()
                    # (Path resolution already done for us so we can just put/overwrite the file)
                    # --- disabled as we assuming ftOpen issues GET request with ?ogc_sync=true *after* uploading the record
                    if res['error'] == 0 and ogc_sync:
                        return { "error":1, "msg":res['msg'] + " -- NOTE: ogc_sync is not supported for POST. Use GET after uploading the record/assets the normal way"}
                    return res
                if self.request.method == "DELETE":
                    ### DELETE refers to /fs/ directories
                    res =  self.fs(provider,userid,path)
                    # Sync to PostGIS database if required
                    if res['error'] == 0 and ogc_sync:
                        postgis.delete_record(provider, userid, path)
                    return res
                if self.request.method == "GET":
                    # Check if empty path
                    if path == "/records//" and not self.provider.exists(path):
                        log.debug("creating non-existing records folder")
                        self.provider.mkdir("/records")
                    ### GET /recordname returns /recordname/record.json
                    if recordname_lst[0] != "":
                        ### !!! ogc_sync publishes records to database and returns status
                        if ogc_sync:
                            res = postgis.put_record(provider, userid, path)
                            return res
                        ###
                        return self.fs(provider,userid,path + "/record.json")
                    ### Process all filters one by one and return the result
                    filters = flt.split(",") if flt else []
                    #records_cache = self.create_records_cache(path) <--- WHAT IS THAT???
                    self.create_records_cache(provider, path)
                    ### GET / returns all records after applying filters
                    ### Each filter bellow will remove Records from records_cache
                    records_cache = self.filter_data(filters, None, userid)
                    # End of Filters... return all that's left
                    if "format" in filters:
                        return records_cache
                    bulk = [ r.content for r in records_cache ]
                    return {"records": bulk, "error": 0 }
            elif re.findall("/records//?[^/]+/[^/]+$",path):
                # We have a depth 2 e.g. /records/myrecord/image.jpg. Behave like
                # normal /fs/ for all METHODS
                return self.fs(provider,userid,path)
            else:
                # allowed only : // , /dir1, /dir1/fname   but NOT /dir1/dir2/dir2
                return { "error": 1, "msg": "Path %s has subdirectories, which are not allowed" % path}
        except Exception as e:
                log.exception("Exception: " + str(e))
                return {"error":1 , "msg": str(e)}

    def surveys(self, provider, userid, sid):
        """ This is the new version of editors API for COBWEB which will eventually 
        replace /editors/.
       
        GET /surveys/local/UUID
        A GET request for all editors (path=/) will query geonetwork and return 
        all surveys with their names eg.
        {
            "metadata": [ "b29c63ae-adc6-4732", "c8942133-22ce-4f93" ],
            "names": ["Another Woodlands Survey", "Grassland survey"]
        }
        
        GET /surveys/local/UUID/SURVEYID
        Will return the survey (editor) file contents after querying geonetwork for it
        """
        log.debug('survey({0}, {1}, {2})'.format(provider, userid, sid))

        surveys = geonetwork.get_surveys(userid)
        
        if not sid:
            # Return all registered surveys
            return surveys.get_summary_ftopen()
        else:
            # Return contents of file
            s = surveys.get_survey(sid)
            if not s: # no survey found
                return { "error": 1 , "msg": "User is not registered for syrvey %s" % sid}
            res = self.fs(provider,s["coordinator"],"/editors/%s.edtr" % sid)
            # special case -- portal has survey but coordinator has not created it using Authoring Tool
            #if isinstance(res,dict) and res["msg"].startswith("[Errno 2] No such file or"):
            #    abort(404, "No survey found. Did you create a survey using the Authoring Tool?")
            return res
        return {"error":1, "msg":"Unexpected error" }

    def editors(self, provider, userid, path, flt):
        """ Normally this is just a shortcut for /fs/ calls to the /editors directory.
        
        A GET request for all editors (path=/) should parse each editor and
        return their names (s.a. documentation).
        
        When called with public=true, then PUT/POST requests will also apply to 
        the public folder (as defined in pcapi.ini).

        In the future this call will be obsolete by surveys. We are keeping this
        for compatibility with non-COBWEB users who don't want to depend on geonetwork,
         SAML overrides, geoserver etc.
        """
        
        error = self.auth(provider,userid)
        if (error):
            return error

        # Convert editor name to local filesystem path
        path = "/editors/" + path

        if path == "/editors//" and not self.provider.exists(path):
            log.debug("creating non-existing editors folder")
            self.provider.mkdir("/editors")
        # No subdirectories are allowed when accessing editors
        if re.findall("/editors//?[^/]*$",path):
            res = self.fs(provider,userid,path,frmt=flt)
            
            # If "GET /editors//" is reguested then add a "names" parameter
            if path == "/editors//" and res["error"] == 0 and provider == "local" \
                and self.request.method == "GET":
                log.debug("GET /editors// call. Returning names:")
                names = []
                for fname in res["metadata"]:
                    try:
                        fpath = self.provider.realpath(fname)
                        with open (fpath) as f:
                            parser = COBWEBFormParser(f.read())
                            names.append( parser.get_survey() )
                    # Catch-all as a last resort
                    except Exception as e:
                        log.debug("Exception parsing %s: " % fpath + `e`)
                        log.debug("*FALLBACK*: using undefined as name")
                        names.append(None)
                log.debug(`names`)
                res["names"] = names
                
                # we convert /editors//XXX.whatever as XXX.whatever
                # TODO: when editors become json, put decision trees inside the editor file
                # and remove all filename extensions (like in /surveys/)
                res["metadata"] = [ re.sub(r'/editors//?(.*)', r'\1', x) for x in res["metadata"] ]

            ## If public==true then execute the same PUT/POST command to the 
            ## public UUID (s. pcapi.ini) and return that result
            elif provider == "local" and \
            ( self.request.method == "PUT" or self.request.method == "POST"):
                try:
                    public = self.request.GET.get("public")
                    if public == "true":
                        log.debug("Mirroring command to public uid: ")
                        self.provider.copy_to_public_folder(path)
                except Exception as e:
                    if res.has_key("msg"):
                        res["msg"] + "  PUBLIC_COPY: " + e.message
            return res
        return { "error": 1, "msg": "Path %s has subdirectories, which are not allowed" % path}

    def layers(self, provider, userid, path):
        """ High level layer (overlay) functions. Normally it is a shortcut to 
        /fs/ for the /layers folder.

        When called with public=true, then ALL requests will also apply to 
        the public folder (as defined in pcapi.ini).

        """        
        log.debug('layers(%s, %s, %s)' % (provider, userid, path) )

        error = self.auth(provider, userid)
        if (error):
            return error

        path = "/layers/" + path
        # No subdirectories are allowed when accessing layers
        if re.findall("/layers//?[^/]*$",path):
            res = self.fs(provider,userid,path)
            ## If public==true then execute the same command to the 
            ## public UUID (s. pcapi.ini) and return that result
            try:
                public = self.request.GET.get("public")
                if public == "true":
                    log.debug("Mirroring command to public uid: ")
                    self.provider.copy_to_public_folder(path)
            except Exception as e:
                if res.has_key("msg"):
                    res["msg"] + "  PUBLIC_COPY: " + e.message
            return res
        return { "error": 1, "msg": "Path %s has subdirectories, which are not allowed" % path}

    def fs(self, provider, userid, path, process=None, frmt=None):
        """
            Args:
                provider: e.g. dropbox
                userid: a registered userid
                path: path to a filename (for creating/uploading/querying etc.)
                process (optional) : callback function to process the uploaded
                    file descriptor and return a new file descriptor. This is
                    used when extra content specific processing is required e.g.
                    when record contents should be updated if there is a name
                    conflict.
        """
        #url unquote does not happend automatically
        path = urllib2.unquote(path)
        
        log.debug('fs( %s, %s, %s, %s, %s)' % (provider, userid, path, process, frmt) )

        #TODO: make a ProviderFactory class once we have >2 providers
        error = self.auth(provider, userid) #initializes self.provider
        if (error):
            return error

        method = self.request.method

        log.debug("Received %s request for userid : %s" % (method,userid));
        try:

            ######## GET url is a directory -> List Directories ########
            if method=="GET":
                md = self.provider.metadata(path)
                if md.is_dir():
                    msg = md.ls()
                    return { "error": 0, "metadata" : msg}
                ## GET url is a file -> Download file stream ########
                else:
                    #check here if there is an image part of and if image exists in dropbox
                    httpres, metadata = self.provider.get_file_and_metadata(path)
                    log.debug(metadata)
                    body = httpres.read()
                    headers = {}
                    if (provider == "local"):
                        return Response(body=body, status='200 OK', headers=headers)
                    #DROPBOX-specific error checks for editors and records.
                    #TODO: Move outside /fs/ e.g. GET for /records/...
                    else:
                        for name, value in httpres.getheaders():
                            if name != "connection":
                                self.response[name] = value
                                headers[name] = value
                        log.debug(headers)
                        if not "editors" in path:
                            log.debug("not editors")
                            if "image-" in body or "audio-" in body:
                                log.debug("asset in record")
                                obj = json.loads(body)
                                log.debug(obj)
                                for field in obj["properties"]["fields"]:
                                    if "image-" in field["id"] or "audio-" in field["id"]:
                                        res = self.provider.search(path.replace("record.json", ""), field["val"])
                                        log.debug(len(res.md))
                                        if len(res.md) == 0:
                                            log.debug("no such a file in dbox")
                                            self.response.status = 409
                                            return { "error": 1, "msg" : "The record is incomplete!"}
                            #return httpres
                            return Response(body=body, status='200 OK', headers=headers)
                        else:
                            #body = httpres.read()
                            validator = FormValidator(body)
                            if validator.validate():
                                log.debug("valid html5")
                                if frmt == 'android':
                                    log.debug('it s an android')
                                    parser = COBWEBFormParser(body)
                                    body = parser.extract()
                                return Response(body=body, status='200 OK', headers=headers)
                            else:
                                log.debug("non valid html5")
                                self.response.status = 403
                                return { "error": 1, "msg" : "The editor is not valid"}
            ######## PUT -> Upload/Overwrite file using dropbox rules ########
            if method=="PUT":
                fp = self.request.body
                md = self.provider.upload(path, fp, overwrite=True)
                return { "error": 0, "msg" : "File uploaded", "path":md.ls()}
            ######## POST -> Upload/Rename file using dropbox rules ########
            if method=="POST":
                # POST needs multipart/form-data because that's what phonegap supports (but NOT dropbox)
                data = self.request.files.get('file')
                if data != None:
                    log.debug("data not None")
                    # if process is defined then pipe the body through process
                    log.debug(data.filename)
                    if data.filename.lower().endswith(".jpg") or data.filename.lower().endswith(".jpeg"):
                        body = data.file.read()
                        fp = StringIO(body) if not process else process(data.file)
                        paths = path.split(".")
                        #give a new name to the resized image <name>_res.<extension>
                        new_path = paths[0]+"_orig"+"."+paths[1]
                        thumb_path = paths[0]+"_thumb"+"."+paths[1]
                        md = self.provider.upload(new_path, fp )
                        self.resizeImage(body, path)
                        self.createThumb(body, thumb_path)
                    else:
                        fp = StringIO(data.file.read()) if not process else process(data.file)
                        md = self.provider.upload(path, fp )
                    return { "error": 0, "msg" : "File uploaded", "path":md.ls()}
                else:
                    log.debug("data is None")
                    # if process is defined then pipe the body through process
                    fp = self.request.body if not process else process(self.request.body)
                    md = self.provider.upload(path, fp, overwrite=False)
                    return { "error": 0, "msg" : "File uploaded", "path":md.ls()}
            ####### DELETE file ############
            if method=="DELETE":
                md = self.provider.file_delete(path)
                return { "error": 0, "msg" : "%s deleted" % path}
            else:
                return { "error": 1, "msg": "invalid operation" }
        except Exception as e:
            # userid is probably invalid
            if not self.check_init_folders(path):
                log.exception("Exception: " + str(e))
            return {"error":1 , "msg": str(e)}

    def export(self, provider, userid, path):
        """ Return a globally accessible URL for the file specified by path.
        """
        log.debug('export(%s, %s, %s)' % (provider, userid, path) )
        error = self.auth(provider, userid)
        if (error):
            return error
        # export public url:
        try:
            media = self.provider.media(path)
            # WARNING: Convert https to http which is allowed and used for non-http pages that embed exported files
            res = { "error":0, "url": media["url"].replace("https://","http://") , "expires" : media["expires"], \
            "msg":"Operation successful" }
        except Exception as e:
            log.exception("Exception: " + str(e))
            res =  {"error":1 , "msg": str(e)}
        return res


    def sync(self, provider, userid, cursor):
        log.debug('sync( %s, %s, %s)' % (userid,provider,`cursor`))
        error = self.auth(provider, userid)
        if (error):
            return error
        try:
            sync_res = self.provider.sync(cursor)
            sync_res["error"] = 0
            return sync_res
        except Exception as e:
            log.exception("Exception: " + str(e))
            return {"error":1 , "msg": str(e)}

    def login(self,provider,userid=None):
        log.debug("URL: " + self.request.url)
        # Get optional "async", "oath_token" parameters otherwise assume None
        async = True if self.request.GET.get("async", None) == "true" else False
        # oauth_token is  only for "callback" i.e. when the request is coming from dropbox
        oauth_token = self.request.GET.get("oauth_token",None)
        not_approved = True if self.request.GET.get("not_approved", None) == "true" else False
        callback = self.request.GET.get("callback",False)
        callback = self.request.url if async else callback
        log.debug("provider: %s, async: %s, oauth_token: %s, userid: %s, callback: %s" % \
            (provider,async,oauth_token, userid, `callback`) )
        log.debug("host: %s, port: %s" % \
            ( self.request.environ.get("SERVER_NAME", "NONE") , self.request.environ.get("SERVER_PORT") ) )
        if ( provider == "local" ):
            # Local provider has no login yet. It just generates uuids
            if (not userid):
                userid =  uuid.uuid4().hex
            provider = fs_provider.FsProvider(userid)
            res = provider.login()
            log.debug("fs_provider login response: ")
            log.debug( logtool.pp(res))
        elif ( provider == "dropbox"):
            dbox = dbox_provider.DropboxProvider()
            if oauth_token:
                # it's a callback from dropbox and not from user. Try to revive session
                try:
                    msg = dbox.callback(oauth_token)
                    log.debug("Callback WORKED!: " + msg)
                    return "Logged in! Feel free to close your browser."
                except DBException as e:
                    return {"error": 1, "msg": str(e)}

            if userid:
                # Resume session or Poll
                if (async):
                    if not_approved:
                        log.debug("Revoke user_id %s" % userid)
                        dbox.revoke(userid)
                    else:
                        log.debug("got polling request for :" + userid)
                    return dbox.probe(userid)
                else:
                    #just resume:
                    log.debug("resuming session " + userid)
                    return dbox.login(req_key=userid)
            res = dbox.login(req_key=None, callback=callback, async=async)
            log.debug("dropbox_login response: ")
            log.debug( logtool.pp(res))
        else:
            res = { "error": 1 , "msg": "Wrong or unsupported arguments" }
        return res

    def convertToKML(self, records, userid):
        """
        function for converting from json to kml
        """
        self.response.headers['Content-Type'] = 'xml/application'
        self.response.headers['Content-Disposition'] = 'attachment; filename="download.kml"'
        kml = simplekml.Kml(open=1)
        for r in records:
            log.debug(r.content)
            for record in r.content.itervalues():
                description = "editor: %s\n timestamp: %s\n" %(record["properties"]["editor"], record["properties"]["timestamp"])
                for f in record["properties"]["fields"]:
                    if "fieldcontain-image" in str(f["id"]):
                        description += "%s: %s\n" % (str(f["label"]), "<img src='http://%s/1.3/pcapi/records/dropbox/%s/%s/%s' >" % (self.request.environ.get("SERVER_NAME", "NONE"), userid, record["name"], str(f["val"])))
                    else:
                        description += "%s: %s\n" % (str(f["label"]), str(f["val"]))
                log.debug(description)
                pnt = kml.newpoint(name=record["name"], description=description, coords=[(record["geometry"]["coordinates"][0], record["geometry"]["coordinates"][1])])

        return kml.kml()

    def convertToGeoJSON(self, records, userid):
        """
        Export all records to geojson and return result.
        """
        self.response.headers['Content-Type'] = 'application/json'
        features = []
        for r in records:
            #log.debug(r.content)        
            # get first -and only- value of dictionary because records are an array of
            # [ { <name> : <geojson feature> } ....]
            f = r.content.values()[0]
            features.append(f)

        geojson_str = {"type": "FeatureCollection", "features": features}
        log.debug(geojson_str)
        return json.dumps(geojson_str)

    def convertToDatabase(self, records, userid):
        """
        function for converting from json to a PostGIS database

        Also converts all records to "/data.json" for further processing.
        In the future "/data.json" can be incrementally for speed.
        """
        data = self.provider.realpath('/data.geojson')
        log.debug('EXPORTING to ' + data)
        geojson = self.convertToGeoJSON(records,userid)
        with open(data, "w") as fp:
            fp.write(geojson)

        # We can now convert to whatever OGR supports
        return ogr.toPostGIS(data, userid)

    def convertToCSV(self, records, userid):
        """
        function for converting from json to csv
        """
        log.debug("export csv")
        self.response.headers['Content-Type'] = 'text/csv'
        self.response.headers['Content-Disposition'] = 'attachment; filename="download.csv"'
        if not os.path.exists(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..', '..', 'tmp')):
            os.mkdir(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..', '..', 'tmp'))
        temp = tempfile.NamedTemporaryFile(prefix='export_', suffix='.csv', dir=os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..', '..', 'tmp'), delete=False)
        log.debug(temp.name)
        with open(temp.name, "w") as file:
            csv_file = csv.writer(file)
            i=0
            editor = ""
            new_records = []
            for r in records:
                for record in r.content.itervalues():
                    new_records.append(record)
            results = sorted(new_records, key=itemgetter('editor'))
            for record in results:
                if editor != record["properties"]["editor"]:
                    log.debug(record["properties"]["editor"])
                    path = "/editors/"+record["properties"]["editor"]
                    if record["properties"]["editor"] == "image.edtr" or record["properties"]["editor"] == "audio.edtr" or record["properties"]["editor"] == "text.edtr":
                        ed = urllib2.urlopen("http://fieldtripgb.edina.ac.uk/authoring/editors/default/"+record["properties"]["editor"]).read()
                    elif record["properties"]["editor"] == "track.edtr":
                        ed = urllib2.urlopen("http://fieldtripgb.edina.ac.uk/authoring/editors/default/text.edtr").read()
                    else:
                        try:
                            buf, meta = self.provider.get_file_and_metadata(path)
                            ed = buf.read()
                        except Exception as e:
                            log.exception("Exception: " + str(e))
                            pass
                        buf.close()
                    edit = Editor(ed)
                    field_headers = edit.findElements()
                    csv_file.writerow([record["properties"]["editor"]])
                    headers = ["Name", "Timestamp", "Longitude", "Latitude", "Altitude"]
                    for h in field_headers:
                        if h[0] != "fieldcontain-text-1":
                            headers.append(h[1])
                    i=0
                alt = 0
                if len(record["geometry"]["coordinates"]) > 2:
                    alt = record["geometry"]["coordinates"][2]
                fields = [record["name"], record["properties"]["timestamp"], record["geometry"]["coordinates"][0], record["geometry"]["coordinates"][1], alt]

                ## TODO: Remove those ugly ad-hoc checks. The Mobile app should submit records with same length and at the same order.
                all_fields = [ x[0] for x in field_headers ]
                for field in all_fields:
                    # For some reason we need to skip fieldcontain-text-1 because it is omitted from the headers above (Why?)
                    if field=="fieldcontain-text-1":
                        #print "skipping Site-ID"
                        continue

                    found_field_value = False
                    # check if field exists in record
                    for f in record["properties"]["fields"]:
                        if str(f["id"]) == field:
                            #bingo
                            found_field_value = True
                            #log.debug("Found value %s = %s" % (`f["id"]`, `f["val"]` ))
                            if "fieldcontain-image" in str(f["id"]):
                                fields.append("http://%s/1.3/pcapi/records/dropbox/%s/%s/%s" % (self.request.environ.get("SERVER_NAME", "NONE"), userid, record["name"], str(f["val"])))
                            elif "fieldcontain-track" in str(f["id"]):
                                fields.append("http://%s/1.3/pcapi/records/dropbox/%s/%s/%s" % (self.request.environ.get("SERVER_NAME", "NONE"), userid, record["name"], str(f["val"])))
                            elif "fieldcontain-audio" in str(f["id"]):
                                fields.append("http://%s/1.3/pcapi/records/dropbox/%s/%s/%s" % (self.request.environ.get("SERVER_NAME", "NONE"), userid, record["name"], str(f["val"])))
                            else:
                                fields.append(str(f["val"]))
                    if not found_field_value:
                        # append empty string if not field is not found in record
                        fields.append("")
                if i == 0:
                    csv_file.writerow(headers)

                csv_file.writerow(fields)
                editor = record["properties"]["editor"]
                i = i+1
        file.close()
        f = open(temp.name, "r")
        d = f.readlines()
        f.close()
        os.remove(temp.name)
        return d

    def resizeImage(self, fp, path):
        """ method for resizing images. I decided to keep 480px as absolute size for the images to be resized"""
        with Image(blob=fp) as img:
            log.debug(img.size)
            img.resize(480, img.height*480/img.width)
            #upload the resized image
            self.provider.upload(path, StringIO(img.make_blob()) )

    def createThumb(self, fp, path):
        """ method for resizing images. I decided to keep 480px as absolute size for the images to be resized"""
        with Image(blob=fp) as img:
            log.debug(img.size)
            img.resize(100, 100)
            #upload the resized image
            self.provider.upload(path, StringIO(img.make_blob()) )

    def filter_data(self, filters, path, userid):
        records_cache = self.rec_cache
        log.debug("Found %d records" % len(records_cache))
        if len(filters) > 0:
            if "editor" in filters:
                log.debug("filter by editor")
                ## "editor" filter requires param "id"
                f_id = self.request.GET.get("id").lower()
                if not f_id:
                    return {"msg": 'missing parameter "id"', "error":1}
                tmp_cache = []
                for x in records_cache:
                    for r in x.content.itervalues():
                        if x.content is not None and r["properties"]["editor"].lower() == f_id:
                            tmp_cache.append(x)
                records_cache = tmp_cache
                #records_cache = [r for r in records_cache.itervalues() if r is not None and r.content["editor"].lower() == f_id]
                log.debug("found filter by editor")
            if "date" in filters:
                ## "date" filter requires at least a "start_date"
                start_date = self.request.GET.get("start_date")
                if not start_date:
                    return {"msg": 'missing parameter "start_date"', "error":1}
                end_date = self.request.GET.get("end_date")
                log.debug("filter by dates %s %s" % (start_date, end_date) )
                try:
                    # parse the dates to unix epoch format. End time defaults to localtime )
                    epoch_start =  time.mktime(time.strptime(start_date,"%Y%m%d_%H:%M:%S"))
                    epoch_end = time.mktime(time.strptime(end_date,"%Y%m%d_%H:%M:%S") \
                                        if end_date else time.localtime())
                    log.debug("transformed dates %s %s" % (epoch_start, epoch_end))
                except ValueError:
                    return {"msg": "Bad date given. An example date would be 20120327_23:05:12", "error": 1 }
                records_cache = [ r for r in records_cache if \
                            r.metadata.mtime() >= epoch_start and r.metadata.mtime() <= epoch_end ]
                log.debug(len(records_cache))
            if "envelope" in filters:
                bbox = self.request.GET.get("bbox")
                log.debug("filter by bbox %s" % bbox)
                try:
                    (xmin, ymin, xmax, ymax) = map(float, bbox.split(","))
                except AttributeError:
                    # (None).split() gives AttributeError
                    return {"msg": 'Parameter "bbox" was not specified', "error":1}
                except ValueError:
                    return {"msg": \
                            "Wrong format. Use bbox=xmin,ymin,xmax,ymax e.g. bbox=-2.2342,33.55,-2.2290,33.56",\
                            "error":1}
                # convert to numbers
                tmp_cache = []
                for x in records_cache:
                    for r in x.content.itervalues():
                        log.debug(r["point"])
                        try:
                            lon = float(r["geometry"]["coordinates"][0])
                            lat = float(r["geometry"]["coordinates"][1])
                        except ValueError:
                            return {"msg": "Aborting due to error parsing lat/lon of record %s" \
                            % r["name"], "error" : 1}
                        if lon >= xmin and lon <= xmax and lat >= ymin and lat<=ymax:
                            tmp_cache.append(x)
                records_cache = tmp_cache
            if "media" in filters:
                frmt = self.request.GET.get("frmt")
                log.debug("filter by media %s" % frmt)
                if not path:
                    path = self.request.GET.get("mediatype")
                log.debug(frmt)
                if path == "/":
                    records_cache = self.get_media(records_cache, ["jpg", "jpeg", "wav", "amr", "gpx"], frmt)
                elif path == "images/":
                    records_cache = self.get_media(records_cache, ["jpg", "jpeg"], frmt)
                elif path == "audio/":
                    records_cache = self.get_media(records_cache, ["wav", "amr"], frmt)
                elif path == "gpx/":
                    records_cache = self.get_media(records_cache, ["gpx"], frmt)
            if "format" in filters:
                frmt = self.request.GET.get("frmt")
                log.debug("filter by format %s" % frmt)
                if frmt == "geojson":
                    return self.convertToGeoJSON(records_cache, userid)
                elif frmt == "kml":
                    return self.convertToKML(records_cache, userid)
                elif frmt == "csv":
                    return self.convertToCSV(records_cache, userid)
                elif frmt == "database":
                    return self.convertToDatabase(records_cache, userid)
                else:
                    return {"error" :1 , "msg" : "unrecognised format: " + `frmt`}
        return records_cache

    def get_media(self, records_cache, exts, frmt):
        """
        function for returning back the paths of the assets
        """
        if frmt == "url":
            tmp_cache = []
            for x in records_cache:
                for key, r in x.content.iteritems():
                    for field in r["properties"]["fields"]:
                        if self.check_extension(exts, field["val"]):
                            if frmt:
                                x.content = "%s/%s" % (key, field["val"])
                            tmp_cache.append(x)
            return tmp_cache
        else:
            path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..', '..', 'tmp')
            log.debug(path)
            if not os.path.exists(path):
                os.mkdir(path)
            os.chdir(path)
            dirpath = tempfile.mkdtemp()
            for x in records_cache:
                for key, r in x.content.iteritems():
                    for field in r["properties"]["fields"]:
                        if self.check_extension(exts, field["val"]):
                            buf, meta = self.provider.get_file_and_metadata(os.path.join("records", key, field["val"]))
                            f = open(os.path.join(dirpath, field["val"]), "w")
                            f.write(buf.read())
                            f.close()
            tname = "%s.zip" % uuid.uuid4()
            log.debug(tname)
            #if os.path.isfile("myzipfile.zip"):
            #    os.remove("myzipfile.zip")
            zf = zipfile.ZipFile(tname, "w")
            for dirname, subdirs, files in os.walk(dirpath):
                zf.write(dirname)
                for filename in files:
                    zf.write(os.path.join(dirname, filename))
                zf.close()
            return tname

    def check_extension(self, exts, field):
        for ext in exts:
            if ext in field.lower():
                return True
        return False
