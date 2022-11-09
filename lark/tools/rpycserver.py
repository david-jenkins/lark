


"""

A somewhat complex but fully working RPyC example.

It contains server and client code, the rpycclient.py scirpt connects to the service started here

"""

import threading
import socket
from typing import Any, Union

#rpyc imports
import rpyc
from rpyc.utils.registry import UDPRegistryServer, TCPRegistryServer, UDPRegistryClient, TCPRegistryClient
from rpyc.utils.server import ThreadedServer
from rpyc.lib import setup_logger, spawn_waitready, spawn

# the module rpycbrine adds some extra types to the rpyc serialiser, mostly numpy types
# the copydict type is a wrapper to make a dictionary copy on passing, rather than a proxy which is the default
from rpycbrine import copydict

# nameserver IP and port
NS_IP = "127.0.0.1"
NS_PORT = 18512
# starting port for services
RPYC_PORT = 18561


def newNameServer(ip_addr:str, port:int, mode:str="UDP") -> Union[UDPRegistryServer,TCPRegistryServer]:
    """RPyC has the concept of a name server (or RegistryServer), this stores ip and port information of a service which can be recalled by name

    Args:
        ip_addr (str): The namerserver ip
        port (int): THe nameserver port
        mode (str, optional): The namerserver mode. Defaults to "UDP".

    Returns:
        Union[UDPRegistryServer,TCPRegistryServer]: The RPyC nameserver object
    """
    if mode == "UDP":
        server = UDPRegistryServer(host=ip_addr, port=port, allow_listing=True, pruning_timeout=16)
    elif mode == "TCP":
        server = TCPRegistryServer(host=ip_addr, port=port, allow_listing=True, pruning_timeout=16)
    return server

def newRegistrar(ip_addr:str, port:int, mode:str="UDP") -> Union[UDPRegistryClient,TCPRegistryClient]:
    """The easiest way to connect to a nameserver is with a registrar (or RegistryClient) which needs to be passed the ip and port of the nameserver    

    Args:
        ip_addr (str): The nameserver IP
        port (int): The nameserver port
        mode (str, optional): The namerserver mode. Defaults to "UDP".

    Returns:
        Union[UDPRegistryClient,TCPRegistryClient]: The registrar object
    """
    if mode == "UDP":
        registrar = UDPRegistryClient(ip=ip_addr, port=port)
    elif mode == "TCP":
        registrar = TCPRegistryClient(ip=ip_addr, port=port)
    registrar.REREGISTER_INTERVAL = 15
    return registrar


    
def startServer(obj, name=None, block=False, start=True):
    """A helper function to start a server for a given service object

    Args:
        obj (_type_): a rpyc service object
        name (_type_, optional): The name of the object, not actually used here.... Defaults to None.
        block (bool, optional): If the server should start and block. Defaults to False.
        start (bool, optional): If the server should start. Defaults to True.

    Raises:
        Exception: it tries to assign a new port to each service but if it tries >100 times it fails
        e: This error tells us the chosen port is in use

    Returns:
        _type_: The same object supplied but with two new variables, rpyc_port and rpyc_server, with the server started if start is True
    """
    registrar = newRegistrar(NS_IP, NS_PORT)
    
    this_port = RPYC_PORT
    server = None
    while server is None:
        try:
            server = ThreadedServer(obj, port=this_port, protocol_config={"allow_all_attrs":True, 'allow_pickle': True}, registrar=registrar)
        except OSError as e:
            if this_port > RPYC_PORT+100:
                raise Exception("Unable to connect or more than 100 services running")
            if e.errno == 48 or e.errno == 98:
                this_port += 1
            else:
                raise e

    obj.rpyc_port = this_port
    obj.rpyc_server = server

    if start and block:
        server.start()
    elif start and not block:
        obj.rpyc_thread = spawn_waitready(server._listen, server.start)[0]

    return obj
    
def unbindService(port:int):
    """Removes a service from the nameserver with a given port

    Args:
        port (int): The service port number
    """
    if port is not None:
        registrar = newRegistrar(NS_IP, NS_PORT)
        registrar.unregister(port)
        
class RemoteClient:
    """A helper class for a client.
    In RPyC when you connect to a service you get a conn object and then this has root object.
    The root object is the actual service and so this abstracts some of this away so the return value
    of the connectClient functions returns this object that can be used to call service functions.
    """
    def __init__(self, conn):
        self.conn = conn
        self.bg_thrd = None

    def ping(self):
        return self.conn.ping()

    def __getattr__(self, __name: str) -> Any:
        return self.conn.root.__getattribute__(__name)

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name in ["conn","bg_thrd"]:
            return super().__setattr__(__name,__value)
        return self.conn.root.__setattr__(__name,__value)
    
def connectClient(name):
    """A helper function to connect a client to a service

    Args:
        name (str): The name of the service to connect to

    Raises:
        ConnectionError: No service with given name in namerserver
        ConnectionError: No service with given name
        ConnectionRefusedError: An error connecting, perhaps the service died
        e: General error in the connection

    Returns:
        RemoteClient: An instance of RemoteClient above wrapping a connection
    """
    registrar = newRegistrar(NS_IP, NS_PORT)
    addrs = registrar.discover(name)

    if addrs == ():
        # addrs = (("localhost",RPYC_PORT),)
        print("failed to connect to ",name)
        raise ConnectionError("No service available with this name")
    try:
        # print("connecting with", self.addrs)
        conn = rpyc.connect(addrs[0][0],addrs[0][1],config={"allow_all_attrs":True, 'allow_pickle': True})# 'allow_pickle': True})
        # conn = connect_magic(addrs[0][0],addrs[0][1],"lEt Me IN PlEAse",config={"allow_all_attrs":True, 'allow_pickle': True})
    except socket.gaierror as e:
        unbindService(addrs[0][1])
        raise ConnectionError("No service available with this name")
    except ConnectionRefusedError as e:
        if e.errno == 111:
            raise ConnectionRefusedError("Connection refused, is the service still running?") from e
        else:
            raise e
    return RemoteClient(conn)

class ThisServer:
    """The general server class, this can store state, accept function calls and generally run the logic
    """
    def __init__(self):
        self.params = {}
    
    def set(self, name, value):
        print(f"setting {name} to {value}")
        self.params[name] = value
    
    def get(self, name):
        print(f"getting name {name}")
        return self.params[name]
        
    def print(self):
        print(self.params)

def startService(name, block=True):
    """A helper to start a ThisServer service and server

    Args:
        name (str): The name of the service
        block (bool, optional): Whether the server blocks. Defaults to True.

    Returns:
        _type_: _description_
    """
    class RemoteControl(ThisServer, rpyc.Service):
        def __init__(self,name):
            RemoteControl.ALIASES = (name,)
            rpyc.Service.__init__(self)
            ThisServer.__init__(self)
    return startServer(RemoteControl(name), block=block)

if __name__ == "__main__":
    
    # create new name server
    # the nameserver would usually be always running in the background and doesn't need to be started every time
    # here we start one for this example only
    nameserv = newNameServer(NS_IP, NS_PORT)
    # start nameserver in a new thread
    servthr = threading.Thread(target=nameserv.start)
    servthr.start()
    
    # start a service and server and start it, don't block
    service = startService("This Service", block=False)
    
    # accept CLI commands, exit and quit stops the server, print shows the params
    while True:
        cmd = input("Enter command:\n")
        if cmd in ("exit", "quit"):
            break
        elif cmd == "print":
            service.print()
    
    # stop the rpyc server for the service
    service.rpyc_server.close()
    # stop the nameserver
    nameserv.close()