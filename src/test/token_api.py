# -*- coding: utf-8 -*-
# Test tokens
#############################################

import os
import sys
import unittest
#from ipdb import set_trace

# Also libraries to the python path
pwd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(pwd, '../'))  # to find the classes to test

from pcapi.db import tokens

#These are dummy values!
userid = 'aabbcc7aabbc9de'
req_secret = 'rre8eqse2ecre5t0'
acc_key = 'aacc3esskkeeyy'
acc_secret = 'aa3cc3esseec2r2'

#
class TestDropbox(unittest.TestCase):
    """
    Test: API internal of Dropbox provider..
        Also tests db token specific SQL functions
    """
    def setUp(self):
        pass

    def test_all_cookie_functions(self):
        ## Create temp token
        tokens.save_unverified_request(userid,req_secret)

        ## Read request list -> success
        rpair = tokens.get_request_pair(userid)
        self.assertEqual (rpair[0],userid)
        self.assertEqual (rpair[1],req_secret)

        ## Read access list -> None
        apair = tokens.get_access_pair(userid)

        #set_trace()
        self.assertFalse(apair)

        ## Save access list
        tokens.save_access_tokens(userid, req_secret, acc_key, acc_secret)

        ## Read access list (again) -> success
        apair = tokens.get_access_pair(userid)


        self.assertEqual (apair[0],acc_key)
        self.assertEqual (apair[1],acc_secret)

    def tearDown(self):
        tokens.delete_token(userid)

if __name__ == '__main__':
    unittest.main()


