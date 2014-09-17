import argparse
import os
import shutil

from pkg_resources import resource_filename


def create_skeleton(path):
    if os.path.exists(path):
        print 'Directory already exist'
        return False

    config_file = resource_filename('pcapi', 'data/pcapi.ini.example')
    wsgi_file = resource_filename('pcapi', 'wsgi/pcapi.wsgi')
    server_file = resource_filename('pcapi', 'server.py')
    # create the folder structure
    os.makedirs(os.path.join(path, 'data'))
    os.makedirs(os.path.join(path, 'logs'))
    project_dir = os.path.abspath(path)

    # copy the config file
    shutil.copyfile(config_file, os.path.join(project_dir, 'pcapi.ini'))
    shutil.copyfile(wsgi_file, os.path.join(project_dir, 'pcapi.wsgi'))
    shutil.copyfile(server_file, os.path.join(project_dir, 'server.py'))
    return True


def parse_commandline():
    # main parser
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='actions',
                                       dest='action')

    # runserver parser
    subparsers.add_parser('runserver', help='run the pcapi server')

    # create parser
    create = subparsers.add_parser('create',
                                   help='create the pcapi instance structure')
    create.add_argument('path',
                        action='store',
                        help='instance path')

    args = parser.parse_args()

    if args.action == 'create':
        if not create_skeleton(args.path):
            return
        print 'Please edit %s/config.ini' % args.path

    elif args.action == 'runserver':
        from pcapi.server import runserver
        runserver()

if __name__ == '__main__':
    parse_commandline()
