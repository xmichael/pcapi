"""
Export filter for several formats supported by OGR. Implemented as a singleton.

It is currently implemented as wrapper around ogr2ogr to facilitate prototype and easy of use.
Prerequisites: ogr2ogr installed and specified under resources/config.ini file
"""

import subprocess
from pcapi import logtool, config

LOG = logtool.getLogger("ogr", "filters")
OGR2OGR = config.get("ogr", "ogr2ogr")

TARGET_POSTGIS = "PG:user={USER} dbname={DATABASE} host={HOST} password={PASSWORD}"

def toPostGIS(data, userid):
    """ Export "/data.json" to configured PostGIS database. Assumes an up-to-date data.json.
    Returns: JSON object with status, new tablename, message
    """
    # If an email is used for userid we need to change `@' and `.' to something valid
    # for Postgres tables
    tablename = userid.replace('@','_at_').replace('.','_dot_')
    host = config.get("ogr","database_host")
    database = config.get("ogr","database_database")
    user = config.get("ogr","database_user")
    password = config.get("ogr","database_password")

    target = TARGET_POSTGIS.format( USER=user, DATABASE=database, HOST=host, PASSWORD=password )
    source = data

    call_array = [ OGR2OGR, "-overwrite", "-update", "-f", "PostgreSQL", target, \
        source, "OGRGeoJSON", "-nln", tablename]

    LOG.debug("OGR export: " + `call_array`)

    status = subprocess.call( call_array )
    if (status):
        return { "error": status, "msg":"OGR Export failed"}
    return {"error": 0, "table": tablename, "msg":"Successfully exported to {0}".format(tablename) }

if __name__ == "__main__":
    pass
