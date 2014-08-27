from fabric.api import env, hosts, lcd, local, task, run, put, prompt, sudo
from fabric.contrib.project import rsync_project
import os, ConfigParser
import getpass

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
config=None

"""
example uses:
for server1:
fab server:'serv1' setup deploy

for server2:
fab server:'serv2' setup deploy

"""

@task
def deploy_local():
    """Defines local environment"""
    env.local = 'local'
    #pcapi
    env.app_name = _config('app_name')
    # ~/local
    env.base_dir = os.sep.join((os.environ['HOME'], env.local))
    # ~/local/pcapi
    env.domain_path = "%(base_dir)s/%(app_name)s" % {'base_dir': env.base_dir, 'app_name': env.app_name}
    # ./etc/requirements.txt
    env.env_file = os.sep.join((CURRENT_PATH, "etc", "requirements.txt"))

    if os.path.exists(env.domain_path):
        # check if they want to delete existing installation
        msg = 'Directory %s exists.\nDo you wish to delete it(y/n)? > '
        msg = msg % env.domain_path
        answer = raw_input(msg).strip()

        if answer != 'y':
            print 'Choosing not continue. Nothing installed.'
            return

        local('rm -rf {0}'.format(env.domain_path))

    with lcd(env.base_dir):
        local('virtualenv {0}'.format(env.app_name))

    with lcd(env.domain_path):
        # initialise virtual environment
        _virtualenv('pip -q install -r {0}'.format(env.env_file))

        # create sql lie
        _install_custom_locally_pysqlite()

        #create symlink for the src
        local("ln -s %(current_path)s/src %(domain_path)s/pcapi" % { 'current_path': CURRENT_PATH, 'domain_path':env.domain_path})
        local("mkdir {0}/data".format(env.domain_path))
        # don't like sudo!!
        #local("sudo chown {0}:www-data {1}/data".format(getpass.getuser(), env.domain_path))
        #local("chmod 775 {0}/data/".format(env.domain_path))
        local("mkdir {0}/logs".format(env.domain_path))
        #local("sudo chown {0}:www-data {1}/logs/".format(getpass.getuser(), env.domain_path))
        #local("chmod 775 {0}/logs/".format(env.domain_path))

def _install_custom_locally_pysqlite():
    path = _prepare_pysqlite()
    local("cd %(path)s; %(domain_path)s/bin/python setup.py install" % {'path': path, 'domain_path':env.domain_path})

def _prepare_pysqlite():
    tmp_path = os.path.join(os.environ['HOME'], "temp")
    if not os.path.exists(tmp_path):
        os.mkdir(tmp_path)
    local("wget -P  %(tmp_path)s %(sqlite_url)s" % {'tmp_path':tmp_path, 'sqlite_url': _config('pysqlite')})
    local("tar -C %(tmp_path)s -zxvf %(tmp_path)s/pysqlite-2.6.3.tar.gz" % {'tmp_path':tmp_path})
    local("cd %(tmp_path)s/pysqlite-2.6.3" % {'tmp_path':tmp_path})
    p = "%(tmp_path)s/pysqlite-2.6.3/setup.cfg" % {'tmp_path':tmp_path}
    _reconfigure_pysqlite_setup(p)
    return "%(tmp_path)s/pysqlite-2.6.3" % {'tmp_path':tmp_path}


def _reconfigure_pysqlite_setup(p):
    f = open(p, "r")
    t = f.read()
    f.close();
    t = t.replace("define=SQLITE_OMIT_LOAD_EXTENSION", "#define=SQLITE_OMIT_LOAD_EXTENSION")
    f = open(p, "w")
    f.write(t)
    f.close()

def _get_ini():
    f = "src/resources/config.ini"
    ini = open(f, "r")
    text = ini.read()
    ini.close()
    return text

@task
def server(serv):
    """Defines live environment live:'serv1' for cutthroat, live:'serv2' for brook"""
    _check_config()
    env.hosts = [_config("hosts", serv),]
    env.user = _config("user", serv)
    env.port = _config("port", serv)
    _server()

def _server():
    env.home = "/home/%s" % env.user
    env.base_dir = "%s/dist" % env.home
    env.app_name = "pcapi"
    env.app_local_name = "src"
    env.domain_path = "%(base_dir)s/%(app_name)s" % { 'base_dir':env.base_dir, 'app_name':env.app_name }
    env.current_path = "%(domain_path)s/current" % { 'domain_path':env.domain_path }
    env.releases_path = "%(domain_path)s/releases" % { 'domain_path':env.domain_path }
    env.env_file = "etc/requirements.txt"
    env.app_local = "./%(app_name)s" % { 'app_name':env.app_local_name }

@task
def setup():
    """Prepares one or more servers for deployment"""
    run("mkdir -p %(domain_path)s" % { 'domain_path':env.domain_path })
    run("mkdir -p %(domain_path)s/etc" % { 'domain_path':env.domain_path })
    put("%(env_file)s" % { 'env_file':env.env_file }, "%(domain_path)s/etc" % { 'domain_path':env.domain_path })
    run("mkdir -p %(releases_path)s" % { 'releases_path':env.releases_path })
    run("mkdir -p %(current)s" % { 'current':env.current_path })
    run("if [ ! -d %(domain_path)s/data ]; then mkdir -p %(domain_path)s/data; fi" % { 'domain_path':env.domain_path })

@task
def deploy():
    """Deploys your project, updates the virtual env then restarts"""
    _update()

def _update():
    """Copies your project and updates environment and symlink"""
    main_version = _checkout()
    _update_env()
    symlink = prompt('Do you want to make it live (=symlink it)? [y/N]')
    _symlink(symlink, main_version)

def _check_config():
    """
    If config.ini exists update from remote location, otherwise prompt user for location
    """
    global config

    root = CURRENT_PATH
    print root
    conf_dir = os.sep.join((root, 'etc'))
    conf_file = os.sep.join((conf_dir, 'config.ini'))
    if not os.path.exists(conf_file):
        msg = '\nProvide location of config file > '
        answer = raw_input(msg).strip()
        if len(answer) > 0:
            if answer.find('@') == -1:
                if os.path.exists(answer):
                    local('cp {0} {1}'.format(answer, conf_file))
                else:
                    print "File not found, can't continue."
                    exit(0)
            else:
                port = _config('location_port')
                if port:
                    local('scp -P {0} {1} {2}'.format(port, answer, conf_dir))
                else:
                    local('scp {0} {1}'.format(answer, conf_dir))

    # pick up any changes from remote config
    location = _config('location')
    print location
    if location[0: 4] == 'git@':
        # config is in secure git repo
        with lcd(conf_dir):
            # work out how deep config file is in directory structure to flatten it
            parts = location.split(' ')
            strip_comp = len(parts[len(parts) - 1].split('/')) - 1

            # fetch file from git repo
            local('git archive --remote={0} | tar -x --strip-components {1}'.format(
                location, strip_comp))
    elif location.find('@') != -1:
        port = _config('location_port')
        if port:
            local("rsync -avz -e 'ssh -p {0}' {1} {2}".format(
                port, location, conf_dir))
        else:
            local('rsync -avz {0} {1}'.format(location, conf_dir))
    config = None # make sure it is re-read

def _checkout():
    """Checkout code to the remote servers"""
    refspec = _find_version()
    #manual = prompt('Do you want to insert the main api version manually? [y/N]')
    #if manual.lower() == "y":
    #    main_version = prompt('Please enter the main version (x.x):')
    #else:
    #    splits = refspec.split(".")
    #    main_version = "%s.%s" % (splits[0], splits[1])
    env.current_release = "%(releases_path)s/%(release)s" % { 'releases_path':env.releases_path, 'release':refspec }
    print env.current_release
    #run("mkdir -p %(current_release)s" % { 'current_release':env.current_release })
    rsync_project(local_dir=env.app_local_name, remote_dir=env.current_release, exclude='.git,.pyc,.gitignore')
    #put("%(app_local)s" % { 'app_local':env.app_local }, "%(current_release)s" % { 'current_release':env.current_release })
    return refspec

def _find_version():
    refspec = local('git tag | sort -V | tail -1 | cut -d"v" -f2', capture=True)
    use_tag = prompt('Use Tagging for installation? [y/N]: ')
    if use_tag == 'y':
        print "Showing the last 5 tags"
        local('git tag | sort -V | tail -5')
        create_tag = prompt('Tag this release? [y/N]')
        if create_tag.lower() == 'y':
            notify("Showing latest tags for reference")
            refspec = prompt('Tag name [in format x.x.x for general tagging or x.x.x.x for pcapi tagging]? ')
            local('git tag %(ref)s -m "Tagging version %(ref)s in fabfile"' % {'ref': refspec})
            local('git push --tags')
    else:
        use_commit = prompt('Build from a specific commit? [y/N] ')
        if use_commit.lower() == 'y':
            refspec = prompt('Choose commit to build from [in format x.x.x]: ')
            local('git stash save')
            local('git checkout v%s' % refspec)
            print "Don't forget to run the command <git stash pop> after the app is installed"
        else:
            refspec = prompt('Create dev folder to build in [e.g. dev]: ')
            if refspec == "":
                refspec = "dev"
    return refspec

def _update_env():
    """Update servers environment on the remote servers"""
    if not env.has_key('current_release'):
        _releases()
    run("cd %(current_release)s; virtualenv --no-site-packages ." % { 'current_release':env.current_release })
    run("cd %(current_release)s; ./bin/pip -q install -r %(domain_path)s/%(env_file)s" % { 'current_release':env.current_release, 'domain_path':env.domain_path, 'env_file':env.env_file })
    run("mkdir -p %(run_folder)s/logs" % { 'run_folder':env.current_release })
    _install_custom_remotely_pysqlite()
    _remote_configure_ini()

def _install_custom_remotely_pysqlite():
    """installs the pysqlite library but with custom cfg file"""
    _prepare_pysqlite_setup()
    tmp_path = os.path.join("%(home)s" % {'home': env.home}, "downloads")
    run("wget -P  %(tmp_path)s https://pypi.python.org/packages/source/p/pysqlite/pysqlite-2.6.3.tar.gz#md5=7ff1cedee74646b50117acff87aa1cfa" % {'tmp_path':tmp_path})
    run("tar -C %(tmp_path)s -zxvf %(tmp_path)s/pysqlite-2.6.3.tar.gz" % {'tmp_path':tmp_path})
    run("cd %(tmp_path)s/pysqlite-2.6.3" % {'tmp_path':tmp_path})
    put("setup.cfg", "%(tmp_path)s/pysqlite-2.6.3" % { 'tmp_path': tmp_path })
    run("cd %(home)s/downloads/pysqlite-2.6.3; %(current_release)s/bin/python setup.py install" % {'home': env.home, 'current_release':env.current_release})
    local("rm setup.cfg")

def _prepare_pysqlite_setup():
    """create the custom setup.cfg"""
    f = open("setup.cfg", "w")
    f.write("[build_ext]\n")
    f.write("#define=\n")
    f.write("#include_dirs=/usr/local/include\n")
    f.write("#library_dirs=/usr/local/lib\n")
    f.write("libraries=sqlite3\n")
    f.write("#define=SQLITE_OMIT_LOAD_EXTENSION\n")
    f.close()

def _remote_configure_ini():
    """create and upload the custom config.ini for the specific server"""
    f = open("config.ini", "w")
    new_path = "pcapi = %(domain_path)s/current" % { 'domain_path':env.domain_path}
    f.write(_get_ini().replace("pcapi = /home/pterzis/local/pcapi", new_path))
    f.close()
    put("config.ini", "%(current_release)s/src/resources/" % { 'current_release':env.current_release })
    local("rm config.ini")

def _symlink(symlink, main_version):
    """Updates the symlink to the most recently deployed version"""
    if symlink.lower() == 'y':
        run("if [ -d %(current_path)s ]; then rm %(current_path)s; fi" % { 'current_path':env.current_path, 'main_version': main_version })
        run("ln -s %(current_release)s %(current_path)s" % { 'current_release':env.current_release, 'current_path':env.current_path })
    else:
        print "You need to run these two commands to make your service live: "
        print "*********************************************************"
        print "if [ -d %(current_path)s ]; then rm %(current_path)s; fi" % { 'current_path':env.current_path }
        print "ln -s %(current_release)s %(current_path)s" % { 'current_release':env.current_release, 'current_path':env.current_path }
        print "*********************************************************"

def _virtualenv(command):
    """run command using virtual environment and the current runtime directory"""
    local('. %s/bin/activate && %s' % (env.domain_path, command))

@task
def restart_devel():
    """Start the application servers"""
    run("$HOME/local/www/bin/apachectl restart")

@task
def live_apache_restart():
    """Restarts your application"""
    sudo("/etc/init.d/httpd restart")

@task
def live_apache_graceful():
    """Apache graceful"""
    sudo("/etc/init.d/httpd graceful")

@hosts('user@server1')
def deploy_server():
    """Deploy server"""
    # app is everything under ./src
    app  = '%s/src/' % local('pwd', capture=True).strip()
    local('rsync --exclude "*.kate-swp" --exclude "*.pyc" --exclude logs --exclude external --exclude data --exclude resources -C -av %s/* %s@%s:~/dist/pcapi/' % (app,
                                                         env.user,
                                                         env.host))

@hosts('user@server2')
def deploy_live_server():
    """Deploy server"""
    # app is everything under ./src
    app  = '%s/src/' % local('pwd', capture=True).strip()
    local('rsync --exclude "*.kate-swp" --exclude "*.pyc" --exclude logs --exclude external --exclude data --exclude resources -C -av %s/* %s@%s:~/dist/pcapi/' % (app,
                                                         env.user,
                                                         env.host))


########Configuration###########
def _config(var, section='install'):
    global config
    if config == None:
        config = ConfigParser.ConfigParser()
        conf_file = os.sep.join((CURRENT_PATH, 'etc', 'config.ini'))
        config.read(conf_file)
    return config.get(section, var)
