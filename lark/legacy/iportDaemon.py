#!/usr/bin/python
"""A daemon that sits and listens to data from the iport, generated as a response to serial cameralink commands.


Messages to/from iport:
In order to send commands to the camera over cameralink serial, these
commands are sent to the ocam.

So, iportSerial.py sets aravisMem to something.

It then appears that the iport sends a command by UDP to a port given
in register 0xb00.

The iport sdk then responds to this.

See /root/wiresharkocam* on darc for captures.

Ok, so, what I need is a little daemon.  What this does is:
Opens a listening port (for UDP packets).
Sends: 

0x420000800004000100000a00 to port 4 on the ocam.
Sets register 0xb00 to the port number that is listening on.
Sets reg 0xb10 to the host IP. eg 0xc0a80101
Reg 0xb14 to 0x190  (transmission timeout in ms)
REg 0xb18 to 0x3 (number of retransmissions allowed)
Then, whenever it receives a 36 byte UDP data packet from port 4 of
ocam, takes byte 8 (or maybe bytes 7 and 8...) and then replies with a
udp packet to port 4 that says:
0x000000c30000XXXX  where XXXX is bytes 7 and 8.


"""
import sys
import numpy
import socket
import darc
from functools import partial
import builtins

print = partial(builtins.print,flush=True)

def runDaemon(ip="169.254.24.100", ipiport="169.254.24.101", prefix="main", cam=4):
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.bind((ip,0))
    port=sock.getsockname()[1]
    print("Bound on port %d.  Sending initial data"%port)
    initdata=numpy.array([0x42,0x00,0x00,0x80,0x00,0x04,0x00,0x01,0x00,0x00,0x0a,0x00]).astype(numpy.uint8)
    sock.sendto(initdata,(ipiport,4))
    d=darc.Control(prefix)
    ipdata=numpy.zeros((4,),numpy.uint8)
    ipdata[:]=list(map(int,ip.split(".")))
    ipstr=hex(ipdata.view(numpy.uint32).byteswap()[0])
    if ipstr[-1]=="L":
        ipstr=ipstr[:-1]
    d.Set("aravisCmd%d"%cam,"R[0xb14]=0x190;R[0xb18]=0x3;R[0xb10]=%s;R[0xb00]=%d;R[0x20017800]=0x0;R[0x20017814]=0x6;R[0x2001781c]=0x0;R[0x20017818]=0x0;R[0x20017830]=0x0;R[0x16000]=0x1;"%(ipstr,port))
    vhex=numpy.vectorize(hex)
    while 1:
        data,addr=sock.recvfrom(1024)
        print("Got data %s from %s"%(str(data),str(addr)))
        print(vhex(numpy.fromstring(data,dtype=numpy.uint8)))
        print(data[28:])
        if addr[0]==ipiport and addr[1]==4:
            data=numpy.fromstring(data,dtype=numpy.uint8)
            packet=numpy.zeros((8,),numpy.uint8)
            packet[3]=0xc3
            packet[6:8]=data[6:8]
            sock.sendto(packet,(ipiport,4))
            print("Sent response:",packet)
            print(vhex(packet))

def main():
    prefix="main"
    if len(sys.argv)>1:
        prefix=sys.argv[1]
    if prefix=="ocam" or prefix=="canapy":
        cam=0
    else:
        cam=4
    runDaemon(prefix=prefix,cam=cam)

if __name__=="__main__":
    main()
