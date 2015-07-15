""" Convert PCAPI's GeoJSON to a simple GeoJSON file that is specifically parsable by QA"""

import json, re, sets

from pcapi import logtool
log = logtool.getLogger("json2qa", "pcapi.publish")

def dbg(x):
    print x

def mapping(recs, normalize=True):
    """ Takes records as json featurecolletion (parsed) and returns a new "flat" featurecolletion with compatible with "simple features"
    encoding that will rename all properties in a way that doesn't break QA.
    
    @param {dict} recs -- JSON (parsed) as produced by PCAPI with id,val,label triplets
    @param Normalize -- Whether to add null properties where appropriate to make sure all features have the exact same parameters.
    @returns {dict} flat GeoJSON, compatible with QA
    """

    headers = sets.Set()
    for i in xrange ( len(recs["features"]) ):
        dbg("processing {0}".format(str(i)))
        rec = recs["features"][i]
        # Move all properties.fields on top to properties and remove fields
        for p in rec["properties"]["fields"]:
            h = whitelist_column(p["label"])
            # If "val" is missing (this is a common FTOpen regression), add an empty field 
            if not p.has_key("val"):
                p["val"] = ""
            value = p["val"]
            # move properties.fields on top to rec.properties
            rec["properties"][h] = value
        del rec["properties"]["fields"]

        ## Add mandatory "id". Check if exists for backwards compatibility
        if rec["properties"].has_key("id"):
            rec["properties"][u"record_id"] = rec["properties"]["id"]
            del(rec["properties"]["id"])

        # Using new PostGIS 2.0 functions that don't rely on AddGeometryColumn
        if not rec["geometry"].has_key("crs"):
            #Assumme 4326 if source geometry has no crs field
            rec["geometry"]["crs"] = {"type":"name", "properties":{"name":"EPSG:4326"} }
        
        # name to properties.qa_name
        if rec.has_key("name"):
            rec["properties"][u"qa_name"] = rec["name"]
            del(rec["name"])

        # Process properties != fields
        for p in rec["properties"]:
            headers.add(p)            

    # optional.. use a superschema as a minimum denominator with properties from all observations to normalize them by
    # adding null values where necessary. The end result should be a featurecolletion with same schema for all features.
    if normalize:
        for rec in recs["features"]:
            for h in headers:
                if not rec["properties"].has_key(h):
                    dbg("adding null value for property '{0}' in record '{1}'".format(h, rec["properties"]["qa_name"]))
                    rec["properties"][h] =  None;    
    return recs

def whitelist_column(column_name):
    """ 
    We need to escape spaces with underscores because the GML breaks when 
    ,amongs other things, variables have spaces in them (well done again) 
    e.g. "Goodbye Cruel World" would become "Goodbye_Cruel_World"
    
    Moreover, COBwEB's QA will crash when certain exotic names like "description" 
    are used so quote them e.g. description -> QA_description
    """
    if column_name == "description":
        return "QA_description"
    if column_name == "location":
        return "QA_location"
    if column_name == "metaDataProperty":
        return "QA_metaDataProperty"
    if column_name == "boundedBy":
        return "QA_boundedBy"
    return column_name.replace(" ","_")


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        with open (sys.argv[1]) as f:
            recs_js = f.read()
    recs = json.loads(recs_js)
    recs_out = mapping(recs)
    #print ( logtool.pp(recs))
    json.dump( recs_out, open( "qa.geojson", 'w'))
