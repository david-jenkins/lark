'''
A replacement for the darc python module.
Inherits the new lark ParamBuf for direct access to the parambuf

'''

# this prints the file name and line number below every print out
# the format allows links to work in the VS code terminal
STACKPRINT = 0
if STACKPRINT:
    from inspect import stack
    import builtins
    printfn = print
    def print(*args, **kwargs):
        frameinfo = stack()[1]
        printfn(*args,**kwargs)
        printfn(f"\t\"{frameinfo.filename}\", line {frameinfo.lineno}")
    builtins.print = print

import os
# all files created with lark should have this umask, i.e group permissions should be greater than default
# the default mask is usually 0o022. 
os.umask(0o002)

from pathlib import Path
import sys
import toml
from .configLoader import config

from .interface import (connectClient,
                        ControlClient,
                        startControlClient,
                        connectDaemon,
                        startServiceClient,
                        larkNameServer,
                        get_registry_parameters
                        )

# # read config at /etc/lark.cfg
# cfile = Path("/etc/lark.cfg")
# config = {}
# if cfile.exists():
#     config.update(toml.load(cfile))

# # read config at $HOME/lark.cfg
# cfile = Path.home()/"lark.cfg"
# if cfile.exists():
#     config.update(toml.load(cfile))

PREFIX = config.get("DEFAULT_PREFIX", None)
# HOSTNAME = config.get("DEFAULT_HOST", None)
# by default lark will connect to the local daemon
# to connect to a remote daemon it should be specified during connection
# e.g. lrk = lark.LarkConfig(prefix="Lgs", hostname="LASERLAB")
HOSTNAME = get_registry_parameters()["hostname"]

RTCDS = {}
SERVICES = {}

def local_print(*args,**kwargs):
    print(*args,**kwargs)

class NoLarkError(BaseException):
    """An exeption for no lark available"""

def _checkprefix(_prefix):
    global PREFIX
    if _prefix is None:
        if PREFIX is None:
            raise RuntimeError("No prefix specified")
        _prefix = PREFIX
    return _prefix

def _checkhostname(_hostname):
    global HOSTNAME
    if _hostname is None:
        if HOSTNAME is None:
            raise RuntimeError("No prefix specified")
        _hostname = HOSTNAME
    return _hostname

class LarkConfig:
    def __init__(self, prefix=None, hostname=None):
        self._prefix = _checkprefix(prefix)
        self._hostname = _checkhostname(hostname)
        self._lark = None

    @property
    def prefix(self):
        return self._prefix

    @prefix.setter
    def prefix(self, value):
        self._prefix = _checkprefix(value)

    @property
    def hostname(self):
        return self._hostname

    @hostname.setter
    def hostname(self, value):
        self._hostname = _checkhostname(value)

    def startlark(self, params):
        try:
            return self.getlark()
        except NoLarkError:
            self._lark = startControlClient(self._prefix,hostname=self._hostname,params=params)
            # self._lark.control.print_to(local_print)
            return self._lark
            
    def startlocal(self, params):
        try:
            return self.getlark()
        except NoLarkError:
            pass

    def getlark(self, unique=False) -> ControlClient:
        if not unique:
            if self._lark is not None:
                try:
                    self._lark.conn.ping()
                except EOFError:
                    self._lark = None
                else:
                    return self._lark
            try:
                self._lark = ControlClient(self._prefix)
            except ConnectionError as e:
                raise NoLarkError("No Lark available with this name")
            # self._lark.control.print_to(local_print)
            return self._lark
        else:
            lark = ControlClient(self._prefix)
            # lark.control.print_to(local_print)
            return lark

    def closelark(self, prefix=None):
        """
        Does not stop the running lark, just closes a connection
        """
        self.getlark()
        if self._lark is not None:
            try:
                self._lark.conn.close()
            except Exception as e:
                print(e)
            else:
                self._lark = None

    def stoplark(self, prefix=None):
        """Stops a running lark, either specified by prefix or by global PREFIX"""
        self.getlark()
        if self._lark is not None:
            try:
                self._lark.stop()
            except Exception as e:
                print(e)
            else:
                self._lark = None

def getdaemon(hostname=None):
    global RTCDS
    hostname = _checkhostname(hostname)
    rtcd = RTCDS.get(hostname,None)
    if rtcd is not None:
        try:
            rtcd.conn.ping()
        except EOFError:
            RTCDS.pop(hostname)
        else:
            return rtcd
    RTCDS[hostname] = connectDaemon(hostname)
    return RTCDS[hostname]

def getservice(name):
    global SERVICES
    instance = SERVICES.get(name,None)
    if instance is not None:
        try:
            instance.conn.ping()
        except Exception as e:
            print(e)
            SERVICES.pop(name)
        else:
            return instance
    SERVICES[name] = connectClient(name)
    return SERVICES[name]

def startservice(service_class, name, hostname=None):
    hostname = _checkhostname(hostname)
    try:
        return getservice(name)
    except Exception as e:
        print(e)
    SERVICES[name] = startServiceClient(service_class,name,hostname=hostname)
    return SERVICES[name]

def stopservice(name):
    try:
        serv = getservice(name)
    except Exception as e:
        print(e)
    else:
        serv.stop()



