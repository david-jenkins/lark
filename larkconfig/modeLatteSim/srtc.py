
"""This defines and registers functions for the SRTC systemd
"""
from types import SimpleNamespace
from lark.rpyclib.interface import BgServer
from pathlib import Path
from typing import Any, Union
from lark.utils import appendSimpleDict, make_data_dirs, saveDict, saveDictDiff, saveSimpleDict
import numpy
from lark import LarkConfig
from lark.services import BaseService, BasePlugin

class CanapySrtc(BaseService):
    PLUGINS = {}
    RESULTS = {}
    INITIALISED = {}
    def notify(self, *args):
        print(*args)

# @CanapySrtc.register_plugin("data_saver")
class DataSaver(BasePlugin):
    """
    For saving parameter buffers and command telemetry saving"""
    def Init(self):
        self.defaults = {
            "srtcname":"",
            "prefixes":[],
            "info":{},
        }
        self.arg_desc = {
            "strcname": "The name of the srtc",
            "prefixes": "The prefixes to be saved",
            "info": "A dict containing keys to be saved to the srtc info file"
        }
        self.params = None
        self.changes = {}
        self.telemfiles = []
        self.saved = {}
        self.first_run = True
        self.larks = None
        self.srtcinfofile = None
        
    def update_info(self, values:dict):
        self["info"].update(values)

    def Configure(self, srtcname: str = None, prefixes: list = None, info: dict = None):
        if info: self.update_info(info)
        info = None
        kwargs = {key:value for key,value in locals().items() if key in self.defaults and value is not None}
        return super().Configure(**kwargs)

    def Setup(self):
        if self["prefixes"]:
            self.larks = {prefix:LarkConfig(prefix).getlark(unique=True) for prefix in self["prefixes"]}
        if self.first_run and self.larks and self["srtcname"]:
            self.params = {prefix:lrk.getChanges(True) for prefix,lrk in self.larks.items()}
            self.srtcdir,self.prefixdirs,self.tstamp = make_data_dirs(self["srtcname"],self["prefixes"])
            self.srtcinfofile = saveSimpleDict({"name":self["srtcname"]},self.srtcdir/"info")
            print(self.srtcdir,self.prefixdirs,self.tstamp)
            for prefix,params in self.params.items():
                self.prefixdirs[prefix] = saveDict(params[list(params.keys())[1]],self.prefixdirs[prefix]/self.prefixdirs[prefix].name)
                self.saved[prefix] = []
            self.first_run = False

    def Acquire(self):
        self.changes = {prefix:lrk.getChanges() for prefix,lrk in self.larks.items()}

    def Execute(self):
        for prefix,changes in self.changes.items():
            saveDictDiff(changes,self.prefixdirs[prefix])
            self.changes = {}
        if self.telemfiles:
            self["info"]["Telemetry"] = {prefix:{} for prefix in self.larks}
            for fileinfo in self.telemfiles:
                self["info"]["Telemetry"][fileinfo["prefix"]][fileinfo["timestamp"]] = (fileinfo["hostname"],fileinfo["filepath"])
            self.telemfiles = {}
        if self["info"]:
            appendSimpleDict(self["info"],self.srtcinfofile)
            self["info"] = {}

    def Finalise(self):
        self.result = f"{self['srtcname']}, {self['prefixes']}", self.saved

    def stop(self):
        for lrk in self.larks.values():
            lrk.conn.close()
        super().stop()
        # save the params received from addParamCallback
        # save some info in the srtc dir
        # setup telemetry saving?

@CanapySrtc.register_plugin("data_saver_cb")
class CallbackDataSaver(DataSaver):
    """
    For saving parameter buffers and command telemetry saving
    gets changes using callbacks from switch buffer"""
    def Init(self):
        super().Init()
        self.bgsrvs = {}
        self.pids = {}
        self.tids = {}
        self.cbs_set = False
        self.begin_on_start = True
        
    def changes_callback(self,prefix:str,changes:dict):
        print(prefix,changes)
        self.changes[prefix] = changes
        
    def telemfile_callback(self, fileinfo):
        print("Got Telem File Info:")
        print(fileinfo)
        self.telemfiles.append(fileinfo)

    def bgsrv_starter(self,prefix,conn):
        self.bgsrvs[prefix] = BgServer(conn)

    def Setup(self):
        super().Setup()
        if not self.cbs_set:
            self.pids = {}
            self.tids = {}
            for prefix,lrk in self.larks.items():
                self.bgsrv_starter(prefix,lrk.conn)
                self.pids[prefix] = lrk.addParamCallback(self.changes_callback)
                self.tids[prefix] = lrk.addTelemFileCallback("ALL",self.telemfile_callback)
            self.cbs_set = True

    def Acquire(self):
        pass

    def stop(self):
        for prefix,bgsrv in self.bgsrvs.items():
            bgsrv.stop()
        for prefix,pid in self.pids.items():
            self.larks[prefix].removeParamCallback(pid)
        for prefix,tids in self.tids.items():
            for stream, tid in tids.items(): self.larks[prefix].removeTelemFileCallback(stream,tid)
        self.cbs_set = False
        super().stop()
        # save the params received from addParamCallback
        # save some info in the srtc dir
        # setup telemetry saving?

@CanapySrtc.register_plugin("telemetry_saver")
class TelemetrySaver(BasePlugin):
    """Manage saving telemetry"""
    def Init(self):
        self.defaults = {
            "prefixes": ["LgsWF","PyScoring"],
            "streams": ["rtcCentBuf","rtcMirrorBuf","rtcStatusBuf"]
        }
        self.arg_desc = {
            "prefixes": "The prefixes to save",
            "streams": "The telemetry streams to save"
        }

    def Configure(self, prefixes:list[str] = None, streams:list[str] = None):
        kwargs = {key:value for key,value in locals().items() if key in self.defaults and value is not None}
        return super().Configure(**kwargs)
        
    def Setup(self):
        pass


@CanapySrtc.register_plugin("pyr_center")
class CenterPyr(BasePlugin):
    """Find the center and radius of the pyramid quadrants
    """
    def Init(self):
        self.defaults = {
            "n_img": 10,
            "prefix": "LgsWF",
            "p1": 68,
            "p2": 95,
        }
        self.arg_desc = {
            "n_img": "The number of images to average over",
            "prefix": "The lark prefix to use"
        }


    def Configure(self,
            n_img: int = None,
            prefix: str = None,
            p1: int = None,
            p2: int = None,
        ):
        kwargs = {key:value for key,value in locals().items() if key in self.defaults and value is not None}
        return super().Configure(**kwargs)

    def Setup(self):
        self.lark = LarkConfig(self["prefix"]).getlark()

    def Acquire(self):
        n_img = self["n_img"]
        pxls = self.lark.getStreamBlock("rtcPxlBuf",n_img)[0]
        print(pxls.shape)
        npxlx = self.lark.get("npxlx")
        npxly = self.lark.get("npxly")
        px = npxlx[0]
        py = npxly[0]

        py_imgs = numpy.zeros((n_img,px*py),dtype=pxls.dtype)
        for i in range(n_img):
            py_imgs[i,:] = pxls[i,:px*py]

        py_imgs.shape = n_img,py,px

        self.im = py_imgs.mean(0)

    def Execute(self):
        # subapLocation = getlark().get("subapLocation")
        # self.circles = cv2.HoughCircles(self.im.astype(numpy.uint8), cv2.HOUGH_GRADIENT, 2.0, 50)
        self.circles = myCircleAlgo(self.im,self["p1"],self["p2"])
        pass

    def Check(self):
        assert len(self.circles[0])==4
        pass

    def Finalise(self):
        self.result = self.im,self.circles


@CanapySrtc.register_plugin("pyr_quadcell")
class QuadCellPyr(BasePlugin):
    def Init(self):
        self.defaults = {
            "n_img": 10,
            "prefix": "LgsWF",
            "p1": 85,
            "p2": 95
        }
        self.arg_desc = {
            "n_img": "The number of images to average over",
            "prefix": "The lark prefix to use"
        }
        self.im = self.pupils = self.circles = self.flux = None

    def Configure(self,
            n_img: int = None,
            prefix: str = None,
            p1: int = None,
            p2: int = None,
        ):
        kwargs = {key:value for key,value in locals().items() if key in self.defaults and value is not None}
        super().Configure(**kwargs)

    def Setup(self):
        self.lark = LarkConfig(self["prefix"]).getlark()

    def Acquire(self):
        from lark.interface import asyncfunc
        n_img = self["n_img"]
        # pxls = self.lark.getStreamBlock("rtcCalPxlBuf",n_img)[0]
        pxls = self.lark.getStreamBlock("rtcPxlBuf",n_img)[0]
        getstream = asyncfunc(self.lark.getStreamBlock)
        result = getstream("rtcPxlBuf",n_img)
        calsub = self.lark.get("calsub")
        calmult = self.lark.get("calmult")
        calthr = self.lark.get("calthr")
        pxls = result.value[0]
        data = pxls.astype(numpy.float32)
        if calmult is not None:
            data*=calmult
        if calsub is not None:
            data-=calsub
        if calthr is not None:
            data[numpy.where(data<calthr)] = 0
        pxls = data.astype(pxls.dtype)
        print(pxls.shape)
        npxlx = self.lark.get("npxlx")
        npxly = self.lark.get("npxly")
        px = npxlx[0]
        py = npxly[0]

        py_imgs = numpy.zeros((n_img,px*py),dtype=pxls.dtype)
        for i in range(n_img):
            py_imgs[i,:] = pxls[i,:px*py]

        py_imgs.shape = n_img,py,px

        self.im = py_imgs.mean(0)

    def Execute(self):
        # subapLocation = getlark().get("subapLocation")
        # self.circles = cv2.HoughCircles(self.im.astype(numpy.uint8), cv2.HOUGH_GRADIENT, 2.0, 50)
        # if self.circles is None or len(self.circles[0])!=4:
        try:
            self.circles = myCircleAlgo(self.im,self["p1"],self["p2"])
        except Exception as e:
            print(e)
            return
        self.pupils = []
        self.flux = []
        for x,y,r in self.circles[0]:
            x = int(x)
            y = int(y)
            r = int(r)
            circ = numpy.zeros((2*r,2*r),int)
            for i in range(2*r):
                for j in range(2*r):
                    if (i-r)**2+(j-r)**2 < r**2:
                        circ[i,j] = 1
            pup = self.im[y-r:y+r,x-r:x+r]
            self.pupils.append(pup)
            if pup.shape==circ.shape:
                self.flux.append(pup[numpy.where(circ==1)].sum())

        self.flux = numpy.array(self.flux)
        self.flux /= numpy.sum(self.flux)

    def Check(self):
        if self.circles is not None:
            if len(self.circles[0])!=4:
                print("Error in pyr_quadcell")

    def Finalise(self):
        self.result = self.im, self.pupils, self.circles, self.flux


@CanapySrtc.register_plugin("save_data")
class DataSaver(BasePlugin):
    """Save data"""
    def Init(self):
        self.defaults = {"file_name":Path.home()}

    def Configure(self, file_name: Union[Path, str] = None):
        if file_name is not None:
            file_name = Path(file_name)
        kwargs = {key:value for key,value in locals().items() if key in self.defaults and value is not None}
        return super().Configure(**kwargs)

    def Finalise(self):
        self.result = "THIS IS MY RESULT " + str(self["file_name"])

@CanapySrtc.register_plugin("calc_stats")
class CalculateStatistics(BasePlugin):
    """Calculate atmospheric AO statistics"""
    def Finalise(self):
        self.result = "THE FUNXTION RAN"

@CanapySrtc.register_plugin("take_background")
class TakeBackground(BasePlugin):
    """Take N images and average to get a background frame"""
    def Init(self):
        self.defaults = {
            "prefix":"LgsWF",
            "n_img":20,
        }

    def Configure(self, prefix:str = None, n_img:int = None):
        kwargs = {key:value for key,value in locals().items() if key not in ["__class__","self"] and value is not None}
        return super().Configure(**kwargs)

    def Setup(self):
        self.lark = LarkConfig(self["prefix"]).getlark()

    def Acquire(self):
        n_img = self["n_img"]
        # pxls = self.lark.getStreamBlock("rtcCalPxlBuf",n_img)[0]
        self.pxls = self.lark.getStreamBlock("rtcPxlBuf",n_img)[0]

    def Execute(self):
        n_img = self["n_img"]
        npxlx = self.lark.get("npxlx")
        npxly = self.lark.get("npxly")
        px = npxlx[0]
        py = npxly[0]

        py_imgs = numpy.zeros((n_img,px*py),dtype=self.pxls.dtype)
        for i in range(n_img):
            py_imgs[i,:] = self.pxls[i,:px*py]

        self.im = py_imgs.mean(0).astype(float)

    def Apply(self):
        self.lark.set("bgImage",self.im)

    def Finalise(self):
        self.result = self.im

MIN_RADIUS = 2

PLOT = 0

def findCircle(image,p1=68,p2=95):

    if PLOT:
        from matplotlib import pyplot
    # find p1(68) percentile
    p1 = numpy.percentile(image.flatten(),p1)

    # threshold to p1 percentile
    print(f"p1 = {p1}")

    image -= p1
    image[numpy.where(image<=0)] = 0

    # now find p2(95) percentile of image
    p2 = numpy.percentile(image.flatten(),p2)
    print(f"p2 = {p2}")
    # equalise all above 95 percentile to 95 percentile value
    image[numpy.where(image>=p2)] = p2

    # sum along each axis and find the 1st and 2nd derivative
    x = numpy.sum(image,0)
    y = numpy.sum(image,1)
    gx = numpy.gradient(x)
    gy = numpy.gradient(y)
    g2x = numpy.gradient(gx)
    g2y = numpy.gradient(gy)

    if PLOT:
        pyplot.plot(gx)
        pyplot.plot(g2x)
        pyplot.show()

    # find edges based on 2nd derivative
    whg2xmax1 = numpy.where(g2x==max(g2x))[0][0]
    whg2ymax1 = numpy.where(g2y==max(g2y))[0][0]

    whg2xmax2 = whg2xmax1
    cnt = 0
    while abs(whg2xmax2 - whg2xmax1) < 2*MIN_RADIUS:
        whg2xmax2 = numpy.where(g2x==numpy.partition(g2x, -2-cnt)[-2-cnt])[0][0]
        cnt+=1

    whg2ymax2 = whg2ymax1
    cnt = 0
    while abs(whg2ymax2 - whg2ymax1) < 2*MIN_RADIUS:
        whg2ymax2 = numpy.where(g2y==numpy.partition(g2y, -2-cnt)[-2-cnt])[0][0]
        cnt+=1

    xb = (whg2xmax1+whg2xmax2)/2.
    yb = (whg2ymax1+whg2ymax2)/2.

    d1b = abs(whg2xmax1 - whg2xmax2)
    d2b = abs(whg2ymax1 - whg2ymax2)

    r = (d1b+d2b)/4.
    r = max(d1b,d2b)/2.
    if r >= MIN_RADIUS:
        return (xb,yb,r)

    # something goes wrong with 2nd derivative....

    # find edges based on 1st derivative
    whgxmax = numpy.where(gx==max(gx))[0][0]
    whgxmin = numpy.where(gx==min(gx))[0][0]
    whgymax = numpy.where(gy==max(gy))[0][0]
    whgymin = numpy.where(gy==min(gy))[0][0]

    # find position based on first derviative
    xa = ( whgxmax + whgxmin )/2.
    ya = ( whgymax + whgymin )/2.

    # find diameter based on first derivative
    d1a = abs(whgxmax - whgxmin)
    d2a = abs(whgymax - whgymin)

    r = (d1a+d2a)/4.
    r = max(d1a,d2a)/2

    return (xa,ya,r)

def myCircleAlgo(image,p1=68,p2=95):
    shape = image.shape
    circles = numpy.zeros(((1,4,3)))

    for i in range(2):
        for j in range(2):
            circles[0,i*2+j,:] = findCircle(image[i*shape[0]//2:(i+1)*shape[0]//2,j*shape[1]//2:(j+1)*shape[1]//2],p1,p2)
            circles[0,i*2+j,:] += j*shape[1]//2,i*shape[0]//2,0
    return circles