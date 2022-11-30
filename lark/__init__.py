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
from .configLoader import get_lark_config

from .interface import (connectClient,
                        ControlClient,
                        startControlClient,
                        connectDaemon,
                        startServiceClient,
                        larkNameServer,
                        get_registry_parameters,
                        copydict
                        )



DEFAULT_PREFIX = get_lark_config().DEFAULT_PREFIX

# by default lark will connect to the local daemon
# to connect to a remote daemon it should be specified during connection
# e.g. lrk = lark.LarkConfig(prefix="Lgs", hostname="LASERLAB")
HOSTNAME = get_registry_parameters().RPYC_HOSTNAME

RTCDS = {}
SERVICES = {}

def local_print(*args,**kwargs):
    print(*args,**kwargs)

class NoLarkError(BaseException):
    """An exeption for no lark available"""

class LarkConfig:
    """Used to connect to a lark instance and control it.
    Basic usage: LarkControl.getlark(prefix) -> a lark object
    """
    def __init__(self, prefix:str=DEFAULT_PREFIX, hostname:str=HOSTNAME):
        self.prefix = prefix
        self.hostname = hostname
        self._lark = None

    def __enter__(self):
        return self.getlark()
        
    def __exit__(self, *args):
        self.closelark()

    def startlark(self, params:dict):
        """Start the lark instance throught the daemon with self.hostname

        Args:
            params (dict): Parameters for initialisation

        Returns:
            ControlClient: The RPyC client to control lark
        """
        try:
            return self.getlark()
        except NoLarkError:
            self._lark = startControlClient(self.prefix,hostname=self._hostname,params=params)
            # self._lark.control.print_to(local_print)
            return self._lark
            
    def startlocal(self, params:dict):
        """Not yet implemented, start a local lark instance and not through the daemon

        Args:
            params (dict): Parameters for initialisation

        Returns:
            _type_: _description_
        """
        try:
            return self.getlark()
        except NoLarkError:
            pass

    def getlark(self, unique:bool=False) -> ControlClient:
        """Get a ControlClient object associated with this LarkConfig

        Args:
            unique (bool, optional): whether to request a new connection. Defaults to False and the previous connection is reused.

        Raises:
            NoLarkError: If no lark is available with this prefix

        Returns:
            ControlClient: The lark object
        """
        if not unique:
            if self._lark is not None:
                try:
                    self._lark.conn.ping()
                except EOFError:
                    self._lark = None
                else:
                    return self._lark
            try:
                self._lark = ControlClient(self.prefix)
            except ConnectionError as e:
                raise NoLarkError(f"No Lark available with name {self.prefix}")
            # self._lark.control.print_to(local_print)
            return self._lark
        else:
            try:
                lark = ControlClient(self.prefix)
            except ConnectionError as e:
                raise NoLarkError(f"No Lark available with name {self.prefix}")
            else:
                # lark.control.print_to(local_print)
                return lark

    def closelark(self, prefix=None):
        """
        Does not stop the running lark, just closes the current connection
        """
        if self._lark is not None:
            try:
                self._lark.conn.close()
            except Exception as e:
                print(e)
            else:
                self._lark = None

    def stoplark(self):
        """Stops the running lark associated with this LarkConfig"""
        try:
            self.getlark()
        except NoLarkError as e:
            pass
        if self._lark is not None:
            try:
                self._lark.stop()
            except Exception as e:
                print(e)
            else:
                self._lark = None

def getdaemon(hostname:str=HOSTNAME):
    """Get the RPyC object for the daemon with the hostname specified

    Args:
        hostname (str, optional): hostname of daemon. Defaults to None.

    Returns:
        RemoteClient: An RPyC client to the daemon
    """
    global RTCDS
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

def startservice(service_class, name, hostname=HOSTNAME):
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



