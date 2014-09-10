## Just some static utility functions that didn't justify the creation of a class
#################

def strfilter(text , remove):
    """
    remove chars defined in "remove" from "text"
    """
    return ''.join([c for c in text if c not in remove])

def basename(filename):
    """ Converts uploaded filename from something like "C\foo\windows\name.zip to name """
    #remove suffix
    tmp = filename
    tmp = tmp[ :tmp.rfind('.')]
    #remove funny chars
    return strfilter(tmp , "\\/")
