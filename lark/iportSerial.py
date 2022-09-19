#!/usr/bin/python
"""Sends a serial command via darc..."""

import sys
import os
import string
import time
import numpy
import lark

def sendCmd(cmd,prefix="",cam=0):
    """Sends a cameralink serial command through an iport device, using the darc interface.  Packet format is:
    4 bytes 0
    4 bytes for number of characters following
    The characters
    Padding up to 4 bytes"""
    print(f"{cmd} (cam {cam})")
    d = lark.LarkConfig(prefix).getlark()
    if cmd[-2:]!="\r\n":
        cmd = cmd + "\r\n"
    l = len(cmd)
    a = numpy.zeros((4+(l+3)//4,),numpy.uint32)
    a[0] = cam
    a[1] = 0x40058000 #the address
    a[2] = 0
    a[3] = l
    a[3] = a[3].byteswap()
    cmd += "\0"*((4-l%4)%4)
    a[4:] = numpy.frombuffer(cmd.encode(),dtype=numpy.uint32)
    for i in a:
        print(hex(i))
    d.set("aravisMem", a.view(numpy.int32))

    #Now, I think the message has to and with 0x093e02 (byteswapped), and has to be preceeded by 0x09  (and maybe some extra zeros as well).
    #So, work backwards from the end of the message...
    #Msg always ends with \n, so, the last 4 bytes can be assigned.
    #a[-1]=0x023e090a
    #cmd=cmd[:-1]#strip off the "\n" (0x0a).
    #b=numpy.fromstring(cmd,dtype=numpy.uint8)
    #pad=(4-(len(cmd)+1)%4)%4
    #padarr=numpy.fromstring("\0"*pad+chr(9),dtype=numpy.uint8)
    #c=numpy.concatenate([padarr,b]).view(numpy.uint32)
    #a[-1-c.size:-1]=c
    #for i in a:
    #    print hex(i)
    #d.Set("aravisMem",a.view(numpy.int32))


txt="""Selection of available commands:
cooling 20
fps 5         00 00 00 00 00 00 00 07 66 70 73 20 35 0d 0a 00
fps 50        00 00 00 00 00 00 00 08 66 70 73 20 35 30 0d 0a
fps 500       00 00 00 00 00 00 00 09 66 70 73 20 35 30 30 0d 0a 35 37 02
fps 1000
gain 1        00 00 00 00 00 00 00 08 67 61 69 6e 20 31 0d 0a
gain 10
gain 100
gain 1000
vss 0    - new NIMO clocking.  Note, gain must be set to 1 first.
vss 2500 - old IMO clocking.  Note, gain must be set to 1 first.
test on       00 00 00 00 00 00 00 09 74 65 73 74 20 6f 6e 0d 0a 45 9c 03
test off      00 00 00 00 00 00 00 0a 74 65 73 74 20 6f 66 66 0d 0a 14 04
led on
led off
cooling reset   00 00 00 00 00 00 00 0f 63 6f 6f 6c 69 6e 67 20 72 65 73 65 74 0d 0a 00
cooling -60
cooling 1    00 00 00 00 00 00 00 0b 63 6f 6f 6c 69 6e 67 20 31 0d 0a 03
cooling 20   00 00 00 00 00 00 00 0c 63 6f 6f 6c 69 6e 67 20 32 20 0d 0a
cooling on   00 00 00 00 00 00 00 0c 63 6f 6f 6c 69 6e 67 20 6f 6e 0d 0a
cooling off (don't use unless previously done a cooling 20 and waited)
             00 00 00 00 00 00 00 0d 63 6f 6f 6c 69 6e 67 20 6f 66 66 0d 0a 00 00 00
bias on
bias off
flat on
flat off
protection reset    - must be used at startup to enable gain.
shutter on
shutter off
shutter internal
shutter external
shutter single
shutter burst
shutter sweep 0  (or 1 or 2)  - 0 is off, 1 is continuous, 2 is continuous started by an external trigger.
shutter pulse #ns  (set duration of shutter opening in ns - with an increment of 9.21 ns)
shutter blanking #ns (duration of blanking between 2 pulses in ns - increments of 9.21ns)
shutter position #ns (delay between frame trigger and first pulse - in 9.21ns increments).
shutter step #ns (delay in ns added to each frame shutter starting position when on sweep mode).  
shutter end #ns (time limit in ns that will reset the sweep)
shutter count #n Number of sequential pulses to fire in burst mode.

synchro on   switch to externally triggered mode (frame rate).  Low value 
             triggers a frame transfer and readout (so if it remains low, 
             will operate at 1.5kHz).
synchro off  switch back to internal triggering.

--prefix=WHATEVER
--cam=DARC CAM NUMBER


Or:
setup LaserFreq ShutterOpenTime(us) ShutterDelay(us - 666 to avoid readout+extra optionally to delay for LGS height) CameraFrameRate --prefix=main --cam=2

or:
shutter off --prefix=main --cam=2

or:
cool -45 --prefix=main --cam=2

(note, use cool 20 and wait for a bit before doing cooling off, or powering off).

or:
gui  (to run the gui)

"""

def prepareShutter(laserfreq, exptime, delay, frate, on=1, prefix="", cam=0):
    """Sets up parameters for laser freq, 
    with exposure time exptime (in us) 
    and camera frame rate frate, 
    and delay from start of frame transfer of delay (in us).
    """
    period = (1./laserfreq)*1e9
    frameperiod = (1./frate)*1e9
    sendCmd("shutter off", prefix, cam)
    time.sleep(0.5)
    sendCmd("shutter internal", prefix, cam)
    time.sleep(0.5)
    sendCmd("shutter burst", prefix, cam)
    time.sleep(0.5)
    sendCmd("shutter pulse %d"%int(exptime*1000), prefix, cam)
    time.sleep(0.5)
    bl=int(period-int(exptime*1000))
    sendCmd("shutter blanking %d"%bl, prefix, cam)
    time.sleep(0.5)
    sendCmd("shutter position %d"%int(delay*1000), prefix, cam)
    time.sleep(0.5)
    n=int(frameperiod-int(delay*1000))//(bl+int(exptime*1000))
    sendCmd("shutter count %d"%n, prefix, cam)
    time.sleep(0.5)
    if on:
        sendCmd("shutter on",prefix,cam)

def coolCamera(temp, prefix="", cam=0):
    sendCmd("cooling reset", prefix, cam)
    time.sleep(0.2)
    sendCmd("cooling %d"%temp, prefix, cam)
    time.sleep(0.2)
    sendCmd("cooling on", prefix, cam)



# class OcamGUI:
#     def __init__(self,w=None):
#         import socket
#         self.prefix="main"
#         self.cam=4
#         self.countdown=None
#         if w==None:
#             self.win=gtk.Window()
#             self.win.set_title("OcamGUI FOR CANARY ON %s"%socket.gethostname())
#             self.win.connect("delete-event",self.quit)
#         else:
#             self.win=w
#         self.vbox=gtk.VBox()
#         self.win.add(self.vbox)
#         self.vbox.pack_start(gtk.Label("\nPlease ensure iportDaemon.py is running!\n(on darc)"))
#         h=gtk.HBox()
#         self.vbox.pack_start(h,False)
#         h.pack_start(gtk.Label("OCAM control GUI"),False)
#         e=gtk.Entry()
#         e.set_text(self.prefix)
#         e.set_tooltip_text("darc instance")
#         e.set_width_chars(5)
#         e.connect("focus-out-event",self.setPrefix)
#         h.pack_start(e,False)
#         e=gtk.Entry()
#         e.set_text("%d"%self.cam)
#         e.set_tooltip_text("camera number within darc")
#         e.set_width_chars(2)
#         e.connect("focus-out-event",self.setCam)
#         h.pack_start(e,False)

#         h=gtk.HBox()
#         self.vbox.pack_start(h,False)
#         b=gtk.Button("External trig")
#         b.set_tooltip_text("Start external triggering (synchro on)")
#         h.pack_start(b,False)
#         b.connect("clicked",self.trigger,1)
#         b=gtk.Button("Internal")
#         b.set_tooltip_text("Start internal triggering (synchro off)")
#         h.pack_start(b,False)
#         b.connect("clicked",self.trigger,0)
#         b=gtk.Button("Temp")
#         b.set_tooltip_text("Send the temp command (see iportDaemon output for the actual temperatures)")
#         h.pack_start(b,False)
#         b.connect("clicked",self.cool,"get",None)
#         t=gtk.ToggleButton("New mode")
#         t.set_tooltip_text("Set the CCD to operate in NIMO mode")
#         h.pack_start(t,False)
#         t.connect("toggled",self.nimo)
#         h=gtk.HBox()
#         self.vbox.pack_start(h,False)
#         b=gtk.Button("Shutter off")
#         b.set_tooltip_text("Turn shuttering off.  Also sends a shutter blockonread 0 as a bug fix (email from J-L Gach 8th Sept 2017)")
#         b.connect("clicked",self.shutter,"off")
#         h.pack_start(b,False)
#         b=gtk.Button("Shutter external")
#         b.set_tooltip_text("Shutter on external signal")
#         b.connect("clicked",self.shutter,"external")
#         h.pack_start(b,False)
#         b=gtk.Button("Set FPS")
#         b.set_tooltip_text("Set the OCAM Frames Per Second")
#         h.pack_start(b,False)
#         e=gtk.Entry()
#         e.set_text("150")
#         e.set_width_chars(4)
#         e.set_tooltip_text("Frame rate in Hz")
#         efps=e
#         h.pack_start(e,False)
#         b.connect("clicked",self.setFps,e)
#         h=gtk.HBox()
#         self.vbox.pack_start(h,False)
#         b=gtk.Button("Shutter on")
#         b.set_tooltip_text("Turn on shuttering with the specified frequency, shutter-open-time, delay and framerate (specified above)")
#         h.pack_start(b,False)
#         e=gtk.Entry()
#         e.set_text("10000")
#         e.set_tooltip_text("Laser frequency, Hz")
#         e.set_width_chars(5)
#         h.pack_start(e,False)
#         e2=gtk.Entry()
#         e2.set_text("3")
#         e2.set_tooltip_text("Shutter open time, us")
#         e2.set_width_chars(3)
#         h.pack_start(e2,False)
#         e3=gtk.Entry()
#         e3.set_text("666")
#         e3.set_tooltip_text("Shutter delay, us (should be greater than the readout time to avoid image artifacts, i.e. about 665.339).")
#         e3.set_width_chars(3)
#         h.pack_start(e3,False)
#         l=gtk.Label("150")
#         h.pack_start(l,False)
#         efps.connect("focus-out-event",self.setFpsLabel,l)
#         b.connect("clicked",self.shutter,(e,e2,e3,efps))
#         h=gtk.HBox()
#         self.vbox.pack_start(h,False)
#         b=gtk.Button("Cooling")
#         b.set_tooltip_text("Set camera cooling to specified temperature (-45 recommended)")
#         h.pack_start(b,False)
#         e=gtk.Entry()
#         e.set_text("-45")
#         e.set_tooltip_text("Cooling temperature (eg -45)")
#         e.set_width_chars(3)
#         h.pack_start(e,False)
#         bw=gtk.Button("Warm up")
#         bw.set_tooltip_text("Start the camera warming back up (takes about 10 minutes)")
#         h.pack_start(bw,False)
#         bc=gtk.Button("Cooling off")
#         self.coolOffButton=bc
#         bc.set_tooltip_text("Turn off the cooling system (WARNING: May result in thermal shock.  Only click this after you've started the camera warming).  Will become active 10 minutes after clicking 'warm up'")

#         h.pack_start(bc,False)
#         bc.connect("clicked",self.cool,"Cooler off",bc)
#         bw.connect("clicked",self.cool,"warm",bc)
#         b.connect("clicked",self.cool,e,bc)
#         bc.set_sensitive(False)

#         h=gtk.HBox()
#         self.vbox.pack_start(h,False)
#         b=gtk.Button("Geng freq:")
#         b.set_tooltip_text("Set the frequency of the laser pulses (spartan 3 board).  Requires ssh access to root@darc")
#         b.set_sensitive(False)
#         h.pack_start(b,False)
#         e=gtk.Entry()
#         e.set_text("10000")
#         e.set_width_chars(4)
#         h.pack_start(e,False)
#         b.connect("clicked",self.setTrigFreq,e)
#         b=gtk.ToggleButton("Blockonread")
#         b.set_tooltip_text("Set block on read option (closes shutter during readout")
#         h.pack_start(b,False)
#         b.connect("toggled",self.blockOnRead)
#         b=gtk.ToggleButton("Correct glitch")
#         b.set_tooltip_text("Do on-the-fly bias correction")
#         h.pack_start(b,False)
#         b.connect("toggled",self.correctGlitch)

#         self.win.show_all()
        

#     def quit(self,w,a=None):
#         gtk.mainquit()

#     def setFps(self,w,e=None):
#         fps=int(e.get_text())
#         print fps,self.cam,self.prefix
#         sendCmd("fps %d"%fps,self.prefix,self.cam)
#     def setFpsLabel(self,w,e=None,l=None):
#         l.set_text(w.get_text())
#     def setCam(self,w,a=None):
#         self.cam=int(w.get_text())
#     def setPrefix(self,w,a=None):
#         self.prefix=w.get_text().strip()

#     def trigger(self,w,exttrig=1):
#         if exttrig:
#             sendCmd("synchro on",self.prefix,self.cam)
#         else:
#             sendCmd("synchro off",self.prefix,self.cam)
#     def blockOnRead(self,w,a=None):
#         sendCmd("shutter blockonread %d"%w.get_active(),self.prefix,self.cam)

#     def correctGlitch(self,w,a=None):
#         sendCmd("shutter correctglitch %d"%w.get_active(),self.prefix,self.cam)

#     def shutter(self,w,a=None):
#         if a=="off":
#             print "Shutter off"
#             sendCmd("shutter off",self.prefix,self.cam)
#             sendCmd("shutter blockonread 0",self.prefix,self.cam)
#             d=darc.Control(self.prefix)
#             d.Set("ocamShutter",0)#for reference only
#         elif a=="external":
#             sendCmd("shutter external",self.prefix,self.cam)
#             sendCmd("shutter on",self.prefix,cam)
#             d=darc.Control(self.prefix)
#             d.Set("ocamShutter",1)#reference only
#         else:
#             lfreq=float(a[0].get_text())
#             opentime=float(a[1].get_text())
#             delay=float(a[2].get_text())
#             fps=int(a[3].get_text())
#             print lfreq,opentime,delay,fps
#             prepareShutter(lfreq,opentime,delay,fps,prefix=self.prefix,cam=self.cam)
#             d=darc.Control(self.prefix)
#             #and for reference (only)...
#             d.Set("ocamShutter",numpy.array([lfreq,opentime,delay,fps]).astype("f"))
#     def setCountdown(self):
#         rt=False
#         bc=self.coolOffButton
#         if self.countdown!=None and self.countdown>0:
#             self.countdown-=1
#             if self.countdown==0:
#                 bc.set_sensitive(True)
#                 bc.set_tooltip_text("Turn off the cooling system (WARNING: May result in thermal shock.  Only click this after you've started the camera warming).")
#             else:
#                 bc.set_tooltip_text("Turn off the cooling system (WARNING: May result in thermal shock.  Only click this after you've started the camera warming).  Will become active in %d seconds"%self.countdown)
#                 rt=True
#         return rt

#     def cool(self,w,a,b):
#         if a=="warm":
#             print "Warming"
#             self.countdown=600
#             self.setCountdown()
#             gobject.timeout_add(1000,self.setCountdown)
#             coolCamera(20,self.prefix,self.cam)
#         elif a=="Cooler off":
#             print "Cooler off"
#             sendCmd("cooling off",self.prefix,self.cam)
#         elif a=="get":
#             sendCmd("temp",self.prefix,self.cam)
#         else:
#             temp=int(a.get_text())
#             print "Cooling to %g"%temp
#             b.set_sensitive(False)
#             self.countdown=None
#             b.set_tooltip_text("Turn off the cooling system (WARNING: May result in thermal shock.  Only click this after you've started the camera warming).  Will become active 10 minutes after clicking 'warm up'")
#             coolCamera(temp,self.prefix,self.cam)
#     def setTrigFreq(self,w,e):
#         import subprocess
#         import traceback
#         freq=int(e.get_text())
#         result=""
#         cmd="ssh root@darc python /root/git/ocamtrig/setupScript.py %d"%freq
#         # try:
#         #     result = subprocess.check_output([cmd], stderr=subprocess.STDOUT,shell=True)
#         # except subprocess.CalledProcessError, e:
#         #     traceback.print_exc()
#         #     print e.output
#         # except:
#         #     traceback.print_exc()
#         p=subprocess.Popen(cmd,stderr=subprocess.STDOUT,stdout=subprocess.PIPE,shell=True)
#         result=p.stdout.read()

#         print result

#     def nimo(self,w):
#         if w.get_active():
#             print "Setting NIMO (new) mode (and turning gain to 1)"
#             sendCmd("gain 1",self.prefix,self.cam)
#             sendCmd("gain 1",self.prefix,self.cam)
#             sendCmd("vss 0",self.prefix,self.cam)

#         else:
#             print "Setting IMO (old) mode (and turning gain to 1)"
#             sendCmd("gain 1",self.prefix,self.cam)
#             sendCmd("gain 1",self.prefix,self.cam)
#             sendCmd("vss 2500",self.prefix,self.cam)
        
# def runGUI():
#     import gtk
#     global gtk
#     import gobject
#     global gobject
#     try:
#         sys.path.append("/home/ali/git/canaryLaserCommissioning")
#         import myStdout
#     except:
#         print "Could not import myStdout"
#         myStdout=None
#     g=OcamGUI()
#     if myStdout!=None:
#         m=myStdout.MyStdout(g.vbox)
#         m.sw.set_size_request(10,60)

#     gtk.main()

def main():
    prefix = ""
    cam = 0
    if len(sys.argv)>1:
        cmdlist = list(sys.argv[1:])
        newlist = []
        for cmd in cmdlist:
            if cmd.startswith("--prefix="):
                #cmdlist.remove(cmd)
                prefix = cmd[9:]
            elif cmd.startswith("--cam="):
                #cmdlist.remove(cmd)
                cam = int(cmd[6:])
            else:
                newlist.append(cmd)
        cmdlist = newlist
        if cmdlist[0]=="setup":
            if len(cmdlist)!=5:
                print(f"Usage: {sys.argv[0]} setup LaserFreq ShutterOpenTime(us) ShutterDelay(us - 666 to avoid readout) CameraFrameRate")
            else:
                laserfreq = float(cmdlist[1])
                shuttertime = float(cmdlist[2])
                delay = float(cmdlist[3])
                framerate = float(cmdlist[4])
                prepareShutter(laserfreq, shuttertime, delay, framerate, prefix=prefix, cam=cam)
        elif cmdlist[0]=="cool":
            if len(cmdlist)!=2:
                print(f"Usage: {sys.argv[0]} cool TEMP")
            else:
                temp = float(cmdlist[1])
                coolCamera(temp,prefix=prefix,cam=cam)
        # elif cmdlist[0]=="gui":
        #     runGUI()
        else:
            cmd = " ".join(cmdlist)
            sendCmd(cmd, prefix, cam)
    else:
        print(txt)


if __name__=="__main__":
    main()