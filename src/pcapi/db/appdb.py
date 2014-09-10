from pcapi import logtool
from pcapi.db import spatialite
from pcapi.pcapi_exceptions import DBException

""" High Level PCAPI Wrapper arround Spatialite
Supports:
1) Session management
2) GIS ops (nearby etc)

NOTE: Currently implemented as a module (i.e. Singleton in python).
       Could perhaps split into "geo" and "metadata" specific functions
"""

log = logtool.getLogger("appdb", "db")

#################### SESSION / KEYWORD FUNCTIONS #############
def get_tags(userid):
    """ Get all tags associated with a userid
    """
    stdout = spatialite.execute("""
        BEGIN;
        select group_concat(tag) as tags from sessions LEFT OUTER JOIN tags
        USING userid LEFT OUTER JOIN tag USING tag_id where userid=?
        COMMIT;""", (userid,))
    if stdout == None:
        raise DBException("No tags found!")
    return stdout.split(',')

def insert_key(key):
   """ register a new keyword. Noop if keyword exists. """
   res = spatialite.execute("""
       INSERT OR IGNORE INTO tag(tag) VALUES (?);
       """ , (key,))
   return res

def insert_userid(userid, lon=None, lat=None):
    """ register userid. No-op if userid already exists.
    Optional argument lon/lat allow for geocoded userids.
    """
    if ( not (lon and lat)):
        res = spatialite.execute("""
            INSERT OR IGNORE INTO sessions(userid) VALUES (?);
        """, (userid,))
    else:
        res = spatialite.execute("""
            INSERT OR IGNORE INTO sessions(userid, geom)
            VALUES (?,PointFromText('POINT('|| ? || ' '|| ? || ')', 4326))
        """, (userid, lon, lat) )
    return res

def geotag_userid(userid, lon, lat):
    """ geocode existing userid
    args:
        lon/lat WGS84 coords.
    """
    log.debug("lon is %s" % lon)
    log.debug("UPDATE sessions SET geom = PointFromText('POINT('|| %s || ' '|| %s || ')', 4326) WHERE userid='%s'" % (lon,lat,userid))
    res = spatialite.execute("""
        UPDATE sessions SET geom = PointFromText('POINT('|| ? || ' '|| ? || ')', 4326) WHERE userid=?
    """, (lon, lat, userid) )
    return res

def get_userid_list(bbox,key):
    """
    Return all userids in database for mediafile within a BBOX and/or with keyword `key'

    Args:
        bbox (optional): string of comma separated xmin,ymin,xmax,ymax
        key (optional): keyword string to filter by

    Returns:
        String of comma-separated userids
    """
    if bbox and not key:
        res = spatialite.execute("""
            SELECT group_concat(userid) from sessions WHERE sessions.ROWID IN
            (SELECT pkid FROM idx_sessions_geom WHERE xmin >= ? AND ymin >= ? AND xmax <= ? AND ymax <= ?)
        """, bbox.split(',') )
    if not bbox and key:
        res = spatialite.execute("""
            SELECT group_concat(userid) from sessions s, tags, tag
            WHERE s.id = tags.sessions_id and tag.id = tags.tag_id and tag=?
        """, (key,) )
    if bbox and key:
        res = spatialite.execute("""
            SELECT group_concat(userid) from sessions s, tags, tag
            WHERE s.id = tags.sessions_id and tag.id = tags.tag_id and tag=?
            AND s.ROWID IN (SELECT pkid FROM idx_sessions_geom
                WHERE xmin >= ? AND ymin >= ? AND xmax <= ? AND ymax <= ?)
        """, (key,) + tuple(bbox.split(',')) )
    res = ','.join(res[0]) if res[0]!=(None,) else ""
    return res

def connect_key(userid,key):
   """ Associate a userid with a keyword. Both MUST already exist
   (so run insert_key&insert_userid before just in case.) """
   res = spatialite.execute("""
       INSERT OR IGNORE INTO tags(sessions_id,tag_id)
           SELECT s.id, t.id from sessions s, tag t
           WHERE s.userid=? and t.tag=?
       """ , (userid,key))
   return res

################### MAIN #######################
if __name__ == "__main__" :
    import sys
    # IGNORE THESE...
    db = sys.argv[1]
