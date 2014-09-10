## This is a Singleton class to return values stored under resources/config.ini.
## Read that file for documentation of values.
## note to java coders: Singletons in python are just modules with plain functions.

"""
For an explanation of each config. item see comments in resource/config.ini
"""

import ConfigParser
import os

config = ConfigParser.SafeConfigParser()

if 'VIRTUAL_ENV' in os.environ:
    pc_api_dir = os.environ['VIRTUAL_ENV']
else:
    pc_api_dir = os.environ['ROOT_PATH']
config.add_section('path')
config.set('path', 'pcapi', pc_api_dir)
config.add_section('test')
config.set('test', 'test_dir', os.sep.join((pc_api_dir, 'pcapi', 'test')))
config.read(['../resources/config.ini'])

def get(section, key):
    return config.get(section,key)

def getCCMap():
    ccmap = {
             "Default" : "",
             "Zero":"http://creativecommons.org/publicdomain/zero/1.0/",
             "CC-BY":"http://creativecommons.org/licenses/by/3.0",
             "CC-SA":"http://creativecommons.org/licenses/by-sa/3.0",
             "BY-NC-CA":"http://creativecommons.org/licenses/by-nc/3.0",
             "BY-NC-DC":"http://creativecommons.org/licenses/by-nc-nd/3.0"
    }
    return ccmap
