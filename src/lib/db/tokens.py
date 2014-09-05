# -*- coding: utf-8 -*-

import spatialite, logtool

#################### Dropbox,flickr etc. credential storage management #############
"""  Wrapper functions around SQL command use for reading/writing/seaching access
credentials for different providers.

The result is normal a list of tuples e.g. [(foo,bar)] for one row and (None,) for no rows.

NOTE: req_key (in dropbox lingo) is "userid" for pcapi
"""

log = logtool.getLogger("tokens", "pcapi")

def dump_tokens():
   res = spatialite.execute("""
       SELECT * FROM tokens;
       """)
   # 2D list of lists
   return res

def save_access_tokens(userid, req_secret, acc_key, acc_secret):
   res = spatialite.execute("""
       INSERT OR IGNORE INTO tokens(userid,reqsec,accsec,acckey) VALUES (?,?,?,?)
       """, (userid,req_secret, acc_key, acc_secret))
   return res==[]

def get_access_pair(userid):
    """ return ( acc_key, acc_secret ) for provided userid or None """
    res = spatialite.execute("""
       SELECT accsec, acckey from tokens WHERE userid=?
       """, (userid,))
    return res[0] if res else None

def delete_token(userid):
    """ delete token with provided userid """
    res = spatialite.execute("""
       DELETE FROM tokens WHERE userid=?
       """, (userid,) )
    return res==[]

### temporary values #####

def get_request_pair(userid):
    """ return ( userid, req_secret ) pair for provided userid or None """
    res = spatialite.execute("""
       SELECT userid, reqsec from temp_request WHERE userid=?
       """, (userid,))
    return res[0] if res else None

def save_unverified_request( userid, req_secret ):
    """ save unverified request keys """
    res = spatialite.execute("""
        INSERT OR IGNORE INTO temp_request(userid,reqsec) VALUES (?,?)
        """, (userid,req_secret))
    return res==[]


def delete_unverified_request(userid):
    res = spatialite.execute("""
        DELETE FROM temp_request WHERE userid=?
        """, (userid,))
    return res == []


def prune_temp_request():
    """ delete temporary requests tables. Should be called at app startup """
    res = spatialite.execute("""
        DELETE FROM temp_request(userid,reqsec) VALUES
        """)
    return res==[]
