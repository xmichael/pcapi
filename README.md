Personal Cloud API
==================

PCAPI is a **storage middleware** that abstracts access to Cloud Storage providers in addition to its own local storage. Authentication to external providers like e.g. Dropbox is based on oAuth.

PCAPI is compatible with the [Fieldtrip-Open](https://github.com/edina/fieldtrip-open) framework for building mobile apps.

Installation
------------
Installation is based on the official python PIP tool. It is included in most linux distributions and is also readily available on Windows, OS X using the upstream [instructions](https://pip.pypa.io/en/latest/installing.html)

In short, you can install PCAPI globally, locally or within  a virtual environment just like most sane python packages. For example, to quickly download, install and execute PCAPI as a local user with no special permissions type:

1. `pip install --user git+https://github.com/cobweb-eu/pcapi`
2. `pcapi`

Advanced Configuration
----------------------

By default pcapi will store its default configuration and data file under *$HOME/.pcapi*. One can then edit the file pcapi.ini in that directory to adjust existing configuration or to enable advanced functionality like e.g. publishing data to geoserver (W*S), geonetwork (CSW) services.

PCAPI can also run using apache's mod_wsgi by configuring apache to use *pcapi/server.py* as a wsgi file.

Advanced Deployment
-------------------

There is minimal support for automating deployment to remote servers using [fabric](http://www.fabfile.org). To use it, look at the existing *fabfile.py*.

Troubleshooting:
----------------

The easiest way to find what is wrong is to do the following:

1. Start the application from the command line locally by running `pcapi`. Look for error messages
2. `tail -f ~/.pcapi/logs/pcapi.log` (The actual location is specified in the configuration file)
3. Start issuing REST calls to localhost using a client like *curl* or *wget* e.g.

`curl http://localhost:8080/auth/providers`



Directory Tree is organised as follows
--------------------------------------

### Documentation:

under ./docs:
	All documenation including the current PCAPI REST API specification.

### Sources:

* under `./src/pcapi`:
	* `server.py`: The main wsgi app. Start reading the source here.

	* `data`: default configuration file in .ini format. Configuration is copied to *~/.pcapi* folder during installation.
* under `./src/test`: the test suite. To run it, cd inside that directory and execute: `python -munittest local_usecase`

### Database/Uploaded Files:

All files are under *~/.pcapi/* (unless overriden by +pcapi.ini+):

* `pcapi.ini`:
	        Default configuration file.
* `data/sessions.db`:
	        Spatialite3 file contained sessions and geo data.
* `data/<userid>`:
		Directory containing chroot of user <userid>.
* `logs/pcapi.log`: 
      		All log outputs as configured in +pcapi.ini+.

License
-------

[Modified BSD](./LICENSE)


**Free Software, Hell Yeah!**
