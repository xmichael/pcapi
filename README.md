Personal Cloud API
==================

PCAPI is a storage middleware that abstracts access to Cloud Storage providers. Authentication to external providers like e.g. Dropbox is based on oAuth.

PCAPI is compatible with Fieldtrip-Open.

Installation
------------

The system should have the following packages installed:
 - libxml 
 - libspatialite ( version 3.0 and above )
 - python-bottle ( version >= 0.10 )

```
   sudo apt-get install libxml2-dev libxslt1-dev python-dev
```

Then the application can be executed by either:

 - configuring apache's mod_wsgi to execute src/main/pcapi.py *OR*
 - executing src/main/pcapi.py for the standalone listener ( host/port are adjusted from resources/config.ini )



Troubleshooting:
----------------

The easiest way to find what is wrong is to do the following:

1. Start the application from the command line locally as described above. Look for error messages
2. tail -f pcapi.log (it location is specified in the configuration file)
3. issue commands to localhost *without* the /pcapi/ prefix e.g.

 http://localhost:8080/auth/providers



Directory Tree is organised as follows
--------------------------------------

### Sources:

under ./src:
	wsgi/pcapi.py:
		The main wsgi app. Takes care of handling Routes.
	lib/*.py:
		The actual functionality
	test/:
		the test suite
	resources:
		configuration files in .ini format

### Database/Uploaded Files:

under ./data (unless overriden by "src/resources/config.ini"):
      sessions.db:
	        Spatialite3 file contained sessions and geo data
      <userid>:
		Directory containing chroot of user <userid> 

### Logs:

under ./logs/pcapi.log: 
      All log outputs as configured in "src/resources/config.ini"

License
-------

BSD


**Free Software, Hell Yeah!**
