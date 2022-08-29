

from functools import partialmethod
import importlib
import sys
from collections import ChainMap
from datetime import datetime
import os
import json
from types import SimpleNamespace
import toml
from typing import Any, Dict, List, Tuple, Union
import numpy
from pathlib import Path
from lark.darc import tel

MAX_ARRAY_SIZE = 20

MANUAL_MODULES = {}

SERIALIZER = "toml" #  or "json"

def partialclass(cls, *args, **kwargs):
    class PartialClass(cls):
        __init__ = partialmethod(cls.__init__, *args, **kwargs)
    return PartialClass

class UpperDict(dict):
    def __getitem__(self, __k: str) -> Any:
        if not isinstance(__k, str):
            raise KeyError("key must be a string")
        return super().__getitem__(__k.upper())
    def __setitem__(self, __k: str, __v: Any) -> None:
        if not isinstance(__k, str):
            raise KeyError("key must be a string")
        return super().__setitem__(__k.upper(), __v)

def encodeValue(value, key="", fname="", inkey="_"):
    return_type = None
    return_file = None
    if isinstance(value, bytes):
        return_value = value.decode()
        return_type = "bytes"
    elif isinstance(value, numpy.number):
        return_value = value.tolist()
        return_type = str(value.dtype)
    elif isinstance(value, numpy.ndarray):
        if value.size > MAX_ARRAY_SIZE:
            return_value = f":_ndarray_:{fname}{inkey}{key}.npy"
            return_file = value
        else:
            return_value = value.tolist()
            return_type = str(value.dtype)
    elif isinstance(value, dict):
        tmp = encodeDict(value,fname,inkey+key)
        return_value = tmp["values"]
        return_file = tmp["files"]
    elif isinstance(value, (int,float,str,bool,type(None))):
        return_value = value
    elif isinstance(value, list):
        inlist = {str(i):v for i,v in enumerate(value)}
        tmp = encodeDict(inlist,fname,inkey+key)
        tmp["values"]["__list__"] = 1
        return_value = tmp["values"]
        return_file = tmp["files"]
    elif isinstance(value, (list,tuple)):
        inlist = {str(i):v for i,v in enumerate(value)}
        tmp = encodeDict(inlist,fname,inkey+key)
        tmp["values"]["__tuple__"] = 1
        return_value = tmp["values"]
        return_file = tmp["files"]
    else:
        raise ValueError(f"Type {type(value)} not yet encodable")
    return return_value, return_file, return_type

# def encodeList(inlist,fname="",inkey="_"):
#     if not inkey.endswith("_"):
#         inkey =  inkey + "_"
#     files = {}
#     values = {}
#     types = {}
#     for key, value in enumerate(inlist):
#         key = str(key)
#         return_value, return_file, return_type = encodeValue(value,key,fname)
#         values[key] = return_value
#         if return_file is not None: files[key] = return_file
#         if return_type is not None: types[key] = return_type
#     return {"values":values, "files":files, "types":types, "__list__":1}

# def encodeList(inlist,fname="",inkey="_"):
#     indict = {str(i):v for i,v in enumerate(inlist)}
#     outdict = encodeDict(indict)
#     outdict["values"]["__list__"] = 1
#     return outdict

def encodeDict(indict,fname="",inkey="_"):
    if not inkey.endswith("_"):
        inkey =  inkey + "_"
    files = {}
    values = {}
    types = {}
    for key, value in indict.items():
        return_value,return_file,return_type = encodeValue(value,key,fname,inkey)
        values[key] = return_value
        if return_file is not None: files[key] = return_file
        if return_type is not None: types[key] = return_type
    if len(files)==0:files=None
    if len(types)!=0:values["__types__"]=types
    return {"values":values, "files":files}


def savefiles(indict,dirpath):
    if indict["files"] is not None:
        for key,value in indict["files"].items():
            if isinstance(value,dict):
                tmp = {"values":indict["values"][key],"files":value}
                savefiles(tmp,dirpath)
            else:
                fn = indict["values"][key].replace(":_ndarray_:","")
                numpy.save(dirpath/fn,value)

# def _savefiles(indict,dirpath):
#     for key,value in indict["files"].items():
#         if isinstance(indict["values"][key],(dict)):
#             _savefiles(indict["files"],dirpath)
#         else:
#             fn = indict["values"][key].replace(":_ndarray_:","")
#             numpy.save(dirpath/fn,value)

# def decodeList(inlist):
#     files = {}
#     for key, value in enumerate(inlist):
#         if type(value) is str:
#             if value[:10] == "_ndarray_:":
#                 files[key] = value[10:]
#             elif value[:8] == "_bytes_:":
#                 inlist[key] = value.encode()
#         elif type(value) is dict:
#             files[key] = decodeDict(value)
#         elif type(value) is list:
#             files[key] = decodeList(value)
#     return {"values":inlist, "files":files}

# def decodeDict(indict):
#     files = {}
#     for key,value in indict.items():
#         if type(value) is str:
#             if value[:10] == "_ndarray_:":
#                 files[key] = value[10:]
#             elif value[:8] == "_bytes_:":
#                 indict[key] = value.encode()
#         elif type(value) is dict:
#             files[key] = decodeDict(value)
#         elif type(value) is list:
#             files[key] = decodeList(value)
#     return {"values":indict, "files":files}


def decodeDict(indict):
    if "__types__" in indict:
        for key,value in indict["__types__"].items():
            if value == "bytes":
                indict[key] = indict[key].encode()
            elif isinstance(indict[key],(list,tuple)):
                indict[key] = numpy.array(indict[key],dtype=numpy.dtype(value))
            else:
                indict[key] = numpy.array((indict[key],),dtype=numpy.dtype(value))[0]
        del indict["__types__"]
    for key,value in indict.items():
        if isinstance(value,dict):
            indict[key] = decodeDict(value)
    if "__list__" in indict:
        del indict["__list__"]
        return list(indict.values())
    if "__tuple__" in indict:
        del indict["__tuple__"]
        return tuple(indict.values())
    return indict

def _loadfiles(indict,dirpath):
    for key,fn in indict.items():
        if type(fn) is str:
            if ":_ndarray_:" in fn:
                fn = fn.replace(":_ndarray_:","")
                indict[key] = numpy.load(dirpath/fn)
        elif isinstance(fn, dict):
            _loadfiles(fn,dirpath)
        elif isinstance(fn,(list,tuple)):
            _loadfiles_list(fn,dirpath)

def _loadfiles_list(inlist,dirpath):
    for i,fn in enumerate(inlist):
        if type(fn) is str:
            if ":_ndarray_:" in fn:
                fn = fn.replace(":_ndarray_:","")
                inlist[i] = numpy.load(dirpath/fn)
        elif isinstance(fn, dict):
            _loadfiles(fn,dirpath)
        elif isinstance(fn,(list,tuple)):
            _loadfiles_list(fn,dirpath)

def saveChainMap(input,path):
    N = len(input.maps)
    name = saveDict(input.maps[N-1],path)
    for i in range(N-2,-1,-1):
        saveDictDiff(input.maps[i],name)
    return name

def saveDict(input,path):
    now = datetime.now().isoformat("_")
    dirpath = Path(path).with_suffix(".dict")
    fname = dirpath.stem
    filepath = dirpath/(fname+f".{SERIALIZER}")
    if not dirpath.exists():
        dirpath.mkdir(parents=True,mode=0o2777)
    output = encodeDict(input,fname)
    print(output["values"])
    print(output["files"])
    output["values"]["__save_timestamp__"] = now
    savefiles(output,dirpath)
    with filepath.open("x") as jf:
        if SERIALIZER in ("json",):
            json.dump(output["values"], jf, indent=4)
        elif SERIALIZER in ("toml",):
            toml.dump(output["values"], jf)
    return str(dirpath)

def saveDictDiff(input,path,compare=False):
    now = datetime.now().isoformat("_")
    dirpath = Path(path)
    if not dirpath.exists():
        raise FileNotFoundError("initial dict doesn't exist")
    cnt = 0
    fname = dirpath.stem + f"-diff{cnt:0>3}"
    filepath = dirpath/(fname+f".{SERIALIZER}")
    while filepath.exists():
        cnt+=1
        fname = dirpath.stem + f"-diff{cnt:0>3}"
        filepath = dirpath/(fname+f".{SERIALIZER}")
    if compare:
        current = loadDictDiffs(path)
        diff = dictDiff(current,input)
        output = encodeDict(diff,fname)
    else:
        output = encodeDict(input,fname)
    output["values"][f"__save_timestamp{cnt:0>3}__"] = now
    savefiles(output,dirpath)
    with filepath.open("x") as jf:
        if SERIALIZER in ("json",):
            json.dump(output["values"], jf, indent=4)
        elif SERIALIZER in ("toml",):
            toml.dump(output["values"], jf)
    return str(dirpath)

def loadDictDiffs(path):
    dirpath = Path(path)
    fname = dirpath.stem
    cnt = 0
    filepath = dirpath/(fname+f"-diff{cnt:0>3}"+f".{SERIALIZER}")
    out = ChainMap()
    while 1:
        if filepath.exists():
            with filepath.open("r") as jf:
                if SERIALIZER in ("json",):
                    input = json.load(jf)
                elif SERIALIZER in ("toml",):
                    input = toml.load(jf)
            indict = decodeDict(input)
            _loadfiles(indict,dirpath)
            out.maps.insert(1,indict)
            cnt+=1
            filepath = dirpath/(fname+f"-diff{cnt:0>3}"+f".{SERIALIZER}")
        else:
            break
    if cnt == 0:
        return None
    return out

def loadDict(path):
    dirpath = Path(path)
    fname = dirpath.stem
    filepath = dirpath/(fname+f".{SERIALIZER}")
    with filepath.open("r") as jf:
        if SERIALIZER in ("json",):
            input = json.load(jf)
        elif SERIALIZER in ("toml",):
            input = toml.load(jf)
    _loadfiles(input,dirpath)
    indict = decodeDict(input)
    out = loadDictDiffs(path)
    if out is not None:
        out.maps.append(indict)
        return out
    return indict
    
def saveSimpleDict(indict,path):
    filepath = Path(path).with_suffix(f".{SERIALIZER}")
    if not filepath.parent.exists():
        filepath.parent.mkdir(parents=True,mode=0o2777)
    with filepath.open("w") as jf:
        if SERIALIZER in ("json",):
            json.dump(indict, jf, indent=4)
        elif SERIALIZER in ("toml",):
            toml.dump(indict, jf)
    return str(filepath)

def loadSimpleDict(filepath):
    filepath = Path(filepath)
    with filepath.open("r") as jf:
        if SERIALIZER in ("json",):
            indict = json.load(jf)
        elif SERIALIZER in ("toml",):
            indict = toml.load(jf)
    return indict

def nestedupdate(d:dict, u:dict):
    for k, v in u.items():
        if isinstance(v, dict) and isinstance(d[k], dict):
            nestedupdate(d[k], v)
        else:
            d[k] = v
    return d

def appendSimpleDict(indict, path):
    current = loadSimpleDict(path)
    nestedupdate(current, indict)
    return saveSimpleDict(current,path)

def listDiff(A:Union[list,tuple], B:Union[list,tuple], astuple=False) -> Union[list,tuple]:
    Ad = {str(i):v for i,v in enumerate(A)}
    Bd = {str(i):v for i,v in enumerate(B)}
    Cd = dictDiff(Ad,Bd)
    if astuple:
        return tuple(Cd.values()) if Cd is not None else None
    else:
        return list(Cd.values()) if Cd is not None else None

def dictDiff(A:dict, B:dict) -> dict:
    C = {}
    for key,value in B.items():
        if key in A:
            if isinstance(value,dict):
                tmp = dictDiff(A[key],value)
                if tmp is not None:
                    C[key] = tmp
            elif isinstance(value,list):
                tmp = listDiff(A[key],value)
                if tmp is not None:
                    C[key] = tmp
            elif isinstance(value,tuple):
                tmp = listDiff(A[key],value,astuple=True)
                if tmp is not None:
                    C[key] = tmp
            else:
                truth = (value == A[key])
                if isinstance(truth,numpy.ndarray):
                    if not truth.all():
                        C[key] = value
                else:
                    if not truth:
                        C[key] = value
        else:
            C[key] = value
    return C

# def dictDiff(A,B):
#     C = {k:v for k,v in B.items() if k not in A or (all(v!=A[k]) if isinstance(v,(numpy.ndarray)) else v!=A[k])}
#     return C

import struct
def parseStatusBuf(data):
    if isinstance(data, list) and len(data)==3:
        data = data[0]
    if not isinstance(data,numpy.ndarray):
        raise ValueError("input must be either a statusBuf or its data entry")
    pos = 0
    statusDict = {}
    data_types = [('i',4),('d',8)]
    data_order = [0,0,0,1,0,1,0,0,0]
    keys = ["nthreads","iter","iters","maxtime","maxiter","frametime","running","FS","mirrorSend"]
    for i in range(len(data_order)):
        this_type = data_types[data_order[i]]
        statusDict[keys[i]]=struct.unpack(this_type[0],data[pos:pos+this_type[1]])[0]
        pos += this_type[1]

    statusString =  "{0}+1 threads\nIteration: {1}/{2}\n".format(statusDict["nthreads"],statusDict["iter"],statusDict["iters"])
    statusString += "Max time {0}s at iter {1}\n".format(statusDict["maxtime"],statusDict["maxiter"])
    statusString += "Frame time {0}s ({1}Hz)\n{2}\n".format(statusDict["frametime"],1/statusDict["frametime"] if statusDict["frametime"]!=0 else 0,("Running..." if statusDict["running"]==0 else "Paused..."))
    statusString += "FS: {0}\n{1}".format(statusDict["FS"],("Sending to mirror" if statusDict["mirrorSend"]==1 else "Not sending to mirror"))

    framestr =[("\nNo cam:","\nCam: "),("\nNo calibration:","\nCalibration: "),("\nNo centroider:","\nCentroider: "),("\nNo reconstructor:","\nReconstructor: "),("\nNo figure:","\nFigure: "),("\nNo buffer:","\nBuffer: "),("\nNo mirror:","\nMirror: ")]
    keys = ["cam","cal","cent","recon","fig","buff","mirr"]
    framenos = [[],[],[],[],[],[],[]]
    for i in range(7):
        framenos[i].append(struct.unpack('i',data[pos:pos+4])[0])
        pos+=4
        statusString += framestr[i][int(framenos[i][0]>0)]
        for j in range(abs(framenos[i][0])):
            framenos[i].append(struct.unpack('I',data[pos:pos+4])[0])
            pos+=4
            statusString += str(framenos[i][j+1])
        statusDict[keys[i]] = framenos[i]

    statusDict["clipped"] = struct.unpack('i',data[pos:pos+4])[0]
    statusString += "\nClipped: {0}".format(statusDict["clipped"])
    statusDict["tostring"] = statusString
    return statusDict

def statusBuf_tostring(data):
    return parseStatusBuf(data)["tostring"]

def make_cog_centIndexArray(npxlx, npxly, subapLocation):
    """Make a centIndexArray which will have the same result as a CoG."""
    nsub = subapLocation.size//6
    print(f"nsub = {nsub}")
    subapLocation.shape = nsub,6
    centIndexArray = numpy.zeros((npxly,npxlx,4),numpy.float32)
    centIndexArray[:,:,2:] = 1 # both sums are with unity scaling
    for i in range(nsub):
        sl = subapLocation[i]
        ny = (sl[1]-sl[0])//sl[2]
        nx = (sl[4]-sl[3])//sl[5]
        if ny*nx>0:
            centIndexArray[sl[0]:sl[1]:sl[2],sl[3]:sl[4]:sl[5],0] = numpy.arange(ny)[:,None]-ny/2.+0.5
            centIndexArray[sl[0]:sl[1]:sl[2],sl[3]:sl[4]:sl[5],1] = numpy.arange(nx)-nx/2.+0.5
    return centIndexArray

def shift_pyr_pupils(shift,subapLocation,stretch=(0,0)):
    nsub = subapLocation.size//6
    subapLocation.shape = nsub,6
    for i in range(nsub):
        subapLocation[:,0:2] += shift[0]
        subapLocation[:,1:3] += stretch[0]
        subapLocation[:,3:5] += shift[1]
        subapLocation[:,4:6] += stretch[1]
    return subapLocation

def generatePyrParams(nsub,npxlx,npxly,nacts,nthreads,xoff,yoff,xsep,ysep):
    nsubaps = nsub*nsub
    subapFlag = numpy.zeros((nsubaps,),"i")
    individualSubapFlag = tel.Pupil(nsub,nsub/2.,0,nsub).subflag.astype("i")
    tmp = subapFlag[:]
    tmp.shape = nsub,nsub
    tmp[:] = individualSubapFlag
    ncents = subapFlag.sum()*2
    npxls = (npxly*npxlx).sum()

    subapLocation = numpy.zeros((nsubaps,6),"i")

    # now set up a default subap location array...
    #this defines the location of the subapertures.
    # xoff = [15] # windowed
    # xoff = 12 # full frame
    # yoff = [15] # windowed
    # yoff = 15 # full frame
    # subx=(npxlx-xoff*2)/nsubx#[10]*ncam#(npxlx-48)/nsubx
    subx = npxlx//2#npxlx//2#npxl
    # suby=(npxly-yoff*2)/nsuby#[10]*ncam#(npxly-8)/nsuby
    suby = npxly//2#npxly//2#npxl

    # sepx = 194 # windowed
    # sepy = 100 # windowed
    sepx = xsep#180 # full frame
    sepy = ysep#175 # full frame

    for i in range(nsub):
        for j in range(nsub):
            indx = i*nsub+j
            # subapLocation[indx] = (yoff[k]+i*suby[k],yoff[k]+i*suby[k]+suby[k],1,xoff[k]+j*subx[k],xoff[k]+j*subx[k]+subx[k],1)
            subapLocation[indx]=(yoff+i,yoff+i+sepy+1,sepy,xoff+j,xoff+j+sepx+1,sepx)
    print(subapLocation)

    pxlCnt = numpy.zeros((nsubaps,),"i")
    subapAllocation=numpy.zeros((nsubaps,),"i")-1
    # set up the pxlCnt array - number of pixels to wait until each subap is ready.  Here assume identical for each camera.
    for i in range(nsub):
        for j in range(nsub):
            indx=i*nsub+j
            n=(subapLocation[indx,1]-1)*npxlx+subapLocation[indx,4]
            pxlCnt[indx]=n
            subapAllocation[i*nsub+j]=i%nthreads
    pxlCnt[-3] = npxlx*npxly

    centIndexSize = 2  # 1<=(value)<=4
    centIndexArray = numpy.zeros((npxls,centIndexSize),numpy.float32)

    cia = centIndexArray[:]
    cia.shape = npxly,npxlx,centIndexSize
    cia[:npxly//2,:,0]=-1#lower
    cia[npxly//2:,:,0]=1#upper
    cia[:,:npxlx//2,1]=-1#left
    cia[:,npxlx//2:,1]=1#right
        # cia[:,:,2:] = 1

    rmx=numpy.random.random((nacts,ncents)).astype("f")
    subapAllocation = None
    return {
        "nsub":nsub*nsub,
        "nsubx":nsub,
        "nsuby":nsub,
        "subapFlag":subapFlag,
        "subapLocation":subapLocation,
        "pxlCnt":pxlCnt,
        "subapAllocation":subapAllocation,
        "centIndexArray":centIndexArray,
        "rmx":rmx
        }

def generatePyrParams(params,cam,diam,xoff,yoff,xsep,ysep):
    param_names = ["nsubx","npxlx","npxly","nacts","ncamThreads","subapFlag","subapLocation","pxlCnt","subapAllocation","centIndexArray","rmx"]
    assert set(param_names) <= set(params.keys())
    params["nsubx"][cam] = diam
    nsubaps = params["nsubx"]*params["nsubx"]
    subapFlag = numpy.zeros((nsubaps,),"i")
    individualSubapFlag = tel.Pupil(nsub,nsub/2.,0,nsub).subflag.astype("i")
    tmp = subapFlag[:]
    tmp.shape = nsub,nsub
    tmp[:] = individualSubapFlag
    ncents = subapFlag.sum()*2
    npxls = (npxly*npxlx).sum()

    subapLocation = numpy.zeros((nsubaps,6),"i")

    # now set up a default subap location array...
    #this defines the location of the subapertures.
    # xoff = [15] # windowed
    # xoff = 12 # full frame
    # yoff = [15] # windowed
    # yoff = 15 # full frame
    # subx=(npxlx-xoff*2)/nsubx#[10]*ncam#(npxlx-48)/nsubx
    subx = npxlx//2#npxlx//2#npxl
    # suby=(npxly-yoff*2)/nsuby#[10]*ncam#(npxly-8)/nsuby
    suby = npxly//2#npxly//2#npxl

    # sepx = 194 # windowed
    # sepy = 100 # windowed
    sepx = xsep#180 # full frame
    sepy = ysep#175 # full frame

    for i in range(nsub):
        for j in range(nsub):
            indx = i*nsub+j
            # subapLocation[indx] = (yoff[k]+i*suby[k],yoff[k]+i*suby[k]+suby[k],1,xoff[k]+j*subx[k],xoff[k]+j*subx[k]+subx[k],1)
            subapLocation[indx]=(yoff+i,yoff+i+sepy+1,sepy,xoff+j,xoff+j+sepx+1,sepx)
    print(subapLocation)

    pxlCnt = numpy.zeros((nsubaps,),"i")
    subapAllocation=numpy.zeros((nsubaps,),"i")-1
    # set up the pxlCnt array - number of pixels to wait until each subap is ready.  Here assume identical for each camera.
    for i in range(nsub):
        for j in range(nsub):
            indx=i*nsub+j
            n=(subapLocation[indx,1]-1)*npxlx+subapLocation[indx,4]
            pxlCnt[indx]=n
            subapAllocation[i*nsub+j]=i%nthreads
    pxlCnt[-3] = npxlx*npxly

    centIndexSize = 2  # 1<=(value)<=4
    centIndexArray = numpy.zeros((npxls,centIndexSize),numpy.float32)

    cia = centIndexArray[:]
    cia.shape = npxly,npxlx,centIndexSize
    cia[:npxly//2,:,0]=-1#lower
    cia[npxly//2:,:,0]=1#upper
    cia[:,:npxlx//2,1]=-1#left
    cia[:,npxlx//2:,1]=1#right
        # cia[:,:,2:] = 1

    rmx=numpy.random.random((nacts,ncents)).astype("f")
    subapAllocation = None
    return {
        "nsub":nsub*nsub,
        "nsubx":nsub,
        "nsuby":nsub,
        "subapFlag":subapFlag,
        "subapLocation":subapLocation,
        "pxlCnt":pxlCnt,
        "subapAllocation":subapAllocation,
        "centIndexArray":centIndexArray,
        "rmx":rmx
        }

def import_from(file_path: Path):
    if not isinstance(file_path, Path):
        file_path = Path(file_path)
    if str(file_path) in MANUAL_MODULES:
        return MANUAL_MODULES[str(file_path)]
    spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)
    # print("path",file_path)
    MANUAL_MODULES[str(file_path)] = foo
    return foo

def var_from_file(var_name, file_path: Path):
    if not isinstance(file_path, Path):
        file_path = Path(file_path).expanduser().resolve()
    return var_from_text(var_name, file_path.read_text(), file_path)

def var_from_text(var_name, code: str, file_path=None):
    values = {"__file__":file_path}
    exec(code,values,values)
    return values[var_name]

def import_modules(dir_name):
    """Import all modules inside a directory."""
    direc = Path(dir_name)
    for f in direc.iterdir():
        if (not f.stem.startswith('_') and not f.stem.startswith('.') and f.suffix == '.py'):
            # module = importlib.import_module(f'{dir_name}.{f.stem}')
            spec = importlib.util.spec_from_file_location(f.stem, f)
            foo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(foo)


def make_data_dirs(name:str, prefixes:list) -> tuple[Path,dict,str]:
    from lark import config

    """This assumes that if an RTC is restarted with the same name during the same minute,
    that the current data should overwritten... i.e. the timestamp for directories only has minute resolution
    This is probably ok as an RTC that runs for less than a minute is not that usefull...."""

    dd = Path(config["DATA_DIR"])
    dd = Path("/home/canapyrtc/temp/DATA_DIR")

    if not dd.exists():
        dd.mkdir(parents=True,mode=0o2777)
    else:
        os.chmod(dd,0o2775)

    now = datetime.now()
    datef = f"{now.year}{now.month:0>2}{now.day:0>2}"
    tstamp = datef+f"_{now.hour:0>2}{now.minute:0>2}"

    namedir = dd/datef/f"{name}_{tstamp}"
    if namedir.exists():
        print("WARNING: data directories exist, overwritting")
    else:
        namedir.mkdir(parents=True)

    if (dd/name).exists():
        os.remove(dd/name)
    os.symlink(namedir,dd/name,target_is_directory=True)

    prefix_dirs = {}
    for prefix in prefixes:
        prefix_dirs[prefix] = dd/datef/f"{prefix}_{tstamp}"
        if not prefix_dirs[prefix].exists():
            prefix_dirs[prefix].mkdir(parents=True,mode=0o2777)
        if (dd/prefix).exists():
            os.remove(dd/prefix)
        os.symlink(prefix_dirs[prefix],dd/prefix,target_is_directory=True)

    return namedir, prefix_dirs, tstamp

if __name__ == "__main__":
    save = 0
    if save:
        namedir, prefixdirs, tstamp = make_data_dirs("LabPySim",["LgsWF","PyScoring"])
        print(namedir,prefixdirs,tstamp)
        print(repr(namedir),str(namedir))

        dd = Path("/home/canapyrtc/temp/DATA_DIR")
        (dd/"LgsWF"/"config.txt").touch()
        # y = loadDict("/tmp/params/canapy-20220125.params/182426-init.dict")

        cf = "~/git/canapy-rtc/canapyconfig/darc/configPyScoring.py"

        params = var_from_file("control",cf)

        params["this_bytes"] = b"HEEELLLLOOOOO THEERRRREEE"

        print(params)

        saveDict(params,dd/"PyScoring"/"params")

        sys.exit()

    #

    testload = 0

    if testload:

        y = loadDict("/home/canapyrtc/temp/DATA_DIR/PyScoring/params.dict")

        # sys.exit()

        print(y["this_bytes"])


        name = "/tmp/saving/mydict"

        if os.path.exists(name+".dict"):
            for fn in os.listdir(name+".dict"):
                os.remove(os.path.join(name+".dict",fn))
            os.rmdir(name+".dict")

        name = saveDict(y,name)

        saveDictDiff(y,name)
        saveDictDiff(y,name)
        y["delay"] = 42562
        saveDictDiff(y,name,compare=True)
        saveDictDiff(y,name)
        z = {"figureOpen":1}
        saveDictDiff(z,name)

        z = loadDict(name)

        print(y==z)

        print(dictDiff(y,z))

        print(len(z.maps))

        print(z["figureOpen"])
        print(z["delay"])

        name = "/tmp/saving/mychain"
        if os.path.exists(name+".dict"):
            for fn in os.listdir(name+".dict"):
                os.remove(os.path.join(name+".dict",fn))
            os.rmdir(name+".dict")

        name =  saveChainMap(z,name)

        z = loadDict(name)

        print(dict(z).keys())
        # print(z.keys())

        sys.exit()

    testnested = 0

    if testnested:
        x = {
            "list1":[1,2,3,(numpy.ones(1,dtype=int),)],
            "list2":[1,2,3,(numpy.ones(100,dtype=int),)],
            "x1":5,
            "y1":7,
            "file1":numpy.ones((5,5)),
            "file3":numpy.ones((7,7))+4,
            "dict1":{
                "x2":4,
                "y2":6,
                "tuple":([1,2],[3,4]),
                "file2":numpy.arange(44),
                "dict2":{
                    "x3":4,
                    "y3":6,
                    "file3":numpy.arange(80),
                    "list2":[1,2,numpy.zeros(4),{"hi":1,"ho":2}]
                    }
                }
            }

        # v,f = encodeDict(x)
        # print(v,f)

        name = "/tmp/saving/mybasicdict"

        if os.path.exists(name+".dict"):
            for fn in os.listdir(name+".dict"):
                os.remove(os.path.join(name+".dict",fn))
            os.rmdir(name+".dict")

        name = saveDict(x,name)

        x1 = {"new":3}
        saveDictDiff(x1,name)
        x2 = {"new":4,"new1":5,"x":1}
        saveDictDiff(x2,name)
        x2 = {"new":{"arr":[numpy.zeros(30)]}}
        saveDictDiff(x2,name)

        y = loadDict(name)

        print(y)
        # print(dictDiff(x,y))

        # y.pop("__save_timestamp__")
        # print(x)
        # print(y)
        # print(dict(y))
        sys.exit()
        
    x = {"prefix":{"1":"hello"}}
    
    name = "/tmp/saving/mysimpledict"
    
    name = saveSimpleDict(x,name)
    
    y = {"prefix":{"2":"hi"},"file1":"this"}
    
    appendSimpleDict(y,name)
