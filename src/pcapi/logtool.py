## Just some utility functions for logging messages. Most important is getLogger.

import sys, pprint, json, logging, config
from logging import handlers

### Constants ###

#################

## Can only log in stderr (or environ['wsgi.errors']) when using WSGI:
def dbg(msg):
    print >> sys.stderr, msg

def pp(obj):
    """
    shortcut for pretty printing a python object on the debug channel
    """
    pprinter = pprint.PrettyPrinter(indent=4)
    return pprinter.pformat(obj)

def jsonpp(obj):
    """
    shortcut for pretty printing a json object on the debug channel
    """
    pp(json.loads(obj))

def getLogger(name, parent=None):
    """ Create a logger with some sane configuration
    Args:
        name (str): name of logger. Should be the name of the file.
        parent (str): name of parent logger to inherit its properties    
    """
    if parent:
        # create child logger that inherits properties from father
        logger = logging.getLogger(parent + "." + name)
    else:
        #create parent logger with new properties
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        # create file handler which logs even debug messages
        #fh = logging.FileHandler(config.get("path","log_file"))
        fh = handlers.TimedRotatingFileHandler(config.get("path","log_file"), when='midnight')
        fh.setLevel(logging.DEBUG)
        # create formatter and add it to the handler
        formatter = logging.Formatter('%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(fh)
    return logger
