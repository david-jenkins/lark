

#!/usr/bin/env python3

import time

from .rpyclib.interface import (RemoteService, 
                            get_registry_parameters, 
                            remoteprint, 
                            connectClient,
                            startServer, 
                            larkNameServer, 
                            get_registrar,
                            asyncfunc,
                            logger,
                            decode)
from .rpyclib.rpyc_brine import copydict

def connectDaemon(hostname:str = None):
    """Connect to a running daemon

    Args:
        hostname (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    if hostname is None:
        hostname = get_registry_parameters().RPYC_HOSTNAME
    logger.info(f"Connecting to host: {hostname}")
    return connectClient(hostname+"_Daemon")

def stopDaemon(hostname:str = None):
    """Stop a running daemon

    Args:
        hostname (_type_, optional): _description_. Defaults to None.
    """
    try:
        h = connectDaemon(hostname)
    except ConnectionError as e:
        print(e)
    else:
        h.unblock()

def startServiceClient(service_class, name, *, hostname=None, params=None):
    """_summary_

    Args:
        service_class (_type_): _description_
        name (_type_): _description_
        hostname (_type_, optional): _description_. Defaults to None.
        params (_type_, optional): _description_. Defaults to None.

    Raises:
        ConnectionRefusedError: _description_

    Returns:
        _type_: _description_
    """
    from .interface import connectClient
    h = connectDaemon(hostname)
    # service_class_pckl = pickle.dumps(service_class)
    service_class_pckl = service_class
    retval = h.startservice(service_class_pckl,name)
    cnt = 10
    err = Exception()
    while cnt:
        try:
            s = connectClient(name)
        except ConnectionRefusedError as e:
            print("waiting...")
            time.sleep(0.5)
            err=e
            cnt-=1
        except ConnectionError as e:
            print("waiting")
            time.sleep(0.5)
            err=e
            cnt-=1
        else:
            break
    if cnt == 0:
        raise ConnectionRefusedError() from err
    if params is not None:
        s.configure(params)
    return s

def startControl(prefix,*,hostname=None,options={},params=None,block=False):
    from .control import Control
    class RemoteControl(Control,RemoteService):
        def __init__(self,prefix,params,hostname,options):
            RemoteControl.ALIASES = (prefix+"Control",)
            RemoteService.__init__(self,prefix+"Control",hostname=hostname)
            Control.__init__(self,prefix,options=options,hostname=hostname,params=params)

        def stop(self):
            Control.stop(self)
            self.remote_close()    
    return startServer(RemoteControl(prefix,params,hostname,options),block=block)

def startService(service_class, name, hostname=None, block=False):
    class RemoteServiceClass(RemoteService, service_class):
        def __init__(self,name):
            RemoteServiceClass.ALIASES = (name,)
            RemoteService.__init__(self,name,hostname=hostname)
            service_class.__init__(self,name)

        def status(self):
            return "If you get this, service is running"

        def stop(self,*args,**kwargs):
            service_class.stop(self)
            self.remote_close()

    return startServer(RemoteServiceClass(name),block=block)

def startControlClient(prefix,*,hostname=None,params=None):
    h = connectDaemon(hostname)
    h.startlark(prefix)
    cnt = 10
    err = Exception()
    while cnt:
        try:
            c = ControlClient(prefix)
        except ConnectionRefusedError as e:
            print("waiting...")
            time.sleep(0.5)
            err=e
            cnt-=1
        except ConnectionError as e:
            print("waiting")
            time.sleep(0.5)
            err=e
            cnt-=1
        else:
            c.control.print_to(print)
            break
    if cnt == 0:
        raise ConnectionRefusedError() from err
    if params is not None:
        c.configure_from_dict(copydict(params))
    return c

class ControlClient:
    def __init__(self, prefix):
        control = connectClient(prefix+"Control")
        self.control = control.conn.root
        self.conn = control.conn

    def __getattr__(self, name):
        return getattr(self.control,name)

    def __getitem__(self, name):
        return self.control.__getitem__(name)

    def __setitem__(self, name, value):
        return self.control.__setitem__(name, value)
        
    def __iter__(self):
        return self.control.__iter__()

    # def startService(self,service_class_pckl,*args,**kwargs):
    #     self.control.startService(service_class_pckl,*args,**kwargs)

# class ServiceClient(Encoder):
#     def __init__(self, name):
#         control = connectClient(name)
#         self.control = control.conn.root
#         self.conn = control.conn
#         for key in self.control.getPlugin():
#             setattr(self,key,self.encoder(getattr(self.control,"remote_"+key)))
