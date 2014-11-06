# -*- coding: utf-8 -*-
"""
Publish to OGC W*S services. Includes:
1) Tests for syncing to a PostGIS databases
2) Tests for exporting the database to a running Geoserver instance

"""
import os
import sys
import unittest

from webtest import TestApp
## Also libraries to the python path
pwd = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(1,os.path.join(pwd, '../'))  # takes precedence over ~/.local

from pcapi.server import application
from pcapi import config

userid = "testexport@domain.co.uk"

# where to get resource and assets
test_dir = config.get("test", "test_resources")
test1 = os.path.join(test_dir,"test1")
test2 = os.path.join(test_dir,"test 2")

# Application
app = TestApp(application)
provider = 'local'

class TestPublish(unittest.TestCase):
    """
    Test Process:
    1) Upload a Form:
        POST /editors/local/uid/SID.edtr
    2) Upload a test record with asset to the local provider at any order
        POST /fs/local/uid/records/TR/record.json
        POST /fs/local/uid/records/TR/asset1.img
        POST
    3) publish record (staging)
        GET /
    """
    ########### UPLOAD RECORDS ###########

    def test_post_records(self):
        """ PREPARATION: posts test1 and test2 includig associated assets to use as test data for next tests"""

        #cleanup previous cruft under /records/
        # -- not necessary since we are overwriting the records
        url = '/records/{0}/{1}//'.format(provider,userid)
        app.delete(url)

        # POST "test1" record to /records/local/uuid/test1
        record_file = os.path.join(test1, "record.json") #full path
        url='/records/{0}/{1}/{2}'.format(provider,userid,"test1")
        with open (record_file) as f:
            resp = app.post(url, params=f.read() )
        self.assertEquals(resp.json["error"], 0 )

        # POST "test1" audio113 to /fs/local/uuid/records/test1/audio113.mp4
        asset_file = os.path.join(test1, "audio113.m4a") #full path
        url='/fs/{0}/{1}/records/{2}/{3}'.format(provider,userid,"test1","audio113.m4a")
        with open (asset_file) as f:
            resp = app.post(url, params=f.read() )
        self.assertEquals(resp.json["error"], 0 )

        # Test POST by reading the contents of test1 directory
        resp = app.get('/fs/{0}/{1}/records/{2}'.format(provider,userid,"test1") )
        self.assertTrue("/records/{0}/record.json".format("test1") in resp.json["metadata"])
        self.assertTrue("/records/{0}/audio113.m4a".format("test1") in resp.json["metadata"])
        ############
        # POST "test 2" record to /records/local/uuid/test 2
        record_file = os.path.join(test2, "record.json") #full path
        url='/records/{0}/{1}/{2}'.format(provider,userid,"test 2")
        with open (record_file) as f:
            resp = app.post(url, params=f.read() )
        self.assertEquals(resp.json["error"], 0 )

        # POST "test2" 1414517099373.jpg to /fs/local/uuid/records/test 2/1414517099373.jpg
        asset_file = os.path.join(test2, "1414517099373.jpg") #full path
        url='/fs/{0}/{1}/records/{2}/{3}'.format(provider,userid,"test 2","1414517099373.jpg")
        with open (asset_file) as f:
            resp = app.post(url, params=f.read() )
        self.assertEquals(resp.json["error"], 0 )

        # Test POST by reading the contents of test 2 directory
        resp = app.get('/fs/{0}/{1}/records/{2}'.format(provider,userid,"test 2") )
        self.assertTrue("/records/{0}/record.json".format("test 2") in resp.json["metadata"])
        self.assertTrue("/records/{0}/1414517099373.jpg".format("test 2") in resp.json["metadata"])

    def test_mapping(self):
        """
        Test that mapping between records and generated SQL actually works
        """
        from pcapi.publish import mapping
        record_file = os.path.join(test1, "record.json") #full path
        with open (record_file) as f:
            r = f.read()
        table, ddl , dml = mapping.mapping (r,userid)
        self.assertEquals(table, 'audio' )
        self.assertEquals(ddl, ['userid TEXT','name TEXT','timestamp TEXT',\
        u'Description TEXT', u'Audio TEXT','pos_acc REAL'] )
        self.assertEquals(dml, [userid,u'test1', u'2014-10-27T15:14:51.335Z',\
            u'', u'audio113.m4a', 12, 'POINT(-3.17905165503 55.9365917614)' ])             
         
    def test_publish(self):
        """ Pubish the 2 records to database one-by-one
        GET /records/local/uid/test1?ogc_sync=true
        GET /records/local/uid/test 2?ogc_sync=true
        """
        url='/records/local/{0}/test1?ogc_sync=true'.format(userid)
        resp = app.get(url).json 
        print `resp`
        url='/records/local/{0}/test 2?ogc_sync=true'.format(userid)
        resp = app.get(url).json
        print `resp`
