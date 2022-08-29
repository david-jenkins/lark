#!/usr/bin/env python3
#darc, the Durham Adaptive optics Real-time Controller.
#Copyright (C) 2010 Alastair Basden.

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
# $Id: 26bf2d97ba7e3811ef88ccd1be67ade16007c486 $
#
# Functions to read and write FITS image files


import string
import numpy
import mmap
import os.path,os
import glob
from functools import reduce
error = 'FITS error'
#
# Read a FITS image file
#
# Returns a header, image tuple
# The header is returned in two forms, a raw list of header records, and
# a parsed dictionary for keyword access.
#
# By default, the image is returned as floats, using the BSCALE and BZERO
# keywords where available. By setting the asFloat keyword to zero it is 
# returned unscaled and in the (presumably more compact) numeric format
# that it was stored in
# 
reservedHdrList=["END","EXTEND","SIMPLE","XTENSION","NAXIS","BITPIX"]

def Read(filename, asFloat = 1,savespace=1,doByteSwap=1,compliant=1,allHDU=1,HDU=None,memmap=None):
    """if savespace is set, the array will maintain its type if asfloat is set.
    If doByteSwap is not set, no byteswap will be done if little endian - if this is the case, the file is not actually fits compliant
    if memmap is used, the file is memmapped rather than read.  If this is used, it is recommended that memmap="r" and that the file is non-byte-swapped.
    If allHDU==0 then will only read the current HDU.
    """
    if isinstance(filename,(str,os.PathLike)):
        flist=glob.glob(os.path.expanduser(filename))
        if len(flist)==0:
            raise Exception("No files found to load")
        else:
            filename=flist[0]
            if len(flist)>1:
                print("Ignoring %s"%str(flist[1:]))
                print("Loading %s"%flist[0])
        file = open(filename, "rb")
        filelen=os.path.getsize(filename)
    else:
        file=filename
        filename=str(filename)
        cur=file.tell()
        file.seek(0,2)#go to end of file
        filelen=file.tell()
        file.seek(cur,0)
    done=0
    returnVal=[]
    hduno=0
    while done==0:
        rawHeader = []
        header = {}
        buffer = file.read(2880)
        if buffer[:6] != b'SIMPLE' and buffer[:8] != b"XTENSION":
            if compliant:
                print("Warning - non compliant FITS file - error reading the %dth HDU - this should start with SIMPLE or XTENSION, but starts with:"%(len(returnVal)/2+1))
                print(buffer[:80])
                raise Exception(error+ 'Not a simple fits file: %s'%filename)
            else:
                print("WARNING - non compliant FITS file for %dth HDU"%(len(returnVal)/2+1))
                return returnVal
        while(1) :
            for char in range(0,2880,80) :
                line = buffer[char:char+80]
                rawHeader.append(line)
                key = line[:8].strip(b" ").strip(b"\0")
                if key :
                    val = line[9:]
                    val = val.strip(b" ").strip(b"\0")
                    if val :
                        if val[0] == "'" :
                            try:
                                pos = val.index(b"'",1)
                                val = val[1:pos]
                            except:
                                val=val[1:]
                        else :
                            pos = val.find(b'/')
                            if pos != -1 :
                                val = val[:pos]
                    if key in header:
                        header[key]+=val
                    else:
                        header[key] = val
            if b'END' in header : break
            buffer = file.read(2880).decode()
        naxis = int(header[b'NAXIS'])
        shape = []
        for i in range(1,naxis+1) :
            shape.append(int(header[b'NAXIS%d' % i]))
        shape.reverse()
        if len(shape)>0:
            numPix = 1
            for i in shape :
                numPix = numPix * i
        else:
            numPix=0
        bitpix = int(header[b'BITPIX'])
        if bitpix == 8 :
            typ = numpy.uint8
        elif bitpix == 16 :
            typ = numpy.int16
        elif bitpix == 32 :
            typ = numpy.int32
        elif bitpix == -32 :
            typ = numpy.float32
            bitpix = 32
        elif bitpix == -64 :
            typ = numpy.float64
            bitpix = 64
        elif bitpix==-16:
            typ=numpy.uint16
            bitpix=16
        elif bitpix==-8:
            typ=numpy.uint8
            bitpix=8
        elif bitpix==64:
            typ=numpy.int64
            bitpix=64
        else:
            print(("Unknown BITPIX: %d"%bitpix))
        numByte = numPix * bitpix//8
        if HDU is None or hduno==HDU:
            if memmap is None:
                data=numpy.fromfile(file,typ,count=numPix)
            else:
                nel=reduce(lambda x,y:x*y,shape)
                data=numpy.memmap(filename,dtype=typ,mode=memmap,offset=file.tell())[:nel]
                file.seek(bitpix/8*nel,1)
        else:
            file.seek(int((numByte+2880-1)//2880)*2880,1)
            data=None
        #data = file.read(numByte)
        #data = numpy.fromstring(data, dtype=typ)
        #data.savespace(1)
        if data is not None:
            if len(shape)>0:
                data.shape = shape
            if numpy.little_endian and doByteSwap:
                if b"UNORDERD" in header and header[b"UNORDERD"]=='T':
                    pass
                else:
                    data.byteswap(True)
            if asFloat :
                bscale = float(header.get(b'BSCALE', '1.0'))
                bzero = float(header.get(b'BZERO', '0.0'))
                if savespace:
                    if bscale!=1:
                        data*=bscale#array(bscale,typecode=typ)
                    if bzero!=0:
                        data+=bzero#array(bzero,typecode=typ)
                else:
                    data = data*bscale + bzero
            returnVal.append({ 'raw' : rawHeader, 'parsed' : header})
            returnVal.append(data)
            ntoread=2880-numByte%2880
            if ntoread!=0 and ntoread!=2880:
                file.read(ntoread).decode()
        #print "Read 1 hdu at %d/%d"%(file.tell(),filelen)
        if file.tell()==filelen or (allHDU==0 and data is not None):
            done=1
        hduno+=1
    return returnVal#( { 'raw' : rawHeader, 'parsed' : header},  data  )

#
# Save a numeric array to a FITS image file
#
# The FITS image dimensions are taken from the array dimensions.
# The data is saved in the numeric format of the array, or as 32-bit
# floats if a non-FITS data type is passed.
#
# A list of extra header records can be passed in extraHeader. The
# SIMPLE, BITPIX, NAXIS* and END records in this list are ignored.
# Header records are padded to 80 characters where necessary.
#
def Write(data, filename, extraHeader = None,writeMode='w',doByteSwap=1,preserveData=1,splitExtraHeader=0) :
    """Writes data to filename, with extraHeader (string or list of strings).  If writeMode="a" will overwrite existing file, or if "a", will append to it.  If doByteSwap==1, then will do the byteswap on systems that require it, to preserve the FITS standard.  If preserveData==1, will then byteswap back after saving to preserve the data.
    """
    #if type(data)==Numeric.ArrayType:
    #    typ = data.typecode()
    #else:#assume numpy...
    dirname=os.path.split(filename)[0]
    if len(dirname)==0:
        dirname="./"
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    typ=data.dtype.char
    if typ == 'b' or typ=='c' : bitpix = 8
    elif typ=='s' or typ=='h': bitpix = 16
    elif typ=='i' : bitpix = 32
    elif typ=='I':
        print("Converting uint32 to int32")
        bitpix=32
        data=data.view(numpy.int32)
    elif typ=='f': bitpix=-32
    elif typ=='d': bitpix=-64
    elif typ=='H': bitpix=-16
    elif typ=='B': bitpix=-8
    elif typ=='l' and data.itemsize==4: bitpix=32
    else :
        print("Converting type %s (itemsize %d) to float32"%(typ,data.itemsize))
        data = data.astype(numpy.float32)
        bitpix = -32
    shape = list(data.shape)
    shape.reverse()
    naxis = len(shape)
    if writeMode=='w' or os.path.exists(filename)==False:
        header = [ 'SIMPLE  = T']
        writeMode='w'
    else:
        header=  [ "XTENSION= 'IMAGE'"]
    header+=['BITPIX  = %d' % bitpix, 'NAXIS   = %d' % naxis ]
    for i in range(naxis) :
        keyword = 'NAXIS%d' % (i + 1)
        keyword = str.ljust(keyword, 8)
        header.append('%s= %d' % (keyword, shape[i]))
    header.append('EXTEND  = T')
    if doByteSwap==0 and numpy.little_endian:
        header.append('UNORDERD= T')
    if extraHeader is not None :
        if type(extraHeader)==type(""):
            extraHeader=[extraHeader]
        for rec in extraHeader :
            try :
                if "=" in rec[:10]:
                    key=rec.split("=")[0]
                else:
                    key = string.split(rec)[0]
            except IndexError :
                pass
            else :
                if key != 'SIMPLE' and \
                   key != 'BITPIX' and \
                   key[:5] != 'NAXIS' and \
                   key != 'END' :
                    if splitExtraHeader:
                        while len(rec)>80:
                            header.append(rec[:80])
                            rec=string.ljust(key,8)+"= "+rec[80:]
                    header.append(rec)
    header.append('END')
    header = [str.ljust(x,80)[:80] for x in header]
    header = ''.join(header)
    numBlock = (len(header) + 2880 - 1) // 2880
    header = str.ljust(''.join(header), numBlock*2880)
    file = open(filename, writeMode)
    file.write(header)
    if numpy.little_endian and doByteSwap:
        #if type(data)==Numeric.ArrayType:
        #    data = data.byteswapped()
        #else:
        data.byteswap(True)
    data.tofile(file)
    #data = data.tobytes()
    #file.write(data)
    numBlock = (data.itemsize*data.size + 2880 - 1) // 2880
    padding = ' ' * (numBlock*2880 - data.itemsize*data.size)
    file.write(padding)
    if numpy.little_endian and doByteSwap and preserveData==1:
        #if type(data)==Numeric.ArrayType:
        #    pass
        #else:#preserve the data...
        data.byteswap(True)


def ReadHeader(filename, asFloat = 1) :
    """Reads the Header.  If filename is an open file, will seek to the end of the data unit before returning"""
    if type(filename)==type(""):
        flist=glob.glob(os.path.expanduser(filename))
        if len(flist)==0:
            raise Exception("No files found to load")
        else:
            filename=flist[0]
            if len(flist)>1:
                print("Ignoring %s"%str(flist[1:]))
                print("Loading %s"%flist[0])
        file = open(filename, "r")
        doseek=0
    else:
        file=filename
        doseek=1
    header = {}
    rawHeader = []
    buffer = file.read(2880)
    if buffer[:6] != 'SIMPLE' and buffer[:8]!="XTENSION":
        raise Exception(error+ 'Not a simple fits file')
    while(1) :
        for char in range(0,2880,80) :
            line = buffer[char:char+80]
            rawHeader.append(line)
            key = string.strip(line[:8])
            if key :
                val = line[9:]
                val = string.strip(val)
                if val :
                    if val[0] == "'" :
                        try:
                            pos = string.index(val,"'",1)
                            val = val[1:pos]
                        except:
                            val=val[1:]
                    else :
                        pos = string.find(val, '/')
                        if pos != -1 :
                            val = val[:pos]
                if key in header:
                    header[key]+=val
                else:
                    header[key] = val
        if 'END' in header : break
        buffer = file.read(2880)
    if doseek:
        elsize=abs(int(header["BITPIX"]))/8
        nax=int(header["NAXIS"])
        size=1
        for i in range(nax):
            size*=int(header["NAXIS%d"%(i+1)])
        datasize=((size*elsize+2880-1)//2880)*2880
        #move to end of data unit (to start of next header)
        file.seek(datasize,1)
    return( { 'raw' : rawHeader, 'parsed' : header} )

def MakeHeader(shape,dtype,extraHeader=None,doByteSwap=1,extension=0,splitExtraHeader=0):
    """Return a text string which can be used as a header"""
    if dtype=="b": bitpix=8
    elif dtype=="B": bitpix=-8
    elif dtype=="s": bitpix=16
    elif dtype=="h": bitpix=16
    elif dtype=="i": bitpix=32
    elif dtype=="I": bitpix=32
    elif dtype=="f": bitpix=-32
    elif dtype=="d": bitpix=-64
    elif dtype=='H': bitpix=-16
    else: raise Exception("Unknown datatype in MakeHeader")
    shape=list(shape)
    shape.reverse()
    naxis=len(shape)
    if extension:
        header=["XTENSION= 'IMAGE'"]
    else:
        header=["SIMPLE  = T"]
    header+=["BITPIX  = %d"%bitpix,"NAXIS   = %d"%naxis]
    for i in range(naxis):
        keyword = 'NAXIS%d' % (i + 1)
        keyword = string.ljust(keyword, 8)
        header.append('%s= %d' % (keyword, shape[i]))
    header.append('EXTEND  = T')
    if doByteSwap==0 and numpy.little_endian:
        header.append('UNORDERD= T')
    if extraHeader is not None :
        if type(extraHeader)==type(""):
            extraHeader=[extraHeader]
        for rec in extraHeader :
            try :
                key = string.split(rec)[0]
            except IndexError :
                pass
            else :
                if key != 'SIMPLE' and \
                        key != 'BITPIX' and \
                        key[:5] != 'NAXIS' and \
                        key != 'END' :
                    if splitExtraHeader:
                        while len(rec)>80:
                            header.append(rec[:80])
                            rec=string.ljust(key,8)+"= "+rec[80:]
                    header.append(rec)
    header.append('END')
    header = [string.ljust(x,80)[:80] for x in header]
    header = ''.join(header)
    numBlock = (len(header) + 2880 - 1) / 2880
    header = string.ljust("".join(header), numBlock*2880)
    return header


def WriteKey(file,key,value=None,comment=None):
    """Will write to file object file at current position."""
    if file.tell()%80!=0:
        print("ERROR: util.FITS.WriteKey - not at the start of a header line")
        raise Exception("FITS error")
    txt=key+" "*(8-len(key))
    if value is not None:
        txt+="= "+str(value)
    if comment is not None:
        txt+=" /"+comment
    txt=txt+" "*(80-len(txt))
    txt=txt[:80]
    file.write(txt)
def EndHeader(file):
    WriteKey(file,"END")
    pos=file.tell()
    pmod=pos%2880
    if pmod>0:
        file.write(" "*(2880-pmod))
def End(file):
    pos=file.tell()
    pmod=pos%2880
    if pmod>0:
        file.write(" "*(2880-pmod))
def WriteHeader(file,shape,typ,firstHeader=1,doByteSwap=1,extraHeader=None):
    """Write the header for a FITS file."""
    if typ == 'b' or typ=='c' : bitpix = 8
    elif typ=='s' or typ=='h' : bitpix = 16
    elif typ=='i' : bitpix = 32
    elif typ=='I' :
        print("Saving uint32 as int32")
        bitpix=32
    elif typ=='f': bitpix=-32
    elif typ=='d': bitpix=-64
    elif typ=='H': bitpix=-16
    elif typ=='B': bitpix=-8
    elif typ=='l':
        if numpy.empty((1,),numpy.int).itemsize==4:
            bitpix=32
        else:
            bitpix=64
    else :
        print("Assuming type %s will be saved as float32"%typ)
        bitpix = -32
    shape=shape[:]
    shape.reverse()
    naxis = len(shape)
    if firstHeader:
        header = [ 'SIMPLE  = T']
    else:
        header=  [ "XTENSION= 'IMAGE'"]
    header+=['BITPIX  = %d' % bitpix, 'NAXIS   = %d' % naxis ]
    for i in range(naxis) :
        keyword = 'NAXIS%d' % (i + 1)
        keyword = string.ljust(keyword, 8)
        header.append('%s= %d' % (keyword, shape[i]))
    header.append('EXTEND  = T')
    if doByteSwap==0 and numpy.little_endian:
        header.append('UNORDERD= T')
    if extraHeader is not None :
        if type(extraHeader)==type(""):
            extraHeader=[extraHeader]
        for rec in extraHeader :
            try :
                key = string.split(rec)[0]
            except IndexError :
                pass
            else :
                if key != 'SIMPLE' and \
                   key != 'BITPIX' and \
                   key[:5] != 'NAXIS' and \
                   key != 'END' :
                    header.append(rec)
    header.append('END')
    header = [string.ljust(x,80)[:80] for x in header]
    header = "".join(header)
    numBlock = (len(header) + 2880 - 1) / 2880
    header = string.ljust("".join(header), numBlock*2880)
    file.write(header)


    
def WriteComment(file,comment):
    if file.tell()%80!=0:
        print("ERROR: util.FITS.WriteComment - not at the start of a header line")
        raise Exception("FITS error")
    while len(comment)>0:
        c="COMMENT "+comment[:72]
        comment=comment[72:]
        c=c+" "*(80-len(c))
        file.write(c)

def savecsc(csc,filename,hdr=None,doByteSwap=1):
    """Save a scipy.sparse.csc sparse matrix"""
    if type(hdr)==type(""):
        hdr=[hdr]
    elif type(hdr)==type(None):
        hdr=[]
    hdr.append("SHAPE   = %s"%str(csc.shape))
    rowind=csc.rowind[:csc.indptr[-1]].view(numpy.int32)
    indptr=csc.indptr.view(numpy.int32)
    
    Write(csc.data[:csc.indptr[-1]],filename,extraHeader=hdr,doByteSwap=doByteSwap)
    Write(rowind,filename,writeMode="a",doByteSwap=doByteSwap)
    Write(indptr,filename,writeMode="a",doByteSwap=doByteSwap)
def loadcsc(filename,doByteSwap=1):
    """Load a scipy.sparse.csc sparse matrix"""
    f=Read(filename,savespace=1,doByteSwap=doByteSwap)
    if len(f)==2:
        print("WARNING - loadcsc - %s is not a sparse matrix"%filename)
        mx=f[1].astype("f")
    elif len(f)>2:
        import scipy.sparse
        mx=scipy.sparse.csc_matrix((numpy.array(f[1],copy=0),numpy.array(f[3],copy=0).view(numpy.uint32),numpy.array(f[5],copy=0).view(numpy.uint32)),eval(f[0]["parsed"]["SHAPE"]))
    return mx

def saveSparse(sp,filename,writeMode="w",hdr=None,doByteSwap=1):
    """Save a sparse matrix - csc or csr."""
    if type(hdr)==type(""):
        hdr=[hdr]
    elif type(hdr)==type(None):
        hdr=[]
    hdr.append("SHAPE   = %s"%str(sp.shape))
    hdr.append("FORMAT  = '%s'"%sp.format)
    if sp.format=="csr":
      if hasattr(sp,'colind'):
         hdr.append("MODERN  = 0")
         ind=sp.colind[:sp.indptr[-1]]
      else:
         hdr.append("MODERN  = 1")
         ind=sp.indices
    elif sp.format=="csc":
      if hasattr(sp,'rowind'):
         hdr.append("MODERN  = 0")
         ind=sp.rowind[:sp.indptr[-1]]
      else:
         hdr.append("MODERN  = 1")
         ind=sp.indices
    else:
        raise Exception("Sparse matrix type not yet implemented")
    Write(sp.data[:sp.indptr[-1]],filename,writeMode=writeMode,extraHeader=hdr,doByteSwap=doByteSwap)

    Write(ind.view(numpy.int32),filename,writeMode="a",doByteSwap=doByteSwap)
    Write(sp.indptr.view(numpy.int32),filename,writeMode="a",doByteSwap=doByteSwap)

def loadSparse(filename,matrixNum=0,doByteSwap=1):
    """load a scipy.sparse matrix - csc or csr."""
    f=Read(filename,savespace=1,doByteSwap=doByteSwap)
    knownForms=('csr','csc')
    if len(f)==2:
        print("WARNING - loadSparse - %s is not a sparse matrix"%filename)
        mx=f[1]
    elif len(f)%6==0 and len(f[1].shape)==1:
        # presuming 1 or more sparse matrices
        numMatrices=len(f)//6
        if matrixNum>=numMatrices:
           raise Exception("ERROR: loadSparse: Cannot load matrix "+
                 "number %d, only %d %s in the file" % (
                    matrixNum,numMatrices,
                    (numMatrices==1)*"matrix"+(numMatrices>1)*"matrices" ))
        f_offset=matrixNum*6
        import scipy.sparse
        if "FORMAT" in f[0+f_offset]["parsed"]:
            fmt=f[0+f_offset]["parsed"]["FORMAT"]
            mxShape=eval(f[0+f_offset]["parsed"]["SHAPE"])
        else:
            print("Warning - loadSparse %s - assuming csc"%filename)
            fmt="csc"
        if "SHAPE" in f[0+f_offset]["parsed"]:
           mxShape=eval(f[0+f_offset]["parsed"]["SHAPE"])
        else:
           raise Exception( "ERROR: loadSparse: No SHAPE header information" )
        if fmt not in knownForms:
           raise Exception( "ERROR: loadSparse: Not a known form, %s"%(fmt) )
        if "MODERN" in f[0+f_offset]["parsed"]:
            modern=int(f[0+f_offset]["parsed"]["MODERN"])
        else:
            print(("Warning - loadSparse %s - assuming not modern type"%filename))
            modern=0
        print(("Format is %s with %s" %
              (fmt, (modern)*"modern scipy"+(~modern)*"unmodern or old scipy")))
        # note, at this stage modern does not affect the logic but it may do
        # in the future hence it is noted.
        if fmt=="csr":
           thisOperator=scipy.sparse.csr_matrix
        elif fmt=="csc":
           thisOperator=scipy.sparse.csc_matrix
       
        # n.b. the following astype's were view's, but they no longer worked,
        #  perhaps because of a change in the Read function?
        data=f[1+f_offset] ; indices=f[3+f_offset].astype(numpy.uint32)
        indptr=f[5+f_offset].astype(numpy.uint32)
        if indptr.shape[0]==(mxShape[int(fmt=='csc')]+1)*2:
           indptr=indptr.astype(numpy.uint64)
        mx=thisOperator( ( data, indices, indptr ), shape=mxShape )
    else:
        mx=f[1]
        print("util.FITS.loadSparse - matrix style not known %s, assuming dense matrix"%filename)
    return mx

def loadBlockMatrix(filename,doByteSwap=1):
    f=Read(filename,savespace=1,doByteSwap=doByteSwap)
    #if len(f)==2:
    #    mx=f[1]
    #else:
    import util.blockMatrix
    mx=util.blockMatrix.BlockMatrix()
    mx.assign(f[1::2])
    return mx
def saveBlockMatrix(mx,filename,extraHeader=None,doByteSwap=1):
    wm="w"
    for b in mx.blockList:#append the blocks to the file.
        Write(b,filename,writeMode=wm,extraHeader=extraHeader,doByteSwap=doByteSwap)
        wm="a"

def extractHDU(filename,hduno,outname,overwrite=0):
    """Extracts a given HDU from a fits file, writing it to a new fits file.
    Numbering from 0 - so first HDU is 0."""
    if os.path.exists(outname) and overwrite==0:
        raise Exception("Output file %s already exists"%outname)
    f = open(filename, "r")
    for i in range(hduno+1):
        pos=f.tell()
        hdr=ReadHeader(f)["parsed"]
        #get the data size:
        # elsize=abs(int(hdr["BITPIX"]))/8
        # nax=int(hdr["NAXIS"])
        # size=1
        # for i in range(nax):
        #     size*=int(hdr["NAXIS%d"%(i+1)])
        # datasize=((size*elsize+2880-1)//2880)*2880
        # #move to end of data unit (to start of next header)
        # f.seek(datasize,1)
        endpos=f.tell()
    #now we've got to correct position - so read into the new file.
    out=open(outname,"w")
    #write first line...
    out.write("SIMPLE  = T"+" "*68+"\n")
    pos+=80#don't copy first line.
    f.seek(pos)
    left=endpos-pos
    while left>0:
        toread=1024*1024
        if left>toread:
            left-=toread
        else:
            toread=left
            left=0
        data=f.read(toread)
        out.write(data)
    f.close()
    out.close()



def updateLastAxis(fd,lastAxis,mm=None):
    """if mm is specidied, fd is not used.
    mm should be a numpy.memmap object...
    """
    doclose=0
    #fd.seek(0)
    if mm is None:
        mm=mmap.mmap(fd.fileno(),2880)#this can fail if fd not opened in mode "+" (a+ or w+).
        doclose=1
    done=0
    naxis=0
    pos=0
    while done==0:
        if type(mm)==numpy.memmap:
            txt=mm[pos*80:pos*80+80].tobytes().decode()
        else:
            txt=mm.read(80)
        if txt[:8]=="NAXIS   ":
            naxis=int(txt[10:])
        elif txt[:8]=="NAXIS%d  "%naxis:
            tmp="NAXIS%d  = %d"%(naxis,lastAxis)
            tmp+=" "*(80-len(tmp))
            if type(mm)==numpy.memmap:
                mm[pos*80:pos*80+80]=tmp
            else:
                mm.seek(-80,1)
                mm.write(tmp)
            done=1
        pos+=1
    if doclose:
        mm.close()

def AddToHeader(fname,txtlist,addcomment=1,format=1):
    """Inserts fits comments/paramters into a fits header
    If addcomment==1, will prefix each line with COMMENT.  
    If addcomment==0, lines must be <=80 characters long.
    If format==1 and addcomment==0, will format name=value lines, and lines without = will be prefixed with COMMENT.
    """
    if type(txtlist)==type(""):
        txtlist=[txtlist]
    f=open(fname,"a+")
    mm=mmap.mmap(f.fileno(),2880)#this can fail if f not opened in mode "+" (a+ or w+).
    for i in range(36):
        txt=mm.read(80)
        if txt[:8]=="END     ":
            break
    nhdr=i
    mm.seek(80*nhdr)
    etxt=mm.read(8)
    if etxt!="END     ":
        raise Exception("Unknown FITS END header: %s (nhdr=%d)"%(etxt,nhdr))
    mm.seek(80*nhdr)
    ttlist=[]
    if addcomment:
        for t in txtlist:
            while len(t)>71:
                ttlist.append("COMMENT ="+t[:70]+"\n")
                t=t[71:]
            ttlist.append("COMMENT ="+t+" "*(70-len(t))+"\n")
    else:#assume is of fits standard.
        if format:
            tmp=[]
            for t in txtlist:
                t=t.split("=")
                if len(t)>1:
                    n=(t[0]+" "*(8-len(t[0])))[:8]
                    v="=".join(t[1:]).strip()
                    tmp.append(n+"= "+v)
                else:
                    if not t[0].startswith("COMMENT"):
                        t="COMMENT = "+t[0]
                    tmp.append(t)
            txtlist=tmp
        for t in txtlist:
            if len(t)>80:
                raise Exception("Line too long for FITS header")
            ttlist.append(t+" "*(80-len(t)))
    if len(ttlist)+nhdr+1>36:
        raise Exception("FITS Header too long to fit")
    ttlist.append("END"+" "*77)
    tthdr="".join(ttlist)
    if len(tthdr)>80*(36-nhdr):
        raise Exception("FITS header too long to fit...")
    mm.write(tthdr)
    mm.close()
    f.close()

if __name__=="__main__":
    import sys
    import pylab
    if len(sys.argv)>1:
        fname=sys.argv[1]
    else:
        print("Usage: %s filename.fits [HDU]"%sys.argv[0])
        sys.exit(0)
    hdu=0
    if len(sys.argv)>2:
        hdu=int(sys.argv[2])
    hdus=Read(fname)
    data=hdus[hdu*2+1]
    for raw in hdus[hdu*2]["raw"]:
        print(raw.strip())
        if raw.strip()=="END":
            break
    #for key in hdus[hdu*2]["parsed"].keys():
    #    print key,hdus[hdu*2]["parsed"][key]
    #print hdus[hdu*2]["parsed"]
    import plot
    import gtk
    p=plot.plot(startGtk=0,quitGtk=1,usrtoolbar=plot.plotToolbar)
    p.buttonPress(None,3)
    #p.mytoolbar.loadFunc=self.p.loadFunc
    p.txtPlot.hide()
    p.txtPlotBox.hide()
    p.image.hide()
    
    p.plot(data)
    gtk.main()
    #if len(data.shape)==1:
    #    pylab.plot(data)
    #else:
    #    data.shape=(data.shape[0],reduce(lambda x,y:x*y,data.shape[1:]))
    #    pylab.imshow(data,interpolation="nearest",cmap=pylab.cm.gray)
    #pylab.show()
    
