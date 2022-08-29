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

from pathlib import Path
from lark.darc import FITS
from lark.darc import tel
import numpy
import time
import os
from lark.utils import make_cog_centIndexArray


delay = 0#10000#10000

control = {}
display = {}
srtc = {}

##### DARC setup, values are returned through control

nacts = 1
ncam = 1
nthreads = 1
nn = nthreads//ncam #threads per camera
ncamThreads = numpy.ones((ncam,),dtype=numpy.int32)*nn
nthreads = ncamThreads.sum() # new total number of threads, multiple of ncam
print(nthreads)
print(ncamThreads)
nsub = numpy.zeros((ncam,),dtype=numpy.int32)
nsub[0] = 3
npxl = numpy.zeros((ncam,),dtype=numpy.int32)
npxl[0] = 10

pyramidMode = numpy.zeros((ncam,),dtype=numpy.int32)
pyramidMode[0] = 0

threadPriority = 50*numpy.ones((nthreads+1,),dtype=numpy.uint32)

threadAffElSize = 1
threadAffinity = numpy.zeros(((1+nthreads)*threadAffElSize),dtype=numpy.uint32)

start_thread = 5

camAffin = numpy.zeros(ncam,dtype=numpy.uint32)
camAffin[0] = 1<<(start_thread+1) #1 thread

for i in range(0,nthreads):
    if (i<8):
        j = (start_thread+2)
        threadAffinity[(i)*threadAffElSize+(j)//32] = 1<<(((j)%32))
    else:
        print("too many threads..")
        exit(0)

threadAffinity[threadAffElSize:] = threadAffinity[:-threadAffElSize]
threadAffinity[:threadAffElSize] = 0
threadAffinity[0] = 1<<(start_thread)# control thread affinity

actFlag=None

print("Using %d cameras"%ncam)
# ncamThreads = numpy.ones((ncam,),numpy.int32)

npxly = numpy.zeros((ncam,),dtype=numpy.int32)
npxly[0] = 512#121

npxlx=numpy.zeros((ncam,),dtype=numpy.int32)
npxlx[0] = 512#1056

nsuby = numpy.zeros((ncam,),dtype=numpy.int32)
nsuby[0] = nsub[0]

nsubx = numpy.zeros((ncam,),dtype=numpy.int32)
nsubx[0] = nsub[0]

nsubaps = (nsuby*nsubx).sum()#(nsuby*nsubx).sum()
subapFlag = numpy.zeros((nsubaps,),"i")
for i in range(ncam):
    individualSubapFlag = tel.Pupil(nsub[i],nsub[i]/2.,0,nsub[i]).subflag.astype("i")
    tmp = subapFlag[(nsuby[:i]*nsubx[:i]).sum():(nsuby[:i+1]*nsubx[:i+1]).sum()]
    tmp.shape = nsuby[i],nsubx[i]
    tmp[:] = individualSubapFlag
#ncents=nsubaps*2
ncents = subapFlag.sum()*2
npxls = (npxly*npxlx).sum()

fakeCCDImage = None#(numpy.random.random((npxls,))*20).astype("i")

bgImage = None#numpy.load("/home/canapyrtc/data/bg_windowed_100Hz.npy")#None#FITS.Read("shimgb1stripped_bg.fits")[1].astype("f")#numpy.zeros((npxls,),"f")
darkNoise = None#numpy.load("/home/canapyrtc/data/dk_windowed_100Hz.npy")#None#FITS.Read("shimgb1stripped_dm.fits")[1].astype("f")
flatField = None#FITS.Read("shimgb1stripped_ff.fits")[1].astype("f")

subapLocation = numpy.zeros((nsubaps,6),"i")
nsubapsCum = numpy.zeros((ncam+1,),numpy.int32)
ncentsCum = numpy.zeros((ncam+1,),numpy.int32)
for i in range(ncam):
    nsubapsCum[i+1] = nsubapsCum[i]+nsuby[i]*nsubx[i]
    ncentsCum[i+1] = ncentsCum[i]+subapFlag[nsubapsCum[i]:nsubapsCum[i+1]].sum()*2

# now set up a default subap location array...
#this defines the location of the subapertures.
xoff = numpy.array([0]*ncam)+0
yoff = numpy.array([0]*ncam)+0
xoff = [100]#, 12]
yoff = [100]#, 1]
# subx=(npxlx-xoff*2)/nsubx#[10]*ncam#(npxlx-48)/nsubx
subx = [100]#,20]#npxlx//2#npxl
# suby=(npxly-yoff*2)/nsuby#[10]*ncam#(npxly-8)/nsuby
suby = [100]#,20]#npxly//2#npxl

sepx = 194
sepy = 100
for k in range(ncam):
    if pyramidMode[k]==0:
        for i in range(nsuby[k]):
            for j in range(nsubx[k]):
                indx = nsubapsCum[k]+i*nsubx[k]+j
                subapLocation[indx] = (yoff[k]+i*suby[k],yoff[k]+i*suby[k]+suby[k],1,xoff[k]+j*subx[k],xoff[k]+j*subx[k]+subx[k],1)
    else:
        for i in range(nsuby[k]):
            for j in range(nsubx[k]):
                indx = nsubapsCum[k]+i*nsubx[k]+j
                # subapLocation[indx] = (yoff[k]+i*suby[k],yoff[k]+i*suby[k]+suby[k],1,xoff[k]+j*subx[k],xoff[k]+j*subx[k]+subx[k],1)
                subapLocation[indx]=(yoff[k]+i,yoff[k]+i+sepy+1,sepy,xoff[k]+j,xoff[k]+j+sepx+1,sepx)
print(subapLocation)

pxlCnt = numpy.zeros((nsubaps,),"i")
# set up the pxlCnt array - number of pixels to wait until each subap is ready.  Here assume identical for each camera.
for k in range(ncam):
    if pyramidMode[k]==0:
        # tot=0#reset for each camera
        for i in range(nsuby[k]):
            for j in range(nsubx[k]):
                indx = nsubapsCum[k]+i
                #n=(subapLocation[indx,1]-1)*npxlx[k]+subapLocation[indx,4]
                n = 2*subapLocation[indx,1]*npxlx[k]#whole rows together...
                pxlCnt[indx] = n
                pxlCnt[nsubaps-indx-1] = n
    else:
        for i in range(nsuby[k]):
            for j in range(nsubx[k]):
                indx=nsubapsCum[k]+i*nsubx[k]+j
                n=(subapLocation[indx,1]-1)*npxlx[k]+subapLocation[indx,4]
                pxlCnt[indx]=n
pxlCnt[-3] = npxlx[0]*npxly[0]
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
camList = ["EVT-HB-1800SM-640002-ESO"][:ncam]
camNames=";".join(camList)#"Imperx, inc.-110323;Imperx, inc.-110324"
print(camNames)
while len(camNames)%4!=0:
    camNames+="\0"
namelen=len(camNames)
cameraParams=numpy.zeros((10*ncam+3+(namelen+3)//4,),numpy.int32)
cameraParams[0:ncam]=8#16 bpp - though aravis should be told it is 8 bpp.
cameraParams[ncam:2*ncam]=65536#block size
cameraParams[2*ncam:3*ncam]=256#x offset
cameraParams[3*ncam:4*ncam]=256#y offset
cameraParams[4*ncam:5*ncam]=npxlx[0]#npxlx
cameraParams[5*ncam:6*ncam]=npxly[0]#npxly
cameraParams[6*ncam:7*ncam]=0#byteswapInt (1 for ocam)
cameraParams[7*ncam:8*ncam]=0#reorder (2 or 3 for the ocam, 0 for no reordering.  4 is for the array specified below...)
cameraParams[8*ncam:9*ncam]=50#priority
cameraParams[9*ncam]=1#affin el size
cameraParams[9*ncam+1:10*ncam+1]=camAffin[:ncam]#affinity
cameraParams[10*ncam+1]=namelen#number of bytes for the name.
cameraParams[10*ncam+2:10*ncam+2+(namelen+3)//4].view("c")[:]=camNames
cameraParams[10*ncam+2+(namelen+3)//4]=0#record timestamp

rmx=numpy.zeros((nacts,ncents)).astype("f")
# rmx=numpy.random.random((nacts,ncents)).astype("f")

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

# control["aravisCmd0"]="GevStreamThroughputLimit=9000;GevSCPSPacketSize=8976;FrameRate=20;Exposure=500;PixelFormat=Mono8;"

control["aravisCmd0"]="GevSCPSPacketSize=9000;FrameRate=100;Exposure=5000;PixelFormat=Mono8;Gain=500;"
#control["aravisCmd0"]+="TriggerSelector=FrameStart;TriggerMode=On;TriggerSource=Hardware;GPI_Start_Exp_Mode=GPI_4;GPI_Start_Exp_Event=Falling_Edge;GPI_End_Exp_Mode=Internal;"
control["aravisCmd0"]+="TriggerMode=Off;"

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

mirrorOpen=0

mirrorParams=None#numpy.zeros((5,),"i")


control.update({
    "switchRequested":0,#this is the only item in a currently active buffer that can be changed...
    "pause":0,
    "go":1,
    "maxClipped":nacts,
    "refCentroids":refCents,
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
    "gain":0.1*numpy.ones((nacts,),"f"),
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
    "pyramidMode":pyramidMode,
    "noPrePostThread":0,
    "actFlag":None,
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
