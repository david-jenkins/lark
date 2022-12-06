"""This defines and registers functions for the SRTC systemd
"""

import os
import select
import socket
from lark.iportSerial import sendCmd, coolCamera
import numpy

from lark import LarkConfig
from lark.services import BaseService, BasePlugin

class iPortService(BaseService):
    PLUGINS = {}
    RESULTS = {}
    INITIALISED = {}
    def notify(self, *args):
        print(*args)

@iPortService.register_plugin("iPortDaemon")
class iPortDaemon(BasePlugin):
    """The iPortDaemon function"""
    def Init(self):
        self.defaults = {
            "prefix":"LgsWf",
            "localip":"169.254.24.100",
            "iportip":"169.254.24.101"
            }
        self.begin_on_start = True
        self.period = 1
        self.pipe = None

    def Setup(self):
        self.lark = LarkConfig(self["prefix"]).getlark()
        if self.pipe is not None:
            try:
                os.close(self.pipe[0])
                os.close(self.pipe[1])
            except Exception as e:
                print(e)
        self.pipe = os.pipe()

    def _thread_func(self, _apply, **kwargs):
        self.Setup()
        cam = 0
        ip = self["localip"]
        ipiport = self["iportip"]
        sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.bind((ip,0))
        sock.settimeout(self.period)
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
            r,w,x = select.select([sock,self.pipe[0]],[],[])
            if sock in r:
                data, addr = sock.recvfrom(2048)
            else:
                continue
            print(f"Got data {str(data)} from {str(addr)}")
            print(vhex(numpy.fromstring(data,dtype=numpy.uint8)))
            print(data[28:])
            print(addr[0],addr[1])
            if addr[0]==ipiport and addr[1]==4:
                print("Sending response")
                data = numpy.fromstring(data,dtype=numpy.uint8)
                packet = numpy.zeros((8,),numpy.uint8)
                packet[3] = 0xc3
                packet[6:8] = data[6:8]
                sock.sendto(packet,(ipiport,4))
                print(f"Sent response: {packet}")
                print(vhex(packet))

    def Configure(self, prefix:str = None, localip:str = None, iportip:str = None):
        kwargs = {key:value for key,value in locals().items() if key not in ["__class__","self"] and value is not None}
        return super().Configure(**kwargs)

    def stop(self):
        os.write(self.pipe[1],b"exit")
        return super().stop()

@iPortService.register_plugin("iPortSerial")
class iPortSerial(BasePlugin):
    """The iPortSerial function"""
    def Init(self):
        self.defaults = {
            "prefix":"LgsWF",
            "command": "",
            "cam":0
        }
        self.begin_on_start = False

    def Configure(self, command:str = None, prefix:str = None, cam:int = None):
        kwargs = {key:value for key,value in locals().items() if key not in ["__class__","self"] and value is not None}
        return super().Configure(**kwargs)

    def Execute(self):
        print(f"Running iPort serial prefix: {self['prefix']}, cmd: {self['command']}")
        cmd = self['command'].split(" ")
        if cmd[0] == "cool":
            coolCamera(cmd[1],self["prefix"],cam=self["cam"])
        else:
            sendCmd(self["command"],self["prefix"],cam=self["cam"])