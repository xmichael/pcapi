# -*- coding: utf-8 -*-
"""
Publish to OGC W*S services. Includes:
1) Tests for syncing to a PostGIS databases
2) Tests for exporting the database to a running Geoserver instance

Test Process:
1) Upload a few test records from the ENVSYS test-data
2) Export to PostGIS
3) Add table to geoserver

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

# where to get records ala "recordXXX.json" from
envsys_records_dir = config.get("test", "records_dir")
# How many records
records_num = 15

# Application
app = TestApp(application)
provider = 'local'

class TestPublish(unittest.TestCase):
    """
    1) POST all test records

    2) DELETE one of them
        /records/local/USER/?filter=database&ftl
    """
    ########### UPLOAD RECORDS ###########

    def test_post_records(self):
        """ PREPARATION: posts <records_num> records to use as test data """
        #cleanup previous cruft under /records/
        # -- not necessary since we are overwriting the records
        url = '/records/{0}/{1}//'.format(provider,userid)
        app.delete(url)

        # RECORD POST records_num records from the envsys dataset
        for i in xrange (records_num):
            record_file = os.path.join(envsys_records_dir, "record%s.json" % str(i)) #full path
            url='/records/{0}/{1}/{2}?ogc_sync=true'.format(provider,userid, str(i))
            with open (record_file) as f:
                resp = app.post(url, params=f.read() ).json
            self.assertEquals(resp["error"], 0 )

        # Test POST by reading the first contents of /records/0/ whuich should be the record0.json
        resp = app.get('/fs/{0}/{1}/records/0'.format(provider,userid) ).json
        self.assertTrue("/records/0/record.json" in resp["metadata"])


    def test_delete_records(self):
        """
        delete a test record
        """
        #post a file just in case
        record_file = os.path.join(envsys_records_dir, "record0.json")#full path
        url='/records/{0}/{1}/{2}?ogc_sync=true'.format(provider,userid, "0")
        with open (record_file) as f:
            resp = app.post(url, params=f.read() ).json
        self.assertEquals(resp["error"], 0 )

        #delete it
        url = '/records/{0}/{1}/0?ogc_sync=true'.format(provider,userid)
        resp = app.delete(url).json
        self.assertEquals(resp["error"], 0)
