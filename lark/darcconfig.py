"""
This file contains helper functions for running darc config files.
These can be used directly by the config files, as templates to copy into config files,
or for generating parameters for sending to a running darc.
"""

from lark.darc import tel
from lark.utils import make_cog_centIndexArray
import numpy

def gen_threadParams(nthreads,ncam,start_thread):

    threadAffElSize = (nthreads+31)//32
    threadAffinity = numpy.zeros(((1+nthreads)*threadAffElSize),dtype=numpy.uint32)

    camAffin = numpy.zeros(ncam, dtype=numpy.uint32)
    camAffin[0] = 1<<(start_thread+1)

    mirAffin = numpy.zeros(1,dtype=numpy.uint32)
    mirAffin[0] = 1<<(start_thread+2)

    for i in range(0,nthreads):
        if (i<8):
            j = i+(start_thread+3) 
            threadAffinity[(i)*threadAffElSize+(j)//32] = 1<<(((j)%32))
        else:
            print("too many threads..")
            exit(0)

    threadAffinity[threadAffElSize:] = threadAffinity[:-threadAffElSize]
    threadAffinity[:threadAffElSize] = 0
    threadAffinity[0] = 1<<start_thread # control thread affinity 3
    names = ("camAffin","mirAffin","threadAffElSize","threadAffinity")
    return names,(camAffin,mirAffin,threadAffElSize,threadAffinity)
    
    
def gen_subapParams(nsubx,nthreads,npxlx,npxly,ncam,pyramidMode,xoff,yoff,xsep,ysep):
    nsuby = numpy.zeros((ncam,),dtype=numpy.int32)
    nsuby[0] = nsubx[0]
    nsubaps = (nsuby*nsubx).sum()#(nsuby*nsubx).sum()
    npxls = (npxly*npxlx).sum()
    subapFlag = numpy.zeros((nsubaps,),"i")
    for i in range(ncam):
        individualSubapFlag = tel.Pupil(nsubx[i],nsubx[i]/2.,0,nsubx[i]).subflag.astype("i")
        tmp = subapFlag[(nsuby[:i]*nsubx[:i]).sum():(nsuby[:i+1]*nsubx[:i+1]).sum()]
        tmp.shape = nsuby[i],nsubx[i]
        tmp[:] = individualSubapFlag
    #ncents=nsubaps*2
    ncents = subapFlag.sum()*2
    
    subapLocation = numpy.zeros((nsubaps,6),"i")
    nsubapsCum = numpy.zeros((ncam+1,),numpy.int32)
    ncentsCum = numpy.zeros((ncam+1,),numpy.int32)
    for i in range(ncam):
        nsubapsCum[i+1] = nsubapsCum[i]+nsuby[i]*nsubx[i]
        ncentsCum[i+1] = ncentsCum[i]+subapFlag[nsubapsCum[i]:nsubapsCum[i+1]].sum()*2

    # now set up a default subap location array...
    #this defines the location of the subapertures.
    # xoff = numpy.array([0]*ncam)+0
    # yoff = numpy.array([0]*ncam)+0
    # xoff = [15] # windowed
    # xoff = [12] # full frame
    # yoff = [15] # windowed
    # yoff = [15] # full frame
    # subx=(npxlx-xoff*2)/nsubx#[10]*ncam#(npxlx-48)/nsubx
    subx = [npxlx[0]//2]#npxlx//2#npxl
    # suby=(npxly-yoff*2)/nsuby#[10]*ncam#(npxly-8)/nsuby
    suby = [npxly[0]//2]#npxly//2#npxl

    # xsep = 194 # windowed
    # ysep = 100 # windowed
    # xsep = [180] # full frame
    # ysep = [175] # full frame
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
                    subapLocation[indx]=(yoff[k]+i,yoff[k]+i+ysep[k]+1,ysep[k],xoff[k]+j,xoff[k]+j+xsep[k]+1,xsep[k])
    # print(subapLocation)
    pxlCnt = numpy.zeros((nsubaps,),"i")
    subapAllocation=numpy.zeros((nsubaps,),"i")-1
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
                    subapAllocation[i*nsubx[k]+j]=i%nthreads
        else:
            for i in range(nsuby[k]):
                for j in range(nsubx[k]):
                    indx=nsubapsCum[k]+i*nsubx[k]+j
                    n=(subapLocation[indx,1]-1)*npxlx[k]+subapLocation[indx,4]
                    pxlCnt[indx]=n
                    subapAllocation[i*nsubx[k]+j]=i%nthreads
    pxlCnt[numpy.where(subapFlag==1)[-1]] = npxlx[0]*npxly[0]
    
    centIndexSize = 2  # 1<=(value)<=4
    centIndexArray = numpy.zeros((npxls,centIndexSize),numpy.float32)
    nn = numpy.concatenate([[0],numpy.cumsum(npxlx*npxly)])
    nnsub = numpy.concatenate([[0],numpy.cumsum(nsubx*nsuby)])
    # print(centIndexArray.shape, nn, nnsub)

    for cam in range(ncam):
        cia = centIndexArray[nn[cam]:nn[cam+1]]
        cia.shape = npxly[cam],npxlx[cam],centIndexSize
        if pyramidMode[cam] == 1:
            cia[:npxly[cam]//2,:,0]=-1#lower
            cia[npxly[cam]//2:,:,0]=1#upper
            cia[:,:npxlx[cam]//2,1]=-1#left
            cia[:,npxlx[cam]//2:,1]=1#right
            # cia[:,:,2:] = 1
        else:
            cia[:,:,:] = make_cog_centIndexArray(npxlx[cam],npxly[cam],subapLocation[nnsub[cam]:,:])[:,:,:centIndexSize]
    nsub = nsubx*nsuby
    refCentroids = numpy.zeros(ncents,dtype=numpy.float32)
    pupilPos = numpy.array([xoff,yoff,xsep,ysep],dtype=numpy.int32)
    names = ("nsub",
        "nsubx",
        "nsuby",
        "nsubaps",
        "subapFlag",
        "ncents",
        "subapLocation",
        "pxlCnt",
        "subapAllocation",
        "centIndexArray",
        "refCentroids",
        "pupilPos")
    return names,(
        nsub,
        nsubx,
        nsuby,
        nsubaps,
        subapFlag,
        ncents,
        subapLocation,
        pxlCnt,
        subapAllocation,
        centIndexArray,
        refCentroids,
        pupilPos)
    
    
# def gen_camParams(camera_name,framerate,ocam_windowed=False):
    
    
