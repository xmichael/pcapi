#!/usr/bin/python
#-*- mode: python; -*-
################# INIT ###################
import os, sys

pwd = os.path.dirname(os.path.realpath(__file__))

#root_path = os.path.join(pwd, "../..")
root_path = os.path.join(os.environ['HOME'], "local/pcapi" )
# append the root directory in your python system path
sys.path.append(root_path)
# ... and the environment path to keep config.py happy.
os.environ['ROOT_PATH'] = root_path

print sys.path

## Change working directory so relative paths work
pwd = os.path.dirname(os.path.realpath(__file__))
os.chdir(pwd)

## Also add library to the python path
sys.path.append(os.path.join(pwd,'../lib'))
sys.path.append(pwd)

import pcapi_routes, config, bottle

##################################################
#################### MAIN ########################
##################################################
# check if "debug" is true
debug = True if config.get("server","debug")=="true" else False
bottle.debug(debug)
application = bottle.default_app()
if __name__ == "__main__":
    bottle.run(host=config.get("server","host"), port=config.get("server","port"), debug=debug)
