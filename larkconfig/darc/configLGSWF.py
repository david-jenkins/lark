#darc, the Durham Adaptive optics Real-time Controller.
#Copyright (C) 2013 Alastair Basden.

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU Affero General Public License as
#published by the Free Software Foundation, either version 3 of the
#License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU Affero General Public License for more details.

#You should have received a copy of the GNU Affero General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.
#This is a configuration file for CANARY.
#Aim to fill up the control dictionary with values to be used in the RTCS.

#A basic config file for getting pixels out of the OCAM.

import sys
import lark
from lark.darcconfig import gen_subapParams, gen_threadParams
from lark.rpyclib.rpyc_brine import copydict
from lark.darc import FITS
from lark.darc import tel
import numpy
import time
import os
from lark.utils import generatePyrParams, make_cog_centIndexArray


ncents:int
nsuby:numpy.ndarray
camAffin:numpy.ndarray
mirAffin:numpy.ndarray
refCentroids:numpy.ndarray
pxlCnt:numpy.ndarray

delay = 0#10000#10000

control = {}
display = {}
srtc = {}

##### DARC setup, values are returned through control

nacts = 97
nactx = 11
ncam = 1
nthreads = 1
nn = nthreads//ncam #threads per camera
ncamThreads = numpy.ones((ncam,),dtype=numpy.int32)*nn
nthreads = ncamThreads.sum() # new total number of threads, multiple of ncam
nsubx = numpy.zeros((ncam,),dtype=numpy.int32)
nsubx[0] = 45
npxl = numpy.zeros((ncam,),dtype=numpy.int32)
npxl[0] = 80

pyramidMode = numpy.zeros((ncam,),dtype=numpy.int32)
pyramidMode[0] = 1

threadPriority = 50*numpy.ones((nthreads+1,),dtype=numpy.uint32)

# the thread 
start_thread = 2
start_thread = 10

globals().update(gen_threadParams(nthreads,ncam,start_thread))


# threadAffElSize = 1
# threadAffinity = numpy.zeros(((1+nthreads)*threadAffElSize),dtype=numpy.uint32)

# camAffin = numpy.zeros(ncam, dtype=numpy.uint32)
# camAffin[0] = 1<<(start_thread+1) #4 thread

# mirAffin = numpy.zeros(1,dtype=numpy.uint32)
# mirAffin[0] = 1<<(start_thread+2) #5 

# for i in range(0,nthreads):
#     if (i<8):
#         j = i+(start_thread+3) 
#         threadAffinity[(i)*threadAffElSize+(j)//32] = 1<<(((j)%32))
#     else:
#         print("too many threads..")
#         exit(0)

# threadAffinity[threadAffElSize:] = threadAffinity[:-threadAffElSize]
# threadAffinity[:threadAffElSize] = 0
# threadAffinity[0] = 1<<start_thread # control thread affinity 3

print("Using %d cameras"%ncam)

npxly = numpy.zeros((ncam,),dtype=numpy.int32)

# npxly[0] = 170 # windowed
npxly[0] = 242 # full frame

npxlx=numpy.zeros((ncam,),dtype=numpy.int32)
npxlx[0] = 264 # both

# nsuby = numpy.zeros((ncam,),dtype=numpy.int32)
# nsuby[0] = nsub[0]

# nsubx = numpy.zeros((ncam,),dtype=numpy.int32)
# nsubx[0] = nsub[0]

xoff = [11]
yoff = [9]
xsep = [175]
ysep = [175]
print("HERE -> ",nsubx,nthreads,npxlx,npxly,ncam,pyramidMode,xoff,yoff,xsep,ysep)
globals().update(gen_subapParams(nsubx,nthreads,npxlx,npxly,ncam,pyramidMode,xoff,yoff,xsep,ysep))

subapAllocation=None

# nsubaps = (nsuby*nsubx).sum()#(nsuby*nsubx).sum()
# subapFlag = numpy.zeros((nsubaps,),"i")
# for i in range(ncam):
#     individualSubapFlag = tel.Pupil(nsub[i],nsub[i]/2.,0,nsub[i]).subflag.astype("i")
#     tmp = subapFlag[(nsuby[:i]*nsubx[:i]).sum():(nsuby[:i+1]*nsubx[:i+1]).sum()]
#     tmp.shape = nsuby[i],nsubx[i]
#     tmp[:] = individualSubapFlag
# #ncents=nsubaps*2
# ncents = subapFlag.sum()*2
npxls = (npxly*npxlx).sum()

actFlag =  numpy.array([[0,0,0,1,1,1,1,1,0,0,0],
            [0,0,1,1,1,1,1,1,1,0,0],
            [0,1,1,1,1,1,1,1,1,1,0],
            [1,1,1,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1,1,1,1],
            [0,1,1,1,1,1,1,1,1,1,0],
            [0,0,1,1,1,1,1,1,1,0,0],
            [0,0,0,1,1,1,1,1,0,0,0]
            ])

fakeCCDImage = None#(numpy.random.random((npxls,))*20).astype("i")

bgImage = None#numpy.load("/home/canapyrtc/data/bg_windowed_100Hz.npy")#None#FITS.Read("shimgb1stripped_bg.fits")[1].astype("f")#numpy.zeros((npxls,),"f")
darkNoise = None#numpy.load("/home/canapyrtc/data/dk_windowed_100Hz.npy")#None#FITS.Read("shimgb1stripped_dm.fits")[1].astype("f")
flatField = None#FITS.Read("shimgb1stripped_ff.fits")[1].astype("f")


# subapLocation = numpy.zeros((nsubaps,6),"i")
# nsubapsCum = numpy.zeros((ncam+1,),numpy.int32)
# ncentsCum = numpy.zeros((ncam+1,),numpy.int32)
# for i in range(ncam):
#     nsubapsCum[i+1] = nsubapsCum[i]+nsuby[i]*nsubx[i]
#     ncentsCum[i+1] = ncentsCum[i]+subapFlag[nsubapsCum[i]:nsubapsCum[i+1]].sum()*2

# # now set up a default subap location array...
# #this defines the location of the subapertures.
# xoff = numpy.array([0]*ncam)+0
# yoff = numpy.array([0]*ncam)+0
# # xoff = [15] # windowed
# xoff = [12] # full frame
# # yoff = [15] # windowed
# yoff = [15] # full frame
# # subx=(npxlx-xoff*2)/nsubx#[10]*ncam#(npxlx-48)/nsubx
# subx = [npxlx[0]//2]#npxlx//2#npxl
# # suby=(npxly-yoff*2)/nsuby#[10]*ncam#(npxly-8)/nsuby
# suby = [npxly[0]//2]#npxly//2#npxl

# # sepx = 194 # windowed
# # sepy = 100 # windowed
# sepx = [180] # full frame
# sepy = [175] # full frame
# for k in range(ncam):
#     if pyramidMode[k]==0:
#         for i in range(nsuby[k]):
#             for j in range(nsubx[k]):
#                 indx = nsubapsCum[k]+i*nsubx[k]+j
#                 subapLocation[indx] = (yoff[k]+i*suby[k],yoff[k]+i*suby[k]+suby[k],1,xoff[k]+j*subx[k],xoff[k]+j*subx[k]+subx[k],1)
#     else:
#         for i in range(nsuby[k]):
#             for j in range(nsubx[k]):
#                 indx = nsubapsCum[k]+i*nsubx[k]+j
#                 # subapLocation[indx] = (yoff[k]+i*suby[k],yoff[k]+i*suby[k]+suby[k],1,xoff[k]+j*subx[k],xoff[k]+j*subx[k]+subx[k],1)
#                 subapLocation[indx]=(yoff[k]+i,yoff[k]+i+sepy[k]+1,sepy[k],xoff[k]+j,xoff[k]+j+sepx[k]+1,sepx[k])
# print(subapLocation)

# pxlCnt = numpy.zeros((nsubaps,),"i")
# subapAllocation=numpy.zeros((nsubaps,),"i")-1
# # set up the pxlCnt array - number of pixels to wait until each subap is ready.  Here assume identical for each camera.
# for k in range(ncam):
#     if pyramidMode[k]==0:
#         # tot=0#reset for each camera
#         for i in range(nsuby[k]):
#             for j in range(nsubx[k]):
#                 indx = nsubapsCum[k]+i
#                 #n=(subapLocation[indx,1]-1)*npxlx[k]+subapLocation[indx,4]
#                 n = 2*subapLocation[indx,1]*npxlx[k]#whole rows together...
#                 pxlCnt[indx] = n
#                 pxlCnt[nsubaps-indx-1] = n
#                 subapAllocation[i*nsubx[k]+j]=i%nthreads
#     else:
#         for i in range(nsuby[k]):
#             for j in range(nsubx[k]):
#                 indx=nsubapsCum[k]+i*nsubx[k]+j
#                 n=(subapLocation[indx,1]-1)*npxlx[k]+subapLocation[indx,4]
#                 pxlCnt[indx]=n
#                 subapAllocation[i*nsubx[k]+j]=i%nthreads
# pxlCnt[-3] = npxlx[0]*npxly[0]
#pxlCnt[-5]=128*256
#pxlCnt[-6]=128*256
#pxlCnt[nsubaps/2-5]=128*256
#pxlCnt[nsubaps/2-6]=128*256

#The params are dependent on the interface library used.
"""
  //Parameters are:
  //bpp[ncam]
  //blocksize[ncam]
  //offsetX[ncam]
  //offsetY[ncam]
  //npxlx[cam]
  //npxly[cam]
  //byteswapInts[cam]
  //reorder[cam]
  //prio[ncam]
  //affinElSize
  //affin[ncam*elsize]
  //length of names (a string with all camera IDs, semicolon separated).
  //The names as a string.
  //recordTimestamp
"""

camerasOpen = 1

#camList = ["Pleora Technologies Inc.-iPORT-CL-Ten-Full--OCAM1","EVT-HB-1800SM-640002-ESO"][:ncam]
camList = ["Pleora Technologies Inc.-iPORT-CL-Ten-Full--OCAM1"][:ncam]
camNames=";".join(camList)#"Imperx, inc.-110323;Imperx, inc.-110324"
print(camNames)
while len(camNames)%4!=0:
    camNames+="\0"
namelen=len(camNames)
cameraParams=numpy.zeros((10*ncam+3+(namelen+3)//4,),numpy.int32)
cameraParams[0:ncam]=16#16 bpp - though aravis should be told it is 8 bpp.
cameraParams[ncam:2*ncam]=65536#block size
cameraParams[2*ncam:3*ncam]=0#x offset
cameraParams[3*ncam:4*ncam]=0#y offset
# cameraParams[4*ncam:5*ncam]=1056#npxlx # windowed
cameraParams[4*ncam:5*ncam]=1056#npxlx # full frame
# cameraParams[5*ncam:6*ncam]=121#npxly # windowed
cameraParams[5*ncam:6*ncam]=121#npxly # full frame
cameraParams[6*ncam:7*ncam]=0#byteswapInt (1 for ocam)
# cameraParams[7*ncam:8*ncam]=3 # windowed, reorder (2 or 3 for the ocam, 0 for no reordering.  4 is for the array specified below...)
cameraParams[7*ncam:8*ncam]=3 # full frame, reorder (2 or 3 for the ocam, 0 for no reordering.  4 is for the array specified below...)
cameraParams[8*ncam:9*ncam]=50#priority
cameraParams[9*ncam]=1#affin el size
cameraParams[9*ncam+1:10*ncam+1]=camAffin[:ncam]#affinity
cameraParams[10*ncam+1]=namelen#number of bytes for the name.
cameraParams[10*ncam+2:10*ncam+2+(namelen+3)//4].view("c")[:]=camNames
cameraParams[10*ncam+2+(namelen+3)//4]=0#record timestamp

rmx = numpy.random.random((nacts,ncents)).astype("f")
# rmx = numpy.arange(nacts*ncents).astype("f")
rmx.shape = nacts,ncents
refCents = None#FITS.Read("/root/canapy-rtc/data/3Jul_calibSys_canapy_pokeValue040_interact_matrix_97_actuators_refcents.fits")[1]

# ab=numpy.array([1056,85]).astype("i")#.byteswap()
# camCommand="DigitizedImageWidth=%d;DigitizedImageHeight=%d;TestPattern=Off;GevStreamThroughputLimit=8000;R[0x0d04]=8164;R[0x12650]=7;Bulk0Mode=UART;R[0x20017814]=6;BulkNumOfStopBits=One;BulkParity=None;BulkLoopback=false;EventNotification=Off;"%(ab[0],ab[1])
# camCommand="DigitizedImageWidth={0};DigitizedImageHeight={1};Width={0};Height={1};TestPattern=Off;GevStreamThroughputLimit=10000;GevSCPSPacketSize=8976;SensorDigitizationTaps=Eight;Bulk0Mode=UART;Bulk0SystemClockDivider=By128;BulkNumOfStopBits=One;BulkParity=None;BulkLoopback=false;EventNotification=Off;".format(ab[0],ab[1])
#GevStreamThroughputLimit=1075773440 #8000 Mbps byteswapped.
#GevSCPSPacketSize=9000 doesn't seem settable - so set via reg instead:
#R[0x0d04]=9000  #Note, this-36 bytes of data sent per packet.  Default on switchon is 576 (540 bytes).  Seems to be set to 8164 by the eBUSPlayer - so probably use this!
#SensorDigitizationTaps=Eight  - doesn't work - need to set the register:
#[0x12650]=7  #Sets SensorDigitizationTaps to Eight

#Bulk0Mode=UART (which is enum 0 so don't need reg)
#Bulk0SystemClockDivider=By128 - need to set via reg:
#R[0x20017814]=6
#BulkNumOfStopBits=One  (which is enum 0 so don't need reg)
#BulkParity=None

# from current file
control["aravisCmd0"]="TestPattern=Off;GevStreamThroughputLimit=8000;GevSCPSPacketSize=8164;SensorDigitizationTaps=Eight;Bulk0Mode=UART;Bulk0SystemClockDivider=By128;BulkNumOfStopBits=One;BulkParity=None;BulkLoopback=false;EventNotification=Off;"

# control["aravisCmd0"]="TestPattern=Off;GevStreamThroughputLimit=9000;GevSCPSPacketSize=8976;SensorDigitizationTaps=Eight;Bulk0Mode=UART;Bulk0SystemClockDivider=By128;BulkNumOfStopBits=One;BulkParity=None;BulkLoopback=false;EventNotification=Off;"
# control["aravisCmd1"]="GevStreamThroughputLimit=9000;GevSCPSPacketSize=8976;FrameRate=20;Exposure=500;PixelFormat=Mono8;"
# control["aravisCmd1"]+="TriggerSelector=FrameStart;TriggerMode=On;TriggerSource=Hardware;GPI_Start_Exp_Mode=GPI_4;GPI_Start_Exp_Event=Falling_Edge;GPI_End_Exp_Mode=Internal;"
# control["aravisCmd1"]+="TriggerMode=Off;"

"""

Because here aravisCmd1 refers to the EVT scoring camera, NOT USED HERE
to change scoring camera parameters,
use darcmagic set -name=aravisCmd1 -string="FrameRate=50;" etc to change the framerate

"""
# reorder=numpy.zeros((264*172,),numpy.int32)
# for i in range(npxlx[0]*npxly[0]):
#     pxl=i//8#the pixel within a given quadrant
#     if((pxl%66>5) and (pxl<66*120)):#not an overscan pixel
#         amp=i%8#the amplifier (quadrant) in question
#         rl=1-i%2#right to left
#         tb=1-amp//4#top to bottom amp (0,1,2,3)?
#         x=(tb*2-1)*(((1-2*rl)*(pxl%66-6)+rl*59)+60*amp)+(1-tb)*(60*8-1)
#         y=(1-tb)*239+(2*tb-1)*(pxl//66)
#         j=y*264+x;
#         reorder[i]=j

# mirrorOpen=0

# mirrorParams=None#numpy.zeros((5,),"i")

# creepAbstats=numpy.random.random(97).astype("f")
# creepMean=numpy.random.random(97).astype("f")
# creepTime=time.time()
# creepMode=0

mirrorOpen=0

mirrorParams=numpy.zeros((5,),"i")
mirrorParams[0]=1#affin el size
mirrorParams[1]=50#prio
mirrorParams[2]=mirAffin[0]#thread affinity
mirrorParams[3:]=numpy.frombuffer(b"BAX224\0\0",dtype="i")#serial number of the mirror.  Need to export ACECFG to point to the directory holding the ALPAO config files.

print(f"mirrorParams = {mirrorParams}")

creepAbstats=numpy.random.random(97).astype("f")
creepMean=numpy.random.random(97).astype("f")
creepTime=time.time()
creepMode=0

# centIndexSize = 2  # 1<=(value)<=4
# centIndexArray = numpy.zeros((npxls,centIndexSize),numpy.float32)
# nn = numpy.concatenate([[0],numpy.cumsum(npxlx*npxly)])
# nnsub = numpy.concatenate([[0],numpy.cumsum(nsubx*nsuby)])
# print(centIndexArray.shape, nn, nnsub)

# for cam in range(ncam):
#     cia = centIndexArray[nn[cam]:nn[cam+1]]
#     cia.shape = npxly[cam],npxlx[cam],centIndexSize
#     if pyramidMode[cam] == 1:
#         cia[:npxly[cam]//2,:,0]=-1#lower
#         cia[npxly[cam]//2:,:,0]=1#upper
#         cia[:,:npxlx[cam]//2,1]=-1#left
#         cia[:,npxlx[cam]//2:,1]=1#right
#         # cia[:,:,2:] = 1
#     else:
#         cia[:,:,:] = make_cog_centIndexArray(npxlx[cam],npxly[cam],subapLocation[nnsub[cam]:,:])[:,:,:centIndexSize]

control.update({
    "switchRequested":0,#this is the only item in a currently active buffer that can be changed...
    "pause":0,
    "go":1,
    "maxClipped":nacts,
    "refCentroids":refCentroids,
    "centroidMode":"CoG",#whether data is from cameras or from WPU.
    "windowMode":"basic",
    "thresholdAlgo":1,
    "reconstructMode":"simple",#simple (matrix vector only), truth or open
    "centroidWeight":None,
    "v0":numpy.zeros((nacts,),"f"),#v0 from the tomograhpcic algorithm in openloop (see spec)
    "bleedGain":0.0,#0.05,#a gain for the piston bleed...
    "actMax":numpy.ones((nacts,),numpy.float32),#4095,#max actuator value
    "actMin":-numpy.ones((nacts,),numpy.float32),#4095,#max actuator value
    "nacts":nacts,
    "nactx":nactx,
    "actFlag":actFlag,
    "ncam":ncam,
    "nsub":nsuby*nsubx,
    "nsubx":nsubx,
    "nsuby":nsuby,
    "npxly":npxly,
    "npxlx":npxlx,
    "ncamThreads":ncamThreads,
    "pxlCnt":pxlCnt,
    "subapLocation":subapLocation,
    "bgImage":bgImage,
    "darkNoise":darkNoise,
    "closeLoop":0,
    "flatField":flatField,#numpy.random.random((npxls,)).astype("f"),
    "thresholdValue":1.0,#could also be an array.
    "powerFactor":1.,#raise pixel values to this power.
    "subapFlag":subapFlag,
    "fakeCCDImage":fakeCCDImage,
    "printTime":0,#whether to print time/Hz
    "rmx":rmx,#numpy.random.random((nacts,ncents)).astype("f"),
    "gain":numpy.ones((nacts,),"f"),#0.1*numpy.ones((nacts,),"f"),
    "E":numpy.zeros((nacts,nacts),"f"),#E from the tomoalgo in openloop.
    "threadAffElSize":threadAffElSize,
    "threadAffinity":threadAffinity,
    "threadPriority":threadPriority,
    "delay":delay,
    "clearErrors":0,
    "camerasOpen":camerasOpen,
    "camerasFraming":1,
    "cameraName":"libcamAravis.so",#"libcamfile.so",#"camfile",
    "cameraParams":cameraParams,
    "mirrorName":"libmirrorAlpaoSdk.so",
    "mirrorParams":mirrorParams,
    "mirrorOpen":mirrorOpen,
    "frameno":0,
    "switchTime":numpy.zeros((1,),"d")[0],
    "adaptiveWinGain":0.5,
    "corrThreshType":0,
    "corrThresh":0.,
    "corrFFTPattern":None,#correlation.transformPSF(correlationPSF,ncam,npxlx,npxly,nsubx,nsuby,subapLocation),
#    "correlationPSF":correlationPSF,
    "nsubapsTogether":1,
    "nsteps":0,
    "addActuators":0,
    "actuators":None,#(numpy.random.random((3,52))*1000).astype("H"),#None,#an array of actuator values.
    "actSequence":None,#numpy.ones((3,),"i")*1000,
    "recordCents":0,
    "pxlWeight":None,
    "averageImg":0,
    "slopeOpen":1,
    "slopeParams":None,
    "slopeName":"librtcslope.so",
    "actuatorMask":None,
    "averageCent":0,
    "calibrateOpen":1,
    "calibrateName":"librtccalibrate.so",
    "calibrateParams":None,
    "corrPSF":None,
    "centCalData":None,
    "centCalBounds":None,
    "centCalSteps":None,
    "figureOpen":0,
    "figureName":"figureSL240",
    "figureParams":None,
    "reconName":"libreconmvm.so",
    "fluxThreshold":0,
    "printUnused":1,
    "useBrightest":0,
    "figureGain":1,
    "decayFactor":None,#used in libreconmvm.so
    "reconlibOpen":1,
    "maxAdapOffset":0,
    "version":" "*120,
    #"lastActs":numpy.zeros((nacts,),numpy.uint16),
    # "camReorder4":reorder,
    "creepMean":creepMean,
    "creepAbstats":creepAbstats,
    "creepMode":creepMode,
    "creepTime":numpy.array([creepTime])[0],
    "pyramidMode":pyramidMode,
    "centIndexArray":centIndexArray,
    "pupilPos":pupilPos,
    "subapAllocation":subapAllocation,
    })
#control["pxlCnt"][-3:]=npxls#not necessary, but means the RTC reads in all of the pixels... so that the display shows whole image


### Display setup, values are returned through display

UTTM_config = {
    "nacts" : 2,
    "actx" : 1,
    "minVal" : -1.0,
    "maxVal" : 1.0,
    "midVal" : 0.0,
    "pokeVal" : 0.05,
    "scale" : lambda x: x,
    "flat" : [0]*2,
    "actMap" : [[1],[1]]
}

DTTM_config = {
    "nacts" : 2,
    "actx" : 1,
    "minVal" : -1.0,
    "maxVal" : 1.0,
    "midVal" : 0.0,
    "pokeVal" : 0.05,
    "scale" : lambda x: x,
    "flat" : [0]*2,
    "actMap" : [[1],[1]]
}

ALPAO9715_config = {
    "nacts" : 97,
    "actx" : 11,
    "offset" : 0.0,
    "minVal" : -1.0,
    "maxVal" : 1.0,
    "midVal" : 0.,
    "pokeVal" : 0.02,
    "scale" : lambda x: x,
    "flat" : [0]*97,
    "actMap" : [[0,0,0,1,1,1,1,1,0,0,0],
                [0,0,1,1,1,1,1,1,1,0,0],
                [0,1,1,1,1,1,1,1,1,1,0],
                [1,1,1,1,1,1,1,1,1,1,1],
                [1,1,1,1,1,1,1,1,1,1,1],
                [1,1,1,1,1,1,1,1,1,1,1],
                [1,1,1,1,1,1,1,1,1,1,1],
                [1,1,1,1,1,1,1,1,1,1,1],
                [0,1,1,1,1,1,1,1,1,1,0],
                [0,0,1,1,1,1,1,1,1,0,0],
                [0,0,0,1,1,1,1,1,0,0,0]
                ]
}

dms = [DTTM_config,UTTM_config,ALPAO9715_config]

display = {
    "dms" : dms
}

#### SRTC config, returned through srtc

modal_pmx = numpy.diag(numpy.ones(97))
zonal_pmx = numpy.diag(numpy.ones(97))

srtc = {
    "modal_pmx": modal_pmx,
    "zonal_pmx": zonal_pmx
}

printDEBUG = print



if 1:
    
    threadCounts = numpy.zeros(nthreads+1,dtype='i')
    # for i in range(len(subapAllocation)):
    #     if subapFlag[i]:
    #         threadCounts[subapAllocation[i]]+=1
    # for i in range(nthreads):
    #     try:
    #         j = numpy.where(subapAllocation==i)[0][-1]
    #         printDEBUG("thread {}, last subap={}, waiting for {} pixels".format(i,j,pxlCnt[j]))
    #     except Exception:
    #         printDEBUG("No more pixels")
    # print thread affinity and subaps per thread
    printDEBUG("thread\t\tcore\tsubaps\tbinary affin")
    printDEBUG("______________________________________________")
    bs = [bin(i) for i in mirAffin]
    for x in range(len(bs)):
            b = bs[x]
            l = [k for k in len(b)-numpy.array([j for j in range(len(b)) if b[j]=='1'])]
            if len(l):
                printDEBUG("mirror\t\t", x*32+l[0],"\t\t", [bin(j) for j in mirAffin])

    bs = [bin(i) for i in camAffin]
    for x in range(len(bs)):
            b = bs[x]
            l = [k for k in len(b)-numpy.array([j for j in range(len(b)) if b[j]=='1'])]
            if len(l):
                printDEBUG("camera\t\t", x*32+l[0],"\t\t", [bin(j) for j in camAffin])

    # print out threadAfinity in binary form for verification
    for i in range(nthreads+1):
        #print i,[bin(j) for j in threadAffinity[i*threadAffElSize:(i+1)*threadAffElSize]]
        bs = [bin(j) for j in threadAffinity[i*threadAffElSize:(i+1)*threadAffElSize]]
        for x in range(len(bs)):
            b = bs[x]
            l = [k for k in len(b)-numpy.array([j for j in range(len(b)) if b[j]=='1'])]
            if len(l):
                printDEBUG("recon:{}".format(i) if i>0 else "darc\t","\t", x*32+l[0],"\t", threadCounts[i-1] if i>0 else "","\t", [bin(j) for j in threadAffinity[i*threadAffElSize:(i+1)*threadAffElSize]])



if __name__ == "__main__":
    from lark import NoLarkError
    # xoff = [0]
    # xoff = xoff
    # yoff = [0]
    # yoff = yoff
    # sys.exit()
    # nsub1 = nsub
    # nsub1 = [42]
    # 
    print(nsubx,nthreads,npxlx,npxly,ncam,pyramidMode,xoff,yoff,xsep,ysep)
    old_ps = gen_subapParams(nsubx,nthreads,npxlx,npxly,ncam,pyramidMode,xoff,yoff,xsep,ysep)
    try:
        lrk = lark.LarkConfig("LgsWF").getlark()
    except NoLarkError as e:
        print(e)
    else:
        l = lrk
    
    param_names = list(old_ps.keys())
    param_names.append("rmx")
    
    print(param_names)
    
    # param_names = ["nsubx","ncamThreads","npxlx","npxly","ncam","pyramidMode"]
    params1 = l.getMany(param_names)
    # params1 = {k:v for k,v in params1.items()}
    # globals().update(params1)
    # # print(params1)

    nsubx[0] = 32
    xoff = [5]
    yoff = [5]
    xsep = [160]
    ysep = [160]
    print(nsubx,ncamThreads.sum(),npxlx,npxly,ncam,pyramidMode,xoff,yoff,xsep,ysep)
    params = gen_subapParams(nsubx,ncamThreads.sum(),npxlx,npxly,ncam,pyramidMode,xoff,yoff,xsep,ysep)

    # print(old_ps)
    # print(params)

    params["rmx"] = numpy.random.random((nacts,params["ncents"])).astype("f")
    
    # stuff = copydict(params)
    stuff = copydict(old_ps)
    for k,v in params1.items():
        print(k,repr(v),repr(params[k]))
    
    # sys.exit()
    # print(type(params1))
    print(l.setMany(copydict(params)))
    
    print(l.get("nsub",inactive=1))
    # print(l.queued)
    # ddd
    
    print(l.setMany(copydict(params),check=1,switch=1))
    # l.setMany(copydict(params1))
    # l.setMany(copydict(old_ps))
    
    # l.switchBuffer()
        