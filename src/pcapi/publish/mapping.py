""" This module is responsible for the mapping between json properties and postgis 
SQL Data Definition and Data Manipulation Language (DDL & DML) i.e schema and data"""

import json, re

from pcapi import logtool
log = logtool.getLogger("mapping", "pcapi.publish")


def mapping(js_rec,userid):
    """ Takes records as json and returns and array of [<tablename>, <title>, <DDL>, <DML>] 
    values for SQL substitution.

    Furthermore, it adds userid and "compulsory QA values" e.g. pos_acc    
    """

    # parse record json
    rec = json.loads(js_rec)

    # check if table exists -- defined by editor field without the ".edtr" extension
    # However there is an unresolved FTOpen bug where sometimes the ".edtr" is missing.
    if( len(rec["properties"]["editor"]) == 41 ):
        tname = rec["properties"]["editor"][:-5]
    else:
        tname = rec["properties"]["editor"]
        log.debug('Workaround -- record {0} sent without ".edtr" suffix'.format(rec["name"]))
    tname = whitelist_table(tname)
    # title is purely for making people using geoserver directly
    if ( rec["properties"].has_key("title") ):
        title = rec["properties"]["title"]
    else:
        title = tname # fallback to tablename
    ## DDL for table creation
    ddl = ["userid TEXT",]
    ddl.append("QA_name TEXT") # Use QA_name instead of name to avoid breaking QA WPS
    ddl.append("timestamp TEXT")    
    ## DML for field properties
    dml = [userid,]
    dml.append(rec["name"])
    dml.append(rec["properties"]["timestamp"])    
    for p in rec["properties"]["fields"]:
        # assuming all are TEXT for now
        ddl.append('"%s" TEXT' % whitelist_column(p["label"]))
        # If "val" is missing (this is a common FTOpen regression), add an empty field 
        if not p.has_key("val"):
            p["val"] = ""
        # convert images to relative URLs
        if p["id"].startswith("fieldcontain-image-"):
            value = "{0}/records/{1}/{2}".format(userid, rec["name"], p["val"])
        else:
            # assuming verbatim value
            value = p["val"]
        dml.append(value)
    ## Add mandatory QA values
    ddl.append("pos_acc REAL")
    dml.append(rec["properties"]["pos_acc"])
    ## Add mandatory "id". Check if exists for backwards compatibility
    if rec["properties"].has_key("id"):
        ddl.append("record_id TEXT")
        dml.append(rec["properties"]["id"])
    ## Geometry(!)
    # Using new PostGIS 2.0 functions that don't rely on AddGeometryColumn and 
    # can parse GeoJSON with custom crs
    if not rec["geometry"].has_key("crs"):
        #Assumme 4326 if source geometry has no crs field
        rec["geometry"]["crs"] = {"type":"name", "properties":{"name":"EPSG:4326"} }
    # target geometry is always 4326
    ddl.append('geom geometry({0},4326)'.format(rec["geometry"]["type"]))
    dml.append( json.dumps(rec["geometry"]))
    res = [ tname, title, ddl, dml ]
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
    and we must somehow blacklist suspicious input 
    
    Furthemore, we need to escape spaces with underscores because the GML breaks when 
    ,amongs other things, variables have spaces in them (well done again) 
    e.g. "Goodbye Cruel World" would become "Goodbye_Cruel_World"
    
    Moreover, (will this ever end?) COBwEB's QA will crash when certain exotic
    names like "description" are used so quote them e.g. description -> QA_description
    
    Furthermore, escape "%" to "%%" for psycopg2
    """
    if ( ';' in column_name ):
        raise Exception("Illegal column name: %s" % column_name)
    if column_name == "description":
        return "QA_description"
    if column_name == "location":
        return "QA_location"
    if column_name == "metaDataProperty":
        return "QA_metaDataProperty"
    if column_name == "boundedBy":
        return "QA_boundedBy"
    return column_name.replace(" ","_").replace("%","%%")


if __name__ == "__main__":
    import sys
    # use this default record unless we have argv[1]
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
            "title":  "Thy Survey",
            "fields": [
                {
                    "id": "fieldcontain-textarea-1",
                    "val": "",
                    "label": "Description with Space"
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
            "timestamp": "2014-10-27T15:14:51.335Z",
            "id": "_9vqvi15sp"
            },
        "name": "Audio (27-10-2014 15h14m39s)"
        }"""
    if len(sys.argv) == 2:
        with open (sys.argv[1]) as f:
            rec = f.read()
    print rec
    fields = mapping (rec, "userid")
    print "FIELDS"
    print `fields`
    print "PostGIS translation"
    sid = fields[0]
    ddl= fields[2]
    table = "sid-" + sid
    create_query = u'CREATE TABLE IF NOT EXISTS "{0}" ({1});'.format(table,\
    u", ".join(ddl))
    print create_query
