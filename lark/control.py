#!/usr/bin/env python3

"""
control.py
==========
Provides control functionality for lark
"""

from pathlib import Path
import os
import pickle
import sys
import time
import numpy
from lark.utils import get_datetime_stamp, var_from_file
from lark.daemon import LarkDaemon
try:
    import numa
except:
    print("Numa not available")
    USENUMA = False
else:
    USENUMA = True
import argparse
from collections import ChainMap
import traceback

from .parambuf import ParamBuf, BufferError
from .circbuf import CircReader, TelemetrySystem
from . import check
# from .configLoader import remote_fns
from .configLoader import get_lark_config
import lark

def process_args():
    """Process command line arguments for larkcontrol and return a dictionary
    with the values.

    Returns:
        dict: The command line parameters stored in a dict.
    """
    usage = '''
    larkcontrol [options]

    larkcontrol --configfile <input file name> --prefix <instance prefix name>

    Example:
    larkcontrol pulnixConfigFile.py  -s pulnixcamera
    larkcontrol -f pulnixConfigFile.py  -s pulnixcamera

    note:
    * more information, please use --help
    '''
    parser = argparse.ArgumentParser(usage=usage,conflict_handler='resolve')
    parser.add_argument('configfile', nargs="?",type=str,help='Configuration file path', default=None)
    parser.add_argument('-s', '--prefix', dest='prefix', type=str, help='Prefix name to handle instace', default="")
    parser.add_argument('-h', '--hostname', dest='hostname', type=str, help='Hostname where to start lark', default="localhost")
    # parser.add_argument('-p', '--port', dest='port', type=int, help='Port to be used', default=4242)
    # parser.add_argument('-H', '--host', dest='host', type=str, help='Host to be used', default=socket.gethostname())
    # parser.add_argument('-d', '--dataswitch', dest='dataswitch', action='store_true', help='Host to be used', default=False)
    parser.add_argument('-a', '--affin', dest='affin', type=int, help='Number of affinity to be used,  default 0x7fffffff', default=0x7fffffff)
    parser.add_argument('-i', '--prio', dest='prio', type=int, help='Thread priority (importance) to be used', default=0)
    parser.add_argument('-l', '--lock', dest='lock', action='store_false', help='Use lock,  default True', default=True)
    parser.add_argument('-q', '--routput', dest='routput', action='store_true', help='Redirect the output of darcmain', default=False)
    parser.add_argument('-b', '--buffersize', dest='bufsize', type=int,  help='Set buffer size',  default=None)
    parser.add_argument('-n', '--nodarc', dest='nodarc', action='store_true', help='No instance of darc - just the shm buffer.', default=False)
    parser.add_argument('-f', '--configfile', dest='configFile', type=str, help='Configuration file path', default=None)
    parser.add_argument('-c', '--nstore', dest='nstore', type=str,  nargs=2,  action='append',  help='stream name and number of circular buffer entries', default=None)
    parser.add_argument('-m', '--circBufMemSize', dest='circBufMaxMemSize', type=int, help='Memory for circular buffers', default=None)
    parser.add_argument('-C', '--cleanstart', dest='cleanStart', action='store_true', help='Remove /dev/shm/*rtcParam[1,2] befpre starting', default=False)

    # darcmain only
    parser.add_argument('-o', '--output', dest='output', action='store_true', help='Don\'t redirect the output of darcmain', default=False)
    parser.add_argument('-I','--affinity',dest='darcaffinity',type=str,help='Thread affinity for darc core, default -1',default="0xffffffffffffffff")
    parser.add_argument('-e', '--nhdr', dest='nhdr',  type=str,  help='NHDR size',  default=None)
    parser.add_argument('-N', '--numaSize', dest='numaSize', type=int,help='numa memory buffer size',default=0)

    options = parser.parse_args()
    options.nstoreDict = {}

    if options.nstore is not None:
        for stream in options.nstore:
            options.nstoreDict[stream[0]] = int(stream[1])

    options.redirectdarc = 1 if options.output else 0
    options.shmPrefix = options.prefix
    if options.configFile is not None:
        options.configfile = options.configFile

    return vars(options)

def processConfigFile(prefix,fname):
    d = {"control":{}, "prefix":prefix, "numpy":numpy}
    #execfile(configFile,globals())
    #global control#gives syntax warning, but is required to work!
    control = var_from_file("control", file_path=fname, prefix=prefix)
    # exec(compile(open(fname, "rb").read(), fname, 'exec'),d)
    # control=d["control"]
    if "comments" in d:
        comments=d["comments"]
    if "configfile" not in control:
        control["configfile"]=str(fname)
    # processing stuff
    return control

class Control(ParamBuf, TelemetrySystem):
    """The Main Control Class, inherits from TelemetrySystem and ParamBuf

    Args:
        TelemetrySystem (prefix): [description]
        ParamBuf (prefix): [description]
    """
    def __init__(self,prefix,*,options:dict={},hostname=None,params=None):
        self.datetime = get_datetime_stamp()
        # self.options = ChainMap(options,check.default_options)
        options.update({key:value for key,value in check.default_options.items() if key not in options})
        self.options = options
        self.hostname = hostname
        self.startedDarc = 0
        self.running = 0
        self.initialised = 0
        self.telem_initialised = 0
        print("INIT RTC 1")
        self.initialiseRTC(prefix, params)

    def initialiseRTC(self, prefix, params=None):
        cnt=0
        print("CALLED INIT RTC")
        while cnt<10:
            try:
                self.param_init(prefix,datetime=self.datetime)
            except BufferError as e:
                print("failed to open previous buffer")
                from . import interface
                host:LarkDaemon = interface.connectDaemon(self.hostname)
                host.startdarcmain(prefix,options=None)#self.options)
                self.startedDarc = 1
                time.sleep(0.2)
            else:
                labels = self.keys()
                if len(labels) != 0:
                    self.initialised = 1
                break
            finally:
                cnt+=1
        if self.options["numaSize"]!=0:#check for numa-aware buffers...
            if not USENUMA or numa.available() == False:
                raise Exception("Numa specified but not available, please install with pip install numa")
            self.openNuma()
        if self.options["configfile"] is not None:
            self.configure_from_file(self.options["configfile"])
        elif params is not None:
            self.configure_from_dict(params)

    def connect_telemetry(self):
        if not self.telem_initialised:
            self.telem_init(self.prefix,self.datetime)
        # self.startTelemetry()
        # time.sleep(1)
        # self.stopTelemetry()
        # self.startStream("rtcStatusBuf")
        # self.startStream("rtcTimeBuf")

    def configure_from_file(self,fname):
        # here put the file processing
        params = processConfigFile(self.prefix,fname)
        self.configure_from_dict(params)

    def configure_from_dict(self,params):
        params = check.inventAndCheck(params)
        self.set("switchRequested", 0)
        params.pop("switchRequested", None)
        numaParams = {key:params.pop(key) for key in list(params) if key.startswith("numa")}
        failed,changes = self.setMany(params,switch=0)
        # try again...
        if failed:
            failed,changes = self.setMany(failed,switch=0)
        if failed:
            raise Exception("Failed to initialise buffer")
        self.setNuma(numaParams)
        self.switchBuffer(init=True)
        self.connect_telemetry()

    def is_running(self):
        return True

    def stop(self,stopRTC=1,stopControl=1):
        print("RUNNING STOP 1")
        self.stopTelemetry()
        if stopRTC:
            # self.set("go",0,switch=1)
            # self.set("go",0,active=1)
            if self.startedDarc:
                from . import interface
                host = interface.connectDaemon(self.hostname)
                print("RUNNING STOP 2")
                host.stopdarcmain(self.prefix)
                self.startedDarc = 0
                self.rtcStopped = 1
            # remove the shm
                # print("Removing SHM")
                # if os.path.exists("/dev/shm/%srtcParam1"%self.prefix):
                #     try:
                #         os.unlink("/dev/shm/%srtcParam1"%self.prefix)
                #     except:
                #         print("Failed to unlink %srtcParam1"%self.prefix)
                # if os.path.exists("/dev/shm/%srtcParam2"%self.prefix):
                #     try:
                #         os.unlink("/dev/shm/%srtcParam2"%self.prefix)
                #     except:
                #         print("Failed to unlink %srtcParam2"%self.prefix)
                # d=os.listdir("/dev/shm")
            else:
                print("SETTING GO TO 0")
                self.set("go",0,switch=1)
                time.sleep(0.5)
                # print("Removing SHM")
                if os.path.exists("/dev/shm/%srtcParam1"%self.prefix):
                    try:
                        os.unlink("/dev/shm/%srtcParam1"%self.prefix)
                    except:
                        print("Failed to unlink %srtcParam1"%self.prefix)
                if os.path.exists("/dev/shm/%srtcParam2"%self.prefix):
                    try:
                        os.unlink("/dev/shm/%srtcParam2"%self.prefix)
                    except:
                        print("Failed to unlink %srtcParam2"%self.prefix)
                d=os.listdir("/dev/shm")
        if stopControl:
            try:
                print("REMOTE CLOSE")
                self.remote_close()
            except Exception as e:
                print(e)
        print("FINISHED STOP")

    # def getDataDir(self,subdir=None):
    #     if subdir is None:
    #         tmp = Path(get_lark_config().DATA_DIR)
    #         if not tmp.exists():
    #             tmp.mkdir(parents=True)
    #         return [str(tmp)]+[p.name for p in tmp.iterdir() if not p.name.startswith(".")]
    #     else:
    #         tmp = Path(get_lark_config().DATA_DIR)/subdir
    #         if tmp.is_dir():
    #             return [p.name for p in tmp.iterdir() if not p.name.startswith(".")]
    #         else:
    #             return str(tmp)

    def getDataDir(self, subdir=""):
        tmp = Path(get_lark_config().DATA_DIR)/subdir
        if subdir == "":
            if not tmp.exists():
                tmp.mkdir(parents=True)
        if not tmp.is_dir():
            if tmp.exists():
                return str(tmp)
        stuff = [p for p in tmp.iterdir() if not p.name.startswith(".")]
        return {
            "name":str(tmp),
            "dirs":[p.name for p in stuff if p.is_dir()],
            "file":[p.name for p in stuff if not p.is_dir()]
        }
        
    def setStreamShape(self,stream,shape=None):
        if shape is None:
            if stream == "rtcCentBuf":
                ncam = self.get("ncam")
                nsub = self.get("nsub")
                subapFlag = self.get("subapFlag")
                vsubs = []
                ncumsub = 0
                for k in range(ncam):
                    vsubs.append(int(subapFlag[ncumsub:ncumsub+nsub[k]].sum()))
                    ncumsub+=nsub[k]
                if ncam!=1:
                    if all(v==vsubs[0] for v in vsubs):
                        shape = ncam,vsubs[0]*2
                    else:
                        print(f"Unable to reshape array to {ncam},{vsubs}")
                        return 1
                else:
                    shape = (vsubs[0]*2,)
            elif stream in ("rtcPxlBuf","rtcCalPxlBuf"):
                ncam = self.get("ncam")
                npxlx = self.get("npxlx")
                npxly = self.get("npxly")
                if ncam!=1:
                    if all(x==npxlx[0] and y==npxly[0] for x,y in zip(npxlx,npxly)):
                        shape = (ncam,int(npxlx[0]),int(npxly[0]))
                    else:
                        print(f"Unable to reshape array to {ncam},{npxlx},{npxly}")
                        return 1
                else:
                    shape = (int(npxlx[0]),int(npxly[0]))
            elif stream=="rtcSubLocBuf":
                nsub = int(sum(self.get("nsub")))
                shape = (nsub,6)

            else:
                print("stream can't be reshaped")

            self.setStreamShape(stream, shape) # the recursion is to aid in testing using rpyc
            # self.CircReaders[stream].shape = shape
        else:
            self.CircReaders[stream].shape = shape

def main():
    from lark.interface import startControl
    options = process_args()

    controlName = "Control"
    controlName = options["prefix"] + controlName

    if options["cleanStart"]:
        yn=input(f"Remove /dev/shm/{options['prefix']:s}rtcParam1 and 2? [y]/n")
        if yn in ["","y","yes","Y","Yes","YES"]:
            try:
                os.unlink(f"/dev/shm/{options['prefix']:s}rtcParam1")
            except:
                pass
            try:
                os.unlink(f"/dev/shm/{options['prefix']:s}rtcParam2")
            except:
                pass
        yn=input("Killall instances of lark (regardless of prefix)? [y]/n ")
        if yn in ["","y","yes","Y","Yes","YES"]:
            os.system("killall darcmain")
        yn=input("Exit?  Yes to exit, no to continue.  [y]/n ")
        if yn in ["","y","yes","Y","Yes","YES"]:
            sys.exit(0)

    print(options['configfile'])

    # ctrl = Control(options.prefix, vars(options))
    print("STARTING CONTROL 1")
    ctrl = startControl(options['prefix'], hostname=options['hostname'], options=options)

    ctrl.block()
    ctrl.rpyc_close()

    sys.exit()

    ei=None
    while ei==None:
        ei=lark.initialiseServer(controlName=controlName)#this is called here to remove any corba stuff from argv.
        if ei==None:
            time.sleep(1)
    c=Control(globals(), options)
    if ei!=None:
        ei.initialise(c,c.lock)
    try:
        c.loop()
    except KeyboardInterrupt:
        traceback.print_exc()
        msg="died with keyboard interrupt"
    except:
        traceback.print_exc()
        msg="died"
    else:
        msg="finished"

    print("Ending - control for lark has %s, darcmain may still be running"%msg)
    if c.logread!=None:
        c.logread.go=0
    if c.ctrllogread!=None:
        c.ctrllogread.go=0
    lark.unbind(ei=ei, controlName=controlName)
    if msg=="died with keyboard interrupt":
        sys.__stdout__.write("\nEnding - control for lark has %s, darcmain may still be running.\nIf you wanted to stop lark, please use larkmagic stop -c in future.\n(Note - this will only work now if you restart larkcontrol).\n"%msg)
    elif msg=="died":
        sys.__stdout__.write("\nEnding - control for lark has %s, darcmain may still be running.\nIf this was an unintentional crash, you can restart the control object using\nlarkcontrol which should not affect operation of the real-time part of lark\n."%msg)

    # parser = argparse.ArgumentParser()

    # parser.add_argument("config", type=str)
    # parser.add_argument("--prefix",dest="prefix",type=str)

    # args = parser.parse_args()

    # c = Control(args.prefix)

    # c.processConfigFile(args.config)



if __name__ == "__main__":
    from lark.interface import startControl

    # p = ParamBuf("canapy")
    print("making remote control")
    prefix = "canapy"
    if len(sys.argv)>1:
        prefix = sys.argv[1]
    # config_file = "/home/canapyrtc/git/canapy-rtc/config/configOcamTest.py"
    config_file = "/home/canapyrtc/git/canapy-rtc/config/canapy/TestPyrSH/configTestPyrSH.py"

    # params = processConfigFile(prefix,config)
    # params = check.checkParams(params)
    # print(params.keys())
    # sys.exit()

    params = processConfigFile(prefix,config_file)

    c = startControl(prefix,params=params)
    # c.configure_from_file(config_file)
    # c.connect_telemetry()
    try:
        print(c["npxlx"])
    except KeyError as e:
        print(e)

    try:
        c.block()
    except KeyboardInterrupt as e:
        print("Cancelled")
    c.close()



