## This is a Singleton class to return values stored under resources/config.ini.
## Read that file for documentation of values.
## note to java coders: Singletons in python are just modules with plain functions.

"""
For an explanation of each config. item see comments in resource/config.ini
"""

import ConfigParser
import sys
import os

config = ConfigParser.SafeConfigParser()


def get(section, key):
    return config.get(section, key)


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

pc_api_dir = os.getcwd()
config.add_section('path')
config.set('path', 'pcapi', pc_api_dir)
config.add_section('test')
config.set('test', 'test_dir', os.sep.join((pc_api_dir, 'pcapi', 'test')))

home = os.path.expanduser("~")

# init config
config_paths = []
config_paths.append(os.path.join(home, '.config', 'pcapi', 'pcapi.ini'))
config_paths.append(os.path.join(pc_api_dir, 'pcapi.ini'))

# combine the config files
found_paths = config.read(config_paths)

if len(found_paths) == 0:
    print 'Not config files found in the default locations tried:'
    for path in config_paths:
        print path
    sys.exit(-1)
else:
    print 'Using the following config files'
    for path in found_paths:
        print path
