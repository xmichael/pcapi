import psycopg2
import sys
import ppygis
import logtool
import socket, struct, fcntl
import config

#DB Constants

HOST = config.get("pg","database_host")
DBNAME = config.get("pg","database_database")
USER = config.get("pg","database_user")
PASSWD = config.get("pg","database_password")

SRID=4326
#Table names
OBSGP='obsgroup'
OBST='observations'
IMGT='images'
POLT='observation_polygons'
DECT='decision'
RECOT='recordobs'
RECUSER='recorduser'


#Observation table
RID='RecordID'
PSAT='pos_sat' # Number of satellites connected to
PACC='pos_acc'
PTECH='pos_tech' # Type of technology used (eg. GPS)
DOS='dev_os'
MMOD='make_model'
IWTH='image_width'
IHHT='image_height'
CHOZ='cam_hoz'
CVERT='cam_vert'
TSTMP='timestamp'
#COMPB='comp_bar' # Compass
AZI='azimuth'
PTH='pitch'
RLL='roll'
#TILT='tilt'
TEMP='temp'
PRESS='press'
GEO='geom'
OBS_INSERT="INSERT INTO "+OBST+"("+RID+","+PSAT+","+PACC+","+PTECH+","+DOS+\
","+MMOD+","+IWTH+","+IHHT+","+CHOZ+","+CVERT+","+TSTMP+","+AZI+","+PTH+","+RLL+","+TEMP+","+PRESS+","+GEO+\
") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"

#Observation group table
OID='oid'
NT='note'

OBSGP_INSERT="INSERT INTO "+OBSGP+"("+OID+","+NT+\
        ","+TSTMP+","+GEO+\
        ") VALUES (%s,%s,%s,%s);"
        

#Image table
PL='polyline'
FL='fileloc'
MRK='marker'
IMG_INSERT="INSERT INTO "+IMGT+"("+PL+","+FL+","+MRK+","+RID+\
        ") VALUES (%s,%s,%s,%s);"
        

#Decision table
OPT='option'
STA='state'
DEC_INSERT="INSERT INTO "+DECT+"("+OID+","+OPT+","+STA+\
        ") VALUES (%s,%s,%s);"
        
#Polygon table
POL_INSERT="INSERT INTO "+POLT+"("+OID+","+GEO+\
        ") VALUES (%s,%s);"
        
#Record observation table
REC_INSERT="INSERT INTO "+RECOT+"("+OID+","+RID+\
		") VALUES (%s,%s);"

#Record user table
USER_ID='UserID'
RU_INSERT="INSERT INTO "+RECUSER+"("+RID+","+USER_ID+\
		") VALUES (%s,%s);"
		
#App Constants
PROP='properties'
NOTE='Note'
TIMES="Time Stamp"
ACC='Accuracy'
IMAGE='Image'
FNAME='File Name'
VA='View Angle'
VER='Vertical'
HOR='Horizontal'
COMPASS='Compass'
AZIMUTH='Azimuth'
PITCH='Pitch'
ROLL='Roll'
#YAW='Yaw'
TPR='Temperature'
PRSS='Pressure'
LS='Location Service'
COORD='coordinates'
MK='Marker'
XVAL='X Value'
YVAL='Y Value'
GEOM='geometry'
FTS='features'
TYPE='type'
POINT='Point'
DEC='Decision'
RIDENT='Record ID'
OSV='OS Version'
MKM='Make and Model'
IWIDTH='Image Width'
IHEIGHT='Image Height'

        
log = logtool.getLogger("Export Variable GeoJSON", "pcapi")

def export(path):
    try:
        import config, json
        file = open(config.get("path", "data_dir") + "/"+path,'r')
        flooddata=file.read()
        geojflood = json.loads(flooddata)
        
        fts=geojflood[FTS]
        plat=-1000
        plon=-1000
       
        img=[]
        polyCoord=[]
       
        for feat in fts:
            geo = feat[GEOM]
            coord=geo[COORD]
            if geo[TYPE] == POINT:
               
                if plat == -1000:
                   
                    plat=coord[0]
                    plon=coord[1]
                    timeSt=feat[PROP][TIMES]
                else:
                    prop=feat[PROP]
                    
                    marker=prop.get(MK)
                    
                    if marker == None:
                    	mkX=''
                    	mkY=''
                    else:
                    	mkX=marker[XVAL]
                    	mkY=marker[YVAL]
                    	
                    polyline=prop.get(PL)
                    if polyline==None:
                    	polyline=''
                    temperature=prop.get(TPR)
		    if temperature==None:
			temperature='nan'
		    
		    pressure=prop.get(PRSS)
		    if pressure==None:
			pressure='nan'
          	    viewAngle=prop[VA]
		    compass=prop[COMPASS]        
                    img.append(Img(prop[RIDENT],prop[FNAME],prop[TIMES],prop[ACC],viewAngle[VER],viewAngle[HOR],\
                    compass[AZIMUTH],compass[PITCH],compass[ROLL],prop[LS],coord[0],coord[1],mkX,mkY,polyline,temperature,pressure))
            else:
                for crd in coord[0]:
                    lat=crd[0]
                    lon=crd[1]
                    polyCoord.append(ppygis.Point(lon, lat))   
   
        fcProp=geojflood[PROP]
        note=fcProp[NOTE]
        oid=path[path.rindex('/')+1:path.rindex('.')]
        userid=path[0:path.index('/')]
	
        osver=fcProp[OSV]
	mkMod=fcProp[MKM]
	iWth=fcProp[IWIDTH]
	iHht=fcProp[IHEIGHT]
  
        dec=fcProp[DEC]
       
       
        #Define connection string
        conn_string = "host='"+HOST+"' dbname='"+DBNAME+"' user='"+USER+"' password='"+PASSWD+"'"
     
        log.debug("Connecting to database\n    ->%s" % (conn_string))
     
        # get a connection, if a connect cannot be made an exception will be raised here
        conn = psycopg2.connect(conn_string)
       
        cursor = conn.cursor()
        log.debug("Connected!\n")
       
      
        point=ppygis.Point(plon, plat)
        point.srid=SRID

		#OID+","+NT+\
        #","+TSTMP+","+GEO
        cursor.execute(OBSGP_INSERT,\
        (oid,note,timeSt,point))
       
	ipA=ipaddr('eth0')+config.get("imgurl","iurl")+path[0:path.rindex('/')+1]

	
        for image in img:
            image.insert(cursor,oid,userid,osver,mkMod,iWth,iHht,ipA)
      
        #OID+","+OPT
        
        st=1
        for opt in dec:
            cursor.execute(DEC_INSERT,(oid,opt,st))
            st=st+1
            
     
        	
        if len(polyCoord) > 0:
            ls=ppygis.LineString((polyCoord))
            pgon=ppygis.Polygon((ls,))
            pgon.srid=SRID
       
       		#OID+","+GEO
            cursor.execute(POL_INSERT,(oid,pgon))
	else:
	    cursor.execute(POL_INSERT,(oid,None))
               
        conn.commit()
        cursor.close()
        conn.close()
       
    except Exception as e:
    	import traceback;
        exMsg=traceback.format_exc()
        log.exception("Exception: "+exMsg)
        #return  {"error":1 , "msg": exMsg}
        return  {"error":1 , "msg": str(e)}
        

    return { "error":0,"msg":"Operation successful"}
    

class Img:
   
    def __init__(self,recID,fileN,timeS,accuracy,vaV,vaH,azimuth,pitch,roll,lService,lt,ln,markerX,markerY,polyL,tmp,prss):
        self.rid=recID
        self.fn=fileN
        self.ts=timeS
        self.acc=accuracy
        self.vav=vaV
        self.vah=vaH
	self.azi=azimuth
        self.pth=pitch
	self.rll=roll
        #self.yw=yaw
        self.ls=lService
        self.lat=lt
        self.lon=ln
        self.mkX=markerX
        self.mkY=markerY
        self.pl=polyL
	self.temp=tmp
   	self.press=prss
   		
    def insert(self,cursor,oid,userid,osver,mkMod,iWth,iHht,ipA):
        
        
        
        nSat=0
        if "GPS" in self.ls:
        	nSat=self.ls[self.ls.index('(')+1:self.ls.index(')')]
        

        ipoint=ppygis.Point(self.lon, self.lat)
        ipoint.srid=SRID	
        print self.rid
        cursor.execute(OBS_INSERT,\
        (self.rid,nSat,self.acc,self.ls,osver,mkMod,iWth,iHht,self.vah,self.vav,self.ts,self.azi,self.pth,self.rll,self.temp,self.press,ipoint))
        
        
        mk=str(self.mkX)+' '+str(self.mkY)
        
           
        
        imURL=ipA+self.fn
	print imURL
        #PL+","+FL+","+MRK+","+RID
        cursor.execute(IMG_INSERT,\
        (self.pl,imURL,mk,self.rid))
        
        
        
        #OID+","+RID
        cursor.execute(REC_INSERT,\
        (oid,self.rid))

	#RID, USER_ID
	cursor.execute(RU_INSERT,\
	(self.rid,userid))


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sockfd = sock.fileno()
SIOCGIFADDR = 0x8915
def ipaddr(iface = 'eth0'):
	ifreq = struct.pack('16sH14s', iface, socket.AF_INET, '\x00'*14)
  	try:
		res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
	except:
		return None
	ip = struct.unpack('16sH2x4s8x', res)[2]
	return socket.inet_ntoa(ip)
