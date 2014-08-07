# Unit test for the DropboxProvider REST API   #
###############################################

import json
import os, sys, unittest, re
import urllib2

from urllib2 import URLError
from webtest import TestApp

try:
    import threadpool
except ImportError:
    sys.stderr.write("Error: Can't find threadpool...")

## Also libraries to the python path
pwd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(pwd,'../lib')) # to find the classes to test
sys.path.append(os.path.join(pwd,'../wsgi'))

import pcapi, config, logtool
from form_validator import FormValidator, Editor

# User ID should exist in DATABASE
userid = None
#userid='aaabbbccbbdd'

# to test path ending in a directory
dirpath = "lev1/lev2/"

# to test uploading an editor
editorname = "myed.edtr"

# to testing uploading a record
recordname = "myrec.rec"

textfilepath = config.get("test", "testfile")
imagefilepath = config.get("test", "imagefile")
editorfilepath = config.get("test", "editorfile")

# the contents of the file are here (full path to local file)
localfile = open ( textfilepath , "r")

#schemafile = open ( schemafilepath , "r")

# Application
app = TestApp(pcapi.application)

def _verify_token():
    """
    Get user id from token file and validate it. If it is not there or invalid
    generate a new one.
    """
    global userid
    tokenfile = os.sep.join((config.get('test', 'test_resources'), 'token.txt'))

    with open(tokenfile, 'w+') as f:
        token = f.read()

    if len(token) > 0:
        resp = app.get('/auth/dropbox/{0}'.format(token)).json

        if resp["state"] == 1:
            userid = token

    if userid is None:
        def get_json():
            obj = None
            try:
                f = urllib2.urlopen('http://127.0.0.1:8080/auth/dropbox?async=true')
                obj = json.loads(f.read())
            except URLError:
                print 'Run python pcapi_devel.py, press Ret to continue'
                raw_input()
                obj = get_json()

            return obj

        obj = get_json()
        userid = obj['userid']
        print 'Goto {0}  press Ret to continue'.format(obj['url'])
        raw_input()
        print 'Using {0}'.format(userid)

        with open(tokenfile, 'w') as f:
            f.write(userid)

    return userid
_verify_token()

class TestDropboxFs(unittest.TestCase):
    """
    Test: REST functions for /fs/dropbox API
    """

    #@unittest.skip("skipping dbox_provider token valid")
    def test_verify_token(self):
        """ Verify that token exists in database """
        #print "test_verify_token"
        resp = app.get('/auth/dropbox/%s' % userid).json
        self.assertEqual(resp["state"],1)

    def test_put_file(self):
        """ PUT file in /fs/ URL under lev1/lev2 """
        # delete /lev1/lev2
        #print "test_put_file"
        app.delete('/fs/dropbox/%s/lev1/lev2' % userid)
        # put first file at /lev1/lev2
        resp = app.put('/fs/dropbox/%s/lev1/lev2' % userid, params=localfile.read() ).json
        self.assertEquals(resp["error"], 0 )
        #second put should overwrite the first
        resp = app.put('/fs/dropbox/%s/lev1/lev2' % userid, params=localfile.read() ).json
        self.assertEquals(resp["path"], "/lev1/lev2")

    def test_post_file(self):
        """ POST file in /fs/ URL using BODY """
        # delete /lev1/*
        #print "test_post_file"
        app.delete('/fs/dropbox/%s/lev1/' % userid)
        # post /lev1/lev2
        resp = app.post('/fs/dropbox/%s/lev1/lev2' % userid, params=localfile.read() ).json
        self.assertEquals(resp["error"], 0 )
        #second post should transparently create /lev1/lev2 \(1)
        resp = app.post('/fs/dropbox/%s/lev1/lev2' % userid, params=localfile.read() ).json
        self.assertEquals(resp["path"], "/lev1/lev2 (1)")

    def test_get_dir(self):
        """ GET on a /fs/ directory returns contents """
        # delete /lev1/*
        #print "test_get_dir"
        app.delete('/fs/dropbox/%s/lev1/' % userid)
        # post /lev1/lev2
        resp = app.post('/fs/dropbox/%s/lev1/lev2' % userid, params=localfile.read() ).json
        self.assertEquals(resp["error"], 0 )
        # Contents of /lev1/ should be the "/lev1/lev2" (always receives absolute paths)
        resp = app.get('/fs/dropbox/%s/lev1' % userid, params=localfile.read() ).json
        self.assertEquals(resp["metadata"], ["/lev1/lev2",])

    def test_get_file(self):
        """ GET on a /fs/ path to a file returns the file itself"""
        # put first file at /lev1/lev2 with content: "Hello World!\n"
        #print "test_get_file"
        contents = "Hello World!\n"
        resp = app.put('/fs/dropbox/%s/lev1/lev2' % userid, params=contents ).json
        self.assertEquals(resp["error"], 0 )
        # Contents of GET should be the same
        resp = app.get('/fs/dropbox/%s/lev1/lev2' % userid )
        self.assertEquals(resp.body , contents)

    def test_delete_file(self):
        """ DELETE on /fs/ path deletes the file or directory """
        #print "test_delete_file"
        # put first file at /lev1/lev2
        resp = app.put('/fs/dropbox/%s/lev1/lev2' % userid, params=localfile.read() ).json
        self.assertEquals(resp["error"], 0 )
        # Now delete it
        resp = app.delete('/fs/dropbox/%s/lev1/lev2' % userid ).json
        self.assertEquals(resp["error"], 0 )

class TestDropboxRecords(unittest.TestCase):
    """
    Test: REST functions for /records/dropbox API
    """
    ##### RECORDS ####

    def test_put_record(self):
        """ ALL PUT requests should be level 2 (full path to /records/myrecord/asset.ext ) """
        #print "test_put_record"
        #cleanup
        app.delete('/records/dropbox/%s/myrecord/image.jpg' % userid)
        resp = app.put('/records/dropbox/%s/myrecord/image.jpg' % userid, params=localfile.read() ).json
        self.assertEquals(resp["error"], 0)
        self.assertEquals(resp["path"], "/records/myrecord/image.jpg")
    
    def test_put_folder(self):
        """ Move record """
        app.delete('/records/dropbox/%s//' % userid)
        resp = app.post('/records/dropbox/%s/myrecord' % userid, upload_files=[("file" , textfilepath )] ).json
        resp = app.post('/records/dropbox/%s/myrecord/image.jpg' % userid, upload_files=[("file" , textfilepath )] ).json
        # put first file at /lev1/lev2
        resp = app.put('/records/dropbox/%s/myrecord' % userid, params = 'myrecord1').json
        self.assertEquals(resp["error"], 0 )
        
        resp = app.post('/records/dropbox/%s/myrecord' % userid, upload_files=[("file" , textfilepath )] ).json
        resp = app.post('/records/dropbox/%s/myrecord/image.jpg' % userid, upload_files=[("file" , textfilepath )] ).json
        # put first file at /lev1/lev2
        resp = app.put('/records/dropbox/%s/myrecord1' % userid, params = 'myrecord').json
        self.assertEquals(resp["error"], 0 )
        app.delete('/records/dropbox/%s//' % userid)

    def test_post_record(self):
        """ POST level 1 /myrecord should create /myrecord/record.json if myrecord doesn't exist OR
        /myrecord (1)/record.json if myrecord exists.

        Also the file is POSTed using the Content-Type multipart/form-data according to the RFC 2388
        or just placed in body (both are supported).

        """
        #print "test_post_record"
        #cleanup EVERYTHING under /records/
        app.delete('/records/dropbox/%s//' % userid)
        #POST to level 1 which does *not exist* should create /myrecord/record.json
        resp = app.post('/records/dropbox/%s/myrecord' % userid, upload_files=[("file" , textfilepath )] ).json
        self.assertEquals(resp["error"], 0)
        self.assertEquals(resp["path"], "/records/myrecord/record.json")
        #POST to level 1 which *exists* should create /myrecord (1)/record.json
        # AND update the json contents!!
        resp = app.post('/records/dropbox/%s/myrecord' % userid, upload_files=[("file" , textfilepath )] ).json
        self.assertEquals(resp["error"], 0)
        self.assertEquals(resp["path"], "/records/myrecord (1)/record.json")
        # now get the new record and make sure the name is updated!
        resp  = app.get('/records/dropbox/%s/myrecord (1)/record.json' % userid ).body
        import json
        content = json.loads(resp)
        self.assertEquals(content["name"], "myrecord (1)")
        #POST to level 2 behaves like fs but DOES NOT overwrite:
        #app.delete('/records/dropbox/%s/myrecord/image.jpg' % userid)
        #app.delete('/records/dropbox/%s/myrecord/image (1).jpg' % userid)
        resp = app.post('/records/dropbox/%s/myrecord/test' % userid, upload_files=[("file" , textfilepath )] ).json
        self.assertEquals(resp["path"], "/records/myrecord/test")
        resp = app.post('/records/dropbox/%s/myrecord/test' % userid, upload_files=[("file" , textfilepath )]).json
        self.assertEquals(resp["path"], "/records/myrecord/test (1)")

    def test_get_record(self):
        """ GET on exact record name return contents """
        #print "test_get_record"
        #cleanup EVERYTHING under /records/
        app.delete('/records/dropbox/%s//' % userid)
        # create the record
        content = localfile.read()
        resp = app.post('/records/dropbox/%s/myrecord' % userid, params=content ).json
        self.assertEquals(resp["error"], 0)
        # GET specifying only recordname
        resp = app.get('/records/dropbox/%s/myrecord' % userid )
        self.assertEquals(resp.body, content)
        # GET specifying full path
        resp = app.get('/records/dropbox/%s/myrecord/record.json' % userid )
        self.assertEquals(resp.body, content)

    def test_get_all_records(self):
        """ GET with *no* record specified returns all records """
        #print "start test_get_all_records"
        #cleanup EVERYTHING under /records/
        app.delete('/records/dropbox/%s//' % userid)
        # create myrecord/record.json
        resp = app.post('/records/dropbox/%s/myrecord' % userid, upload_files=[("file" , textfilepath )] ).json
        self.assertEquals(resp["error"], 0)
        self.assertEquals(resp["path"], "/records/myrecord/record.json")
        # create myrecord (1)record.json
        resp = app.post('/records/dropbox/%s/myrecord (1)' % userid, upload_files=[("file" , textfilepath )] ).json
        self.assertEquals(resp["error"], 0)
        self.assertEquals(resp["path"], "/records/myrecord (1)/record.json")
        resp = app.get('/records/dropbox/%s/' % userid).json
        self.assertEquals(resp["error"], 0)
        #print len ( resp["records"] )
        self.assertEquals(len ( resp["records"] ) , 2 )

    ### RECORD FILTERS

    def test_filter_by_date(self):
        """ GET by date """
        #print "start test_filter_by_date"
        #cleanup EVERYTHING under /records/
        app.delete('/records/dropbox/%s//' % userid)
        # get current time
        import time
        timenow = time.strftime("%Y%m%d_%H:%M:%S", time.localtime())
        # create myrecord/record.json
        resp = app.post('/records/dropbox/%s/myrecord' % userid, upload_files=[("file" , textfilepath )] ).json
        self.assertEquals(resp["error"], 0)
        self.assertEquals(resp["path"], "/records/myrecord/record.json")
        # Get all file since start time
        resp = app.get('/records/dropbox/%s/' % userid, params={ "filter":"date","start_date": timenow}).json
        self.assertEquals(resp["error"], 0)

    def test_filter_by_editor_id(self):
        """ GET by editor id """
        #cleanup EVERYTHING under /records/
        #print "start test_filter_by_editor_id"
        app.delete('/records/dropbox/%s//' % userid)
        # create myrecord/record.json using BODY
        content = localfile.read()
        resp = app.post('/records/dropbox/%s/myrecord' % userid, upload_files=[("file" , textfilepath )] ).json
        self.assertEquals(resp["error"], 0)
        # get its id:
        eid = 'text.edtr'
        # Get all file since editor id
        resp = app.get('/records/dropbox/%s/' % userid, params={ "filter":"editor","id": eid}).json
        self.assertEquals(resp["error"], 0)
    
    def test_resize_image(self):
        
        app.delete('/records/dropbox/%s/myrecord' % userid)
        resp = app.post('/records/dropbox/%s/myrecord' % userid, upload_files=[("file" , textfilepath )] ).json
        self.assertEquals(resp["error"], 0)
        resp = app.post('/records/dropbox/%s/myrecord/myimage.jpg' % userid, upload_files=[("file" , imagefilepath)] ).json
        self.assertEquals(resp["error"], 0)
        resp = app.get('/records/dropbox/%s/myrecord/myimage.jpg' % userid )
        from wand.image import Image
        with Image(blob=resp.body) as img:
            self.assertEquals(img.width, 480)
        
        #check for original image size
        resp = app.get('/records/dropbox/%s/myrecord/myimage_orig.jpg' % userid )
        from wand.image import Image
        with Image(blob=resp.body) as img:
            self.assertEquals(img.width, 640)
    
    def test_filter_by_mediatype(self):
        app.delete('/records/dropbox/%s/myrecord' % userid)
        resp = app.post('/records/dropbox/%s/myrecord' % userid, upload_files=[("file" , textfilepath )] ).json
        self.assertEquals(resp["error"], 0)
        resp = app.post('/records/dropbox/%s/myrecord/myimage.jpg' % userid, upload_files=[("file" , imagefilepath)] ).json
        self.assertEquals(resp["error"], 0)
        resp = app.get('/records/dropbox/%s/' % userid, params={ "filter":"media","mediatype": "images"}).json
        self.assertEquals(resp["error"], 0)

class TestDropboxEditors(unittest.TestCase):
    """
    Test: REST functions for /editors/dropbox API
    """
    ##### EDITORS ####

    def test_upload_editor(self):
        resp = app.put('/editors/dropbox/%s/myeditor.edtr' % userid, params=localfile.read() ).json
        self.assertEquals(resp["error"], 0)
        self.assertEquals(resp["path"], '/editors/myeditor.edtr' )

class TestValidEditors(unittest.TestCase):

    def test_editor_with_javascript(self):
        ed = '''<form id="form962" data-ajax="false">
            javascript:alert('Hello, World');
            <div class="fieldcontain" id="fieldcontain-text-1">
            javascript:alert('Hello, World');
            <button onclick="javascript:alert('Hello, World');">aaa</button>
            <label for="form-text-1">Title"</label>
            <input name="form-text-1" id="form-text-1" type="text" required="" placeholder="Placeholder" maxlength="10" value="javascript:alert('Hello, World');" />
            </div>

            <div class="fieldcontain" id="fieldcontain-range-1">
            <label for="form-range-1">Range</label>
            <input name="form-range-1" id="form-range-1" type="range" required="" step="1" min="0" max="10" placeholder="Placeholder" maxlength="10" />
            </div>

            <div id="test1-buttons" class="fieldcontain ui-grid-a">
            <div class="ui-block-a">
            <input type="submit" name="record" id="962_record" value="Save" />
            <input type="submit" name="record" id="962_record" value="Save" onclick="javascript:alert('Hello, World');" />
            </div>
            <div class="ui-block-b">
            <input type="button" name="cancel" id="962_cancel" value="Cancel" />
            </div>
            </div>
            </form>
            '''
        val = FormValidator(ed)
        self.assertEquals(val.validate(), False)

    def test_valid_editor(self):
        ed = '''<form id="form962" data-ajax="false">
            <div class="fieldcontain" id="fieldcontain-text-1">
            <label for="form-text-1">Title"</label>
            <input name="form-text-1" id="form-text-1" type="text" required="" placeholder="Placeholder" maxlength="10">
            </div>

            <div class="fieldcontain" id="fieldcontain-range-1">
            <label for="form-range-1">Range</label>
            <input name="form-range-1" id="form-range-1" type="range" required="" step="1" min="0" max="10" placeholder="Placeholder" maxlength="10">
            </div>

            <div id="test1-buttons" class="fieldcontain ui-grid-a">
            <div class="ui-block-a">
            <input type="submit" name="record" id="962_record" value="Save">
            </div>
            <div class="ui-block-b">
            <input type="button" name="cancel" id="962_cancel" value="Cancel">
            </div>
            </div>
            </form>
            '''
        val = FormValidator(ed)
        self.assertEquals(val.validate(), True)

    def test_editor_with_onclick(self):
        ed = '''<form id="form962" data-ajax="false">
            <div class="fieldcontain" id="fieldcontain-text-1">

            <div id="test1-buttons" class="fieldcontain ui-grid-a">
            <div class="ui-block-a">
            <input type="submit" name="record" id="962_record" value="Save" onclick="javascript:alert('Hello, World');" />
            </div>
            <div class="ui-block-b">
            <input type="button" name="cancel" id="962_cancel" value="Cancel" />
            </div>
            </div>
            </form>
            '''
        val = FormValidator(ed)
        self.assertEquals(val.validate(), False)

    def test_editor_with_email(self):
        ed = '''<form id="form962" data-ajax="false">
            <div class="fieldcontain" id="fieldcontain-text-1">
            <label for="form-text-1">Title"</label>
            <input name="form-text-1" id="form-text-1" type="email" required="" placeholder="Placeholder" maxlength="10" />
            </div>
            </form>
            '''
        val = FormValidator(ed)
        self.assertEquals(val.validate(), False)

    def test_editor_with_action(self):
        ed = '''<form id="form962" data-ajax="false" action="skata.php">
            <div class="fieldcontain" id="fieldcontain-text-1">
            <label for="form-text-1">Title"</label>
            <input name="form-text-1" id="form-text-1" type="text" required="" placeholder="Placeholder" maxlength="10" />
            </div>
            </form>
            '''
        val = FormValidator(ed)
        self.assertEquals(val.validate(), False)

@unittest.skip("not implemented")
class TestDropboxBreak(unittest.TestCase):
    """
    Test: Bad REST URLs trying to break the app
    """
    def test_provider(self):
        """ Bad spelling of dropbox provider should say "unsupported provider" """
        print "Issuing bad request for provider dropboxxx"
        resp = app.get('/records/dropboxxxx/%s/' % userid, params=localfile.read() )
        self.assertEquals(resp["error"], 1)

class TestDropboxExport(unittest.TestCase):
    """
    Test: Sync related testing.
    """

    def test_export(self):
        """Export a url to a file"""
        #print "test export"
        #create new record
        put_resp = app.put('/records/dropbox/%s/myrecord/record.json' % userid, params=localfile.read() ).json
        self.assertEquals(put_resp["error"], 0)
        # export
        resp = app.get('/export/dropbox/%s/%s' % ( userid, put_resp["path"] ) ).json
        self.assertEquals( resp["error"] , 0 )
        self.assertTrue ( resp["url"].startswith("http://") )


class TestDropboxSync(unittest.TestCase):
    """
    Test: Sync related testing.
    """

    def test_create_sync(self):
        """Get Cursor before adding a file, then sync to see the changes made"""
        #cleanup EVERYTHING under /records/
        app.delete('/records/dropbox/%s//' % userid)
        # get cursor
        cur_resp = app.get('/sync/dropbox/%s' % userid).json
        #create new record
        put_resp = app.post('/records/dropbox/%s/myrecord' % userid, params=localfile.read() ).json
        self.assertEquals(put_resp["error"], 0)
        # get diffs
        diff_resp = app.get('/sync/dropbox/%s/%s' % ( userid, cur_resp["cursor"] ) ).json
        self.assertEquals( diff_resp["updated"] , [u'/records/myrecord', u'/records', u'/records/myrecord/record.json'] )

class TestEditor(unittest.TestCase):
    def setUp(self):
        self.f = open ( editorfilepath , "r")
        self.editor = Editor(self.f.read())
    
    def tearDown(self):
        self.f.close()
    
    def test_editor_elements(self):
        result = [[u'fieldcontain-text-1', u'Title'], [u'fieldcontain-range-1', u'Range'], [u'fieldcontain-textarea-1', u'Description'], [u'fieldcontain-checkbox-1', u'Choose'], [u'fieldcontain-radio-1', u'Choose'], [u'fieldcontain-select-1', u'Choose'], [u'fieldcontain-image-1', 'image'], [u'fieldcontain-audio-1', 'audio']]
        self.assertEquals(result, self.editor.findElements())

class TestDropboxProvider(unittest.TestCase):
    """
    testing dropbox provider
    """
    
    
    def setUp(self):
        self.dbox = dbox_provider.DropboxProvider()
        self.dbox.login(userid)
        self.threads = 10
        self.i=0
    
    def test_mkdir(self):
        app.delete('/records/dropbox/%s//' % userid)
        records = []
        for i  in xrange(self.threads):
            records.append("rec")
        print len(records)
        
        requests = threadpool.makeRequests(self.make_dirs, records, self.result, self.handle_exception)
        #insert the requests into the threadpool
        pool = threadpool.ThreadPool(100)
        i=0
        for req in requests:
            i = i+1
            print i
            pool.putRequest(req)
            print "Work request #%s added." % req.requestID
    
        #wait for them to finish (or you could go and do something else)
        pool.wait()
        pool.dismissWorkers(100, do_join=True)
        print "workers length: %s" % len(pool.workers)
        metadata = self.dbox.search("/records/", "rec")
        j = 0
        for el in metadata.md:
            if el["is_dir"]:
                j = j+1
        self.assertEquals(self.threads, j)
    
    def make_dirs(self, rec):
        self.dbox.mkdir("records/"+rec)
        #self.dbox.api_client.file_create_folder(rec)
        #put_resp = app.post('/records/dropbox/%s/%s' % (userid, rec), params=localfile.read()).json
        
    def result(self, request, result):
        print "result is %s" % result
        if result is None:
            self.i = self.i+1
    
    def handle_exception(self, request, exc_info):
        if not isinstance(exc_info, tuple):
            # Something is seriously wrong...
            print request
            print exc_info
            raise SystemExit
        print "**** Exception occured in request #%s: %s" % \
          (request.requestID, exc_info)
    
    def test_search(self):
        app.delete('/records/dropbox/%s//' % userid)
        resp = app.post('/records/dropbox/%s/myrecord' % userid, upload_files=[("file" , textfilepath )] ).json
        resp = app.post('/records/dropbox/%s/myrecord/image.jpg' % userid, upload_files=[("file" , textfilepath )] ).json
        metadata = self.dbox.search("/records/", ".jpg")
        self.assertEquals(len(metadata.md), 1)
        
    
    def tearDown(self):
        print self.i


if __name__ == '__main__':
    unittest.main()
