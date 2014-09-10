# -*- coding: utf-8 -*-
"""
Export to an OGR compatible datasource. Currently only PostGIS is supported with the
intent to extend this to other formats (e.g. GeoPackage)

Test Process:
1) Upload a few test records from the ENVSYS test-data
2) Export to PostGIS

"""
import os
import sys
import unittest

from webtest import TestApp

## Also libraries to the python path
pwd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(pwd, '../'))  # to find the classes to test
sys.path.append(os.path.join(pwd, '../wsgi'))

import pcapi_devel
from pcapi import config

userid = "testexport@domain.co.uk"

# where to get records ala "recordXXX.json" from
envsys_records_dir = config.get("test", "records_dir")
# How many records
records_num = 15

# Application
app = TestApp(pcapi_devel.application)
provider = 'local'

class TestDatabaseExport(unittest.TestCase):
    """
    1) POST all test records

    2) EXPORT to postgis
        /records/local/USER/?filter=database&ftl
    """
    ########### UPLOAD RECORDS ###########

    def test_post_records(self):
        """ PREPARATION: posts <records_num> records to use as test data """
        #cleanup previous cruft under /records/
        # -- not necessary since we are overwriting the records
        url = '/records/{0}/{1}//'.format(provider,userid)
        app.delete(url)

        # POST records_num records from the envsys dataset
        for i in xrange (records_num):
            record_file = os.path.join(envsys_records_dir, "record%s.json" % str(i)) #full path
            url='/fs/{0}/{1}/records/{2}/record.json'.format(provider,userid, str(i))
            with open (record_file) as f:
                resp = app.post(url, params=f.read() ).json
            print `resp`
            self.assertEquals(resp["error"], 0 )

        # Test POST by reading the first contents of /records/0/ whuich should be the record0.json
        resp = app.get('/fs/{0}/{1}/records/0'.format(provider,userid) ).json
        self.assertTrue("/records/0/record.json" in resp["metadata"])


    def test_export_to_database(self):
        """
        Export all records to a database named after the userid/uuid probably with
        some character mangling.
        """

        #export to database
        url = '/records/{0}/{1}/?filter=format&frmt=database'.format(provider,userid)
        resp = app.get(url)
        self.assertEquals(resp.json["error"], 0)
