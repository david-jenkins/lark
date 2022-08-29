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

import os
import sys
import numpy
import traceback
import controlVirtual
from controlVirtual import parseStatusBuf, statusBuf_tostring
import rpyc
from rpyc.utils.server import ThreadedServer
from rpyc.lib import spawn_waitready
from rpyc.lib import setup_logger
from rpyc.utils.registry import TCPRegistryClient, UDPRegistryClient
from rpycNames import get_default_registry_parameters
import socket

RPYC_PORT = 18861

class Encoder:
    def encode(self,val,typ=None):
        if isinstance(val, (numpy.ndarray,numpy.memmap)):
            data = ("rpyc_ndarray",val.shape,str(val.dtype),val.tobytes())
        elif isinstance(val, (numpy.int32,numpy.int64,numpy.float32,numpy.float64)):
            data = ("rpyc_ndvalue",str(val.dtype),val.tobytes())
        elif isinstance(val, list):
            data = ("rpyc_list",*(self.encode(item) for item in val))
        elif isinstance(val, tuple):
            data = tuple(self.encode(item) for item in val)
        elif isinstance(val,(int,bool,float,str,bytes,complex)):
            data = val
        elif val is None:
            data = None
        else:
            raise Exception(f"data type:{type(val)} not yet convertable, add encoder")
        return data

    def decode(self,val,typ=None):
        if isinstance(val, tuple):
            if val[0] == "rpyc_ndarray":
                data = numpy.frombuffer(val[3],dtype=numpy.dtype(val[2]))
                data.shape = val[1]
            elif val[0] == "rpyc_ndvalue":
                data = numpy.frombuffer(val[2],dtype=numpy.dtype(val[1]))[0]
            elif val[0] == "rpyc_list":
                data = [self.decode(item) for item in val[1:]]
            else:
                data = tuple(self.decode(item) for item in val)
        elif isinstance(val,(int,bool,float,str,bytes,complex)):
            data = val
        elif val is None:
            data = None
        else:
            raise Exception(f"data type:{type(val)} not yet convertable, add decoder")
        return data

class ControlServer(Encoder,controlVirtual.ControlServer,rpyc.Service):
    def __init__(self,c=None,l=None,controlName="Control"):
        """c is the instance of the control object
        l is a lock that should be obtained before calling an operation.
        """
        #Pyro.core.ObjBase.__init__(self)
        rpyc.Service.__init__(self)
        controlVirtual.ControlServer.__init__(self,c,l)
        ControlServer.ALIASES = (controlName,)
        self.close = None

    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        pass

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        pass


class Control(Encoder,controlVirtual.Control):
    def __init__(self,prefix="",debug=0,orb=None):
        self.prefix=prefix
        controlVirtual.Control.__init__(self,self.prefix)
        self.debug=debug
        self.orb=orb
        self.obj=None
        self.conn=None
        self.newconn=None
        self.printcnt=0
        self.printat=1
        self.connect()#controlName)

    # def __getattribute__(self,*args,**kwargs):
    #     print(*args,**kwargs)
    #     return super().__getattribute__(*args,**kwargs)

    def connect(self):
        if self.debug:
            print("Attempting to connect to rtc RPyC")
        self.obj=None

        registry_ip, registry_port, registry_mode = get_default_registry_parameters()

        registry_port = int(registry_port)
        # print("attempting to connect to registry at: {}:{}".format(registry_ip,registry_port))
        if find_registry(registry_ip,registry_port,registry_mode):
            return None

        if registry_mode == "UDP":
            registrar = UDPRegistryClient(ip=registry_ip, port=registry_port)
        elif registry_mode == "TCP":
            registrar = TCPRegistryClient(ip=registry_ip, port=registry_port)

        self.addrs  = registrar.discover(self.prefix+"Control")
        if self.addrs == ():
            self.addrs = (("localhost",RPYC_PORT))
        try:
            # print("connecting with", self.addrs)
            self.conn = rpyc.connect(self.addrs[0][0],self.addrs[0][1])
        except socket.gaierror as e:
            print("No DARC available with this prefix")
            return 1
        except ConnectionRefusedError as e:
            if e.errno == 111:
                print("Connection refused, is DARC still running?")
                return 1
            else:
                raise e
        self.obj = self.conn.root
        # self.bgsrv = rpyc.BgServingThread(self.conn)
        if self.obj is None:
            if self.debug:
                print("Object reference not connected")
        else:
            if self.debug:
                print("Connected to rtc RPyC",self.obj)
            # Invoke the echoString operation
            message = "Hello from Python"
            try:
                result = self.obj.echoString(message)
            except Exception as e:
                result="nothing (failed)"
                traceback.print_exc()
                print("EchoString failed - continuing but not connected")
                self.obj=None
            if self.debug:
                print("I said '%s'. The object said '%s'." % (message,result))
        return self.obj!=None

    def WatchParam(self,tag,paramList,timeout=-1):
        """Because WatchParam blocks, this has been reimplemented for the RPyC backend
        a new conenction is made that allows the previous connection to function as normal"""
        plist=self.encode(paramList,[str])

        self.newconn = rpyc.connect(self.addrs[0][0],self.addrs[0][1])
        watcher = rpyc.async_(self.newconn.root.WatchParam)
        result = watcher(tag,plist,float(timeout))
        '''this now blocks on this connection'''
        changed = result.value
        self.newconn.close()

        changed = self.decode(changed)
        tag=changed.pop(0)
        return tag,changed

def find_registry(registry_ip, registry_port, registry_mode):
    name = ("isalive",)
    port = 18860
    try:
        if registry_mode == "UDP":
            registrar = rpyc.utils.registry.UDPRegistryClient(ip=registry_ip,port=registry_port)
        elif registry_mode == "TCP":
            registrar = rpyc.utils.registry.TCPRegistryClient(ip=registry_ip,port=registry_port)
        if registrar.register(name,port):
            registrar.unregister(port)
            return 0
        else:
            print("Unable to register with the RPYC name server")
            return 1
    except ConnectionRefusedError as e:
        if e.errno == 61:
            print("No registry server found")
            return 1
        else:
            raise e
    except OSError as e:
        if e.errno == 49:
            print("Broadcasting not allowed")
            return 1
        else:
            raise e

# def find_registry(registry_ip,registry_port):
#     "first try UDP broadcast, then direct UDP, then finally direct TCP"
#     name = ("isalive",)
#     port = 18860
#     try:
#         registrar = rpyc.utils.registry.UDPRegistryClient(port=registry_port)
#         if registrar.register(name,port):
#             registrar.unregister(port)
#             return "255.255.255.255",registry_port,"UDP"
#         else:
#             print(registrar.discover("isalive"))
#     except ConnectionRefusedError as e:
#         if e.errno == 61:
#             print("No registry server found, trying next connection")
#         else:
#             raise e
#     except OSError as e:
#         if e.errno == 49:
#             print("Broadcasting not allowed")
#         else:
#             raise e
#     try:
#         registrar = rpyc.utils.registry.UDPRegistryClient(ip=registry_ip,port=registry_port)
#         if registrar.register(name,port):
#             registrar.unregister(port)
#             return registry_ip,registry_port,"UDP"
#         else:
#             print(registrar.discover("isalive"))
#     except ConnectionRefusedError as e:
#         if e.errno == 61:
#             print("No registry server found, trying next connection")
#         else:
#             raise e
#     try:
#         registrar = rpyc.utils.registry.TCPRegistryClient(ip=registry_ip,port=registry_port)
#         if registrar.register(name,port):
#             registrar.unregister(port)
#             return registry_ip,registry_port,"TCP"
#         else:
#             print(registrar.discover("isalive"))
#     except ConnectionRefusedError as e:
#         if e.errno == 61:
#             print("No registry server found")
#             return None,None,None,None
#         else:
#             raise e

def initialiseServer(c=None,l=None,block=0,controlName="Control"):
    """c is the control object
    l is a threading.Lock object (or soemthing with acquire and release methods
    block is whether to block here, or return.
    """

    # Create an instance of Control_i and a Control object reference
    registry_ip, registry_port, registry_mode = get_default_registry_parameters()

    registry_port = int(registry_port)
    print("attempting to connect to registry at: {}:{}".format(registry_ip,registry_port))
    if find_registry(registry_ip,registry_port,registry_mode):
        print("Cannot find RPyC NameServer, run darcNames or disable the firewall")
        return None

    ei = ControlServer(c,l,controlName)
    aliases = ei.get_service_aliases()

    if registry_mode == "UDP":
        registrar = UDPRegistryClient(ip=registry_ip, port=registry_port)
    elif registry_mode == "TCP":
        registrar = TCPRegistryClient(ip=registry_ip, port=registry_port)

    this_port = RPYC_PORT
    t = None
    while t is None:
        try:
            t = ThreadedServer(ei, port=this_port, protocol_config={"allow_public_attrs":True, 'allow_pickle': True},registrar=registrar)
        except OSError as e:
            if this_port > RPYC_PORT+10:
                print("Unable to connect or more than 10 darcs running")
                return None
            if e.errno == 48 or e.errno == 98:
                this_port += 1
            else:
                print("Error occured: ",e)
                return None
        except Exception as e:
            print("got this exception here!")
            print(e)

    ei.rpyc_port = this_port
    ei.server = t

    if block:
        # Block for ever (or until the ORB is shut down)
        # setup_logger(None, None)
        t.start()
    else:
        # setup_logger(None,None)
        spawn_waitready(t._listen, t.start)[0]
    return ei

def unbind(ei=None,controlName="Control"):
    registry_ip, registry_port, registry_mode = get_default_registry_parameters()

    registry_port = int(registry_port)

    if registry_mode == "UDP":
        registrar = UDPRegistryClient(ip=registry_ip, port=registry_port)
    elif registry_mode == "TCP":
        registrar = TCPRegistryClient(ip=registry_ip, port=registry_port)

    registrar.unregister(ei.rpyc_port)

if __name__=="__main__":
    controlName="Control"
    for arg in sys.argv[1:]:
        if arg[:2]=="-s":#shmname
            controlName=arg[2:]+controlName

    initialiseServer(block=1,controlName=controlName)
