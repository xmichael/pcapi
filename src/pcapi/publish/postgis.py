# -*- coding: utf-8 -*-
"""
Module used for synchronizing records to a postgis database.

This can be used for all kinds of things a PostGIS datasource is used for but
our current focus is exposure to geoserver W*S services.

This is implemented as a singleton  (python module) as we only have one postgis
db.
"""

### Initialization code ###
import os

import psycopg2
import psycopg2.extensions

from pcapi.fs_provider import FsProvider
from pcapi.publish import mapping, geoserver

# Needed for transparent unicode support
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

from pcapi import config, logtool

log = logtool.getLogger("postgis", "pcapi.publish")

# full path of PostGIS database
host = config.get("pg","database_host")
database = config.get("pg","database_database")
user = config.get("pg","database_user")
password = config.get("pg","database_password")

log.debug("Starting connection with PostGIS database: {0}@{1}".format(user,password))

# When host is not supplied then default to peer (UNIX sockets) authentication
conn_string = "dbname={database} user={user}".format(database=database, user=user)
if host:
    conn_string += " host={host} password={password}".format(host=host, password=password)

# NOTE: mod_wsgi could initialize these global variables in *different* processes for each request.
con = None

def execute(sql, args=()):
    """
        Execute *sql* statement using list *args* for sql substitution.
        
        Args:
            sql (str):  SQL statement
            args (list) : (optional) list of susbtitution values
            
        Returns:
            Dictionary with:
                columns (list): columns names (or None if no output)
                rows (list): rows (or None if no output)
                status (str): status message from postgres
    """
    # Start connection if None
    global con
    if not con:
        con = psycopg2.connect(conn_string)
        con.set_session(autocommit=True)

    with con.cursor() as cur:
        cur.execute(sql, args)
        con.commit()
        try:
            res = cur.fetchall()
            rows = res
            columns = [ x[0] for x in cur.description ]
        except psycopg2.ProgrammingError:
            #Thrown when there is no result (go figure)
            rows = None
            columns = None
        status = cur.statusmessage
    return { "columns": columns, "rows": rows, "status": status }

######## High Level Record Functions #########

def put_record(provider, userid, path):
    """
    Will create a postgis representation of record by using "Session ID" (taken 
    from SID.edtr) as name of the table and record contents/assets as a row. If 
    the table does not exist, it will be created.
    
    Normally we should have used UUID for each table and EDITOR as a column,
    however geoserver seems to only support the-whole-table as a Layer... hence the
    ugly solution.
    
    Args:
        provider, userid, path    
    Returns (bool):
        True: Success
        False: Error -- see logs
    """
    log.debug("Postgis INSERT: %s , %s , %s" % (provider, userid, path))
    ## Fetch Record file using userid and fsprovider
    record_path = FsProvider(userid).realpath(path)
    with open(os.path.join(record_path,"record.json")) as f:
        record_data = f.read()
        ## Create mapping
        fields = mapping.mapping(record_data,userid)
        
    sid = fields[0] # table is whitelisted as psycopg does not allow table escaping
    title = fields[1] # human readable survey title to keep geoserver/portal happy
    ddl= fields[2] # columns are also whitelisted as psycopg... column escaping
    dml=tuple(fields[3]) # tuples are necessary to make scheme-like expansions
    table = "sid-" + sid # prefix "sid-" because numbers breaks WFS
    
    res = { "msg": "", "status":"", "error": 0 }
    res2 = res
    
    # This is necessary because of psycopg2 escape limitations for functions like ST_Xxx
    query = 'INSERT INTO "{0}" VALUES ({1} ST_GeomFromGeoJSON(%s) ) RETURNING true;'.format(table, \
        "%s, "* (len(dml)-1) )
    try:
        res = execute(query,dml)
        res = res["status"] if res.has_key("status") else `res`
        # table exists        
    except psycopg2.ProgrammingError:
        ### TABLE does not exist so CREATE it ###
        con.rollback() # necessary after failures
        log.info('Table "{0}" does not exist. Creating...'.format(table))
        try:
            create_query = u'CREATE TABLE IF NOT EXISTS "{0}" ({1});'.format(table,\
            u", ".join(ddl))
            log.debug(create_query)
            res = execute(create_query)
        ### Sometimes many threads try to create the table for the "first time"so ignore them,
        except (psycopg2.IntegrityError, psycopg2.ProgrammingError):
            log.debug("Caught race condition: more than 1 thread trying to create database")
            log.debug("Ignoring extra CREATE calls")
            con.rollback() # rollback not necessary as we use "autocommit" but good to have.
        ### INSERT again, now with a table
        log.debug('Query:\n    {0}'.format(query))
        log.debug('Data:\n    {0}'.format(dml))
        res2 = execute(query,dml)
        res = "{0} {1}".format(res["status"], res2["status"])
        log.debug(res) # join status messages of CREATE and INSERT
        # Publish to geoserver if this is enabled in the configuration file
        geoserver.publish(table, title, "cobweb", sid)
    return { "error":0, "message": res } 

def delete_record(provider, userid, path):
    """
    Delete the record that is stored in the postgis database.
    
    If the record is not in the database or if there is some other kind of error
    it will just return False.
    
    Args:
        provider, userid, path
    Returns (bool):
        True: Success
        False: Error -- see logs
    """
    log.debug("Postgis DELETE: %s , %s , %s" % (provider, userid, path))
    return True

def table_exists(tablename):
    """ Returns True if table exists else False """
    # no needed. Better use exceptions.
    res = execute("SELECT EXISTS( SELECT * FROM information_schema.tables WHERE table_name = %s )", (tablename,))
    return res["rows"][0][0]

if __name__=="__main__":
    print "Starting connection with PostGIS database: " + conn_string
    print `execute("CREATE TABLE IF NOT EXISTS test (id serial PRIMARY KEY, num integer, data varchar);")`
    print `execute("INSERT INTO test (num, data) VALUES (%s, %s)",(100, "abc'def"))`
    print `execute("SELECT * FROM test;")`
    if table_exists("test"):
        print "test exists"
    print `execute("DROP TABLE test;")`
