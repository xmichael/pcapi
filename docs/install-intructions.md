# Instruction for using PCAPI
Instructions for using the PCAPI for app development. Original documentation can be found [here](https://github.com/xmichael/pcapi/blob/master/docs/PC_design_1_3.odt "API documentation"). Source code is hosted on [Github](https://github.com/xmichael/pcapi "Source code").

### Virtual machine with Ubuntu running

To setup a test server, easiest way is to use a clean Ubuntu installation. You can get a clean installation of Ubuntu running on every operating system with [Virtual Box](https://www.virtualbox.org/wiki/Downloads). You can download the latest version of Ubuntu [here](http://www.ubuntu.com/download/desktop/). [Here](http://www.wikihow.com/Install-Ubuntu-on-VirtualBox) is a guide how to get ubuntu running with in virtualbox. 
  
### Prerequisites on clean Ubuntu installation

You can install the prerequisites by issueing the commands in terminal which are listed after every dash.

* [Fabric](http://www.fabfile.org/) - sudo apt-get install fabric
* virtualenv - sudo apt-get install python-virtualenv
* [Wand](http://docs.wand-py.org/en/0.3.7/) -  sudo apt-get install python-pip && sudo apt-get install libmagickwand-dev && sudo pip install Wand
* libxml2-dev - sudo apt-get install libxml2-dev
* libxslt1-dev - sudo apt-get install libxslt1-dev 
* python-dev - sudo apt-get install python-dev

### Run development server first time

Checkout code, deploy with fabric and run python script in virtualenv by executing the following commands in the terminal:

1.  `git clone https://github.com/xmichael/pcapi.git && cd pcapi`
2.  `fab deploy_local`
3.  `cd ~/local/pcapi`
4.  `. bin/activate`
5.  `python ~/local/pcapi/pcapi/wsgi/pcapi_devel.py`

* When installing, it might complain on some python modules missing, then you can install them with: `sudo easy_install NAME_OF_PACKAGE`. Some package that were missing: dropbox, beautifulsoup4 and then try later.   

Now the PCAPI test server should be running on http://127.0.0.1:8080. You can check it by requesting http://127.0.0.1:8080/auth/local in your browser.

### Making development server accesible to other machines 

1. Make sure that the network adaptor of the VM is running in bridged mode
2. Edit and save `~/local/pcapi/pcapi/resources/config.ini` to set host IP in config file to IP adress of VM machine on local network (get this ip adress by executing `ifconfig` on VM machine)
3. Execute`cd ~/local/pcapi`
4. `. bin/activate`
5. `python ~/local/pcapi/pcapi/wsgi/pcapi_devel.py`

If you experience problems first try to ping the VM from the host machine. If that works try telnet; `telnet IPADRESS PORTNUMBER`. If that works, you know that you do not experience network problems, so therefore the problem is with the (running) server (perhaps it is not running after all?). 

### PCAPI usage

Currently PCAPI does not have authentication for local storage. For the moment this is fine, for the application. Theoretically, nobody knows the URL for the application, so at least it is. As a consequence of this lack of authentication every user is anonymous.  For testing the PCAPI yourself you can create a new user (1), create a new file to create a directory for the user (2)  and (3) start uploading records. In the app itself only (3) will take place, since all the users will upload records to the same userid.  

Down here are some examples how to use the PCAPI. For this I use curl, a commandline tool for sending http requests (and much more). You can install curl by typing `sudo apt-get install curl` in the terminal. 

1. Issue authentication request: 
            `curl http://127.0.0.1:8080/auth/local`
Which returns, if succesfull:
            `{"state": 1, "userid": "7c3474746e9c4067898a3dd4bb7e3a79"}`
2. Create first file if userid has never been used: 
            `curl -X POST --form file=@/path/tosomefile http://127.0.0.1:8080/fs/local/7c3474746e9c4067898a3dd4bb7e3a79/myDirectory/myfilename`
3. Upload a record: 
            `curl --form file=@/path/tosomerecord http://localhost:8080/records/dropbox/EXVLgQ5yVXaS8scB/myrecord/myrecord.json`

The userid can be used for subsequent requests you can use this userid for uploading records and files. For now there is now authentication yet. Nobody knows the URL so it is security through obscurity.
 
### Current record format (custom JSON)

        {
            "editor": "some test form.edtr",
            "fields": [
                {
                    "id": "fieldcontain-image-1",
                    "val": "1400232234488.jpg",
                    "label": "Image"
                },
                {
                    "id": "fieldcontain-textarea-1",
                    "val": "aaaaaa",
                    "label": "Are you crazy?"
                }
            ],
            "name": "Image (16-05-2014 10h23m48s)",
            "point": {
                "lon": -2.61423674216074,
                "lat": 53.75417231374662
            },
            "timestamp": "2014-05-16T09:24:08.620Z"
        }

