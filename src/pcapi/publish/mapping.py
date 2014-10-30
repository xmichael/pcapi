""" This module is responsible for the mapping between json properties and postgis DDL / DML """

import json

def mapping(js_rec):
    """ Takes records as json and returns and array of [<tablename>, <DDL>, <DML>] values for SQL substitution """

    # parse record json
    rec = json.loads(js_rec)

    # check if table exists -- defined by editor field
    tname =  rec["properties"]["editor"]
    # DDL for creatign table
    ddl = []
    # DML for inserting properties
    dml = []
    for p in rec["properties"]["fields"]:
        # assuming all are TEXT for now
        ddl.append("%s TEXT" % p["label"])
        # assuming verbatim value
        dml.append(p["val"])
    res = [ tname, ddl, dml ]
    return res

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
            "pos_acc": "",
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
    print `mapping (rec)`
