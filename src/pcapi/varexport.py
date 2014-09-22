import psycopg2
import sys
import ppygis
import logtool

#DB Constants
HOST='localhost'
USER='user'
PASSWD='cobweb'
DBNAME='tstdb'
SRID=4326
#Table names
OBSGP='obsgroup'
OBST='observations'
IMGT='images'
POLT='observation_polygons'
DECT='decision'
RECOT='recordobs'


#Observation table
RID='RecordID'
PSAT='pos_sat' # Number of satellites connected to
PACC='pos_acc'
PTECH='pos_tech' # Type of technology used (eg. GPS)
DOS='dev_os'
CHOZ='cam_hoz'
CVERT='cam_vert'
TSTMP='timestamp'
COMPB='comp_bar' # Compass
TILT='tilt'
TEMP='temp'
PRESS='press'
OBS_INSERT="INSERT INTO "+OBST+"("+RID+","+PSAT+","+PACC+","+PTECH+","+DOS+\
","+CHOZ+","+CVERT+","+TSTMP+","+COMPB+","+TILT+","+TEMP+","+PRESS+\
") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"

#Observation group table
OID='oid'
NT='note'
GEO='geom'
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
		
#App Constants
PROP='properties'
NOTE='Note'
TIMES="Time Stamp"
ACC='Accuracy'
IMAGE='Image'
FNAME='File Name'
VAV='VA Vertical'
VAH='VA Horizontal'
PITCH='Pitch'
YAW='Yaw'
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
                    
                   
                    img.append(Img(prop[RIDENT],prop[FNAME],prop[TIMES],prop[ACC],prop[VAV],prop[VAH],\
                    prop[PITCH],prop[YAW],prop[LS],coord[0],coord[1],mkX,mkY,polyline))
            else:
                for crd in coord[0]:
                    lat=crd[0]
                    lon=crd[1]
                    polyCoord.append(ppygis.Point(lat, lon))   
   
        fcProp=geojflood[PROP]
        note=fcProp[NOTE]
        oid=path[path.rindex('/')+1:path.rindex('.')]
        userid=oid[0:oid.rindex('_')]
        osver=fcProp[OSV]
        
       
      
       
       	
        dec=fcProp[DEC]
       
       
        #Define connection string
        conn_string = "host='"+HOST+"' dbname='"+DBNAME+"' user='"+USER+"' password='"+PASSWD+"'"
     
        log.debug("Connecting to database\n    ->%s" % (conn_string))
     
        # get a connection, if a connect cannot be made an exception will be raised here
        conn = psycopg2.connect(conn_string)
       
        cursor = conn.cursor()
        log.debug("Connected!\n")
       
      
        point=ppygis.Point(plat, plon)
        point.srid=SRID

		#OID+","+NT+\
        #","+TSTMP+","+GEO
        cursor.execute(OBSGP_INSERT,\
        (oid,note,timeSt,point))
       

        for image in img:
            image.insert(cursor,oid,userid,osver)
      
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
               
        conn.commit()
        cursor.close()
        conn.close()
       
    except Exception as e:
    	import traceback;
        exMsg=traceback.format_exc()
        log.exception("Exception: "+exMsg)
        return  {"error":1 , "msg": exMsg}
        #return  {"error":1 , "msg": str(e)}
        

    return { "error":0,"msg":"Operation successful"}
    

class Img:
   
    def __init__(self,recID,fileN,timeS,accuracy,vaV,vaH,pitch,yaw,lService,lt,ln,markerX,markerY,polyL):
        self.rid=recID
        self.fn=fileN
        self.ts=timeS
        self.acc=accuracy
        self.vav=vaV
        self.vah=vaH
        self.pth=pitch
        self.yw=yaw
        self.ls=lService
        self.lat=lt
        self.lon=ln
        self.mkX=markerX
        self.mkY=markerY
        self.pl=polyL
   		
   		
    def insert(self,cursor,oid,userid,osver):
        
        #RID+","+PSAT+","+PACC+","+PTECH+","+DOS+\
		#","+CHOZ+","+CVERT+","+TSTMP+","+COMPB+","+TILT+","+TEMP+","+PRESS+\
        
        nSat=0
        if "GPS" in self.ls:
        	nSat=self.ls[self.ls.index('(')+1:self.ls.index(')')]
        #  compass(COMPB), tilt, temperature, and pressure
        
        cursor.execute(OBS_INSERT,\
        (self.rid,nSat,self.acc,self.ls,osver,self.vah,self.vav,self.ts,'nan','nan','nan','nan'))
        
        
        mk=str(self.mkX)+' '+str(self.mkY)
        
           
        ipoint=ppygis.Point(self.lat, self.lon)
        ipoint.srid=SRID
           
        #to do: add va
        #PL+","+FL+","+MRK+","+RID
        cursor.execute(IMG_INSERT,\
        (self.pl,self.fn,mk,self.rid))
        
        
        
        #OID+","+RID
        cursor.execute(REC_INSERT,\
        (oid,self.rid)) 