# Test: loging in and uploading a file.


# Unit test for connecting to Dropbox bottle webapp

import os, sys, unittest
#from ipdb import set_trace

## Also libraries to the python path
pwd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(pwd,'../lib')) # to find the classes to test
sys.path.append(os.path.join(pwd,'../wsgi'))

import pcapi
from webtest import TestApp
import time

app = TestApp(pcapi.application)
#pdb.set_trace()
class TestWSGI(unittest.TestCase):

    def setUp(self):
        self.app = TestApp(pcapi.application)
        # dummy file
        self.localimg = "./foo.txt"
        
    @unittest.skip("skipping Dropbox Synchronous test")
    def test_dropbox_login_noasync(self):
        # load a file and get a dropbox cookie
        resp = self.app.get('/auth/dropbox').json
        userid = resp["userid"]
        url = resp["url"]
        self.assertTrue( url
        .startswith('https://www.dropbox.com/1/oauth/authorize?oauth_token='))
        self.assertEquals( resp["state"], 0)
        # pause and wait for user to login
        print "Please login using the browser window: %s" % url
        raw_input()
        resp = self.app.get('/auth/dropbox/%s' % userid).json
        print "resp was " + `resp`
        self.assertEquals( resp["state"], 1)
       
    #@unittest.skip("skipping Dropbox Asynchronous test")
    def test_dropbox_login_async(self):
        """ This test only works with normal http request, not app.get(url)
        """
        # load a file and get a request key
        # The HTTP_HOST is an ugly hack to get the WebTest to emulate a url
        resp = self.app.get('/auth/dropbox', {'async': "true"},
                            extra_environ=dict(HTTP_HOST="localhost:8080") )
        url = resp.json["url"]
        userid = resp.json["userid"]
        print "Click on the url below:"
        print "url is : " + url
        # 
        # poll for N seconds
        N=30
        for i in xrange(N):
            print "polling %d/%d" % (i,N)
            resp = self.app.get('/auth/dropbox/%s' % userid, {'async': "true"}).json
            print resp
            if resp["state"]==1 :
                print "LOGGED IN by polling"
                break
            time.sleep(1)
            
        self.assertEquals( resp["state"], 1)
        
if __name__ == '__main__':
    unittest.main()

