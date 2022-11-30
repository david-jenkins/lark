#!/usr/bin/env python3

'''
Prototype of param buf access for darc.
Uses a new C based interface to the underlying memory buffer.
Some parameters are defined as a @property with it's own setter which
implements the logic from darc's Check.py
The class can be used by itself or inherited.
It needs a prefix on initialisation and will find the corresponding buffers
Options will be added if the buffer doesn't exist.

This will (eventually) become the sole way to set paramters in DARC.
'''

from logging import getLogger
import time
import rpyc.core.netref
import numpy
import numa
# import darc
import sys
from .cbuffer import cParamBuf, BufferError
import code
from lark import get_lark_config
from lark.utils import dictDiff, saveDict, saveDictDiff
import os
from pathlib import Path
from . import check as Checker
from .interface import copydict
from lark.utils import get_datetime_stamp

PARAM_DIR = get_lark_config().DATA_DIR

no_default = "1h3b4hrb1erbjkerbt"

class ParamBuf(cParamBuf):
    def __init__(self, prefix, numa=-1, datetime=None):
        self.param_init(prefix,numa,datetime)

    def param_init(self, prefix, numa=-1, datetime=None):
        assert isinstance(prefix,str)
        assert isinstance(numa,int)
        self.logger = getLogger(f"{prefix}.ParamBuf")
        self.logger.info(f"Opening cParamBuf for {prefix}")
        try:
            cParamBuf.__init__(self, prefix, numa)
        except BufferError as e:
            self.logger.info(f"Unable to open parambuf for {prefix}")
            self.bufferopen = 0
            raise BufferError(f"Unable to open parambuf for {prefix}") from e
        else:
            self.bufferopen = 1
            self.logger.info(f"Opened cParamBuf for {prefix}")
        self.changes = {}
        self.queued = {}
        if datetime==None: datetime = get_datetime_stamp()
        self.datestamp, self.timestamp = datetime.split("T")
        self.savedonce = False
        self.setParamSaveDir(PARAM_DIR/"darc")
        self.numaNodes = 0
        self.numaBuffers = {}
        self.paramcbs = {}
        self.now = None

    @property
    def prefix(self):
        return self._buf_prefix
        
    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self,key,value):
        value = Checker.valid(key,value,self)
        return self.set(key,value,switch=1,check=0)
        
    def __iter__(self):
        keys = self.getLabels()
        for key in keys:
            yield key
            
    def keys(self):
        try:
            return self._getnames()
        except Exception as e:
            self.logger.warn(f"Error in ParamBuf getLabels: {repr(e)}")
            raise e
            
    def items(self):
        keys = self.getLabels()
        for key in keys:
            yield key, self.get(key)
            
    def update(self,values,switch=0,check=1):
        self.setMany(values,switch,check)

    def set(self,name,value,switch=1,active=0,check=1,_set_dependencies=True):
        if check:
            try:
                value = Checker.valid(name,value,self)
            except Exception as e:
                self.logger.warn(repr(e))
                raise e
        try:
            self.logger.debug(f"setting {name} to {value} of type {type(value)}")
            retval = self._set(name,value,active)
        except TypeError as e:
            raise TypeError("Expects: set(name:str,value:obj | switch=1:int,active=0:int") from e
        else:
            self.queued[name]=value
            if _set_dependencies:
                Checker.setDependencies(name,Inactive(self))
            if switch:
                self.switchBuffer()
            return retval

    def checkWithInactive(self,values):
        values = copydict(values)
        inactive = dict(Inactive(self))
        for name,value in values.items():
            try:
                inactive[name] = Checker.valid(name,value,inactive)
            except Exception as e:
                self.logger.warn(repr(e))
                raise e
        for name,value in values.items():
            try:
                Checker.setDependencies(name,inactive)
            except Exception as e:
                self.logger.warn(repr(e))
                raise e
        try:
            Checker.checkParams(inactive)
        except Exception as e:
            self.logger.warn(repr(e))
            raise e
        diff = dictDiff(dict(Inactive(self)),inactive)
        return copydict(diff)

    def setMany(self,values,switch=0,check=0):
        self.logger.debug(f"setMany got : {values}")
        self.logger.debug(f"of type {type(values)}")
        values = copydict(values) # this will turn a remote dict into a local dict
        if check:
            try:
                values = self.checkWithInactive(values)
            except Exception as e:
                raise e
        try:
            failed = self._setN(values)
        except TypeError as e:
            raise TypeError(f"Expects: set(values:dict) got set({type(values)}") from e
        else:
            self.queued.update(values)
            if switch:
                self.switchBuffer()
            return copydict(failed), copydict(values)

    def _setManyToBuf(self,values,buffer):
        try:
            retval = self._setNToBuf(values,buffer)
        except TypeError as e:
            raise TypeError("Expects: set(values:dict | switch=1:int") from e
        else:
            return retval

    def get(self,name,default=no_default,*,inactive=0):
        """Getter for parambuf entries

        Args:
            name (str): name of the parameter to set
            inactive (int, optional): Set to 1 to get from the inactive buffer. Defaults to 0.

        Raises:
            TypeError: If the underlying _get returns a TyperError

        Returns:
            object: The parameter request, either int, float, str or numpy.ndarray
        """
        try:
            return self._get(name,inactive)
        except TypeError as e:
            raise TypeError("Expects: get(name:str | inactive=0:int") from e
        except KeyError as e:
            if default==no_default:
                raise e
            else:
                return default

    def getMany(self,names,inactive=0):
        # self.logger.debug(names)
        # self.logger.debug(type(names))
        self.logger.debug(f"getting many = {names}")
        try:
            return copydict(self._getN(names,inactive))
        except TypeError as e:
            raise TypeError("Expects: get(name:str | inactive=0:int") from e
        
    def getAll(self):
        # return self.getMany(self.getLabels())
        return copydict(self)

    def getAll2(self):
        return self.getMany(self.getLabels())

    def getChanges(self,reset=False):
        if reset:
            chg = self.changes
            self.changes = {}
            return chg
        return self.changes
        
    def getLatestChanges(self):
        if self.now:
            return self.changes[self.now]

    def switchBuffer(self,wait=0,init=False):
        self.now = get_datetime_stamp(microseconds=True)
        frameno = cParamBuf.switchBuffer(self, wait)
        index = f"{self.now}-{frameno}"
        self.changes[index] = self.queued.copy()
        self.changes[index]["switchTimePy"] = self.now
        self.changes[index]["switchTime"] = self.get("switchTime",default=None)
        self.changes[index]["frameno"] = self.get("frameno",default=None)
        self.queued.clear()
        todel = []
        for pid,callback in self.paramcbs.items():
            try:
                callback(self.prefix,self.changes[self.now])
            except Exception as e:
                self.logger.warn(repr(e))
                todel.append(pid)
        for pid in todel:
            del self.paramcbs[pid]
        if init:
            self.changes.clear()
        return frameno

    def openNuma(self):
        self.numaNodes = numa.get_max_node()+1
        self.logger.debug(f"self.numaNodes: {self.numaNodes}")
        for i in range(self.numaNodes):
            self.numaBuffers[f"numa{i}"] = ParamBuf(self.prefix,i)

    def setNuma(self,values,active=0):
        index = self._inactive
        if active==1:
            index = self._active
        for key,value in values.items():
            self.numaBuffers[key]._setManyToBuf(value,index)

    def getLabels(self):
        return self.keys()
        
    def setParamSaveDir(self, root_dir):
        self.paramsavedir = Path(root_dir)/self.datestamp/(self.timestamp+"-"+self.prefix)
        if not self.paramsavedir.is_absolute():
            self.paramsavedir = get_lark_config().LARK_DIR/"lost"/self.paramsavedir

    def saveParamBuf(self):
        now = get_datetime_stamp()
        if not self.savedonce:
            self.paramsavedir.mkdir(parents=True, exist_ok=True)
            this_path = self.paramsavedir/f"{self.prefix}_{self.datestamp}T{self.timestamp}"
            self.paramsavedir = saveDict(self._getN(self._getnames()), this_path)
            self.savedonce = True
            self.saveParamBuf()
        else:
            print(self.changes)
            if self.changes != {}:
                saveDictDiff(self.changes, self.paramsavedir)
                self.changes.clear()

    def addParamCallback(self, paramcb):
        pid = id(paramcb)
        # paramcb = rpyc.async_(paramcb)
        self.paramcbs[pid] = paramcb
        return pid

    def removeParamCallback(self,pid):
        try:
            del self.paramcbs[pid]
        except Exception as e:
            self.logger.warn(f"cb with id {str(pid)} is not registered")
        

class Active:
    def __init__(self,parambuf:ParamBuf):
        self.parambuf = parambuf
        self.check=1
        
    def __getitem__(self,key):
        return self.get(key)

    def __setitem__(self,key,value):
        return self.set(key,value)

    def get(self, name, inactive=0):
        return self.parambuf.get(name, inactive=0)

    def set(self,name,value,switch=0,active=1,check=1,_set_dependencies=False):
        return self.parambuf.set(name, value, switch=0, active=1, check=self.check, _set_dependencies=False)
        
    def getMany(self, names, inactive=0):
        return self.parambuf.getMany(names, inactive=0)
        
    def setNuma(self, values, active=1):
        return self.parambuf.setNuma(values, active=1)

class Inactive:
    def __init__(self,parambuf:ParamBuf):
        self.parambuf = parambuf
        self.check=0
        
    def keys(self):
        return self.parambuf.keys()

    def __getitem__(self,key):
        return self.get(key)

    def __setitem__(self,key,value):
        return self.set(key,value)
        
    def __iter__(self):
        keys = self.parambuf.getLabels()
        for key in keys:
            yield key,self.get(key)
            
    def update(self,items):
        for key,value in items.items():
            self.set(key, value)
    
    def items(self):
        return self

    def get(self, name, default=no_default, *, inactive=1):
        return self.parambuf.get(name, default, inactive=1)

    def set(self,name,value,switch=0,active=0,check=0,_set_dependencies=False):
        return self.parambuf.set(name, value, switch=0, active=0, check=self.check, _set_dependencies=False)
        
    def getMany(self, names, inactive=1):
        return self.parambuf.getMany(names, inactive=1)
        
    def setNuma(self, values, active=0):
        return self.parambuf.setNuma(values, active=0)
        

if __name__ == "__main__":

    print("starting....")
    try:
        p = ParamBuf("canapy")
    except BufferError as e:
        print(e)
        sys.exit()

    # print(p.getMany(["delay","npxlx"],0))
    # p.switchBuffer()
    # print(sorted(p._getnames()))
    # print(p.getMany(p._getnames()))

    print(p.prefix)

    p.prefix = "hello"

    # p.save()
    sys.exit()
    params = {}
    # d = darc.Control("canapy")
    # labels = d.GetLabels()
    # print(labels)

    # for name in labels:
    #     print(f"{name}:  {p._get(name)}")
    #     params[name] = p._get(name)

    # code.interact(local=locals())
    # sys.exit()


    # p.get(5)

    # try:
    #     p.get("wrong")
    # except AttributeError as e:
    #     print(repr(e))
    # print(p.get("v0"))
    # print(p.get("aravisCmd0"))
    # print(p.get("creepTime"))
    # print(p.get("powerFactor"))
    # print(p.get("mirrorParams"))
    # print(p.get("subapAllocation"))

    # print(p._get("delay"))
    # p._set("delay",100)
    # print(p._get("delay"))

    # print(p._get("switchRequested"))
    # # p._switch()

    p._set("hello",234576)
    p._set("hellod",234576.345)
    p._set("hellos","72456.345")
    p._set("hellob",b"hellomybaby")
    p._set("helloa",numpy.arange(10).astype(numpy.int8))
    try:
        p._set("thisisastringthatstoolong",5)
    except BufferError as e:
        print(e)
    p._set("justlongenough4u",5)
    p._set("afterthelongone",8)
    p.switchBuffer()

    print(p._get("hellos"))
    print(p._get("hellos",1))

    # p.switchBuffer()
    # time.sleep(0.1)

    print(p["hellob"])
    print(p._get("helloa"))
    print(p._active)
    print(p._getnames())

    print(p.setMany({"x":2456,"y":24562},switch=1))
    print(p._getN(["x","y"]))
    print(p.setMany({"x":43,"y":78},switch=1))
    all = p._getN(p._getnames())
    x = p._getN(["x","y"])
    print(x)
    p.save()

    p.set("david",47)
    p.set("myarray",numpy.array([1,2,3,45]))
    p.save()
    # print("Switch active....")
    # p._active = 1
    # p._active = 0
    # time.sleep(1)
    # print(p._inactive)
    # print("Switch inactive....")
    # try:
    #     p._inactive = 3
    # except BufferError as e:
    #     print(repr(e))
    # p._inactive = 0

