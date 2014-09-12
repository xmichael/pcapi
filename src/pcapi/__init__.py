import os


def get_resource(filename):
    """ Get the location of resource in the package """
    pwd = os.path.abspath(os.path.dirname(__file__))
    return os.path.normpath(os.path.join(pwd, '..', 'resources', filename))
