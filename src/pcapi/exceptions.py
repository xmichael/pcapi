class PcapiException(Exception):
    """ This class covers all exceptions thrown by the PCAPI

    Typical Handling:
        except SomePcapiException as e:
            msg = e.shortmsg
            log.debug("ExifException: " + msg )
            return { "uuid":uuid, "error":1, "msg": msg }
    """
    # Everything in stderr after executing something or all info regarding wrapped exception
    msg = None
    # A user friendlier shorter version of msg
    shortmsg = None

    def __init__(self, msg):
        self.msg = msg
        self.shortmsg = msg
    def __str__(self):
        return repr(self.msg)

class DBException(PcapiException):
    """ This class covers all exceptions thrown during spatialite accesses """
    pass

class FsException(PcapiException):
    """ This class covers all exceptions thrown during the use of FsProvider """
    pass
