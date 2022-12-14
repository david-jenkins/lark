

"""This defines and registers functions for the SRTC systemd,
this file will sent as text to the daemon so it should be kept as small as possible
"""

import socket
import time
import numpy

from lark import LarkConfig, NoLarkError
from lark.services import BaseService, BasePlugin

class iPortService(BaseService):
    PLUGINS = {}
    def notify(self, *args):
        print(*args)

@iPortService.register_plugin("iPortDaemon")
class iPortDaemon(BasePlugin):
    """The iPortDaemon function"""
    parameters = ("prefix", "localip", "iportip")
    prefix = "LgsWF"
    localip = "169.254.24.100"
    iportip = "169.254.24.101"

    def Init(self):
        self.auto_start = True
        self.loop_period = 1
        
    def Setup(self):
        try:
            self.lark = LarkConfig(self["prefix"]).getlark()
        except NoLarkError as e:
            print(e)
            self.lark = None
        
    def _thread_func(self, _apply, **kwargs):
        cnt = 0
        while self._go:
            print(f"Iter number {cnt}\nAnd this is the second line\nplus also a third\nfourth\nanf fin!")
            cnt+=1
            time.sleep(self.loop_period)
        return
        cam = 0
        ip = self["localip"]
        ipiport = self["iportip"]
        sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.bind((ip,0))
        port = sock.getsockname()[1]
        print(f"Bound on port {port}.  Sending initial data")
        initdata = numpy.array([0x42,0x00,0x00,0x80,0x00,0x04,0x00,0x01,0x00,0x00,0x0a,0x00]).astype(numpy.uint8)
        sock.sendto(initdata,(ipiport,4))
        ipdata = numpy.zeros((4,),numpy.uint8)
        ipdata[:] = list(map(int,ip.split(".")))
        ipstr = hex(ipdata.view(numpy.uint32).byteswap()[0])
        if ipstr[-1]=="L":
            ipstr = ipstr[:-1]
        self.lark.set("aravisCmd%d"%cam,"R[0xb14]=0x190;R[0xb18]=0x3;R[0xb10]=%s;R[0xb00]=%d;R[0x20017800]=0x0;R[0x20017814]=0x6;R[0x2001781c]=0x0;R[0x20017818]=0x0;R[0x20017830]=0x0;R[0x16000]=0x1;"%(ipstr,port))
        vhex = numpy.vectorize(hex)
        while self.go:
            data, addr = sock.recvfrom(1024)
            print(f"Got data {str(data)} from {str(addr)}")
            print(vhex(numpy.fromstring(data,dtype=numpy.uint8)))
            print(data[28:])
            if addr[0]==ipiport and addr[1]==4:
                data = numpy.fromstring(data,dtype=numpy.uint8)
                packet = numpy.zeros((8,),numpy.uint8)
                packet[3] = 0xc3
                packet[6:8] = data[6:8]
                sock.sendto(packet,(ipiport,4))
                print(f"Sent response: {packet}")
                print(vhex(packet))

    def Execute(self):
        print(f"Running the iPort Daemon with options {self['localip']}, {self['iportip']}, {self['prefix']},{0}")

@iPortService.register_plugin("iPortSerial")
class iPortSerial(BasePlugin):
    """The iPortSerial function"""
    parameters = ("prefix", "iPortCommand", "cam")
    # defaults
    prefix:str = "LgsWF"
    iPortCommand:str = ""
    cam:int = 0

    def Execute(self):
        print(f"Running iPort serial prefix: {self['prefix']}, cmd: {self['iPortCommand']}")

if __name__ == "__main__":
    ips = iPortService("iPortService")
    
    x = ips.getPlugin("iPortSerial")
    
    print(x.Types)
    print(x.run())
