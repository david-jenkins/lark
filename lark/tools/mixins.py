

# WORK IN PROGRESS, MIGHT NEVER BE USED

from lark.parambuf import ParamBuf, no_default
from lark.circbuf import TelemetrySystem

class Parambuf_TelemetrySystem:
    def __init__(self):
        self.ParamBuf:ParamBuf = None
        self.TelemetrySystem:TelemetrySystem = None
        
    def initParamBuf(self, prefix:str, numa:int=-1):
        self.ParamBuf = ParamBuf(prefix, numa)
        
    def initTelemetrySystem(self, prefix:str="", connect:int=1):
        self.TelemetrySystem = TelemetrySystem(prefix, connect)

    @property
    def prefix(self):
        return self.ParamBuf.prefix
        
    def __getitem__(self, key):
        return self.ParamBuf.__getitem__(key)

    def __setitem__(self,key,value):
        return self.ParamBuf.__setitem__(key,value)
        
    def __iter__(self):
        yield from self.ParamBuf.__iter__()
            
    def keys(self):
        return self.ParamBuf.keys()
            
    def items(self):
        yield from self.ParamBuf.items()
            
    def update(self,values,switch=0,check=1):
        return self.ParamBuf.update(values,switch,check)

    def set(self,name,value,switch=1,active=0,check=1,_set_dependencies=True):
        return self.ParamBuf.set(name,value,switch,active,check,_set_dependencies)

    def checkWithInactive(self,values):
        return self.ParamBuf.checkWithInactive(values)

    def setMany(self,values,switch=0,check=0):
        return self.ParamBuf.setMany(values, switch, check)


    def get(self,name,default=no_default,*,inactive=0):
        return self.ParamBuf.get(name,default,inactive=inactive)

    def getMany(self,names,inactive=0):
        return self.ParamBuf.getMany(names)
        
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
        self.savedir = Path(root_dir)/self.datestamp/(self.timestamp+"-"+self.prefix)

    def saveParamBuf(self):
        now = get_datetime_stamp()
        if not self.savedonce:
            self.savedir.mkdir(parents=True, exist_ok=True)
            this_path = self.savedir/f"{self.prefix}_{self.datestamp}T{self.timestamp}"
            self.savedir = saveDict(self._getN(self._getnames()), this_path)
            self.savedonce = True
        else:
            print(self.changes)
            if self.changes != {}:
                saveDictDiff(self.changes, self.savedir)
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