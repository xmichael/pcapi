""" This module is responsible for the mapping between json properties and postgis DDL / DML """

import json, re

def mapping(js_rec,userid):
    """ Takes records as json and returns and array of [<tablename>, <DDL>, <DML>] 
    values for SQL substitution.

    Furthermore, it adds userid and "compulsory QA values" e.g. pos_acc    
    """

    # parse record json
    rec = json.loads(js_rec)

    # check if table exists -- defined by editor field without ".edtr" extension
    tname =  rec["properties"]["editor"][:-5]
    tname = whitelist_table(tname)
    ## DDL for creatign table
    ddl = ["userid TEXT",]
    ddl.append("name TEXT")
    ddl.append("timestamp TEXT")    
    ## DML for field properties
    dml = [userid,]
    dml.append(rec["name"])
    dml.append(rec["properties"]["timestamp"])    
    for p in rec["properties"]["fields"]:
        # assuming all are TEXT for now
        ddl.append("%s TEXT" % whitelist_column(p["label"]))
        # assuming verbatim value
        dml.append(p["val"])
    ## Add mandatory QA values
    ddl.append("pos_acc REAL")
    dml.append(rec["properties"]["pos_acc"])
    ## Geometry(!)
    # Assume caller will use "AddGeometryColumn" on ddl when creating the table
    lon, lat = rec["geometry"]["coordinates"]
    dml.append( 'POINT({0} {1})'.format(lon,lat))
    res = [ tname, ddl, dml ]
    return res

def whitelist_table(tablename):
    """ Checks if tablename is dodgy. Psycopg cannot escape tablename (well done!)
    and we must somehow blacklist suspicious input """
    TABLE_RE = re.compile(r'[;()]')
    if ( TABLE_RE.match(tablename) ):
        raise Exception("Illegal tablename: %s" % tablename)
    return tablename

def whitelist_column(column_name):
    """ Checks if column is dodgy. Psycopg cannot escape columnnames(well done!)
    and we must somehow blacklist suspicious input """
    if ( ';' in column_name ):
        raise Exception("Illegal column name: %s" % column_name)
    return column_name


if __name__ == "__main__":
    rec = """{
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [
                -3.1790516550278154,
                 55.936591761403896
                 ]
            },
        "properties": {
            "editor": "audio.edtr",
            "fields": [
                {
                    "id": "fieldcontain-textarea-1",
                    "val": "",
                    "label": "Description"
                    },
                {
                    "id": "fieldcontain-audio-1",
                    "val": "audio113.m4a",
                    "label": "Audio"
                    }
                ],
            "pos_sat": "",
            "pos_acc": 37,
            "pos_tech": "",
            "dev_os": "",
            "cam_hoz": "",
            "cam_vert": "",
            "comp_bar": "",
            "temp": "",
            "press": "",
            "dtree": [],
            "timestamp": "2014-10-27T15:14:51.335Z"
            },
        "name": "Audio (27-10-2014 15h14m39s)",
        "id": "_9vqvi15sp"
        }"""
    print rec
    print `mapping (rec, "userid")`
