#FS Provider tries to be "loosely" dropbox compliant to make your life a bit easier especially regarding the Metadata object

# WARNING!!! 
# No `/' directory will be created unless you upload a file first. This is to avoid 
# a mess by clients calling /auth/local repeatedly and creating a new users every time without authentication.
# Might revisit once we have authentication in place!


import os, time, shutil, re
import logtool, config, helper

from pcapi_exceptions import FsException

log = logtool.getLogger("FsProvider", "pcapi")

class Metadata(object):
    """ metadata of files/dir as returned from local filesystem. This is plain filesystem 
    metadata and NOT high-level pcapi metadata for records or editors"""
    
    def __init__ (self, md):
        self.md = md

    def __str__(self):
        return `self.md`
        
    def mtime(self, fmt=None):
        """ Return last modification time of self.
        Args:        
            fmt (optional): format (s. strftime() system call) for the output date
        Returns: 
         a date string in format described in "fmt" as in strftime. If no
        format is specified then seconds since unix epoch are returned. This is useful for date comparisons.
        
        Timezones are ignored (assuming GNT) and invalid mtimes return None
        """
        
        # Dropbox format. Last 5 characters are for timezone
        try:
            tm = time.gmtime(self.md["modified"])
            if not fmt:
                return time.mktime(tm)
                return time.strftime(fmt,tm)
        except ValueError:
            log.exception("ValueError. Should not happen. Could not parse mtime: \n"\
                                + self.md["modified"][:-6])            
            return None
    
    def ls(self):
        """ Contents of directory (or just the file) """            
        if self.is_dir():
            return [ x["path"] for x in self.md["contents"] ]
        else:
            return self.md["path"]
    
    def lsdirs(self):
        """ list only directories """
        if self.is_dir():
            return [ x["path"] for x in self.md["contents"] if x["is_dir"] == "true" ]
        else:
            return []

    def path(self):
        """ return path of file/dir """
        return self.md["path"]
    
    def is_dir(self):
        return True if self.md["is_dir"] == "true" else False
        

class FsProvider(object):
    """
        Local filesystem provider
    """

    ## STATIC variables
    EMAIL_RE = re.compile(r'[^@ ./]+@[^@ ./]+\.[^@ ./]+$')
    HEX_RE = re.compile(r'[0-9a-fA-F]+$')
    
    def __init__(self, userid):
        """ Args:
                userid (string) : Userid (aka request key) of user. 
                    Only valid emails or hexnums are allowed
        """
        if not ( FsProvider.EMAIL_RE.match(userid) or FsProvider.HEX_RE.match(userid) ):
            raise FsException("Illegal userid: %s -- should either HEX or EMAIL" % userid)
        self.userid = userid
        # Full path pointing to the user's sandbox *directory*
        self.basedir = config.get("path", "data_dir") + "/" + userid
    
    def login(self):
        """ Login -- This is currently dummy as there is no login
            
            Returns:
                a json repose with state=1 and userid
        """
        return { "state": 1, "userid": self.userid}
        
    def realpath(self, path):
        """ converts chrooted path to real fs path """
        #warning: don't use os.path.join without testing for `//' in path 
        return self.basedir + self._addslash(path)

    def _addslash(self, path):
        """ prepends a "/" to the path """
        # path should start with `/' otherwise add it!
        if path[0] !='/':
            path = "/" + path
        return path

    def put_file(self, path, fp, overwrite):
        """ Save file handler fp contents at path 
        Args:
            path (str) : chroot based path including filename
            fp (File) : file pointer pointing to data
            overwrite (bool): overwrite the file if it exists

        Returns:
            string: chrooted path that was actually used. This may be different than the 
                    original in case of existing file, illegal chars etc.

        Raises:
            error exception if the leaf directory already exists or cannot be created
        """
        # create dir if fullfile path has a dir
        # assume filename is everything after last `/'

        # TODO: make whitelisting instead of blacklisting filter!
        # TODO: WARNING: this needs serious auditing before release!

        # path should start with `/' otherwise add it!
        path = self._addslash(path)
        #ban special characters after last `/'
        dirname = helper.strfilter( path[:path.rfind("/")] ,"\\.~" )
        filename = helper.strfilter( path[path.rfind("/"):], "~/" )                
        #create dir if it doesn't exist
        realdir = self.realpath(dirname)
        realfile = os.path.join(realdir, filename)
        if not os.path.exists(realdir):
            log.debug("creating dir: %s" % realdir)
            os.makedirs(realdir, 0770)
        # Check overwrite flag
        if not overwrite:
            if os.path.exists(realfile):
                return path #do nothing
        log.debug("writing file: %s/%s" % (realdir, filename))
        with open ( realdir + "/" + filename , "w" ) as f:
            f.write(fp.read())        
        return path

    def mkdir(self, path):
        """ Wrapper call around create_folder. Returns metadata. 
        If folder already exists we have to implement to "new file name" algorithm.        
        """
        path = self._addslash(path)
        #ban special characters for dirname
        dirname = helper.strfilter( path ,"\\.~" )
        #create dir if it doesn't exist
        realdir = self.realpath(dirname)
        if not os.path.exists(realdir):
            log.debug("creating dir: %s" % realdir)
            os.makedirs(realdir, 0770)
            return self.metadata(path)
        else:
            # File already exists. Find the next filename (XXX) available 
            # by calling this function recursively. (Can be much faster
            # by first checking the results of ls before doing the recursion)
            numlist = re.findall(".* \(([0-9]*)\)$",path)
            if numlist:
                num = numlist[0]
                newpath = path[:path.rfind(num)-2] + " (%d)" % ( int(num) + 1 )
            else:
                newpath = path + " (1)"
            log.debug("mkdir(): folder collisions. Trying new name: %s" % newpath)
            return self.mkdir(newpath)

    def ls(self,path):
        """ List contents of chrooted path """
        return self._addslash( os.listdir(self.realpath(path)))
    
    def upload(self,name, fp, overwrite=False):
        """ Upload the media file stream fp
        Args:
            name (str): destination path of file in sandbox with directories 
                        created on-the-fly e.g. "/foo.jpg" for apps/pcapi/foo.jpg
            fp (File): the file object to upload.
            overwrite (bool): whether to overwrite the file or save under a new name
        
        Returns: Dictionary of Metadata of uploaded file.
                 similar to https://www.dropbox.com/developers/reference/api#metadata-details
        
        Raises:
            FsException
        """
        log.debug("uploading file: " + name)
        new_path = self.put_file(name, fp, overwrite )
        try:
            fp.close()
        except Exception as e:
            log.debug(str(e))
        return self.metadata(new_path)
            
    def metadata(self,path):
        """ Provides dropbox API-compatible interface for filesystem metadata.
        It reads all informations it cans about <path> and return a Metadata 
        object.
        
        Args:
            path (string): A chroot-relative path of file or directory (e.g. `/')
        
        Returns:
            Metadata: an object with filesystem metadata about path
            
        s.a. https://www.dropbox.com/developers/core/docs#metadata for
        documentation of drobpox's "conventions" which we loosely follow
        
        NOTE: again this is only loosly compatible with dropbox so  compatibility
        issues with AbstractWhataverProvider abstractions could arise.
        """
        path = self._addslash(path)
 
        realpath = self.realpath(path)
        md = {}
        if( not os.path.isdir(realpath) ):
            # It is a file
            md["path"] = path
            md["is_dir"] = "false"
            md["modified"] = os.path.getmtime(realpath) #in epoch seconds
            md["bytes"] = os.path.getsize(realpath)
        else:
            #It is a directory. 
            # List files but DON'T just recurse because we only want depth level 1.
            md["path"] = path
            md["is_dir"] = "true"
            md["modified"] = os.path.getmtime(realpath) #in epoch seconds
            contents = []
            for f in os.listdir(realpath):
                fpath = os.path.join(path,f)
                realfpath = os.path.join(realpath,f)
                if os.path.isdir(realfpath):
                    #we only need paths
                    contents.append( { "path": fpath, "is_dir" : "true" } )
                else:
                    realfpath = self.realpath(fpath)
                    contents.append( { \
                        "path" : fpath, \
                        "is_dir" : "false", \
                        "modified" : os.path.getmtime(realfpath), \
                        "bytes" : os.path.getsize(realfpath)\
                    })
            md["contents"] = contents
        return Metadata(md)
        
    def get_file_and_metadata(self, from_path, rev=None):
        """ Added for dropbox-API compatibility
        
        Returns:
            Tuple containing HttpResponse as well as parsed metadata as a dict.
            (s. https://www.dropbox.com/developers/core/docs#metadata)
        """
        f = open (self.realpath(from_path))
        m = self.metadata(from_path)
        return f,m
 
    def exists(self, path):
        """ Check if path exists """
        return True if os.path.exists(self.realpath(path)) else False
   
    def sync(self, cursor=None):
        """ Converts returns files that were created or modified from specified time/cursor
        
        Args:
            cursor(int): UNIX epoch in seconds
        
        returns:
            List of updated/created files in json format { "updated" = [file1,file2,...] }
        
        NOTE: Unlike dropbox sync, this call will NOT include deleted files!
        """
        #curent time as unix epoch
        epoch = int(time.mktime(time.localtime()))
        # If we don't have a cursor create a new one
        updated = []
        deleted = []
        if not cursor:
            return { "cursor" : epoch }
        # Else just return { "updated" : ...  , "deleted": .. }
        try:
            cur_time = int(cursor)
        except ValueError:
            return { "error" : 1, "msg": "Invalid cursor. Must be a positive integer"}
        for root,dirs,files in os.walk( self.realpath('/') ):  
            for f in files:
                fpath=os.path.join(root,f)
                mtime=os.stat(fpath).st_mtime    
                if cur_time < mtime:
                    #fpath is full fs path, real_fname is relative to chroot
                    rel_fname = fpath[len(self.basedir):]
                    updated.append(rel_fname)
        return { "updated": updated, "deleted": deleted }

        
    def file_delete(self,path):
        """ Delete file and return parsed metadata"""
        m = self.metadata(path)
        f = self.realpath(path)
        if (os.path.isdir(f)):
            shutil.rmtree(f)
        else:
            os.remove(f)
        return Metadata(m)

if __name__ == "__main__":
    userid = "testuser"
    fp = FsProvider(userid)
    #list metadata   
    fp.metadata("/")
    # upload
    uploadData = open ( config.get("test","textfile") )
    print "put_file -> " + fp.put_file("/Myfile.test" , uploadData)
    #### now list directory ##
    print "================================"
    print "ls -> " + `fp.ls("/")`    
    #### now delete the file ##
    print "================================"
