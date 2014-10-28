# -*- coding: utf-8 -*-
"""
Module used for synchronizing records to a postgis database.

This can be used for all kinds of things a PostGIS datasource is used for but
our current focus is exposure to geoserver W*S services.

This is implemented as a singleton  (python module) as we only have one postgis
db.
"""

### Initialization code ###
import psycopg2
import psycopg2.extensions

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

def put_record(provider, userid, path):
    """
    Will create a postgis representation of record by using UUID_EDITOR as
    name of the table and record as a row. If the table does not exist, it will be created.
    
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
    return True

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
    # stub
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
