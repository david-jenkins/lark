

import copy
import os
import time
import numpy
from collections import ChainMap
from astropy.io import fits
from logging import getLogger
from lark.logger import log_to_stdout

logger = getLogger(__name__)
logger.setLevel("DEBUG")
# logger.setLevel("INFO")
logger.propagate = False
log_to_stdout(logger,"DEBUG")

default_options = {
    "darcaffinity"        : None,
    "nhdr"                : None,
    "bufsize"             : None,
    "circBufMaxMemSize"   : None,
    "redirectdarc"        : None,
    "shmPrefix"           : None,
    "numaSize"            : None,
    "nstoreDict"          : None,
    "numaSize"            : 0,
    "configfile"          : None,
}

def maxClipped_default(params):
    return params["nacts"]

def subapFlag_default(params):
    nsub=numpy.array(params["nsub"])
    nsubaps=nsub.sum()
    return numpy.ones((nsubaps,),numpy.int32)

def computeFillingSubapLocation(params,nsubaps,nvalues=6):
    """Compute a subapLocation (and pxlcnt) such that all pixels are in a subap.
    Used during initialisation.
    """
    logger.debug("computing filling subap location")
    subapLocation = numpy.zeros((nsubaps,nvalues),numpy.int32)
    subapFlag = params["subapFlag"]
    ncam = params["ncam"]
    npxlx = params["npxlx"]
    npxly = params["npxly"]
    nsub = params["nsub"]
    subapLocationType = params["subapLocType"]
    #nsuby=b.get("nsuby")
    subcum=0
    if subapLocationType==0:
        for i in range(ncam):
            sf=subapFlag[subcum:subcum+nsub[i]]
            sl=subapLocation[subcum:subcum+nsub[i]]
            #sf.shape=nsuby[i],nsubx[i]
            sl.shape=nsub[i],6
            #Compute the number of rows and columns that have a value in them.
            #ncols=(sf.sum(0)>0).sum()
            sfsum=sf.sum()
            nrows=int(numpy.sqrt(sfsum))
            ndone=0
            pos=0
            for j in range(nrows):
                ncols=int((sfsum-ndone)/(nrows-j))
                pxldone=0
                for k in range(ncols):
                    npxls=(npxlx[i]-pxldone)/(ncols-k)
                    if sf[pos]:
                        sl[pos]=[ndone,ncols,1,pxldone,npxls,1]
                    pos+=1
                    pxldone+=npxls
                ndone+=ncols
            subcum+=nsub[i]#*nsuby[i]
    else:
        subapLocation[:]=-1
        for i in range(ncam):
            sf=subapFlag[subcum:subcum+nsub[i]]
            sl=subapLocation[subcum:subcum+nsub[i]]
            sl.shape=nsub[i],sl.size/nsub[i]
            n=sl.shape[1]
            nused=sf.sum()
            pxl=0
            for j in range(nsub[i]):
                k=0
                while k<n and pxl<npxlx[i]*npxly[i]:
                    sl[j,k]=pxl
                    pxl+=1
                    k+=1
    return subapLocation

def subapLocation_default(params):
    nsub = numpy.array(params["nsub"])
    npxlx = numpy.array(params["npxlx"])
    npxly = numpy.array(params["npxly"])
    nsubaps = nsub.sum()
    nsubapsCum = numpy.zeros((params["ncam"]+1,),numpy.int32)
    for i in range(params["ncam"]):
        nsubapsCum[i+1] = nsubapsCum[i]+nsub[i]
        nsubapsUsed = params["subapFlag"][nsubapsCum[i]:nsubapsCum[i+1]].sum()
    if params["subapLocType"] == 0:
        subapLocation = computeFillingSubapLocation(params,nsubaps)
    else:#give enough pixels to entirely use the ccd.
        maxpxls = numpy.max((npxlx*npxly+nsubapsUsed-1)/nsubapsUsed)
        subapLocation = computeFillingSubapLocation(params,nsubaps,maxpxls)
    return subapLocation

def pxlCnt_default(params):
    nsub = numpy.array(params["nsub"])
    npxlx = numpy.array(params["npxlx"])
    nsubaps = nsub.sum()
    nsubapsCum = numpy.zeros((params["ncam"]+1,),numpy.int32)
    for i in range(params["ncam"]):
        nsubapsCum[i+1]=nsubapsCum[i]+nsub[i]
    pxlcnt = numpy.zeros((nsubaps,),"i")
    # set up the pxlCnt array - number of pixels to wait until each subap is ready.  Here assume identical for each camera.
    if params["subapLocType"]==0:
        for k in range(params["ncam"]):
            # tot=0#reset for each camera
            for i in range(nsub[k]):
                indx=nsubapsCum[k]+i
                n=(params["subapLocation"][indx,1]-1)*npxlx[k]+params["subapLocation"][indx,4]
                pxlcnt[indx]=n
    else:
        params["subapLocation"].shape=nsubaps,params["subapLocation"].size/nsubaps
        for i in range(nsub.sum()):
            pxlcnt[i]=numpy.max(params["subapLocation"][i])
    return pxlcnt

default_params = {
    "ncam"           : 1,
    "nacts"          : 52,
    "nsub"           : [49],
    "npxlx"          : [128],
    "npxly"          : [128],
    "refCentroids"   : None,
    "subapLocType"   : 0,
    "bgImage"        : None,
    "darkNoise"      : None,
    "flatField"      : None,
    "thresholdAlgo"  : 0,
    "thresholdValue" : 0,
    "powerFactor"    : 1,
    "centroidWeight" : None,
    "windowMode"     : "basic",
    "go"             : 1,
    "centroidMode"   : "CoG",
    "pause"          : 0,
    "printTime"      : 0,
    "ncamThreads"    : [1],
    "switchRequested": 0,
    "actuators"      : None,
    "fakeCCDImage"   : None,
    "threadAffinity" : None,
    "threadPriority" : None,
    "delay"          : 0,
    "clearErrors"    : 0,
    "camerasOpen"    : 0,
    "cameraParams"   : [],
    "cameraName"     : "none",
    "mirrorOpen"     : 0,
    "mirrorName"     : "none",
    "frameno"        : 0,
    "switchTime"     : 0,
    "adaptiveWinGain" : 0,
    "corrThreshType" : 0,
    "corrThresh"     : 0,
    "corrFFTPattern" : None,
    "nsteps"         : 0,
    "closeLoop"      : 1,
    "mirrorParams"   : None,
    "addActuators"   : 0,
    "actSequence"    : None,
    "recordCents"    : 0,
    "pxlWeight"      : None,
    "averageImg"     : 0,
    "slopeOpen"      : 1,
    "slopeParams"    : None,
    "slopeName"      : "librtcslope.so",
    "actuatorMask"   : None,
    "averageCent"    : 0,
    "centCalData"    : None,
    "centCalBounds"  : None,
    "centCalSteps"   : None,
    "figureOpen"     : 0,
    "figureName"     : "none",
    "figureParams"   : None,
    "reconName"      : "libreconmvm.so",
    "fluxThreshold"  : 0,
    "printUnused"    : 1,
    "useBrightest"   : 0,
    "figureGain"     : 1.0,
    "reconlibOpen"   : 1,
    "maxAdapOffset"  : 0,
    "version"        : " "*120,
    "currentErrors"  : 0,
    "actOffset"      : None,
    "actScale"       : None,
    "actsToSend"     : None,
    "reconParams"    : None,
    "adaptiveGroup"  : None,
    "calibrateName"  : "librtccalibrate.so",
    "calibrateParams": None,
    "calibrateOpen"  : 1,
    "iterSource"     : 0,
    "bufferName"     : "librtcbuffer.so",
    "bufferParams"   : None,
    "bufferOpen"     : 0,
    "bufferUseSeq"   : 0,
    "noPrePostThread" : 0,
    "subapAllocation" : None,
    "decayFactor"    : None,
    "openLoopIfClip" : 0,
    "adapWinShiftCnt" : None,
    "slopeSumMatrix" : None,
    "slopeSumGroup"  : None,
    "centIndexArray" : None,
    "threadAffElSize" : (os.sysconf("SC_NPROCESSORS_ONLN")+31)//32,
    "adapResetCount" : 0,
    "bleedGain"      : 0.0,
    "bleedGroups"    : None,
    "calsub"         : None,
    "calmult"        : None,
    "calthr"         : None,
    "gainReconmxT"   : None,
    "gainE"          : None,

    # uses functions
    "maxClipped"     : maxClipped_default,
    "subapFlag"      : subapFlag_default,
    "subapLocation"  : subapLocation_default,
    "pxlCnt"         : pxlCnt_default,

    # were commented out in darc...
    # "camerasFraming" : 0,
    # "lastActs"       : None,
    # "calmult"        : None,
    # "calsub"         : None,
    # "calthr"         : None,
    # "slopeFraming"   : 0,
    # "nsubapsTogether" :1,
}

param_basic_types = {
    "ncam"           : int,
    "nacts"          : int,
    "subapLocType"   : int,
    "thresholdAlgo"  : int,
    "thresholdValue" : int,
    "powerFactor"    : int,
    "windowMode"     : str,
    "go"             : int,
    "centroidMode"   : str,
    "pause"          : int,
    "printTime"      : int,
    "switchRequested": int,
    "delay"          : int,
    "clearErrors"    : int,
    "camerasOpen"    : int,
    "cameraName"     : str,
    "mirrorOpen"     : int,
    "mirrorName"     : str,
    "frameno"        : int,
    "switchTime"     : int,
    "adaptiveWinGain" : int,
    "corrThreshType" : int,
    "corrThresh"     : int,
    "nsteps"         : int,
    "closeLoop"      : int,
    "addActuators"   : int,
    "recordCents"    : int,
    "averageImg"     : int,
    "slopeOpen"      : int,
    "slopeName"      : str,
    "averageCent"    : str,
    "figureOpen"     : str,
    "figureName"     : str,
    "reconName"      : str,
    "fluxThreshold"  : int,
    "printUnused"    : int,
    "useBrightest"   : int,
    "figureGain"     : float,
    "reconlibOpen"   : int,
    "maxAdapOffset"  : int,
    "version"        : str,
    "currentErrors"  : int,
    "calibrateName"  : str,
    "calibrateOpen"  : int,
    "iterSource"     : int,
    "bufferName"     : str,
    "bufferOpen"     : int,
    "bufferUseSeq"   : int,
    "noPrePostThread" : int,
    "openLoopIfClip" : int,
    "threadAffElSize" : int,
    "adapResetCount" : int,
    "bleedGain"      : float,
    "maxClipped"     : int,
    "configFile"     : str,
}

def inventAndCheck(params):
    params.update({k:v for k,v in default_params.items() if k not in params})
    # params.update({k:v(params) for k,v in params.items() if callable(v)})
    for key,value in params.items():
        if callable(value):
            params[key] = value(params)
    return checkParams(params)

def checkParams(params):
    for key,value in params.items():
        try:
            params[key] = valid(key,value,params)
            setDependencies(key,params)
        except Exception as e:
            raise Exception(f"{key} error: {repr(e)}")
    return params

def checkParam(name,value,params):
    value = valid(name,value,params)
    setDependencies(name,params)
    return value

def openFits(val):
    # return FITS.Read(val)[1]
    return fits.getdata(val)

def checkNoneOrArray(val,size,dtype,name=""):
    if type(val)==type([]):
        val=numpy.array(val)
    elif type(val)==type(""):
        if os.path.exists(val):
            logger.debug("Loading %s"%val)
            val=openFits(val)
        else:
            logger.warn("File %s not found"%val)
            raise FileNotFoundError("File %s not found"%val)
    if val is None:
        pass
    elif type(val)==numpy.ndarray:
        val=val.astype(dtype)
        if size is not None:
            val.shape=size,
    else:
        raise TypeError(f"{name} is not an array")
    return val

def checkArray(val,shape,dtype,raiseShape=0,name=""):
    if type(val)==type([]):
        val=numpy.array(val)
    elif type(val)==type(""):
        if os.path.exists(val):
            logger.debug("Loading %s"%val)
            val=openFits(val)
        else:
            raise FileNotFoundError("File not found %s"%val)
    if isinstance(val,numpy.ndarray):
        if dtype is not None:
            val=val.astype(dtype)
        if shape is not None:
            if type(shape)!=type(()):
                shape=(shape,)
            if val.shape!=shape:
                logger.warn(f"{name} Warning - shape not quite right (expecting {shape}, got {val.shape})?")
                if raiseShape:
                    raise ValueError(f"checkArray shape for {name}")
            try:
                val.shape=shape
            except:
                logger.debug(val.shape,shape)
                raise
    else:
        raise TypeError(f"{name} is not an array")
    return val

def checkDouble(val):
    val=float(val)
    val=numpy.array([val]).astype("d")
    return val

def checkNoneOrFloat(val):
    if val is None:
        pass
    else:
        val=float(val)
    return val

def checkFlag(val,name=""):
    val=int(val)
    if val!=0 and val!=1:
        raise ValueError(f"checkFlag for {name}")
    return val

def valid(label,val,buf):
    """Checks a value is valid.  buf is the buffer that contains all the other parameters"""
    #buf=guibuf
    # logger.debug("checking:",label,val,buf)
    if label=="reconstructMode":
        if(val not in ["simple","truth","open","offset"]):
            raise Exception(label)
    elif label=="windowMode":
        if val not in ["basic","adaptive","global"]:
            raise Exception(label)
    elif label in ["cameraName","mirrorName","comment","slopeName","figureName","version","configfile"]:
        if type(val)!=type(""):
            raise Exception(label)
    elif label in ["reconName","calibrateName","bufferName"]:
        if type(val) not in [type(""),type(None)]:
            raise Exception(label)
    elif label=="centroidMode":
        if type(val)==numpy.ndarray:
            nsubaps=buf.get("nsub").sum()
            try:
                val=checkArray(val,nsubaps,"i",name=label)
            except Exception as e:
                raise Exception("centroidMode array wrong") from e
        elif val not in ["WPU","CoG","Gaussian","CorrelationCoG","CorrelationGaussian",0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]:
            logger.warn("centroidMode not correct (%s)"%str(val))
            raise Exception(label)
    elif label in ["cameraParams","mirrorParams","slopeParams","figureParams","reconParams","calibrateParams","bufferParams"]:
        if type(val)==type(""):
            l=4-len(val)%4
            if l<4:
                val+="\0"*l
            val=numpy.fromstring(val,dtype=numpy.int32)

        if type(val)==type([]):
            val=numpy.array(val)
        if type(val)!=type(None) and type(val)!=numpy.ndarray:
            logger.warn("ERROR in val for %s: %s"%(label,str(val)))
            raise Exception(label)
    elif label in ["delay","closeLoop","nacts","thresholdAlgo","delay","maxClipped","camerasFraming","camerasOpen","mirrorOpen","clearErrors","frameno","corrThreshType","nsubapsTogether","nsteps","addActuators","recordCents","averageImg","averageCent","kalmanPhaseSize","figureOpen","printUnused","reconlibOpen","currentErrors","xenicsExposure","calibrateOpen","iterSource","bufferOpen","bufferUseSeq","subapLocType","noPrePostThread","asyncReset","openLoopIfClip","threadAffElSize","mirrorStep","mirrorUpdate","mirrorReset","mirrorGetPos","mirrorDoMidRange","lqgPhaseSize","lqgActSize"]:
        # logger.debug(val,type(val))
        val=int(val)
    elif label in ["dmDescription"]:
        if val.dtype.char!="h":
            raise Exception("dmDescription type not int16")
    elif label in ["actuators"]:
        val=checkNoneOrArray(val,None,"f",label)
        if val is not None:
            if val.size%buf.get("nacts")==0:
                # shape okay... multiple of nacts.
                pass
            else:
                raise Exception("actuators should be array (nacts,) or (X,nacts)")
    elif label in ["actMax","actMin"]:
        nact=buf.get("nacts")
        try:
            val=checkArray(val,nact,None,name=label)
        except:
            logger.warn("WARNING (Check.py) - actMax/actMin as int now depreciated... this may not work (depending on which version of RTC you're running).  The error was")
            #traceback.print_exc()
            #val=int(val)
            logger.warn("Continuing... using %s"%str(val))
    #elif label in["lastActs"]:
    #    nact=buf.get("nacts")
    #    val=checkNoneOrArray(val,nact,"H")
    elif label in ["actInit"]:
        val=checkNoneOrArray(val,None,"H",label)
    elif label in ["actMapping"]:
        val=checkNoneOrArray(val,None,"i",label)
    elif label in ["figureActSource"]:
        val=checkNoneOrArray(val,None,"i",label)
    elif label in ["figureActScale","figureActOffset","actScale","actOffset"]:
        val=checkNoneOrArray(val,None,"f",label)
    elif label in ["actuatorMask"]:
        val=checkNoneOrArray(val,None,"f",label)
        if val is not None:
            if val.size==buf.get("nacts"):
                # shape okay... multiple of nacts.
                pass
            else:
                raise Exception("actuatorMask should be array (nacts,)")
    elif label in ["actSequence"]:
        actuators=buf.get("actuators")
        if actuators is None:
            size=None
        else:
            size=actuators.size/buf.get("nacts")
        val=checkNoneOrArray(val,size,"i",label)
    elif label in ["bgImage","flatField","darkNoise","pxlWeight","calmult","calsub","calthr"]:
        val=checkNoneOrArray(val,(buf.get("npxlx")*buf.get("npxly")).sum(),"f",label)
    elif label in ["thresholdValue"]:
        if type(val)==type(""):
            if os.path.exists(val):
                val=openFits(val)
            else:
                val=eval(val)
        if type(val)==numpy.ndarray:
            npxls=(buf.get("npxlx")*buf.get("npxly")).sum()
            if val.size==npxls:
                val=checkArray(val,(npxls,),"f",name=label)
            else:
                val=checkArray(val,(buf.get("nsub").sum(),),"f",name=label)
        else:
            try:
                val=float(val)
            except Exception as e:
                logger.warn("thresholdValue: %s"%str(type(val)))
                logger.warn("thresholdValue should be float or array of floats")
                raise e
    elif label in ["useBrightest"]:
        if type(val)==type(""):
            if os.path.exists(val):
                val=openFits(val)
            else:
                val=eval(val)
        if type(val)==numpy.ndarray:
            val=checkArray(val,(buf.get("nsub").sum(),),"i",name=label)
        else:
            try:
                val=int(val)
            except Exception as e:
                logger.warn("%s: %s"%(label,str(type(val))))
                logger.warn("%s should be int or array of ints size equal to total number of subapertures (valid and invalid)"%label)
                raise e
    elif label in ["fluxThreshold"]:
        if type(val)==type(""):
            if os.path.exists(val):
                val=openFits(val)
            else:
                val=eval(val)
        if type(val)==numpy.ndarray:
            val=checkArray(val,buf.get("subapFlag").sum(),"f",name=label)
        else:
            try:
                val=float(val)
            except:
                logger.warn("%s: %s"%(label,str(type(val))))
                logger.warn("%s should be float or array of floats size equal to tutal number of used subapertures")
                raise

    elif label in ["maxAdapOffset"]:
        if type(val)==type(""):
            if os.path.exists(val):
                val=openFits(val)
            else:
                val=eval(val)
        if type(val)==numpy.ndarray:
            val=checkArray(val,buf.get("subapFlag").sum(),"i",name=label)
        else:
            try:
                val=int(val)
            except:
                logger.warn("maxAdapOffset",val)
                logger.warn("maxAdapOffset should be int or array of ints of size equal to number of valid subaps %s"%str(type(val)))
                raise
    elif label in ["powerFactor","adaptiveWinGain","corrThresh","figureGain","uEyeFrameRate","uEyeExpTime"]:
        val=float(val)
    elif label=="bleedGain":
        if type(val)==numpy.ndarray:
            if val.dtype.char!='f':
                val=val.astype('f')
        else:
            val=float(val)
    elif label=="bleedGroups":
        val=checkNoneOrArray(val,buf.get("nacts"),"i",label)
    elif label in ["switchTime"]:
        val=checkDouble(val)
    elif label in ["fakeCCDImage"]:
        val=checkNoneOrArray(val,(buf.get("npxlx")*buf.get("npxly")).sum(),"f",label)
    elif label in ["centroidWeight"]:
        val=checkNoneOrFloat(val)
    elif label in ["gainE","E"]:
        if val is None:
            pass
        else:
            if type(val)==numpy.ndarray:
                if val.dtype!=numpy.float32:
                    val=val.astype(numpy.float32)
                if val.shape!=(buf.get("nacts"),buf.get("nacts")) and val.shape!=(buf.get("subapFlag").sum()*2,buf.get("nacts")):
                    raise Exception("E should be shape nacts,nacts or nslopes,nacts")
            else:#lazy - this doesn't check for nslopes,nacts...
                val=checkArray(val,(buf.get("nacts"),buf.get("nacts")),"f",name=label)
    elif label in ["gainReconmxT"]:
        val=checkArray(val,(buf.get("subapFlag").sum()*2,buf.get("nacts")),"f",raiseShape=1,name=label)
    elif label in ["kalmanAtur"]:
        val=checkArray(val,(buf.get("kalmanPhaseSize"),buf.get("kalmanPhaseSize")),"f",name=label)
    elif label in ["kalmanInvN"]:
        val=checkNoneOrArray(val,buf.get("nacts")*buf.get("kalmanPhaseSize"),"f",name=label)
        if val is not None:#now check shape
            val=checkArray(val,(buf.get("nacts"),buf.get("kalmanPhaseSize")),"f",name=label)
    elif label in ["kalmanHinfDM"]:
        val=checkArray(val,(buf.get("kalmanPhaseSize")*3,buf.get("kalmanPhaseSize")),"f",name=label)
    elif label in ["kalmanHinfT"]:
        val=checkArray(val,(buf.get("subapFlag").sum()*2,buf.get("kalmanPhaseSize")*3),"f",name=label)
    elif label in ["kalmanReset","kalmanUsed","printTime","usingDMC","go","pause","switchRequested","startCamerasFraming","stopCamerasFraming","openCameras","closeCameras","centFraming","slopeOpen"]:
        val=checkFlag(val)
    elif label in ["nsub","ncamThreads","npxlx","npxly"]:
        val=checkArray(val,buf.get("ncam"),"i",name=label)
    elif label in ["pxlCnt","subapFlag"]:
        val=checkArray(val,buf.get("nsub").sum(),"i",name=label)
    elif label in ["refCentroids"]:
        val=checkNoneOrArray(val,buf.get("subapFlag").sum()*2,"f",label)
    elif label in ["centCalBounds"]:
        val=checkNoneOrArray(val,buf.get("subapFlag").sum()*2*2,"f",label)
    elif label in ["centCalSteps","centCalData"]:
        ncents=buf.get("subapFlag").sum()*2
        val=checkNoneOrArray(val,None,"f",label)
        if val is not None:
            nsteps=val.size/ncents
            if val.size!=nsteps*ncents:
                raise Exception("%s wrong shape - should be multiple of %d, is %d"%(label,ncents,val.size))
    elif label in ["subapLocation"]:
        slt=buf.get("subapLocType")
        if slt==0:
            val=checkArray(val,(buf.get("nsub").sum(),6),"i",name=label)
        else:
            val=checkArray(val,None,"i",name=label)
            n=val.size//buf.get("nsub").sum()#get the size and test again
            val=checkArray(val,(buf.get("nsub").sum(),n),"i",name=label)
    elif label in ["subapAllocation"]:
        val=checkNoneOrArray(val,buf.get("nsub").sum(),"i",label)
    elif label in ["gain"]:
        val=checkArray(val,buf.get("nacts"),"f",name=label)
    elif label in ["v0"]:
        val=checkNoneOrArray(val,buf.get("nacts"),"f",label)
    elif label in ["asyncInitState","asyncScales","asyncOffsets"]:
        val=checkNoneOrArray(val,buf.get("nacts"),"f",label)
    elif label in ["asyncCombines","asyncUpdates","asyncStarts","asyncTypes"]:
        val=checkNoneOrArray(val,None,"i")
    elif label in ["decayFactor"]:
        val=checkNoneOrArray(val,buf.get("nacts"),"f",label)
    elif label in ["rmx"]:
        if val is None and buf.get("reconName") not in ["libreconpcg.so","libreconneural.so","libreconLQG.so","libreconcure.so"]:
            raise Exception("rmx is None")
        elif val is not None:
            val=checkArray(val,(buf.get("nacts"),buf.get("subapFlag").sum()*2),"f",raiseShape=1,name=label)
    elif label in ["slopeSumMatrix"]:
        val=checkNoneOrArray(val,None,"f",label)
        if (val is not None) and val.size%buf.get("nacts")!=0:
            raise Exception("slopeSumMatrix wrong size")
    elif label in ["slopeSumGroup"]:
        val=checkNoneOrArray(val,buf.get("subapFlag").sum()*2,"i",label)
        if (val is not None) and numpy.max(val)+1!=(buf.get("slopeSumMatrix").size/buf.get("nacts")):
            raise Exception("Groupings in slopeSumGroup not consistent with size of slopeSumMatrix")
    elif label in ["ncam"]:
        val=int(val)
        if val<1:
            raise Exception("Illegal ncam")
    elif label in ["threadAffinity"]:
        if val is None:
            pass
        elif type(val)==numpy.ndarray:
            if val.dtype!="i":
                val=val.astype("i")
            if val.size%(buf.get("ncamThreads").sum()+1)!=0:
                raise Exception("threadAffinity error (size not multiple of %d)"%(buf.get("ncamThreads").sum()+1))
        else:
            raise Exception("threadAffinity error (should be an array, or None)")
    elif label in ["threadPriority"]:
        val=checkNoneOrArray(val,buf.get("ncamThreads").sum()+1,"i",label)
    elif label in ["corrFFTPattern","corrPSF"]:
        if type(val)==numpy.ndarray:
            val=val.astype(numpy.float32)
        elif val is not None:
            raise Exception("corrFFTPattern error")
        #val=checkNoneOrArray(val,(buf.get("npxlx")*buf.get("npxly")).sum(),"f")
    elif label in ["adaptiveGroup"]:
        val=checkNoneOrArray(val,buf.get("subapFlag").sum(),"i",label)
    elif label in ["asyncNames"]:
        pass#no checking needed...
    elif label in ["adapWinShiftCnt"]:
        val=checkNoneOrArray(val,buf.get("nsub").sum()*2,"i",label)
    elif label in ["centIndexArray"]:
        if type(val)==type([]):
            val=numpy.array(val)
        elif type(val)==type(""):
            if os.path.exists(val):
                logger.debug("Loading %s"%val)
                val=openFits(val)
            else:
                logger.warn("File %s not found"%val)
                raise Exception("File %s not found"%val)
        if val is None:
            pass
        elif type(val)==numpy.ndarray:
            val=val.astype("f")
            fft=buf.get("corrFFTPattern",None)
            if fft is None:
                npxls=(buf.get("npxlx")*buf.get("npxly")).sum()
            else:
                npxls=fft.size
            if val.size not in [npxls,npxls*2,npxls*3,npxls*4]:
                raise Exception("centIndexArray wrong size")
        else:
            raise Exception("centIndexArray")
    elif label=="actsToSend":
        val=checkNoneOrArray(val,None,"i",label)
    elif label in ["mirrorSteps","mirrorMidRange"]:#used for mirrorLLS.c
        val=checkArray(val,buf.get("nacts"),"i",name=label)
    elif label in ["lqgAHwfs"]:
        val=checkArray(val,(buf.get("lqgPhaseSize")*2,buf.get("lqgPhaseSize")),"f",raiseShape=1,name=label)
    elif label in ["lqgAtur"]:
        val=checkArray(val,(buf.get("lqgPhaseSize"),buf.get("lqgPhaseSize")),"f",raiseShape=1,name=label)
    elif label in ["lqgHT"]:
        val=checkArray(val,(buf.get("subapFlag").sum()*2,2*buf.get("lqgPhaseSize")),"f",raiseShape=1,name=label)
    elif label in ["lqgHdm"]:
        try:
            val=checkArray(val,(2*buf.get("lqgPhaseSize"),buf.get("nacts")),"f",raiseShape=1,name=label)
        except:
            val=checkArray(val,(2,2*buf.get("lqgPhaseSize"),buf.get("nacts")),"f",raiseShape=1,name=label)

    elif label in ["lqgInvN"]:
        try:
            val=checkArray(val,(buf.get("nacts"),buf.get("lqgPhaseSize")),"f",raiseShape=1,name=label)
        except:
            val=checkArray(val,(2,buf.get("nacts"),buf.get("lqgPhaseSize")),"f",raiseShape=1,name=label)

    elif label in ["lqgInvNHT"]:
        val=checkArray(val,(buf.get("subapFlag").sum()*2,buf.get("nacts")),"f",raiseShape=1,name=label)

    else:
        logger.warn("Unchecked parameter %s"%label)
    return val

def setDependencies(name:str,buf:dict):
    """Value name has just changed in the buffer,  This will require some other things updating.
    """
    paramChangedDict = {}
    logger.debug(f"Running check for {name}")
    if name in ["bgImage","flatField","darkNoise","pxlWeight","thresholdValue","thresholdAlgo","subapLocation","subapFlag","npxlx","npxly","nsub","nsuby","calsub","calmult","calthr"]:
        #update calsub, calmult, calthr
        try:
            ff=buf.get("flatField")
            bg=buf.get("bgImage")
            dn=buf.get("darkNoise")
            wt=buf.get("pxlWeight")
            th=buf.get("thresholdValue")
            ta=buf.get("thresholdAlgo")
            sl=buf.get("subapLocation")
            sf=buf.get("subapFlag")
            st=buf.get("subapLocType")
            npxlx=buf.get("npxlx")
            npxly=buf.get("npxly")
            #nsuby=b.get("nsuby")
            nsub=buf.get("nsub")
            ncam=buf.get("ncam")
        except:#buffer probably not filled yet...
            return
        if ff is not None:ff=ff.copy()
        if bg is not None:bg=bg.copy()
        if dn is not None:dn=dn.copy()
        if wt is not None:wt=wt.copy()
        if type(th)==numpy.ndarray:th=th.copy()
        npxls=(npxlx*npxly).sum()
        if ta==2:#add threshold to background then set thresh to zero
            #note this altered background is only used here for calcs.
            if type(th)==numpy.ndarray:#value per subap
                if th.size==npxls:#value per pixel
                    if bg is None:
                        bg=th.copy()
                    else:
                        bg+=th
                else:
                    if bg is None:
                        bg=numpy.zeros((npxls),numpy.float32)
                    nsubapsCum=0
                    npxlcum=0
                    pos=0
                    for k in range(ncam):
                        bb=bg[npxlcum:npxlcum+npxlx[k]*npxly[k]]
                        bb.shape=npxly[k],npxlx[k]
                        for i in range(nsub[k]):
                            s=sl[pos]
                            if sf[pos]!=0:#subap used
                                if st==0:
                                    bb[s[0]:s[1]:s[2],s[3]:s[4]:s[5]]+=th[pos]
                                else:
                                    for i in range(sl.shape[0]):
                                        if sl[i]==-1:
                                            break
                                        bb[sl[i]]=th[pos]
                            pos+=1
                        nsubapsCum+=nsub[k]
                        npxlcum+=npxly[k]*npxlx[k]
            else:
                if (bg is None) and th!=0:
                    bg=numpy.zeros((npxls),numpy.float32)
                if bg is not None:
                    bg[:]+=th

            calthr=numpy.zeros((npxls),numpy.float32)
        elif ta==1:
            #multiply threshold by weight
            if type(th)==numpy.ndarray:
                if th.size==npxls: #threshold per pixel
                    if wt is None:
                        calthr=th
                    else:
                        calthr=th*wt
                else:#threshold per subap
                    calthr=numpy.zeros((npxls),numpy.float32)
                    if wt is None:
                        wtt=numpy.ones((npxls),numpy.float32)
                    else:
                        wtt=wt
                    #now multiply threshold by weight.
                    nsubapsCum=0
                    npxlcum=0
                    pos=0
                    for k in range(ncam):
                        ct=calthr[npxlcum:npxlcum+npxlx[k]*npxly[k]]
                        ct.shape=npxly[k],npxlx[k]
                        w=wtt[npxlcum:npxlcum+npxlx[k]*npxly[k]]
                        w.shape=npxly[k],npxlx[k]
                        for i in range(nsub[k]):
                            s=sl[pos]
                            if sf[pos]!=0:#subap used
                                if st==0:
                                    ct[s[0]:s[1]:s[2],s[3]:s[4]:s[5]]=th[pos]*w[s[0]:s[1]:s[2],s[3]:s[4]:s[5]]
                                else:
                                    for i in range(sl.shape[0]):
                                        if sl[i]==-1:
                                            break
                                        ct[sl[i]]=th[pos]*w[sl[i]]
                            pos+=1
                        nsubapsCum+=nsub[k]
                        npxlcum+=npxly[k]*npxlx[k]
            else:#single threshold value
                if wt is None:
                    calthr=numpy.zeros((npxls),numpy.float32)
                    calthr[:]=th
                else:
                    calthr=wt*th
        else:
            calthr=None
        if ff is None:
            if wt is None:
                calmult=None
            else:
                calmult=wt
        else:
            if wt is None:
                calmult=ff
            else:
                calmult=ff*wt
        #calsub should equal (dn*ff+bg)*wt
        if dn is None:
            if bg is None:
                calsub=None
            else:
                if wt is None:
                    calsub=bg
                else:
                    calsub=bg*wt
        else:
            if ff is None:
                calsub=dn
            else:
                calsub=ff*dn
            if bg is not None:
                calsub+=bg
            if wt is not None:
                calsub*=wt
        if calsub is not None:calsub=calsub.astype(numpy.float32)
        if calmult is not None:calmult=calmult.astype(numpy.float32)
        if calthr is not None:calthr=calthr.astype(numpy.float32)
        paramChangedDict["calsub"] = calsub
        paramChangedDict["calmult"] = calmult
        paramChangedDict["calthr"] = calthr

    if name in ["gain","E","rmx","gainE","gainReconmxT","decayFactor"]:
        #now update the gainE and gainReconmxT.
        try:
            rmx=buf.get("rmx")
            e=buf.get("E")
            g=buf.get("gain")
            d=buf.get("decayFactor")
        except Exception as e:
            logger.warn(repr(e))
            return
        if rmx is not None:
            rmxt = rmx.transpose().astype(numpy.float32,order="C")
            nacts = g.shape[0]
            for i in range(nacts):
                rmxt[:,i] *= g[i]
            #rmxt=rmxt.astype(numpy.float32)
            logger.debug("updating gainreconmxt")
            paramChangedDict["gainReconmxT"] = rmxt
        if e is not None:
            gainE=e.copy()
            if d is None:
                d=1-g
                logger.debug("Computing gainE from 1-g")
            else:
                logger.debug("Computing gainE from decayFactor")
            for i in range(nacts):
                gainE[i]*=d[i]#1-g[i]
            gainE=gainE.astype(numpy.float32)
        else:
            gainE=None
        paramChangedDict["gainE"] = gainE
    buf.update(paramChangedDict)
    return paramChangedDict

if __name__ == "__main__":
    x = {"x":6,"y":8}
    y = checkParams(x)

    logger.debug(y["maxClipped"])
    logger.debug(y["subapFlag"])
    logger.debug(y["subapLocation"])
    logger.debug(y["pxlCnt"])