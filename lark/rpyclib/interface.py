#!/usr/bin/env python3
"""
rpyc_utils.py
=============
By default the registry server listens with the parameters defined in 4 ways with
increasing priority:

* written in this file
* written in the config file at /etc/lark.cfg (lark/conf/lark.cfg) - this is the most consistent option
######## * written in environment variables - RPYC_IP, RPYC_PORT, RPYC_MODE - not used now, leads to inconsistency
* supplied as command line parameters when running this script (larkNames)

The broadcast mode (UDP, ip=255.255.255.255) *SHOULD* allow lark instances on the local network to find
the registry server automatically. If this does not work then a fixed IP should be used.
The Broadcasting mode DOES NOT work with the Linux firewall. Disable the firewall or use a fixed IP.

This script is added to the PATH as larkNames, use -o option to print logs to command line
without -o the log is appended to /dev/shm/larkNames.log. Run larkNames & to put into background.
use "nohup larkNames &" to keep it running even when the terminal is closed, use "pkill -f larkNames" to stop
if nohup is not available, use screen or tmux

if larkNames is killed when lark is running, lark will reconnect to a restarted nameserver with the
same starting arguments after at most 60 seconds

use larkNames ip:port to change the arguments at run time
use the -mode=MODE flag to change the mode
e.g.
larkNames 192.168.1.11:2456 -mode=UDP
larkNames 10.0.1.2:4573 -mode=TCP

alternatively, the ip, port and mode can be set with environment variables,
which can be set persistently if needed, i.e in .bashrc
BUT be careful that the same environment variables are set locally for lark
e.g.
export RPYC_IP=192.168.1.11
export RPYC_PORT=35677
export RPYC_MODE=TCP

EVEN ALTERNATIVELY, and the recomended option,
the paramters are loaded from the file at /etc/rpyc.cfg which is installed from lark/conf/rpyc.cfg
to use this mode do not set any environment variables and do not use command line parameters.
"""

from dataclasses import dataclass
from logging import getLogger
import sys
import os
from typing import Any, Union
import socket
import time
import toml
import rpyc
import numpy
import types
import threading
import argparse
try:
    import systemd.daemon
except:
    print("No systemd module, must run manually")
    USESYSTEMD = False
else:
    USESYSTEMD = True
from pathlib import PurePath, Path, PosixPath
from rpyc.utils.registry import UDPRegistryServer, TCPRegistryServer, UDPRegistryClient, TCPRegistryClient
from rpyc.lib import setup_logger, spawn_waitready, spawn
from rpyc.utils.server import ThreadedServer
from rpyc.utils.authenticators import AuthenticationError
from collections import ChainMap
from threading import Condition
import builtins

from lark.utils import get_datetime_stamp
local_print = builtins.print
remote_print = builtins.print

from rpyc import async_ as asyncfunc

from ..logger import LOG_DIR, log_to_file, log_to_stdout

logger = getLogger("rpyc")
logger.setLevel("DEBUG")
logger.propagate = False
log_to_file("rpyc",logger=logger)
# log_to_stdout(logger,level="DEBUG")

HERE = Path(__file__).parent.parent.parent.resolve()

@dataclass
class RPYCConfig:
    RPYC_IP: str = "255.255.255.255"
    RPYC_PORT: str = "18511"
    RPYC_MODE: str = "UDP"
    RPYC_HOSTNAME: str = "localhost"
    RPYC_PASSWD: str = "lEt Me IN PlEAse"

RPYC_PORT = 18561

#params can be found in /opt/lark/rpyc.cfg and above dict in that order

def decode(value):
    if isinstance(value,rpyc.BaseNetref) and isinstance(value,dict):
        print("decoding dict")
        return {key:value for key,value in value.items()}
    return value

class remoteprint:
    def __init__(self, *args):
        self.args = args
    def __str__(self):
        return " ".join(self.args)
    def __repr__(self):
        return " ".join(self.args)

def print_replacer(*args,**kwargs):
    global remote_print, local_print
    try:
        afunc = rpyc.timed(remote_print,0.2)
        res = afunc(*args,**kwargs)
        return res.value
    except Exception as e:
        return local_print(*args,**kwargs)

class RemoteService(rpyc.Service):
    """A wrapper for making any python object an RPyC service.
    Also should be inhertited from instead of raw rpyc.Service.
    When inherting from this, use startServer, below.
    Either the use the python with() or make sure to close when done.
    name should be unique, if it is not a new name will be given,
    check self.rpyc_name to get the new name.
    Not normally used by itself, use startServer instead.
    """
    def __init__(self, name, obj=None, hostname=None):
        rpyc.Service.__init__(self)
        self.obj = obj
        self.rpyc_port = None
        self.rpyc_server = None
        self.rpyc_thread = None
        self.rpyc_name = name
        self.rpyc_host = hostname
        self.wrapped = False
        self.rpyc_cond = Condition()

    def __del__(self):
        self.rpyc_close()

    def __enter__(self):
        print("RPYC __ENTER__")
        startServer(self,self.rpyc_name,block=0)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.rpyc_close()

    def rpyc_close(self,delay=0):
        time.sleep(delay)
        print(f"Unregistering {self.rpyc_name}:{self.rpyc_port}")
        unbindService(self.rpyc_port)
        try:
            self.rpyc_server.close()
        except AttributeError as e:
            print(e)
        self.unblock()

    def remote_close(self,delay=0.5):
        spawn(self.rpyc_close,delay=delay)

    def close(self,delay=0):
        self.rpyc_close(delay)

    def join(self):
        if self.rpyc_thread:
            self.rpyc_thread.join()

    def set_hostname(self, name):
        self.rpyc_host = name

    def get_hostname(self):
        return self.rpyc_host

    def block(self):
        self.rpyc_cond.acquire()
        self.rpyc_cond.wait()
        self.rpyc_cond.release()

    def unblock(self,*args,**kwargs):
        self.rpyc_cond.acquire()
        self.rpyc_cond.notify()
        self.rpyc_cond.release()

    def notify(self,*args):
        return remoteprint(*args)

    def print_to(self, print_fn):
        global remote_print
        remote_print = print_fn
        builtins.print = print_replacer

    def on_connect(self, conn):
        return super().on_connect(conn)

    def on_disconnect(self, conn):
        builtins.print = local_print
        return super().on_disconnect(conn)

class BgServer:
    def __init__(self,conn,interval=0.1):
        self.event = threading.Event()
        self._thread = None
        self.conn = conn
        self.interval = interval
        self.start()

    def start(self):
        if self._thread is None:
            self.event.clear()
            self._thread = threading.Thread(target=self.bgserve)
            self._thread.start()
        else:
            if self._thread.is_alive():
                raise RuntimeError("Cannot start an already running BgServer")
            self._thread = None
            self.start()

    def bgserve(self):
        try:
            while not self.event.wait(self.interval):
                self.conn.serve(0.0)
        except Exception as e:
            print(e)
            logger.warn("BgServer exited ungracefully")

    def stop(self):
        self.event.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

def get_registry_parameters(reload:bool = False) -> RPYCConfig:
    """Get the RPyC registry parameters, first uses the config file at /etc/lark.cfg and
    then uses defaults defined above.

    Returns:
        str,int,str: returns the IP adress, port and mode
    """

    if get_registry_parameters.PARAMS is None or reload:
        try:
            LARK_DIR =  Path(toml.load("/etc/lark.cfg")["LARK_DIR"])
            cfg_filepath = LARK_DIR()/"lark.cfg"
        except FileNotFoundError:
            print("No file at /etc/lark.cfg found, using /tmp/lark as main dir and conf/lark.cfg")
            LARK_DIR = "/tmp/lark"
            cfg_filepath = HERE/"conf"/"lark.cfg"        

        if os.path.exists(cfg_filepath):
            try:
                with open(cfg_filepath,'r') as tf:
                    cfg_args = toml.load(tf)["rpyc"]
            except Exception as e:
                cfg_args = {}
                print(repr(e))
                print(f"Can't open {cfg_filepath} file")

        # print("GOT RPYC ARGS", cfg_args)

        # this is not consistent with different users/shells....
        # env_args = {}
        # for k in DEFAULT_PARAMS.keys():
        #     value = os.environ.get(k)
        #     if value is not None:
        #         env_args[k] = value

        # print("GOT ENV ARGS ", env_args)

        # a ChainMap combines multiple dictionaries where the first takes
        # precendence when finding values, it then searches along each until
        # it finds a value or raises a KeyError if nothing is found
        # these_args = ChainMap(env_args,cfg_args,DEFAULT_PARAMS)
        # cfg_args.update({k:v for k,v in DEFAULT_PARAMS.items() if k not in cfg_args})
        # for k in DEFAULT_PARAMS.keys():
        #     print(k,these_args[k])

        # registry = {
        #     "ip":cfg_args["RPYC_IP"],
        #     "port":cfg_args["RPYC_PORT"],
        #     "mode":cfg_args["RPYC_MODE"],
        #     "hostname":cfg_args["RPYC_HOSTNAME"],
        #     "passwd":cfg_args["RPYC_PASSWD"],
        #     }
        registry = RPYCConfig(**cfg_args)
        
        get_registry_parameters.PARAMS = registry

    return get_registry_parameters.PARAMS

get_registry_parameters.PARAMS = None

def find_registry(registry_ip, registry_port, registry_mode):
    name = ("isalive",)
    port = 18560
    try:
        if registry_mode == "UDP":
            registrar = UDPRegistryClient(ip=registry_ip,port=registry_port)
        elif registry_mode == "TCP":
            registrar = TCPRegistryClient(ip=registry_ip,port=registry_port)
        if registrar.register(name,port):
            registrar.unregister(port)
            return None
        else:
            raise Exception("Unable to register with the RPYC name server")
    except ConnectionRefusedError as e:
        if e.errno == 61:
            raise ConnectionRefusedError("No registry server found") from e
        else:
            raise e
    except OSError as e:
        if e.errno == 49:
            raise OSError("Broadcasting not allowed") from e
        else:
            raise e

def get_registry():
    regparams = get_registry_parameters()
    registry_ip = regparams.RPYC_IP
    registry_port = int(regparams.RPYC_PORT)
    registry_mode = regparams.RPYC_MODE
    return find_registry(registry_ip,registry_port,registry_mode)
    

def get_registrar() -> Union[UDPRegistryClient,TCPRegistryClient]:
    """Gets a registrar to connect to the registry server
    Caches it in the get_registrar.REGISTRAR value

    Raises:
        Exception: If a rpyc registry server cannot be found
    Returns:
        RegistryClient: either a UDP or TCP RegistryClient
    """
    if get_registrar.REGISTRAR is None:
        
        if get_registry():
            raise Exception("Cannot find RPyC NameServer, run larkNames or disable the firewall")

        registry = get_registry_parameters()

        registry_port = int(registry.RPYC_PORT)

        if registry.RPYC_MODE == "UDP":
            registrar = UDPRegistryClient(ip=registry.RPYC_IP, port=registry_port)
        elif registry.RPYC_MODE == "TCP":
            registrar = TCPRegistryClient(ip=registry.RPYC_IP, port=registry_port)
        registrar.REREGISTER_INTERVAL = 15
        get_registrar.REGISTRAR = registrar
    return get_registrar.REGISTRAR

get_registrar.REGISTRAR = None

# def check_name(rpyc_object, registrar):
#     name = new_name = rpyc_object.ALIASES[0]
#     addrs = registrar.discover(name)
#     if addrs == ():
#         return
#     cnt=1
#     while addrs != ():
#         new_name = name + f"({cnt})"
#         addrs = registrar.discover(new_name)
#         cnt+=1
#     rpyc_object.__class__.ALIASES = (new_name,)
#     rpyc_object.rpyc_name = new_name
#     print("Name already in use, new name given: ", new_name)

def check_duplicate(rpyc_object, registrar) -> None:
    name = rpyc_object.ALIASES[0]
    addrs = registrar.discover(name)
    if addrs == ():
        return
    else:
        for addr in addrs:
            unbindService(addr[1])
            print(f"Duplicate service {name}:{addr[1]} unbound")

def host_authenticator(sock):
    whitelist = ["10.0.2.15","10.45.45.22","134.171.72.129"]
    if sock.getpeername()[0] not in whitelist:
        raise AuthenticationError("Host not in whitelist")
    return sock, None

def password_authenticator(sock):
    passwd = get_registry_parameters().RPYC_PASSWD
    if sock.recv(len(passwd)) != passwd.encode():
        raise AuthenticationError(f"Wrong password {passwd}")
    return sock, None
    
AUTHENTICATOR = password_authenticator

def startServer(obj, name=None, block=False, start=True):

    if not issubclass(type(obj),rpyc.Service):
        if name is not None:
            rpyc_object = type(name+"Service",RemoteService,{})(name, obj)
            rpyc_object.wrapped = True
        else:
            raise Exception("Wrapped service needs a name")
    else:
        # if not hasattr(type(obj),"ALIASES"):
        #     raise AttributeError("Service must have class attribute ALIASES")
        name = obj.ALIASES[0]
        rpyc_object = obj

    registrar = get_registrar()

    check_duplicate(rpyc_object,registrar)

    this_port = RPYC_PORT
    server = None
    while server is None:
        try:
            server = ThreadedServer(rpyc_object, port=this_port, protocol_config={"allow_all_attrs":True, 'allow_pickle': True}, registrar=registrar, logger=logger, authenticator=AUTHENTICATOR)
        except OSError as e:
            if this_port > RPYC_PORT+100:
                raise Exception("Unable to connect or more than 100 services running")
            if e.errno == 48 or e.errno == 98:
                this_port += 1
            else:
                raise e

    rpyc_object.rpyc_port = this_port
    rpyc_object.rpyc_server = server

    # setup_logger(True,f"/dev/shm/rpyc_{name}.log")
    # setup_logger(True)

    if start and block:
        server.start()
    elif start and not block:
        rpyc_object.rpyc_thread = spawn_waitready(server._listen, server.start)[0]

    return rpyc_object

def unbindService(port):
    if port is not None:
        registrar = get_registrar()
        registrar.unregister(port)

class RemoteClient:
    def __init__(self, conn, wrapped=False):
        self.conn = conn
        self._wrapped = wrapped
        
    def ping(self):
        return self.conn.ping()

    def __getattr__(self, __name: str) -> Any:
        try:
            return self.conn.root.__getattribute__(__name)
        except AttributeError as e:
            if self._wrapped:
                return self.conn.root.obj.__getattribute__(__name)
            else:
                raise e

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name in ["conn","_wrapped","bg_thrd"]:
            return super().__setattr__(__name,__value)
        if not self._wrapped:
            return self.conn.root.__setattr__(__name,__value)
        else:
            if hasattr(self.conn.root, __name):
                return self.conn.root.__setattr__(__name,__value)
            return self.conn.root.obj.__setattr__(__name,__value)


def connect_magic(host,port,magic:str,config={}):
    from rpyc.core.stream import SocketStream
    from rpyc.core.service import VoidService
    from rpyc.utils.factory import connect_stream
    s = SocketStream.connect(host, port, ipv6=False, keepalive=False)
    s.sock.send(magic.encode())
    return connect_stream(s,VoidService,config)

def connectClient(name):

    registrar = get_registrar()
    addrs = registrar.discover(name)

    if addrs == ():
        # addrs = (("localhost",RPYC_PORT),)
        print("failed to connect to ",name)
        raise ConnectionError("No service available with this name")
    try:
        # print("connecting with", self.addrs)
        # conn = rpyc.connect(addrs[0][0],addrs[0][1],config={"allow_all_attrs":True, 'allow_pickle': True})# 'allow_pickle': True})
        conn = connect_magic(addrs[0][0],addrs[0][1],"lEt Me IN PlEAse",config={"allow_all_attrs":True, 'allow_pickle': True})
    except socket.gaierror as e:
        unbindService(addrs[0][1])
        raise ConnectionError("No service available with this name")
    except ConnectionRefusedError as e:
        if e.errno == 111:
            raise ConnectionRefusedError("Connection refused, is the service still running?") from e
        else:
            raise e
    if hasattr(conn.root,"wrapped"):
        if conn.root.wrapped:
            return RemoteClient(conn, wrapped=True)
    return RemoteClient(conn)

#### LARK NAMES ####

def newLarkNameServer(ip_addr:str, port:int, mode:str="UDP") -> Union[UDPRegistryServer,TCPRegistryServer]:
    if mode == "UDP":
        server = UDPRegistryServer(host=ip_addr, port=port, allow_listing=True, pruning_timeout=16, logger=logger)
    elif mode == "TCP":
        server = TCPRegistryServer(host=ip_addr, port=port, allow_listing=True, pruning_timeout=16, logger=logger)
    return server

def larkNameServer():
    parser = argparse.ArgumentParser(description='Start the RPyC registry server')

    # this_ip, this_port, this_mode =
    registry = get_registry_parameters()

    default_ip_port = f"{registry.RPYC_IP}:{registry.RPYC_PORT}"
    parser.add_argument("ip_port",default=default_ip_port,nargs='?',type=str,help="format = ip:port")
    parser.add_argument("-mode",dest="mode",default=registry.RPYC_MODE,type=str, help="UDP or TCP")
    parser.add_argument("-o",dest="output",action="store_true",help=f"Use to print output to command line, else prints to {LOG_DIR/'larkNames.log'}")

    args = parser.parse_args()

    ip = args.ip_port.split(':')[0]

    if len(ip.split('.')) != 4:
        if ip != 'localhost':
            print("ip is not valid")
            parser.print_help()
            exit(0)

    try:
        port = int(args.ip_port.split(':')[1])
    except ValueError as e:
        print("error with port, using default port")
        port = registry.RPYC_PORT
    except IndexError as e:
        print("error with port, using default port")
        port = registry.RPYC_PORT

    if args.mode != "UDP" and args.mode != "TCP":
        print("mode is not valid")
        parser.print_help()
        exit(0)

    logger = getLogger("rpyc.larkNames")
    log_to_stdout(logger=logger,level="DEBUG")
    try:
        server = newLarkNameServer(ip,port,args.mode)
    except OSError as e:
        if e.errno == 98:
            print("Address already in use. Is larkNames already running?")
            sys.exit(0)
        else:
            raise e

    # if not args.output:
    #     setup_logger(False,LOG_DIR/"larkNames.log")
    # else:
    #     setup_logger(False, None)
    date_now, time_now = get_datetime_stamp(split=True)
    if USESYSTEMD: systemd.daemon.notify('READY=1')
    logger.info(f"Starting new larkNames at {time_now} on {date_now} :-")
    server.start()
