
from multiprocessing import Process, set_start_method
import os
from pathlib import Path
import pickle
import subprocess
import sys
import time
import lark
import systemd.daemon
from lark.utils import var_from_text

from .interface import connectClient, connectDaemon, get_registry_parameters, remoteprint

from .configLoader import darcmain_format
from .parambuf import ParamBuf, BufferError
from logging import getLogger
from .logger import StreamToLogger, log_to_stdout, log_to_file
# logger = MyLogger("larkDaemon",level="INFO")
import logging
import signal

from .interface import ControlClient, RemoteService, startControl, startService
from lark import configLoader

def larkstarter(prefix, hostname):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    logger = getLogger(prefix)
    logger.setLevel("DEBUG")
    logger.propagate = False
    log_to_file(f"{prefix}",level="DEBUG",logger=logger)
    logger.info(f"\nStarting new Lark: {prefix} on {hostname}")
    logger = getLogger(f"{prefix}.STD")
    sys.stdout = StreamToLogger(logger,logging.STDOUT)
    sys.stderr = StreamToLogger(logger,logging.STDERR)
    control = startControl(prefix, hostname=hostname, block=True)
    # control.block()
    # control.rpyc_close()

def servicestarter(service_class_pckl, name, hostname):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    logger = getLogger(name)
    logger.setLevel("DEBUG")
    logger.propagate = False
    log_to_file(f"{name}",level="DEBUG",logger=logger)
    logger.info(f"\nStarting new Service: {name} on {hostname}")
    logger = getLogger(f"{name}.STD")
    sys.stdout = StreamToLogger(logger,logging.STDOUT)
    sys.stderr = StreamToLogger(logger,logging.STDERR)
    service_class = var_from_text(service_class_pckl[0],service_class_pckl[1])
    service = startService(service_class, name, hostname=hostname, block=True)
    # service.block()
    # service.rpyc_close()

class LarkDaemon:
    def __init__(self, name):
        self.logger = getLogger(name)
        self.logger.setLevel("DEBUG")
        self.name = name
        self.darcmain = {}
        self.larkcontrol = {}
        self.services = {}
        self.transport_notify = None

    def startdarcmain(self, prefix, options=None, nstoreDict={}, *args, **kwargs):
        if type(prefix) is not str:
            raise TypeError("prefix needs to be a string")
        prefix.replace(" ", "")
        if prefix in self.darcmain:
            if self.darcmain[prefix].poll() is None:
                txt = f"darcmain already running with prefix {prefix}"
                self.logger.warn(txt)
                return self.notify(txt)
            self.darcmain.pop(prefix)
        try:
            ParamBuf(prefix)
        except BufferError as e:
            plist = ["darcmain", "-i", "-r", f"-s{prefix}"]
            if options is not None:
                for key in darcmain_format.keys():
                    if options[key] is not None:
                        plist.append(darcmain_format[key].format(options[key]))
            if nstoreDict is not None:
                for opt,value in nstoreDict.items():
                    plist.extend([darcmain_format["nstoreDict"],opt,f"{value:d}"])
            try:
                self.darcmain[prefix] = subprocess.Popen(plist)
            except Exception as e:
                raise RuntimeError(f"Failed to execute {str(plist):s}") from e
            else:
                txt = f"Started darcmain with prefix {prefix}"
                self.logger.info(txt)
                return self.notify(txt)
        else:
            txt = "darcmain already running with this prefix outside of python control"
            self.logger.warn(txt)
            return self.notify(txt)

    def stopdarcmain(self, prefix):
        if prefix in self.darcmain:
            if self.darcmain[prefix].poll() is None:
                self.darcmain[prefix].send_signal(15)
                self.darcmain[prefix].wait(2)
            else:
                self.logger.info("darcmain already stopped")
            self.logger.debug("Removing SHM")
            if os.path.exists("/dev/shm/%srtcParam1"%prefix):
                try:
                    os.unlink("/dev/shm/%srtcParam1"%prefix)
                except:
                    self.logger.warn("Failed to unlink %srtcParam1"%prefix)
            if os.path.exists("/dev/shm/%srtcParam2"%prefix):
                try:
                    os.unlink("/dev/shm/%srtcParam2"%prefix)
                except:
                    self.logger.warn("Failed to unlink %srtcParam2"%prefix)
            d=os.listdir("/dev/shm")
            self.darcmain.pop(prefix)
            self.logger.info(f"darcmain:{prefix} stopped {d}")
        else:
            self.logger.info(f"no darcmain:{prefix} found")

    def startlark(self, prefix):
        ret = self.startdarcmain(prefix)
        if ret is not None:
            self.logger.info(str(ret))
        if prefix in self.larkcontrol:
            if self.larkcontrol[prefix].is_alive():
                txt = f"lark:{prefix} still running"
                self.logger.info(txt)
                return self.notify(txt)
            self.larkcontrol.pop(prefix)
        self.larkcontrol[prefix] = Process(target=larkstarter,args=(prefix,self.name))
        self.larkcontrol[prefix].start()
        self.logger.info(f"started lark:{prefix}")
        if not self.larkcontrol[prefix].is_alive():
            raise RuntimeError("Error starting lark")
        return self.notify(f"Started lark {prefix}")

    def _startservice(self, service_class, name):
        self.services[name] = (Process(target=servicestarter,args=(service_class, name, self.name)),service_class)
        self.services[name][0].start()
        self.logger.info(f"started service:{name}")
        if not self.services[name][0].is_alive():
            raise RuntimeError("Error starting service")
        return self.notify(f"Started service {name}")

    def startservice(self,service_class_pckl,name):
        # service_class = pickle.loads(service_class_pckl)
        # values = {}
        # exec(service_class_pckl[1],values,values)
        # service_class = values[service_class_pckl[0]]
        if name in self.services:
            if self.services[name][0].is_alive():
                txt = f"service:{name} already exists"
                self.logger.info(txt)
                return self.notify(txt)
            self.services.pop(name)
        return self._startservice(service_class_pckl, name)

    def _stopservice(self,name):
        if name in self.services:
            if self.services[name][0].is_alive():
                try:
                    s = connectClient(name)
                except Exception as e:
                    self.logger.warn(repr(e))
                    self.logger.debug(f"Failed to connect {e}")
                else:
                    s.stop()
                    # s.remote_close()
                    # s.close()
            self.services[name][0].terminate()
            self.services[name][0].join()

    def stopservice(self,name):
        self.logger.debug(f"Stopping {name}")
        if name in self.services:
            self._stopservice(name)
            self.services.pop(name)

    def resetservice(self, name):
        if name in self.services:
            service_class = self.services[name][1]
            self.stopservice(name)
            return self._startservice(service_class, name)

    def stoplark(self,prefix):
        # first trying stopping lark externally...
        try:
            c = ControlClient(prefix)
            c.stop()
            # c.remote_close()
        except:
            self.logger.warn("Can't connect to lark")
        if prefix in self.larkcontrol:
            if self.larkcontrol[prefix].is_alive():
                self.larkcontrol[prefix].join()
            self.larkcontrol.pop(prefix)
            self.logger.info(f"stopped lark:{prefix}")
        if prefix in self.darcmain:
            darcmain = self.darcmain[prefix]
            if darcmain.poll() is None:
                darcmain.send_signal(15)
                darcmain.wait(2)
            self.darcmain.pop(prefix)

    def notify(self, *args):
        return remoteprint(*args)

    def shutdown(self):
        self.logger.warn("shutting down")
        for n,v in self.services.items():
            if v[0].is_alive():
                try:
                    s = connectClient(n)
                except Exception as e:
                    self.logger.warn(f"{n} has already died: {repr(e)}")
                    continue
                try:
                    s.stop()
                except Exception as e:
                    self.logger.warn(f"Error stopping {n} gracefully: {repr(e)}")
        for p,v in self.larkcontrol.items():
            if v.is_alive():
                try:
                    c = ControlClient(p)
                except Exception as e:
                    self.logger.warn(f"Can't connect to {p}: {repr(e)}")
                    continue
                try:
                    c.remote_close(0.5)
                except Exception as e:
                    self.logger.warn(f"{repr(e)}")
        for p,v in self.darcmain.items():
            if v.poll() is None:
                try:
                    v.send_signal(15)
                    v.wait(2)
                except Exception as e:
                    self.logger.warn(f"{repr(e)}")
        time.sleep(0.5)
        for n,v in self.services.items():
            try:
                v[0].terminate()
                v[0].join()
            except Exception as e:
                self.logger.warn(f"{repr(e)}")
        for p,v in self.larkcontrol.items():
            try:
                v.terminate()
                v.join()
            except Exception as e:
                self.logger.warn(f"{repr(e)}")
        subprocess.run(["systemctl","restart","larkNames"])
        self.unblock()

    def larkstatus(self,prefix=None):
        if prefix is not None:
            lc = dm = -1
            if prefix in self.larkcontrol:
                lc = 0
                if self.larkcontrol[prefix].is_alive():
                    c = ControlClient(prefix)
                    lc = c.is_running()
                else:
                    self.larkcontrol.pop(prefix)
            if prefix in self.darcmain:
                dm = 0
                if self.darcmain[prefix].poll() is None:
                    dm = 1
                else:
                    self.darcmain.pop(prefix)
            return {prefix:(lc,dm)}
        else:
            status = {}
            prefixes = set(list(self.darcmain.keys())+list(self.larkcontrol.keys()))
            for prefix in prefixes:
                status.update(self.larkstatus(prefix))
            return status

    def servicestatus(self,name=None):
        if name is not None:
            ss = -1
            if name in self.services:
                ss = 0
                if self.services[name][0].is_alive():
                    ss = 1
                else:
                    self.services.pop(name)
            return {name:ss}
        else:
            status = {}
            for name in self.services.keys():
                status.update(self.servicestatus(name))
            return status
            
            
    def listDir(self, dir="", use_data_dir=False):
        tmp = Path(dir)
        if use_data_dir:
            tmp = Path(configLoader.DATA_DIR)/dir
        if not tmp.is_dir():
            if tmp.exists():
                return str(tmp)
        stuff = [p for p in tmp.iterdir() if not p.name.startswith(".")]
        return {
            "name":str(tmp),
            "dirs":[p.name for p in stuff if p.is_dir()],
            "file":[p.name for p in stuff if not p.is_dir()]
        }
        
    def openFile(self, filepath):
        return Path(filepath).open()


def startDaemon():
    # from contextlib import redirect_stdout

    # with open("/var/log/lark/daemon.startDaemon.log", 'w') as f:
    #     with redirect_stdout(f):
    
    registry = get_registry_parameters()
    name = registry["hostname"] + "_Daemon"
    
    logger = getLogger(name)
    logger.setLevel("DEBUG")
    log_to_file(f"{name}",logger=logger)
    log_to_stdout(logger)
    
    sys.stdout = StreamToLogger(logger,logging.STDOUT)
    sys.stderr = StreamToLogger(logger,logging.STDERR)
    print("Now printing to log file!")
    
    set_start_method('spawn')

    class RemoteLarkDaemon(RemoteService,LarkDaemon):
        def __init__(self,name):
            RemoteLarkDaemon.ALIASES = (name,)
            RemoteService.__init__(self,name)
            LarkDaemon.__init__(self,name)

    # name = config.DEFAULT_HOST + "_Daemon"
    # print(config.DEFAULT_HOST)
    this_daemon = RemoteLarkDaemon(name)

    logger.info(f"Starting LarkDaemon server: {name}")

    with this_daemon as remote_obj:
        signal.signal(signal.SIGINT, remote_obj.unblock)
        systemd.daemon.notify('READY=1')
        remote_obj.block()
        logger.info(f"Cancelled LarkDaemon server: {name}")
        remote_obj.shutdown()
                
def resetAll():
    registry = get_registry_parameters()
    d:LarkDaemon = connectDaemon(registry["hostname"])
    d.shutdown()
    
def resetDaemon():
    if len(sys.argv) > 1:
        daemon = sys.argv[1]
    else:
        daemon = get_registry_parameters()["hostname"]
    d:LarkDaemon = connectDaemon(daemon)
    d.shutdown()
    
if __name__=="__main__":
    resetAll()
