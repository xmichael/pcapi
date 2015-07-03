import bottle
from bottle import route, request, response, static_file, hook
## pcapi imports
from pcapi import logtool
from pcapi import config
from pcapi import varexport

from pcapi.rest import PCAPIRest

log = logtool.getLogger("pcapi")

################ ROUTES ####################

#######################################################
###  Rest Callbacks (can be tested with wget/curl)  ###
#######################################################

###  Provider capabilities ###

@route('/auth/providers',method=["GET"])
def capabilities():
    return PCAPIRest(request,response).capabilities()

### /export/ a  public URL
@route('/export/<provider>/<userid>/<path:path>', method=["GET"])
def export(userid, provider, path="/"):
    return PCAPIRest(request,response).export(provider, userid, path)

### /exportvargeoj/... ###
@route('/exportvargeoj/<path:path>',method=["GET"])
def exportvargeoj(path):
    return varexport.export(path)

###  /sync/... API ###
@route('/sync/<provider>/<userid>')
@route('/sync/<provider>/<userid>/<cursor>')
def sync(userid, provider, cursor=None):
    return PCAPIRest(request,response).sync(provider, userid, cursor)

###  /sync/... API ###
@route('/backup/<provider>/<userid>/<folder>', method=["GET"])
def backup(provider, userid, folder):
    return PCAPIRest(request,response).backup(provider, userid, folder)

###  /assets/... API ###
@route('/records/<provider>/<userid>/assets/',method=["GET","PUT","POST","DELETE"] )
@route('/records/<provider>/<userid>/assets/<path:path>',method=["GET","POST","PUT","DELETE"] )
def assets(provider, userid, path="/"):
    flt = request.GET.get("frmt")
    return PCAPIRest(request,response).assets(provider, userid, path, flt)

###  /records/... API ###
@route('/records/<provider>/<userid>/',method=["GET","PUT","POST","DELETE","OPTIONS"] )
@route('/records/<provider>/<userid>/<path:path>',method=["GET","POST","PUT","DELETE","OPTIONS"] )
def records(provider, userid, path="/"):
    flt = request.GET.get("filter")
    ogc_sync = True if request.GET.get("ogc_sync") else False
    return PCAPIRest(request,response).records(provider, userid, path, flt, ogc_sync)

###  /editors/... API ###

@route('/editors/<provider>/<userid>/',method=["GET","POST","PUT","DELETE","OPTIONS"] )
@route('/editors/<provider>/<userid>/<path:path>',method=["GET","POST","PUT","DELETE","OPTIONS"] )
def editors(provider, userid, path="/"):
    flt = request.GET.get("format")
    return PCAPIRest(request,response).editors(provider, userid, path, flt)

###  /surveys/... API ###

@route('/surveys/<provider>/<userid>/',method=["GET","POST","PUT","DELETE","OPTIONS"] )
@route('/surveys/<provider>/<userid>/<survey>',method=["GET","POST","PUT","DELETE","OPTIONS"] )
def surveys(provider, userid, survey=None):
    return PCAPIRest(request,response).surveys(provider, userid, survey)

###  /layers/... API ###

@route('/features/<provider>/<userid>/',method=["GET","POST","PUT","DELETE"] )
@route('/features/<provider>/<userid>/<path:path>',method=["GET","POST","PUT","DELETE"] )
def layers(provider, userid, path="/"):
    return PCAPIRest(request,response).features(provider, userid, path)

###  /fs/... API ###

@route('/fs/<provider>/<userid>/',method=["GET","POST","PUT","DELETE","OPTIONS"] )
@route('/fs/<provider>/<userid>/<path:path>',method=["GET","POST","PUT","DELETE","OPTIONS"] )
def fs(provider, userid, path="/"):
    """ Upload file to path (as documented in the API docs)
    """
    return PCAPIRest(request, response).fs(provider, userid, path)

###  /auth/... API ###

# Login to Dropbox.
@route('/auth/<provider>', method='GET')
@route('/auth/<provider>/<userid>', method='GET')
def login(provider,userid=None):
    return PCAPIRest(request, response).login(provider, userid)

### STATIC FILES (html/css/js etc.)###

def init_static_routes():
    """ Call this function to setup static routes using the documentroot defined in config.ini """
    root = config.getStaticHTML()
    @route('/<filename:re:(?!ws/).*>')
    def serve_static(filename):
        return static_file(filename, root=root, download=False)

    @route('/')
    def default_static():
        return static_file('index.html', root=root, download=False)

########## CORS ##################

@hook('after_request')
def enable_cors():
    log.debug("persistent-id " + `request.headers.get('persistent-id')`)
    #here's the id we need for uploading data
    log.debug("persistent-id: " + `request.headers.get('employeeNumber')`)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS, DELETE'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept'

### Error pages ###
@bottle.error(404)
def error404(error):
    return ['NO PC-API endpoint at this URL:\n', request.environ["REQUEST_URI"], "\n"]

