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
from functools import reduce
if "OS" in os.environ and os.environ["OS"]=="Windows_NT":
    devshm="c:/RTC/shm/"
else:
    import serialise
    devshm="/dev/shm/"


import traceback
import numpy,numpy.random
from matplotlib.figure import Figure
import time
import FITS

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import matplotlib.cm as mpcolour

import PyQt5
import pyqtgraph as pg
from PyQt5 import QtGui as QtG
from PyQt5 import QtCore as QtC
from PyQt5 import QtWidgets as QtW
import sys
import subprocess
import threading
import serialise
import socket
import plotxml
import select
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

def getPyQtColour(colour):
    valid_col_words = {'white':(255,255,255),'w':(255,255,255),'black':(0,0,0),'k':(0,0,0),'red':(255,0,0),'r':(255,0,0),'blue':(0,0,255),'b':(0,0,255),'green':(0,255,0),'g':(0,255,0)}#,'yellow','purple','orange'}
    if type(colour) is str:
        return QtG.QColor(*valid_col_words.get(colour,(255,255,255)))
    elif type(colour) is tuple:
        return QtG.QColor(*colour)

class WatchDir:
    def __init__(self,watchdir="/dev/shm",prefix="",postfix="",addcb=None,remcb=None,modcb=None):
        patterns = "*"
        ignore_patterns = ""
        ignore_directories = False
        case_sensitive = True
        self.my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)

        self.my_event_handler.on_created = self.on_created
        self.my_event_handler.on_deleted = self.on_deleted
        self.my_event_handler.on_modified = self.on_modified

        self.prefix=prefix
        self.postfix=postfix
        self.prelen=len(prefix)
        self.postlen=len(postfix)
        self.addcb=addcb
        self.remcb=remcb
        self.modcb=modcb
        self.my_observer = Observer()
        self.my_observer.schedule(self.my_event_handler, watchdir, recursive=False)
        self.filelist = []

    def addWatchFile(self,fname):
        self.filelist.append(fname)

    def on_modified(self,event):
        name = event.src_path.split("/")[-1]
        if (name[:self.prelen]==self.prefix and (self.postlen==0 or name[-self.postlen:]==self.postfix)):
            if self.modcb is not None:
                self.modcb(name)
            else:
                print("Modified file '%s' (%s)"%(name,str(event)))
        elif name in self.filelist:
            if self.modcb is not None:
                self.modcb(name)
            else:
                print("Modified file '%s' (%s)"%(name,str(event)))
            return

    def on_created(self, event):
        name = event.src_path.split("/")[-1]
        if name[:self.prelen]==self.prefix and (self.postlen==0 or name[-self.postlen:]==self.postfix):
            if self.addcb is not None:
                self.addcb(name)
            else:
                print("Got stream '%s' (%s)"%(name,str(event)))
    
    def on_deleted(self, event):
        name = event.src_path.split("/")[-1]
        if name[:self.prelen]==self.prefix and (self.postlen==0 or name[-self.postlen:]==self.postfix):
            if self.remcb is not None:
                self.remcb(name)
            else:
                print("Stream removed %s"%name)
        
    def start(self):
        self.my_observer.start()

class WatchStdIn(QtC.QThread):
    IOSignal = QtC.pyqtSignal()
    def __init__(self,input_callback=None,hup_callback=None):
        if input_callback is None and hup_callback is None:
            raise Exception("No callback provided")
        super().__init__(self)
        self.hup_callback = hup_callback
        if input_callback is not None:
            self.IOSignal.connect(input_callback)
        self.quit_pipe = os.pipe()
        self.poller = select.poll()
        self.poller.register(sys.stdin, select.POLLIN | select.POLLHUP)
        self.poller.register(self.quit_pipe[0], select.POLLIN)

    def run(self):
        while True:
            readable = self.poller.poll()
            if (self.quit_pipe[0],select.POLLIN) in readable:
                print("Ending StdIn Watcher")
                break
            for state in readable:
                if state[1] & select.POLLIN:
                    self.IOSignal.emit()
                if state[1] & select.POLLHUP:
                    if self.hup_callback is not None:
                        self.hup_callback()
                        print("StdIn HUP received, ending StdIn Watcher")
                        break

    def stop(self):
        os.write(self.quit_pipe[1],b'.')

class WatchStream(QtC.QThread):
    IOSignal = QtC.pyqtSignal()
    def __init__(self,stream=None,input_callback=None,hup_callback=None):
        if input_callback is None and hup_callback is None:
            raise Exception("No callback provided")
        super().__init__(self)
        self.hup_callback = hup_callback
        if input_callback is not None:
            self.IOSignal.connect(input_callback)
        self.quit_pipe = os.pipe()
        self.poller = select.poll()
        self.sockfd = stream.fileno() if stream is not None else sys.stdin.fileno()
        self.poller.register(self.sockfd, select.POLLIN | select.POLLHUP)
        self.poller.register(self.quit_pipe[0], select.POLLIN)

    def run(self):
        while True:
            readable = self.poller.poll()
            if (self.quit_pipe[0],select.POLLIN) in readable:
                print("Ending Stream Watcher")
                break
            for state in readable:
                if state[1] & select.POLLIN:
                    self.IOSignal.emit()
                if state[1] & select.POLLHUP:
                    if self.hup_callback is not None:
                        self.hup_callback()
                        print("Stream HUP received, ending Stream Watcher")
                        break

    def stop(self):
        os.write(self.quit_pipe[1],b'.')

class GridItem(pg.GraphicsObject):
    def __init__(self, data, image_size=(100,100)):
        super().__init__()
        self.data = data  ## data must have fields: startx, starty, pitchx, pitchy, endx, endy, colour
        self.image_size = image_size
        self.generatePicture()
    
    def generatePicture(self):
        ## pre-computing a QPicture object allows paint() to run much more quickly, 
        ## rather than re-drawing the shapes every time.
        self.picture = QtG.QPicture()
        p = QtG.QPainter(self.picture)
        startx,starty,pitchx,pitchy,endx,endy,colour = self.data
        x_points = numpy.arange(startx,endx,pitchx)
        y_points = numpy.arange(starty,endy,pitchy)
        colour = getPyQtColour(colour)
        p.setPen(pg.mkPen(colour))
        for x in x_points[1:]:
            p.drawLine(QtC.QPointF(x,starty), QtC.QPointF(x,endy))
        for y in y_points[1:]:
            p.drawLine(QtC.QPointF(startx,y), QtC.QPointF(endx,y))
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtC.QRectF(self.picture.boundingRect())

    
class ArrowItem(pg.GraphicsObject):
    def __init__(self, data, image_shape=None):
        super().__init__()
        self.data = data  ## data must have fields: startx, starty, endx, endy, property_dict
        self.image_shape = image_shape
        self.generatePicture()
    
    def generatePicture(self):
        ## pre-computing a QPicture object allows paint() to run much more quickly, 
        ## rather than re-drawing the shapes every time.
        self.picture = QtG.QPicture()
        p = QtG.QPainter(self.picture)
        startx,starty,endx,endy,prop_dict = self.data
        colour = getPyQtColour(prop_dict.get("colour",'w'))
        p.setPen(pg.mkPen(colour))
        if endx == -1: endx = self.image_shape[1]
        if endy == -1: endy = self.image_shape[0]
        p.drawLine(QtC.QPointF(startx,starty), QtC.QPointF(endx,endy))
        if "size" in prop_dict:
            size = prop_dict["size"]
            hl = size
            hw = size/2.
            linetheta = numpy.arctan2(endy-starty, endx-startx)
            theta = numpy.arctan2(hw, hl)
            length = numpy.sqrt(hl**2 + hw**2)
            angle = linetheta - theta# - numpy.pi 
            x1 = endx - length*numpy.cos(angle)
            y1 = endy - length*numpy.sin(angle)
            angle = linetheta + theta# - numpy.pi
            x2 = endx - length*numpy.cos(angle)
            y2 = endy - length*numpy.sin(angle)
            # col=args.get("headColour",args.get("ec",col))
            #gc.set_foreground(col)
            filled = prop_dict.get("filled",0)
            if filled:
                points = QtG.QPolygonF([
                    QtC.QPointF(endx,endy),
                    QtC.QPointF(x1,y1),
                    QtC.QPointF(x2,y2),
                ])
                p.setBrush(pg.mkBrush(colour))
                p.drawPolygon(points)
            else:
                p.setPen(pg.mkPen(colour))
                p.drawLine(QtC.QPointF(endx,endy), QtC.QPointF(x1,y1))
                p.drawLine(QtC.QPointF(endx,endy), QtC.QPointF(x2,y2))
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtC.QRectF(self.picture.boundingRect())

X=numpy.random.random((20,20)).astype("f")
class myToolbar(QtW.QWidget):
    def __init__(self,plotfn=None,label="",loadFunc=None,streamName="",parentLayout=None):
        super().__init__()
        """plotfn is a function to call to replot..."""
        self.data=None
        self.label=label
        self.unstick=0
        self.toolbarVisible=1
        self.toolbarWin=None
        self.overlayWin=None
        self.darc=None
        self.prefix=None
        self.tbHbox=None
        self.overlayList=[]
        self.waitClickFunc=None
        l=label
        if len(label)>0:
            l=label+", "
        self.hostnametxt=" [%s%s]"%(l,socket.gethostname())#os.environ.get("HOSTNAME","unknown host"))
        self.loadFunc=loadFunc
        if plotfn is not None:
            self.replot=plotfn
        else:
            self.replot=self.dummyreplot
        self.autoscale=1
        self.freeze=0
        self.logx=0
        self.tbList=[]
        self.tbVal=[]
        self.store={}#can be used by mangle to save inbetween plots...
        self.stream={}#can be uused to store dtaa from all streams.
        self.streamName=streamName
        self.streamTime={}#stores tuples of fno,ftime for each stream
        self.streamTimeTxt=""#text info to show...
        self.mousepostxt=""
        self.subapLocation=None#needed for centroid overlays.
        self.npxlx=None#needed for centroid overlays.
        self.npxly=None#needed for centroid overlays.
        self.nsub=None#needed for centroid overlays.
        #self.nsuby=None#needed for centroid overlays.
        self.subscribeDict={}
        self.subapFlag=None#needed for centroid overlays.
        self.dataCopy=None
        self.mangleTxt=""
        self.mangleTxtDefault=""
        self.scale=[0,1]


        self.mainlayout = QtW.QVBoxLayout()
        self.setLayout(self.mainlayout)

        # self.splitter = QtW.QSplitter(QtC.Qt.Vertical)
        # self.mainlayout.addWidget(self.splitter)
        self.topsplitwidget = QtW.QWidget()
        self.topsplitlayout = QtW.QVBoxLayout()
        self.topsplitlayout.setContentsMargins(0,0,0,0)
        self.topsplitwidget.setLayout(self.topsplitlayout)
        self.bottomsplitwidget = QtW.QWidget()
        self.bottomsplitlayout = QtW.QHBoxLayout()
        self.bottomsplitlayout.setContentsMargins(0,0,0,0)
        self.bottomsplitwidget.setLayout(self.bottomsplitlayout)

        # self.splitter.addWidget(self.topsplitwidget)
        # self.splitter.addWidget(self.bottomsplitwidget)
        self.mainlayout.addWidget(self.topsplitwidget)
        self.mainlayout.addWidget(self.bottomsplitwidget)

        self.hbox = QtW.QHBoxLayout()
        self.hbox.setContentsMargins(0,0,0,0)
        self.hboxB = QtW.QHBoxLayout()
        self.hboxB.setContentsMargins(0,0,0,0)
        self.hbox2 = QtW.QHBoxLayout()
        self.hbox2.setContentsMargins(0,0,0,0)
        self.reprbutton=QtW.QPushButton("Repr")
        self.reprbutton.clicked.connect(self.repr)
        self.reprbutton.setToolTip("Textual representation")
        self.savebutton=QtW.QPushButton("Save")
        self.savebutton.clicked.connect(self.savePlot)
        self.savebutton.setToolTip("Save configuration (as xml) or data (unmodified as FITS)")
        self.loadbutton=QtW.QPushButton("Load")
        self.loadbutton.clicked.connect(self.loadPlot)
        self.loadbutton.setToolTip("Load a xml configuration or data FITS file to replace current")
        self.ds9button=QtW.QPushButton("ds9")
        self.ds9button.clicked.connect(self.sendToDS9)
        self.ds9button.setToolTip("Open image in ds9 (ds9 should found at /opt/ds9/)")
        self.stickbutton=QtW.QPushButton("<")
        self.stickbutton.setCheckable(True)
        self.stickbutton.toggled.connect(self.toggleStick)
        self.stickbutton.setToolTip("Move to separate window, or reparent")
        self.freezebutton=QtW.QCheckBox("Freeze")
        self.freezebutton.setChecked(self.freeze)
        self.freezebutton.toggled.connect(self.togglefreeze)
        self.freezebutton.setToolTip("freeze display")
        self.autobutton=QtW.QCheckBox("Scaling")
        self.autobutton.setChecked(self.autoscale)
        self.autobutton.toggled.connect(self.toggleAuto)
        self.autobutton.setToolTip("autoscale data")
        self.scaleMinEntry=QtW.QLineEdit()
        self.scaleMinEntry.editingFinished.connect(self.rescaleMin)
        self.scaleMinEntry.setFixedWidth(64)
        self.scaleMinEntry.setToolTip("Minimum value to clip when not autoscaling")
        self.scaleMinEntry.setEnabled(False)
        self.scaleMaxEntry=QtW.QLineEdit()
        self.scaleMaxEntry.editingFinished.connect(self.rescaleMax)
        self.scaleMaxEntry.setFixedWidth(64)
        self.scaleMaxEntry.setToolTip("Maximum value to clip when not autoscaling")
        self.scaleMaxEntry.setEnabled(False)
        self.logxbutton=QtW.QCheckBox("Logx")
        self.logxbutton.setChecked(self.logx)
        self.logxbutton.toggled.connect(self.togglelogx)
        self.logxbutton.setToolTip("Logaritm of x axis for 1d plots")
        self.overlaybutton=QtW.QPushButton("Overlay")
        self.overlaybutton.setCheckable(True)
        self.overlaybutton.toggled.connect(self.toggleOverlay)
        self.overlaybutton.setToolTip("Opens the overlay window")
        self.dataMangleEntry=QtW.QTextEdit()#QtW.QLineEdit()
        self.dataMangleEntry.setToolTip("Formatting to perform on data prior to plotting, e.g. data=numpy.log(data) (this gets exec'd).  You can also use this to create an overlay, e.g. overlay=numpy.zeros((10,10,4));overlay[::4,::4,::3]=1 to create an overlay of red dots.")
        self.dataMangleButton=QtW.QPushButton("Mangle\nNow")
        self.dataMangleButton.clicked.connect(self.dataMangle)
        self.hbox.addWidget(self.stickbutton,False)
        self.hbox.addWidget(self.freezebutton,False)
        self.hbox.addWidget(self.reprbutton)
        self.hbox.addWidget(self.savebutton)
        self.hbox.addWidget(self.loadbutton)
        self.hbox.addWidget(self.ds9button)
        self.hboxB.addWidget(self.autobutton,False)
        self.hboxB.addWidget(self.scaleMinEntry)
        self.hboxB.addWidget(self.scaleMaxEntry)
        self.hboxB.addWidget(self.logxbutton,False)
        self.hboxB.addWidget(self.overlaybutton,False)
        self.topsplitlayout.addLayout(self.hbox)#,False,False)
        self.topsplitlayout.addLayout(self.hboxB)#,False,False)
        self.topsplitlayout.addLayout(self.hbox2)#,expand=False,fill=True)
        self.bottomsplitlayout.addWidget(self.dataMangleEntry)#,fill=True)
        self.dataMangleLayout = QtW.QVBoxLayout()
        self.dataMangleLayout.addWidget(self.dataMangleButton)
        self.dataMangleLayout.setAlignment(QtC.Qt.AlignTop)
        self.bottomsplitlayout.addLayout(self.dataMangleLayout)#,fill=True)
        self.parentLayout=parentLayout

    def eventFilter(self, obj: 'QObject', event: 'QEvent') -> bool:
        if obj is self.overlayWin and event.type() == QtC.QEvent.Close:
            self.overlaybutton.toggle()
            return True
        return super().eventFilter(obj, event)

    def dummyreplot(self):
        print("Replot data... (doing nowt)")

    def leftMouseClick(self,x,y):
        wcf=self.waitClickFunc
        self.waitClickFunc=None
        if wcf is not None:
            wcf(x,y)

    def toggleAuto(self):
        self.autoscale=self.autobutton.isChecked()
        self.scaleMinEntry.setEnabled(not self.autoscale)
        self.scaleMaxEntry.setEnabled(not self.autoscale)
        self.replot()

    def toggleOverlay(self,response):
        if response:
            if self.overlayWin is None:
                self.overlayWin = OverlayWin(self)
                self.overlayWin.installEventFilter(self)
            self.overlayWin.show()
        else:
            self.overlayWin.hide()

    def overlayClick(self,x,y):
        """Called in response to a mouse click, if an overlay is waiting for one"""
        #need to scale x,y to pixels...
        name,args=self.overlayClickData
        args=list(args)#convert tuple to list
        if name=="hvline":
            if args[0]:#horizontal line
                args[1]=int(y)
            else:
                args[1]=int(x)
        elif name=="cross":
            args[0]=(int(x),int(y))
        elif name=="line":
            if type(args[0])!=type(()):
                args[0]=(int(x),int(y))
            else:
                args[1]=(int(x),int(y))
        elif name=="grid":
            if type(args[0])!=type(()):
                args[0]=(int(x),int(y))
            elif type(args[1])!=type(()):
                args[1]=(int(x),int(y))
            else:
                args[2]=(int(x),int(y))
        elif name=="text":
            args[1]=(int(x),int(y))
        elif name=="arrow":
            if type(args[0])!=type(()):
                args[0]=(int(x),int(y))
            else:
                args[1]=(int(x),int(y))
        self.addOverlay(name,args)

    def addOverlay(self,name=None,args=None):
        """Adds an overlay to the image"""
        if name=="hvline":
            horiz = int(args[0])
            coord = args[1]
            col = args[2]
            width = int(args[3])
            if coord=="":
                self.waitClickFunc=self.overlayClick
                args=list(args)
                args[0]=int(args[0])
                self.overlayClickData=name,args
                coord=0
                return
            else:
                coord=int(coord)
            print(horiz,coord,col,width)
            if horiz:
                xfr=0
                xto=-1
                yfr=coord
                yto=coord
            else:
                yfr=0
                yto=-1
                xfr=coord
                xto=coord
            self.overlayList.append(("arrow",xfr,yfr,xto,yto,{"size":0,"colour":col,"lineWidth":width}))
            b=QtW.QPushButton("%sLine row %d"%("H" if horiz else "V",coord))
            b.clicked.connect(self.removeOverlay)
            b.overlaylist = self.overlayList[-1:]
            b.setToolTip("Click to remove this overlay")
            self.vboxOverlay.addWidget(b,False)
            b.show()
        elif name=="cross":
            if type(args[0])==type(()):
                x,y=args[0]
            else:
                coords=args[0]
                if len(coords)==0:#grab from the image
                    self.waitClickFunc=self.overlayClick
                    args=list(args)
                    self.overlayClickData=name,args
                    return
                else:
                    x,y=eval(args[0])
            w=int(args[1])
            col=args[2]
            width=int(args[3])
            if w==0:
                xfr=0
                xto=-1
                yfr=y
                yto=y
                self.overlayList.append(("arrow",xfr,yfr,xto,yto,{"size":0,"colour":col,"lineWidth":width}))
                xfr=x
                xto=x
                yfr=0
                yto=-1
                self.overlayList.append(("arrow",xfr,yfr,xto,yto,{"size":0,"colour":col,"lineWidth":width}))
            else:
                xfr=x-w
                xto=x+w
                yfr=y
                yto=y
                if xfr<0:xfr=0
                if yfr<0:yfr=0
                if xto<0:xto=0
                if yto<0:yto=0
                self.overlayList.append(("arrow",xfr,yfr,xto,yto,{"size":0,"colour":col,"lineWidth":width}))
                xfr=x
                xto=x
                yfr=y-w
                yto=y+w
                if xfr<0:xfr=0
                if yfr<0:yfr=0
                if xto<0:xto=0
                if yto<0:yto=0
                self.overlayList.append(("arrow",xfr,yfr,xto,yto,{"size":0,"colour":col,"lineWidth":width}))
            b=QtW.QPushButton("Cross at %d,%d width %d"%(x,y,w))
            b.clicked.connect(self.removeOverlay)
            b.overlaylist = self.overlayList[-2:]
            b.setToolTip("Click to remove this overlay")
            self.vboxOverlay.addWidget(b,False)
            b.show()
        elif name=="line":
            if type(args[0])==type(()):
                xfr,yfr=args[0]
            else:
                coords=args[0]
                if len(coords)==0:#grab from image
                    self.waitClickFunc=self.overlayClick
                    args=list(args)
                    self.overlayClickData=name,args
                    return
                else:
                    xfr,yfr=eval(args[0])
            if type(args[1])==type(()):
                xto,yto=args[1]
            else:
                coords=args[1]
                if len(coords)==0:#grab from image
                    self.waitClickFunc=self.overlayClick
                    args=list(args)
                    args[0]=(xfr,yfr)
                    self.overlayClickData=name,args
                    return
                else:
                    xto,yto=eval(args[1])
            col=args[2]
            width=int(args[3])
            self.overlayList.append(("arrow",xfr,yfr,xto,yto,{"size":0,"colour":col,"lineWidth":width}))
            b=QtW.QPushButton("Line from %d,%d to %d,%d"%(xfr,yfr,xto,yto))
            b.clicked.connect(self.removeOverlay)
            b.overlaylist = self.overlayList[-1:]
            b.setToolTip("Click to remove this overlay")
            self.vboxOverlay.addWidget(b,False)
            b.show()
        elif name=="grid":
            if type(args[0])==type(()):
                xfr,yfr=args[0]
            else:
                coords=args[0]
                if len(coords)==0:#grab from imsage
                    self.waitClickFunc=self.overlayClick
                    args=list(args)
                    self.overlayClickData=name,args
                    return
                else:
                    xfr,yfr=eval(coords)
            if type(args[1])==type(()):
                xto,yto=args[1]
            else:
                coords=args[1]
                if len(coords)==0:
                    self.waitClickFunc=self.overlayClick
                    args=list(args)
                    args[0]=(xfr,yfr)
                    self.overlayClickData=name,args
                    return
                else:
                    xto,yto=eval(coords)

            if type(args[2])==type(()):
                xstep,ystep=args[2]
            else:
                coords=args[2]
                if len(coords)==0:
                    self.waitClickFunc=self.overlayClick
                    args=list(args)
                    args[0]=(xfr,yfr)
                    args[1]=(xto,yto)
                    self.overlayClickData=name,args
                    return
                else:
                    xstep,ystep=eval(coords)
            p=[xfr,yfr,xstep,ystep]
            if xto!=-1:
                p.append(xto)
            if yto!=-1:
                p.append(yto)
            #if len(args[1].get_text())>0:
            #    xto,yto=eval(args[1].get_text())
            #    p.append(xto)
            #    p.append(yto)
            #else:
            #    xto=-1
            #    yto=-1
            col=args[3]
            p.append(col)
            self.overlayList.append(("grid",p))
            b=QtW.QPushButton("Grid from %d,%d to %d,%d spacing %d,%d"%(xfr,yfr,xto,yto,xstep,ystep))
            b.clicked.connect(self.removeOverlay)
            b.overlaylist = self.overlayList[-1:]
            b.setToolTip("Click to remove this overlay")
            self.vboxOverlay.addWidget(b,False)
            b.show()
        elif name=="text":
            text=args[0]
            if type(args[1])==type(()):
                x,y=args[1]
            else:
                coords=args[1]
                if len(coords)==0:#grab from the image
                    self.waitClickFunc=self.overlayClick
                    args=list(args)
                    self.overlayClickData=name,args
                    return
                else:
                    x,y=eval(args[1])
            col=args[2]
            fount=args[3]
            zoom=args[4]
            self.overlayList.append(("text",text,x,y,col,fount,zoom))
            b=QtW.QPushButton("Text %s at %d,%d"%(text,x,y))
            b.clicked.connect(self.removeOverlay)
            b.overlaylist = self.overlayList[-1:]
            b.setToolTip("Click to remove this overlay")
            self.vboxOverlay.addWidget(b,False)
            b.show()
        elif name=="arrow":
            if type(args[0])==type(()):
                xfr,yfr=args[0]
            else:
                coords=args[0]
                if len(coords)==0:#grab from image
                    self.waitClickFunc=self.overlayClick
                    args=list(args)
                    self.overlayClickData=name,args
                    return
                else:
                    xfr,yfr=eval(args[0])
            if type(args[1])==type(()):
                xto,yto=args[1]
            else:
                coords=args[1]
                if len(coords)==0:#grab from image
                    self.waitClickFunc=self.overlayClick
                    args=list(args)
                    args[0]=(xfr,yfr)
                    self.overlayClickData=name,args
                    return
                else:
                    xto,yto=eval(args[1])
            #xfr,yfr=eval(args[0].get_text())
            #xto,yto=eval(args[1].get_text())
            col=args[2]
            width=int(args[3])
            size=int(args[4])
            filled=args[5]
            self.overlayList.append(("arrow",xfr,yfr,xto,yto,{"size":size,"colour":col,"lineWidth":width,"filled":filled}))
            b=QtW.QPushButton("Arrow from %d,%d to %d,%d"%(xfr,yfr,xto,yto))
            b.clicked.connect(self.removeOverlay)
            b.overlaylist = self.overlayList[-1:]
            b.setToolTip("Click to remove this overlay")
            self.vboxOverlay.addWidget(b,False)
            b.show()
        else:
            print("Overlay type %s not known"%(name))
        self.replot()

    def removeOverlay(self,event):
        b = self.sender()
        oList = b.overlaylist
        for overlay in oList:
            self.overlayList.remove(overlay)
        b.close()
        self.replot()

    def toggleStick(self):
        if self.stickbutton.isChecked():
            self.unstick=1
            self.parentLayout.removeWidget(self)
            self.setWindowFlags(QtC.Qt.Window)
            pos = QtG.QCursor().pos()
            self.move(pos)
            self.show()
        else:
            self.unstick=0
            self.setWindowFlags(QtC.Qt.Widget)
            self.parentLayout.addWidget(self)
            self.show()
            
    def hideToolbarWin(self,w,a=None):
        self.toolbarVisible=0
        self.toolbarWin.hide()

    def rescaleMin(self):
        try:
            self.scale[0]=float(self.scaleMinEntry.text())
        except Exception as e:
            print(e)
            pass
        self.replot()

    def rescaleMax(self):
        try:
            self.scale[1]=float(self.scaleMaxEntry.text())
        except Exception as e:
            print(e)
            pass
        self.replot()

    def togglefreeze(self):
        self.freeze=self.freezebutton.isChecked()
        if not self.freeze:
            self.replot()

    def togglelogx(self):
        self.logx=self.logxbutton.isChecked()
        self.replot()

    def dataMangle(self,event,e=None,data=None):
        #txt=w.get_text().strip()
        txt=self.dataMangleEntry.toPlainText()
        if self.mangleTxt!=txt:
            self.mangleTxt=txt
            self.replot()

    def makeArr(self,arr,shape,dtype):
        """This is used if you want to plot a history.
        eg in mangle you would put something like:
        store=makeArr(store,(1000,),"f");store[:999]=store[1:];store[999]=data[1];data=store
        """
        if arr is None or arr.shape!=shape or arr.dtype.char!=dtype:
            arr = numpy.zeros(shape,dtype)
        return arr

    def setUserButtons(self,tbVal,tbNames):
        pass
    
    def redraw(self,w=None,a=None):
        self.redrawFunc()

    def redrawFunc(self):
        """Redraw, if something has changed in the user widgets.  Anything the user adds to hbox can call this function when e.g. a button is clicked."""
        pass
    
    def prepare(self,data,dim=2,overlay=None,arrows=None,axis=None,plottype=None):
        self.origData=data
        title=self.streamName+self.hostnametxt
        streamTimeTxt=self.streamTimeTxt
        freeze=self.freeze
        colour=None
        text=None
        fount=None
        self.grid=None
        fast=0
        if self.freeze==0:
            if type(data)!=numpy.ndarray:
                data=numpy.array([data])
            if self.data is None or type(self.data)==type("") or self.data.shape!=data.shape or self.data.dtype.char!=data.dtype.char:
                self.data=data.copy()
            else:
                self.data[:]=data
            data=self.data
            if len(self.mangleTxt)>0:
                mangleTxt=self.mangleTxt
            else:
                mangleTxt=self.mangleTxtDefault
            if len(mangleTxt)>0:
                d={"parent":self,"data":data,"numpy":numpy,"overlay":overlay,"store":self.store,"makeArr":self.makeArr,"title":self.streamName,"stream":self.stream,"streamTime":self.streamTime,"streamTimeTxt":self.streamTimeTxt,"subapLocation":self.subapLocation,"freeze":0,"tbVal":self.tbVal[:],"debug":0,"dim":dim,"arrows":arrows,"npxlx":self.npxlx,"npxly":self.npxly,"nsub":self.nsub,"subapFlag":self.subapFlag,"quit":0,"colour":colour,"text":None,"axis":axis,"plottype":plottype,"fount":None,"prefix":self.prefix,"darc":self.darc,"hbox":self.tbHbox,"redraw":self.redraw}
                try:
                    # print(self.stream.keys())
                    exec(mangleTxt, d)
                    data=d["data"]#the new data... after mangling.
                    overlay=d["overlay"]#the new overlay
                    self.store=d["store"]
                    title=d["title"]
                    if title==self.streamName:#unchanged
                        title+=self.hostnametxt
                    streamTimeTxt=d["streamTimeTxt"]
                    freeze=d["freeze"]
                    tbNames=d.get("tbNames")#could be None
                    tbVal=d.get("tbVal")
                    fount=d.get("fount")
                    fast=d.get("fast",0)
                    self.grid=d.get("grid",None)#x,y,xstep,ystep,xend,yend,colour
                    self.setUserButtons(tbVal,tbNames)
                    #if d.has_key("tbNames") and type(d["tbNames"])==type([]):
                    #    for i in range(min(len(self.tbList),len(d["tbNames"])):
                    #        self.tbList[i].set_label(d["tbNames"][i])
                    dim=d["dim"]
                    if dim is None:
                        dim=2
                    elif dim>2:
                        dim=2
                    if type(data)==numpy.ndarray:
                        dim=min(dim,len(data.shape))
                    arrows=d["arrows"]
                    colour=d["colour"]
                    text=d["text"]
                    if type(text)==type(""):
                        text=[[text,0,0]]
                    elif type(text) in [type([]),type(())]:
                        if len(text)>0:
                            if type(text[0])==type(""):
                                text=[text]
                    #if title is None:
                    #    title=self.stream
                    axis=d["axis"]
                    plottype=d["plottype"]
                except SyntaxError as msg:
                    print(sys.exc_info())
                    traceback.print_exc()
                except:
                    if d["debug"]:
                        print(sys.exc_info())
                        traceback.print_exc()
                if d["quit"]:
                    sys.exit(0)

            if type(data)==type(""):
                pass
            else:
                if freeze==0:
                    if dim==2:#see if dimensions have changed...
                        dim=min(2,len(data.shape))
                    if self.logx==1 and dim==2:
                        #take log of the data...
                        data = data.astype(float)
                        m=numpy.min(data.ravel())
                        if m<0:
                            data += 0.1-m#now ranges from 0 upwards
                        elif m==0.:#get rid of any zeros...
                            data += 0.1
                        data=numpy.log(data)
                    if self.autoscale:
                        tmp=data.flat
                        #if data.flags.contiguous:
                        #    tmp=data.flat
                        #else:
                        #    tmp=numpy.array(data).flat
                        self.scale[0]=numpy.min(tmp)
                        self.scale[1]=numpy.max(tmp)
                        self.scaleMinEntry.setText("%.4g"%(self.scale[0]))
                        self.scaleMaxEntry.setText("%.4g"%(self.scale[1]))
                    #if dim==1:
                    #    data[:]=numpy.where(data<self.scale[0],self.scale[0],data)
                    #    data[:]=numpy.where(data>self.scale[1],self.scale[1],data)
        
            
            if freeze==0 and type(overlay)==numpy.ndarray and len(overlay.shape)==3 and overlay.shape[2]==4 and len(data.shape)==2:
                # an overlay has been used...
                pass
            else:
                overlay=None
        self.data=data
        return freeze,self.logx,data,self.scale,overlay,title,streamTimeTxt,dim,arrows,colour,text,axis,plottype,fount,fast,self.autoscale,self.grid,self.overlayList

    def repr(self,w=None,a=None):
        Repr(self.data,self.label,parent=self)

    def fileaddtimestamp(self):
        curpos = self.filesavebox.cursorPosition()
        text = self.filesavebox.text()
        self.filesavebox.setText(text[:curpos]+time.strftime("%y%m%d-%H%M%S")+text[curpos:])

    def savePlot(self,w=None,a=None):
        fileName, _ = QtW.QFileDialog.getSaveFileName(self.savebutton,"Save as FITS or xml","","All Files (*);;Text Files (*.txt)","",QtW.QFileDialog.DontConfirmOverwrite)

        if fileName != "":
            self.savedialog = QtW.QDialog(self.savebutton)
            message = QtW.QLabel("Save As:")
            self.filesavebox = QtW.QLineEdit(fileName)

            QBtn = QtW.QDialogButtonBox.Ok | QtW.QDialogButtonBox.Cancel

            buttonBox = QtW.QDialogButtonBox(QBtn)
            buttonBox.accepted.connect(self.filesave)
            buttonBox.rejected.connect(self.savedialog.close)

            button1 = QtW.QPushButton("Insert timestamp")
            button1.clicked.connect(self.fileaddtimestamp)
            buttonBox.addButton(button1,QtW.QDialogButtonBox.ActionRole)

            button2 = QtW.QPushButton("Save unformatted")
            button2.clicked.connect(self.filesaveorig)
            buttonBox.addButton(button2,QtW.QDialogButtonBox.ActionRole)

            layout = QtW.QVBoxLayout()
            layout.addWidget(message)
            layout.addWidget(self.filesavebox)
            layout.addWidget(buttonBox)
            self.savedialog.setLayout(layout)
            self.savedialog.exec_()

    def loadPlot(self,w=None,a=None):
        fileName, _ = QtW.QFileDialog.getOpenFileName(self.loadbutton,"Load FITS file/xml file", "","All Files (*);;Python Files (*.py)")

        if fileName != "":
            self.fileload(fileName)

    def filesaveorig(self):
        fname = self.filesavebox.text()
        self.savedialog.close()
        print("Saving shape %s, dtype %s"%(str(self.origData.shape),str(self.origData.dtype.char)))
        FITS.Write(self.origData,fname)

    def filesave(self):
        fname=self.filesavebox.text()
        self.savedialog.close()
        if fname[-5:]==".fits":
            print("Saving shape %s, dtype %s"%(str(self.data.shape),str(self.data.dtype.char)))
            FITS.Write(self.data,fname)
        elif fname[-4:]==".xml":
            print("Saving config")
            pos=self.savebutton.window.frameGeometry().x(),self.savebutton.window.frameGeometry().y()
            size=self.savebutton.window.frameGeometry().width(),self.savebutton.window.frameGeometry().height()
            vis=0
            tbVal=self.tbVal
            mangleTxt=self.mangleTxt
            subscribeList=[]
            for key in list(self.subscribeDict.keys()):
                subscribeList.append((key,self.subscribeDict[key][0],self.subscribeDict[key][1]))
            if os.path.exists(fname):
                with open(fname,'r') as xf:
                    plotList=plotxml.parseXml(xf.read()).getPlots()
            else:
                plotList=[]
            plotList.append([pos,size,vis,mangleTxt,subscribeList,tbVal,None])
            txt='<displayset date="%s">\n'%time.strftime("%y/%m/%d %H:%M:%D")
            for data in plotList:
                txt+='<plot pos="%s" size="%s" show="%d" tbVal="%s">\n<mangle>%s</mangle>\n<sub>%s</sub>\n</plot>\n'%(str(data[0]),str(data[1]),data[2],str(tuple(data[5])),data[3].replace("<","&lt;").replace(">","&gt;"),str(data[4]))
            txt+="</displayset>\n"
            with open(fname,'w') as xf:
                xf.write(txt)
        else:
            print("Nothing saved")


    def fileload(self,filename):
        if self.loadFunc is not None:
            try:
                self.loadFunc(filename,reposition=0)
            except Exception as e:
                traceback.print_exc()
    
    def sendToDS9(self):
        if self.data is not None:
            FITS.Write(self.data,"/tmp/tmp.fits")
            try:
                subprocess.Popen(["/opt/ds9/ds9","/tmp/tmp.fits"])
            except Exception as e:
                print(e)
                print("Might need to install ds9 to /opt/ds9/")

class OverlayWin(QtW.QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self.setWindowFlags(QtC.Qt.Window)
        self.parent = parent
        self.setWindowTitle("darcplot overlays")
        self.move(QtG.QCursor().pos())
        vbox=QtW.QVBoxLayout()
        self.setLayout(vbox)
        hbox=QtW.QHBoxLayout()
        vbox.addLayout(hbox)

        #add line button
        self.hvlinebutton=QtW.QPushButton("Add H/V line")
        hbox.addWidget(self.hvlinebutton)
        self.horCheck=QtW.QCheckBox("Horizontal")
        hbox.addWidget(self.horCheck)
        self.hvlinecoordEdit=QtW.QLineEdit()
        self.hvlinecoordEdit.setMinimumWidth(64)
        self.hvlinecoordEdit.setToolTip("Coordinate for the line - if empty, can be specified with a click")
        hbox.addWidget(self.hvlinecoordEdit)
        self.hvlinecolourEdit=QtW.QLineEdit()
        self.hvlinecolourEdit.setMinimumWidth(64)
        self.hvlinecolourEdit.setToolTip("Line colour")
        self.hvlinecolourEdit.setText("white")
        hbox.addWidget(self.hvlinecolourEdit)
        self.hvlinewidthSpin=QtW.QSpinBox()
        self.hvlinewidthSpin.setValue(0)
        self.hvlinewidthSpin.setMinimumWidth(64)
        self.hvlinewidthSpin.setToolTip("Line width")
        self.hvlinewidthSpin.setMaximum(1000000)
        self.hvlinewidthSpin.setMinimum(0)
        self.hvlinewidthSpin.setSingleStep(1)
        hbox.addWidget(self.hvlinewidthSpin)
        self.hvlinebutton.clicked.connect(self.addHVLine)

        #add a cross button
        hbox=QtW.QHBoxLayout()
        vbox.addLayout(hbox)
        self.crossbutton=QtW.QPushButton("Add cross")
        hbox.addWidget(self.crossbutton)
        self.crosscoordEdit=QtW.QLineEdit()
        self.crosscoordEdit.setMinimumWidth(64)
        self.crosscoordEdit.setToolTip("Coordinates of centre, x,y (blank to select with mouse)")
        hbox.addWidget(self.crosscoordEdit)
        self.crosswidthSpin=QtW.QSpinBox()
        self.crosswidthSpin.setValue(0)
        self.crosswidthSpin.setMinimumWidth(64)
        self.crosswidthSpin.setToolTip("Cross width")
        self.crosswidthSpin.setMaximum(1000000)
        self.crosswidthSpin.setMinimum(0)
        self.crosswidthSpin.setSingleStep(1)
        hbox.addWidget(self.crosswidthSpin)
        self.crosscolourEdit=QtW.QLineEdit()
        self.crosscolourEdit.setMinimumWidth(64)
        self.crosscolourEdit.setToolTip("Line colour")
        self.crosscolourEdit.setText("white")
        hbox.addWidget(self.crosscolourEdit)
        self.crosswidthSpin=QtW.QSpinBox()
        self.crosswidthSpin.setValue(0)
        self.crosswidthSpin.setMinimumWidth(64)
        self.crosswidthSpin.setToolTip("Line width")
        self.crosswidthSpin.setValue(0)
        self.crosswidthSpin.setMaximum(1000000)
        self.crosswidthSpin.setMinimum(0)
        self.crosswidthSpin.setSingleStep(1)
        hbox.addWidget(self.crosswidthSpin)
        self.crossbutton.clicked.connect(self.addCross)

        #add a line button
        hbox=QtW.QHBoxLayout()
        vbox.addLayout(hbox)
        self.linebutton=QtW.QPushButton("Add line")
        hbox.addWidget(self.linebutton)
        self.linecoord1Edit=QtW.QLineEdit()
        self.linecoord1Edit.setMinimumWidth(64)
        self.linecoord1Edit.setToolTip("Coordinates of line start, x,y (blank to select with mouse)")
        hbox.addWidget(self.linecoord1Edit)
        self.linecoord2Edit=QtW.QLineEdit()
        self.linecoord2Edit.setMinimumWidth(64)
        self.linecoord2Edit.setToolTip("Coordinates of line end, x,y (blank to select with mouse)")
        hbox.addWidget(self.linecoord2Edit)
        self.linecolourEdit=QtW.QLineEdit()
        self.linecolourEdit.setMinimumWidth(64)
        self.linecolourEdit.setToolTip("Line colour")
        self.linecolourEdit.setText("white")
        hbox.addWidget(self.linecolourEdit)
        self.linewidthSpin=QtW.QSpinBox()
        self.linewidthSpin.setValue(0)
        self.linewidthSpin.setMinimumWidth(64)
        self.linewidthSpin.setToolTip("Line width")
        self.linewidthSpin.setValue(0)
        self.linewidthSpin.setMaximum(1000000)
        self.linewidthSpin.setMinimum(0)
        self.linewidthSpin.setSingleStep(1)
        hbox.addWidget(self.linewidthSpin)
        self.linebutton.clicked.connect(self.addLine)
        
        #add a grid button
        hbox=QtW.QHBoxLayout()
        vbox.addLayout(hbox)
        self.gridbutton=QtW.QPushButton("Add grid")
        hbox.addWidget(self.gridbutton)
        self.gridcoord1Edit=QtW.QLineEdit()
        self.gridcoord1Edit.setMinimumWidth(64)
        self.gridcoord1Edit.setToolTip("Coordinates of grid start, x,y (blank to select with mouse - first click)")
        hbox.addWidget(self.gridcoord1Edit)
        self.gridcoord2Edit=QtW.QLineEdit()
        self.gridcoord2Edit.setMinimumWidth(64)
        self.gridcoord2Edit.setToolTip("Coordinates of grid end, x,y (blank to select with mouse - second click)")
        hbox.addWidget(self.gridcoord2Edit)
        self.gridpitchEdit=QtW.QLineEdit()
        self.gridpitchEdit.setMinimumWidth(64)
        self.gridpitchEdit.setToolTip("Grid pitch, x,y (blank to select with mouse - third click)")
        hbox.addWidget(self.gridpitchEdit)
        self.gridcolourEdit=QtW.QLineEdit()
        self.gridcolourEdit.setMinimumWidth(64)
        self.gridcolourEdit.setToolTip("Line colour")
        self.gridcolourEdit.setText("white")
        hbox.addWidget(self.gridcolourEdit)
        self.gridbutton.clicked.connect(self.addGrid)

        #add text button
        hbox=QtW.QHBoxLayout()
        vbox.addLayout(hbox)
        self.textButton=QtW.QPushButton("Add text")
        hbox.addWidget(self.textButton)
        self.textEdit=QtW.QLineEdit()
        self.textEdit.setToolTip("Text to be added")
        hbox.addWidget(self.textEdit)
        self.textcoordEdit=QtW.QLineEdit()
        self.textcoordEdit.setMinimumWidth(64)
        self.textcoordEdit.setToolTip("Coordinates of text, x,y (blank to select with mouse)")
        self.textcoordEdit.setText("")
        hbox.addWidget(self.textcoordEdit)
        self.textcolourEdit=QtW.QLineEdit()
        self.textcolourEdit.setMinimumWidth(64)
        self.textcolourEdit.setToolTip("Text colour")
        self.textcolourEdit.setText("white")
        hbox.addWidget(self.textcolourEdit)
        self.textfontEdit=QtW.QLineEdit()
        self.textfontEdit.setMinimumWidth(64)
        self.textfontEdit.setToolTip("Font description")
        self.textfontEdit.setText("10")
        hbox.addWidget(self.textfontEdit)
        self.textzoomCheck=QtW.QCheckBox("Zoom")
        self.textzoomCheck.setToolTip("Whether the text is zoomable")
        self.textzoomCheck.setChecked(True)
        hbox.addWidget(self.textzoomCheck)
        self.textButton.clicked.connect(self.addText)

        #add arrows button
        hbox=QtW.QHBoxLayout()
        vbox.addLayout(hbox)
        self.arrowButton=QtW.QPushButton("Add arrow")
        hbox.addWidget(self.arrowButton)
        self.arrowcoord1Edit=QtW.QLineEdit()
        self.arrowcoord1Edit.setMinimumWidth(64)
        self.arrowcoord1Edit.setToolTip("Coordinates of line start, x,y (blank to select with mouse)")
        hbox.addWidget(self.arrowcoord1Edit)
        self.arrowcoord2Edit=QtW.QLineEdit()
        self.arrowcoord2Edit.setMinimumWidth(64)
        self.arrowcoord2Edit.setToolTip("Coordinates of line end (arrow head), x,y (blank to select with mouse)")
        hbox.addWidget(self.arrowcoord2Edit)
        self.arrowcolourEdit=QtW.QLineEdit()
        self.arrowcolourEdit.setMinimumWidth(64)
        self.arrowcolourEdit.setToolTip("Line colour")
        self.arrowcolourEdit.setText("white")
        hbox.addWidget(self.arrowcolourEdit)
        self.arrowwidthSpin=QtW.QSpinBox()
        self.arrowwidthSpin.setValue(0)
        self.arrowwidthSpin.setMinimumWidth(64)
        self.arrowwidthSpin.setToolTip("Line width")
        self.arrowwidthSpin.setValue(0)
        self.arrowwidthSpin.setMaximum(1000000)
        self.arrowwidthSpin.setMinimum(0)
        self.arrowwidthSpin.setSingleStep(1)
        hbox.addWidget(self.arrowwidthSpin)
        self.arrowheadSpin=QtW.QSpinBox()
        self.arrowheadSpin.setValue(3)
        self.arrowheadSpin.setMinimumWidth(64)
        self.arrowheadSpin.setToolTip("Head width")
        self.arrowheadSpin.setValue(3)
        self.arrowheadSpin.setMaximum(1000000)
        self.arrowheadSpin.setMinimum(0)
        self.arrowheadSpin.setSingleStep(1)
        hbox.addWidget(self.arrowheadSpin)
        self.arrowsolidCheck=QtW.QCheckBox("Solid")
        hbox.addWidget(self.arrowsolidCheck)
        self.arrowsolidCheck.setToolTip("Solid head?")
        self.arrowButton.clicked.connect(self.addArrow)
        

        self.sw=QtW.QScrollArea()
        self.gb=QtW.QGroupBox()
        vbox.addWidget(self.sw)
        self.sw.resize(100,100)
        self.sw.setWidgetResizable(True)
        self.parent.vboxOverlay=QtW.QVBoxLayout()
        self.gb.setLayout(self.parent.vboxOverlay)
        self.sw.setWidget(self.gb)
    
    def addHVLine(self):
        c = self.horCheck.isChecked()
        e = self.hvlinecoordEdit.text()
        e2 = self.hvlinecolourEdit.text()
        s = self.hvlinewidthSpin.value()
        self.parent.addOverlay("hvline",(c,e,e2,s))
        
    def addCross(self):
        e = self.crosscoordEdit.text()
        s = self.crosswidthSpin.value()
        e2 = self.crosscolourEdit.text()
        s2 = self.crosswidthSpin.value()
        self.parent.addOverlay("cross",(e,s,e2,s2))

    def addLine(self):
        e = self.linecoord1Edit.text()
        e2 = self.linecoord2Edit.text()
        e3 = self.linecolourEdit.text()
        s2 = self.linewidthSpin.value()
        self.parent.addOverlay("line",(e,e2,e3,s2))

    def addGrid(self):
        e = self.gridcoord1Edit.text()
        e2 = self.gridcoord2Edit.text()
        e3 = self.gridpitchEdit.text()
        e4 = self.gridcolourEdit.text()
        self.parent.addOverlay("grid",(e,e2,e3,e4))

    def addText(self):
        e = self.textEdit.text()
        e2 = self.textcoordEdit.text()
        e3 = self.textcolourEdit.text()
        e4 = self.textfontEdit.text()
        c = self.textzoomCheck.isChecked()
        self.parent.addOverlay("text",(e,e2,e3,e4,c))

    def addArrow(self):
        e = self.arrowcoord1Edit.text()
        e2 = self.arrowcoord2Edit.text()
        e3 = self.arrowcolourEdit.text()
        s2 = self.arrowwidthSpin.value()
        s3 = self.arrowheadSpin.value()
        c = self.arrowsolidCheck.isChecked()
        self.parent.addOverlay("arrow",(e,e2,e3,s2,s3,c))

class Repr(QtW.QScrollArea):
    def __init__(self,data,label="Text representation",**kwargs):
        super().__init__(**kwargs)
        self.resize(640,480)
        self.setWindowTitle(label)
        self.label=label
        po=numpy.get_printoptions()["threshold"]
        numpy.set_printoptions(threshold=2**31)
        if type(data)==numpy.ndarray:
            st="Array shape=%s, dtype=%s\n"%(str(data.shape),str(data.dtype.char))
        else:
            st=""
        st+=str(data)
        numpy.set_printoptions(threshold=po)
        self.l=QtW.QLabel(st)
        self.setWidget(self.l)
        self.setWindowFlags(QtC.Qt.Window)
        self.show()

class circToolbar(myToolbar):
    def __init__(self,plotfn=None,label=""):
        myToolbar.__init__(self,plotfn=plotfn,label=label)
        self.frameWidget=QtW.QLabel()
        self.hbox2.addWidget(self.frameWidget)
        self.initialised=0

    def initialise(self,execute,toggle):
        """execute is a method called to execute the command"""
        self.initialised=1
        self.execute=execute
        self.toggle=toggle

        
    def gocirc(self,w,a=None):
        if self.initialised:
            if self.gobutton.get_active():
                freq=int(self.freqspin.get_text())
                #self.execute("c.circBufDict['%s'].freq[0]=%d"%(self.label,freq),tag=self.label)
                self.execute("c.subscribe(sock,'%s',%d)"%(self.label,freq),tag=self.label)

            else:
                #self.execute("c.circBufDict['%s'].freq[0]=0"%(self.label),tag=self.label)
                self.execute("c.subscribe(sock,'%s',0)"%(self.label),tag=self.label)

    def stop(self,w=None,a=None):
        #print "STOP"
        #self.gobutton.setChecked(0)
        #self.toggle.setChecked(0)
        pass

    def __del__(self):
        """Turn off the buffer..."""
        print("Destroying circ %s"%self.label)
        self.stop()
        
class circTxtToolbar(myToolbar):
    def __init__(self,plotfn=None,label=""):
        myToolbar.__init__(self,plotfn=plotfn,label=label)
        self.hbox.remove(self.reprbutton)
        self.hbox.remove(self.savebutton)
        self.hbox.remove(self.loadbutton)
        self.hbox.remove(self.autobutton)
        self.hbox.remove(self.scaleMaxEntry)
        self.hbox.remove(self.scaleMinEntry)
        self.hbox.remove(self.logxbutton)
        del(self.reprbutton)
        del(self.savebutton)
        del(self.loadbutton)
        del(self.autobutton)
        del(self.scaleMinEntry)
        del(self.scaleMaxEntry)
        del(self.logxbutton)
        self.frameWidget=QtW.QLabel()
        self.hbox.addWidget(self.frameWidget)
        self.hbox2.remove(self.scrollMangle)
        self.toolbar.remove(self.hbox2)
        del(self.dataMangleEntry)
        del(self.scrollMangle)
        del(self.hbox2)
        self.initialised=0

    def initialise(self,execute,toggle):
        """execute is a method called to execute the command"""
        self.initialised=1
        self.execute=execute
        self.toggle=toggle

        
    def gocirc(self,w,a=None):
        if self.initialised:
            if self.gobutton.get_active():
                freq=int(self.freqspin.get_text())
                #self.execute("c.circBufDict['%s'].freq[0]=%d"%(self.label,freq),tag=self.label)
                self.execute("c.subscribe(sock,'%s',%d)"%(self.label,freq),tag=self.label)

            else:
                #self.execute("c.circBufDict['%s'].freq[0]=0"%(self.label),tag=self.label)
                self.execute("c.subscribe(sock,'%s',0)"%(self.label),tag=self.label)

    def stop(self,w=None,a=None):
        #print "STOP"
        #self.gobutton.setChecked(0)
        #self.toggle.setChecked(0)
        pass
    
    def __del__(self):
        """Turn off the buffer..."""
        print("Destroying circ %s"%self.label)
        self.stop()

class plotWindow(QtW.QMainWindow):
    def __init__(self,*args,**kwargs):
        super().__init__()
        plot = plot(*args,**kwargs)
        self.setCentralWidget(plot)
        
class plot(QtW.QWidget):
    plotSignal = QtC.pyqtSignal()
    plotClosedSignal = QtC.pyqtSignal()
    """Note, currently, this cant be used interactively - because Qt has to be running...."""
    
    def __init__(self,dims=None,label="darcplot [%s]"%os.environ.get("HOSTNAME","unknown host"),usrtoolbar=None,loadFunc=None,loadFuncArgs=(),subplot=(1,1,1),deactivatefn=None,scrollWin=0,pylabbar=0,qtapp=None,**kwargs):
        """If specified, usrtoolbar should be a class constructor, for a class containing: initial args of plotfn, label, a toolbar object which is the widget to be added to the vbox, and a prepare method which returns freeze,logscale,data,scale and has args data,dim

        """
        super().__init__(**kwargs)
        self.dims=dims
        self.data=numpy.zeros((7,15),numpy.float32)
        self.data[1:6,1]=1
        self.data[2,4]=1
        self.data[3,3]=1
        self.data[4,2]=1
        self.data[1:6,5]=1
        self.data[1:4,7]=1
        self.data[1:4,9]=1
        self.data[1,8]=1
        self.data[3,8]=1
        self.data[1:4,11]=1
        self.data[1:4,13]=1
        self.data[3,12]=1
        self.ds=None
        self.fullscreen=False
        self.plot1dAxis=None
        self.line1d=None
        self.image2d=None
        self.plottype=None
        self.scatcol='b'
        self.overlay=None
        self.userLoadFunc=loadFunc
        self.loadFuncArgs=loadFuncArgs
        self.deactivatefn=deactivatefn#this can be set by the caller, eg to turn off buttons...
        self.zoom=1
        self.zoomx=0.
        self.zoomy=0.
        self.actualXzoom=1.
        self.actualYzoom=1.
        self.dataScaled=0

        centerPoint = QtW.QDesktopWidget().availableGeometry().center()
        self.setGeometry(1500,600, 600, 600)
        self.setWindowTitle(label)
        self.settitle=1

        self.label=label
        self.cmap = mpcolour.gray
        self.interpolation="nearest"#see pylab documantation for others.


        self.mainlayout = QtW.QVBoxLayout()#VPaned()
        self.mainlayout.setContentsMargins(0,0,0,0)
        self.setLayout(self.mainlayout)

        # self.splitter = QtW.QSplitter(self)
        # self.splitter.setOrientation(QtC.Qt.Vertical)
        # self.splitter.setStretchFactor(1,0)
        # self.mainlayout.addWidget(self.splitter)

        self.plotwidget = QtW.QWidget()
        self.plotlayout = QtW.QVBoxLayout()
        self.plotlayout.setContentsMargins(0,0,0,0)
        self.plotwidget.setLayout(self.plotlayout)
        # self.plotwidget.setSizePolicy(QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Expanding)
        # self.splitter.addWidget(self.plotwidget)
        self.mainlayout.addWidget(self.plotwidget)#,stretch=1)

        self.toolbarwidget = QtW.QWidget()
        self.toolbarlayout = QtW.QVBoxLayout()
        self.toolbarlayout.setContentsMargins(0,0,0,0)
        self.toolbarwidget.setLayout(self.toolbarlayout)
        # self.toolbarwidget.setSizePolicy(QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Minimum)
        # self.splitter.addWidget(self.toolbarwidget)
        self.mainlayout.addWidget(self.toolbarwidget)#,stretch=1)

      
        self.txtPlot=QtW.QLabel("")

        self.graphicslay = pg.GraphicsLayoutWidget()
        self.viewbox = pg.ViewBox()
        self.image = pg.ImageItem()
        self.viewbox.addItem(self.image)
        self.viewbox.setAspectLocked(True)
        self.graphicslay.setCentralItem(self.viewbox)
        self.viewbox.setMenuEnabled(False)
        self.graphicslay.setMouseTracking(True)
        self.graphicslay.installEventFilter(self)
        self.graphicslay.viewport().installEventFilter(self)
        self.pixbuf=None
        self.lay=QtW.QScrollArea()
        self.txtPlot.mousePressEvent = self.buttonPress
        self.plotlayout.addWidget(self.txtPlot)
        self.plotlayout.addWidget(self.graphicslay)#self.image)

        self.fig=Figure(dpi=50)

        self.ax = self.fig.add_subplot(*subplot)
        self.fig.subplots_adjust(right=0.99,left=0.08,bottom=0.05,top=0.99)

        self.canvas = FigureCanvas(self.fig)  # a gtk.DrawingArea
        self.canvas.mousePressEvent = self.buttonPress
        self.plotlayout.addWidget(self.canvas)

        if pylabbar:
            self.toolbar = NavigationToolbar(self.canvas, self)
            self.toolbarlayout.addWidget(self.toolbar)
        else:
            self.toolbar=None
        
        if usrtoolbar is None:
            self.mytoolbar=myToolbar(plotfn=self.plot,label=label,loadFunc=self.loadFunc,streamName=label,parentLayout=self.toolbarlayout)
        else:
            self.mytoolbar=usrtoolbar(plotfn=self.plot,label=label,parentLayout=self.toolbarlayout)
        #self.toolbar.save_figure=self.mytoolbar.mysave
        # self.mytoolbar.setSizePolicy(QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Minimum)
        self.toolbarlayout.addWidget(self.mytoolbar)
        # self.splitter.addWidget(self.plottingWidget)
        # self.splitter.addWidget(self.mytoolbar)
        self.show()
        self.txtPlot.hide()
        self.graphicslay.hide()
        # self.lay.hide()
        if self.toolbar is not None:
            self.toolbar.hide()
        self.active=1#will be set to zero once quit or window closed.
        self.update=0
        self.plotArgs = ()
        self.plotSignal.connect(self.plotTrigger)

        self.installEventFilter(self)
        self.lastframetime = time.time()
        self.frametime = 0.02
        self.griditems = []
        self.textitems = []
        self.arrowitems = []
        self.qtapp = qtapp

    def eventFilter(self,obj,event):
        if event.type() == QtC.QEvent.MouseButtonPress and obj is self.graphicslay.viewport():
            self.buttonPress(event)
        elif event.type() == QtC.QEvent.MouseButtonDblClick and obj is self.graphicslay.viewport():
            self.viewbox.autoRange()
        elif event.type() == QtC.QEvent.MouseMove and obj is self.graphicslay.viewport():
            self.mousemove(event)
        elif event.type() == QtC.QEvent.Leave and obj is self.graphicslay.viewport():
            self.mousefocusout(event)
        elif event.type() == QtC.QEvent.Close and obj is self:
            self.quit(event)
        return super().eventFilter(obj, event)

    def plotTrigger(self):
        if time.time() - self.lastframetime > self.frametime:
            self.lastframetime = time.time()
            if self.active:
                self.plot(*self.plotArgs)
                self.plotArgs = ()
        else:
            return

    def quit(self,event):
        if self.deactivatefn is not None:
            d=self.deactivatefn
            self.deactivatefn=None
            d(self)
        self.active=0
        try:
            self.plotSignal.disconnect()
        except Exception as e:
            pass
        self.plotClosedSignal.emit()

    def keyPress(self,w,e=None):
        if e.keyval==QtC.Qt.Key_F5:
            if self.fullscreen:
                self.unfullscreen()
                self.fullscreen=False
            else:
                self.fullscreen()
                self.fullscreen=True
        elif e.keyval==QtC.Qt.Key_Escape:
            if self.fullscreen:
                self.unfullscreen()
                self.fullscreen=False
        return False

    def newPalette(self,palette):
        if palette[-3:]==".gp":
            palette=palette[:-3]
        if palette in list(mpcolour.datad.keys()):
            self.cmap=getattr(mpcolour,palette)
        else:
            print("Palette %s not regocnised"%str(palette))
            print(list(mpcolour.datad.keys()))
        #self.plot()

    def newInterpolation(self,interp):
        if interp not in ["bicubic","bilinear","blackman100","blackman256","blackman64","nearest","sinc144","sinc64","spline16","spline36"]:
            print("Interpolation %s not recognised"%str(interp))
        else:
            self.interpolation=interp
        #self.plot()
        
    def buttonPress(self,event):
        """If the user right clicks, we show or hide the toolbar..."""
        if event.buttons() == QtC.Qt.RightButton:
            self.rightMouseClick()
        elif event.buttons() == QtC.Qt.LeftButton:#left click
            pos = event.pos()
            if self.image.sceneBoundingRect().contains(pos):
                mousePoint = self.viewbox.mapSceneToView(pos)
                self.mytoolbar.leftMouseClick(mousePoint.x(),mousePoint.y())
    
    def rightMouseClick(self):
        if self.mytoolbar.toolbarVisible:
            if self.toolbar is not None:
                self.toolbar.hide()
            self.mytoolbar.hide()
            self.mytoolbar.toolbarVisible=0
        else:
            if self.toolbar is not None:
                self.toolbar.show()
            self.mytoolbar.show()
            self.mytoolbar.toolbarVisible=1

    def mousefocusout(self,event):
        self.mytoolbar.mousepostxt=""
        self.mytoolbar.frameWidget.setText(self.mytoolbar.streamTimeTxt)

    def mousemove(self,event):
        pos = event.pos()
        if self.image.sceneBoundingRect().contains(pos):
            mousePoint = self.viewbox.mapSceneToView(pos)
            px = int(mousePoint.x())
            py = int(mousePoint.y())
            if px > 0 and px < self.pixbuf.shape[0] and py > 0 and py < self.pixbuf.shape[1]:
                val=self.mytoolbar.data[py,px]
                # sf=(self.mytoolbar.scale[1]-self.mytoolbar.scale[0])
                # if self.dataScaled:
                #     val=val*sf+self.mytoolbar.scale[0]
                self.mytoolbar.mousepostxt=" (%d, %d) %s"%(px,py,str(val))
                self.mytoolbar.frameWidget.setText(self.mytoolbar.streamTimeTxt+self.mytoolbar.mousepostxt)
        else:
            self.mousefocusout(event)
                
    def loadFunc(self,fname,reposition=1,index=None):
        if fname is None:
            print("Clearing plot")
            if self.userLoadFunc is not None:
                try:
                    self.userLoadFunc(None)
                except:
                    traceback.print_exc()
            self.mytoolbar.dataMangleEntry.setText("")
            self.mytoolbar.mangleTxt=""
            self.mytoolbar.setUserButtons(())
            self.plottype=None
            self.mytoolbar.store={}
            self.overlay=None
            self.mytoolbar.stream={}#can be uused to store dtaa from all streams.
            self.mytoolbar.streamName=fname
            self.mytoolbar.streamTime={}#stores tuples of fno,ftime for each stream
            self.mytoolbar.streamTimeTxt=""#text info to show...
        elif fname[-5:]==".fits":
            data=FITS.Read(fname)[1]
            print("Loading shape %s, dtype %s"%(str(data.shape),str(data.dtype.char)))
            self.plot(data)
            if self.userLoadFunc is not None:
                self.userLoadFunc(self.label,data,fname,*self.loadFuncArgs)
        elif fname[-4:]==".xml":
            print("loading this? : ",fname)
            #change the confuration.
            with open(fname,'r') as xf:
                plotList=plotxml.parseXml(xf.read()).getPlots()
            print(plotList)
            if index is None:
                if len(plotList)>1:#let the user choose which plot to load (or all)
                    d=gtk.Dialog("Choose a plot within the configuration",None,gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
                    v=d.get_content_area()
                    for i in range(len(plotList)):
                        b=QtW.QPushButton("Plot %d"%(i+1))
                        v.addWidget(b)
                        b.clicked.connect(lambda:d.response(i+1))
                        d.set_position(QtG.QCursor().pos())
                    d.show_all()
                    resp=d.run()
                    d.close()
                    if resp==gtk.RESPONSE_NONE or resp==gtk.RESPONSE_DELETE_EVENT or resp==gtk.RESPONSE_REJECT:
                        index=None
                    else:
                        index=resp-1
                else:
                    index=0
            if index is None:
                return 1
            if self.userLoadFunc is not None:#allow the function to select the one it wants, and do stuff... (subscribe etc).
                try:
                    theplot=self.userLoadFunc([plotList[index]],*self.loadFuncArgs)
                except:
                    theplot=plotList[index]
                    traceback.print_exc()
            else:
                theplot=plotList[index]
            pos=theplot[0]
            size=theplot[1]
            show=theplot[2]
            mangle=theplot[3]
            sub=theplot[4]
            tbVal=theplot[5]
            self.mytoolbar.setUserButtons(())
            for i in range(self.mytoolbar.tbHbox.count()):
                w = self.mytoolbar.tbHbox.takeAt(i)
                if w is not None: w.widget().deleteLater()
            self.mytoolbar.dataMangleEntry.setText(mangle)
            self.mytoolbar.mangleTxt=mangle
            self.mytoolbar.setUserButtons(tbVal)
            self.plottype=None
            self.mytoolbar.store={}
            self.overlay=None
            self.mytoolbar.stream={}#can be uused to store dtaa from all streams.
            self.mytoolbar.streamName=fname
            self.mytoolbar.streamTime={}#stores tuples of fno,ftime for each stream
            self.mytoolbar.streamTimeTxt=""#text info to show...

            #if tbVal is not None:
            #    for i in range(len(tbVal)):
            #        self.mytoolbar.tbList[i].setChecked(tbVal[i])
            if reposition:
                if size is not None:
                    try:
                        self.win.set_default_size(size[0],size[1])
                        self.win.resize(size[0],size[1])
                    except:
                        traceback.print_exc()
                if pos is not None:
                    try:
                        self.win.move(pos[0],pos[1])
                    except:
                        traceback.print_exc()
            return 0

    def queuePlot(self,axis,overlay=None,arrows=None,clear=1):
        """puts a request to plot in the idle loop... (gives the rest of the
        gui a chance to update before plotting)
        """
        if self.qtapp is not None:
            self.qtapp.processEvents()
        if self.update and self.active:
            ax=self.ax
            #t1=time.time()
            if hasattr(self.ax.xaxis,"callbacks"):
                try:
                    self.ax.xaxis.callbacks.callbacks=dict([(s,dict()) for s in self.ax.xaxis.callbacks.signals])#needed to fix a bug!
                    self.ax.yaxis.callbacks.callbacks=dict([(s,dict()) for s in self.ax.yaxis.callbacks.signals])#needed to fix a bug!
                except:
                    pass
            if clear:
                # print("doing self.ax.cla()")
                self.ax.cla()
            
            #self.ax.clear()
            #t2=time.time()
            #print "axclear time %g"%(t2-t1),self.ax,self.ax.plot,self.ax.xaxis.callbacks
            freeze,logscale,data,scale,overlay,title,streamTimeTxt,dims,arrows,colour,text,axis,self.plottype,fount,fast,autoscale,gridList,overlayList=self.mytoolbar.prepare(self.data,dim=self.dims,overlay=overlay,arrows=arrows,axis=axis,plottype=self.plottype)
            if colour is not None:
                self.newPalette(colour)
            if title is not None and self.settitle==1:
                self.setWindowTitle(title)
            if len(streamTimeTxt)>0:
                self.mytoolbar.frameWidget.setText(streamTimeTxt+self.mytoolbar.mousepostxt)
            if freeze:#This added May 2013.
                self.update=0
                return False
            if type(data)!=numpy.ndarray:
                data=str(data)#force to a string.  we can then just print this.
            updateCanvas=0
            if type(data)==type(""):
                #self.ax.text(0,0,data)
                # self.mouseOnImage=None
                if freeze==0:
                    data=data.replace("\0","")
                    self.canvas.hide()
                    self.graphicslay.hide()
                    self.txtPlot.show()
                    # self.lay.hide()
                    # if fount is not None:
                    #     self.txtPlot.modify_font(pango.FontDescription(fount))
                    self.txtPlot.setText(data)
                    self.txtPlot.repaint()
                    # self.ax.annotate(data,xy=(10,10),xycoords="axes points")
            elif len(data.shape)==1 or dims==1:
                # self.mouseOnImage=None
                updateCanvas=1
                self.canvas.show()
                self.txtPlot.hide()
                self.graphicslay.hide()
                # self.lay.hide()
                #1D
                if len(data.shape)==1:
                    if freeze==0:
                        if type(axis)==type(None) or axis.shape[0]!=data.shape[0]:
                            if self.plot1dAxis is None or self.plot1dAxis.shape[0]<data.shape[0]:
                                self.plot1dAxis=numpy.arange(data.shape[0])+1
                            axis=self.plot1dAxis[:data.shape[0]]
                        if logscale:
                            if self.plottype=="bar":
                                try:
                                    data=numpy.log10(data)
                                except:
                                    print("Cannot take log of data")
                            else:
                                try:
                                    axis=numpy.log10(axis)
                                except:
                                    print("Cannot take log")
                        #self.fig.axis([axis[0],axis[-1],scale[0],scale[1]])
                        #if self.line1d is not None and self.line1d.get_xdata().shape==axis.shape and max(self.line1d.get_ydata())==scale[1] and min(self.line1d.get_ydata())==scale[0]:
                        #    self.line1d.set_data(axis,data)
                        #else:
                        #    print "replot"
                        #    self.ax.cla()
                        if self.plottype=="scatter":
                            self.line1d=self.ax.scatter(axis,data,s=1,c=self.scatcol)
                        elif self.plottype=="bar":
                            self.line1d=self.ax.bar(axis,data)
                        else:
                            self.line1d=self.ax.plot(axis,data)[0]
                        if autoscale==0:
                            try:
                                self.ax.autoscale(False,"y")
                            except:
                                pass
                                #print "Old versions of pylab don't have Axis.autoscale"
                            xlim=list(self.ax.axis()[:2])
                            self.ax.axis(xlim+list(scale))
                        else:
                            try:
                                self.ax.autoscale(True,"y")
                            except:
                                pass
                                #print "Old versions of pylab don't have Axis.autoscale"
                else:#use first row of data for the x axis...
                    #axis=data[0]
                    #freeze,logscale,data,scale=self.mytoolbar.prepare(self.data,dim=1)
                    if freeze==0:
                        start=0
                        if type(axis)==type(None) or axis.shape[-1]!=data.shape[1] or (len(axis.shape)==2 and axis.shape[0]!=data.shape[0]):
                            #print "Using first row as axis"
                            #axis=numpy.arange(data.shape[0])+1
                            axis=data[0]#first rox of data is the axis.
                            start=1
                        if logscale:
                            if self.plottype=="bar":
                                try:
                                    data=numpy.log10(data)
                                except:
                                    print("Cannot take log of data")
                            else:
                                try:
                                    axis=numpy.log10(axis)
                                except:
                                    print("Cannot take log")
                        #self.fig.axis([axis[0],axis[-1],scale[0],scale[1]])
                        try:
                            if len(axis.shape)==1:#single axis
                                if self.plottype=="scatter":
                                    for i in range(start,data.shape[0]):
                                        self.ax.scatter(axis,data[i],s=1,c=self.scatcol)
                                elif self.plottype=="bar":
                                    for i in range(start,data.shape[0]):
                                        self.ax.bar(axis,data[i])
                                else:
                                    for i in range(start,data.shape[0]):
                                        self.ax.plot(axis,data[i])
                            else:#axis for each data
                                if self.plottype=="scatter":
                                    for i in range(start,data.shape[0]):
                                        self.ax.scatter(axis[i],data[i],s=1,c=self.scatcol)
                                elif self.plottype=="bar":
                                    for i in range(start,data.shape[0]):
                                        self.ax.bar(axis[i],data[i])
                                else:
                                    for i in range(start,data.shape[0]):
                                        self.ax.plot(axis[i],data[i])
                                
                            if autoscale==0:
                                self.ax.autoscale(False,"y")
                                xlim=list(self.ax.axis()[:2])
                                self.ax.axis(xlim+list(scale))
                            else:
                                self.ax.autoscale(True,"y")
                        except:
                            print("Error plotting data")
                            traceback.print_exc()
                if text is not None:
                    for t in text:
                        if len(t)>=5:
                            ax.text(t[1],t[2],t[0],color=t[3],size=t[4])
                        elif len(t)==4:
                            ax.text(t[1],t[2],t[0],color=t[3])
                        else:
                            ax.text(t[1],t[2],t[0])
            else:#2D
                if fast:
                    self.canvas.hide()
                    self.txtPlot.hide()
                    self.graphicslay.show()
                    self.viewbox.show()
                    self.image.show()
                    # self.lay.show()
                    # colour_channels = 1
                    if freeze==0:
                        ds=data.shape
                        self.ds=ds
                        self.actualXzoom=1
                        self.actualYzoom=1

                        if autoscale==0:
                            data[:]=numpy.where(data<0,0,data)
                            data[:]=numpy.where(data>255,255,data)

                        self.dataScaled=(data is self.mytoolbar.data)
                    
                        self.pixbuf = data.T

                        self.image.setImage(self.pixbuf,autoLevels=autoscale,levels=scale)
                        for o in overlayList:
                            if o[0]=="text":
                                if text is None:
                                    text=[o[1:]]
                                else:
                                    text.append(o[1:])
                            elif o[0]=="arrow":
                                if arrows is None:
                                    arrows=[o[1:]]
                                else:
                                    arrows.append(o[1:])
                            elif o[0]=="grid":
                                if gridList is None:
                                    gridList=[o[1]]
                                else:
                                    gridList.append(o[1])
                        
                        for t in self.textitems:
                            self.viewbox.removeItem(t)
                        self.textitems = []
                        if text is not None:
                            for t in text:
                                ti = pg.TextItem(t[0],color=getPyQtColour(t[3]))
                                fi = QtG.QFont()
                                fi.setPointSize(int(t[4]))
                                ti.setFont(fi)
                                self.textitems.append(ti)
                                self.viewbox.addItem(ti)
                                ti.setPos(t[1],t[2])

                        for a in self.arrowitems:
                            self.viewbox.removeItem(a)
                        self.arrowitems = []
                        if arrows is not None:
                            for a in arrows:
                                self.arrowitems.append(ArrowItem(a,ds))
                                self.viewbox.addItem(self.arrowitems[-1])

                        #now work out the grid
                        if type(gridList)!=type([]):
                            gridList=[gridList]
                        for grid in self.griditems:
                            self.viewbox.removeItem(grid)
                        self.griditems = []
                        for grid in gridList:
                            if grid is not None and type(grid) in [type([]),type(())] and len(grid)>3:
                                self.griditems.append(GridItem(grid))
                                self.viewbox.addItem(self.griditems[-1])
                            
                else:
                    # self.mouseOnImage=None
                    updateCanvas=1
                    self.canvas.show()
                    self.txtPlot.hide()
                    self.graphicslay.hide()
                    # self.lay.hide()
                    #freeze,logscale,data,scale=self.mytoolbar.prepare(self.data)
                    if freeze==0:
                        if self.plottype!=self.interpolation and self.plottype is not None and self.plottype!="scatter" and self.plottype!="bar":
                            self.newInterpolation(self.plottype)
                        if len(data.shape)!=2:#force to 2d
                            data=numpy.reshape(data,(reduce(lambda x,y:x*y,data.shape[:-1]),data.shape[-1]))
                        self.image2d=ax.imshow(data,interpolation=self.interpolation,cmap=self.cmap,vmin=scale[0],vmax=scale[1],origin="lower",aspect="auto")
                        # self.image2d=pg.ImageItem(data.T)
                        # self.imageAx.addItem(self.image2d)
                        # if self.curAx is not self.imageAx:
                        #     self.fig.removeItem(self.curAx)
                        #     self.curAx = self.imageAx
                        #     self.fig.addItem(self.curAx)#row=0,col=0)
                        if overlay is not None:
                            ax.imshow(overlay,interpolation=self.interpolation,cmap=self.cmap,vmin=scale[0],vmax=scale[1],origin="lower",aspect="auto",extent=(-0.5,data.shape[1]-0.5,-0.5,data.shape[0]-0.5))
                        #arrows=[[10,10,500,50,{"head_width":10,"head_length":20,"head_width":10,"head_length":10,"length_includes_head":True,"fc":"red","ec":"green"}]]
                        if arrows is not None:
                            for a in arrows:
                                if len(a)>=4:
                                    if len(a)==5:
                                        args=a[4]
                                    else:
                                        args={}
                                    ax.arrow(a[0],a[1],a[2],a[3],**args)#head_width=10,head_length=10)
                        if text is not None:
                            for t in text:
                                if len(t)>=5:
                                    ax.text(t[1],t[2],t[0],color=t[3],size=t[4])
                                elif len(t)==4:
                                    ax.text(t[1],t[2],t[0],color=t[3])
                                else:
                                    ax.text(t[1],t[2],t[0])

            if freeze==0 and updateCanvas==1:
                try:
                    self.ax.draw()
                except:
                    pass
                #self.ax.update()
                self.canvas.draw()
                #self.canvas.queue_draw()
        self.update=0
        # self.mutex.unlock()
        return False
    
    def plot(self,data=None,copy=0,axis=None,overlay=None,arrows=None,clear=1):
        """Plot new data... axis may be specified if 1d...
        overlay is an optional overlay...
        """
        if self.active==0:
            self.active=1
            self.show()
        self.overlay=overlay
        if data is not None:
            if copy:
                self.data=data.copy().astype("d")
            else:
                if not hasattr(data,"dtype"):#not an array or a numpy.float/int type.
                    self.data=numpy.array([data]).view("b")
                else:
                    self.data=data
        self.update=1
        # gobject.idle_add(self.queuePlot,axis,overlay,arrows,clear)
        self.queuePlotArgs = (axis,overlay,arrows,clear)
        self.queuePlot(*self.queuePlotArgs)
        # self.queuePlot(axis,overlay,arrows,clear)
        return True

class plotTxt:
    def __init__(self,window=None,startGtk=0,dims=2,label="Window",usrtoolbar=None,loadFunc=None,loadFuncArgs=(),subplot=(1,1,1),deactivatefn=None):
        """
        This is a class for displaying text messages rather than images.
        If specified, usrtoolbar should be a class constructor, for a class containing: initial args of plotfn, label, a toolbar object which is the widget to be added to the vbox, and a prepare method which returns freeze,logscale,data,scale and has args data,dim

        """
        self.dims=dims
        self.data=numpy.zeros((7,15),numpy.float32)
        self.data[1:6,1]=1
        self.data[2,4]=1
        self.data[3,3]=1
        self.data[4,2]=1
        self.data[1:6,5]=1
        self.data[1:4,7]=1
        self.data[1:4,9]=1
        self.data[1,8]=1
        self.data[3,8]=1
        self.data[1:4,11]=1
        self.data[1:4,13]=1
        self.data[3,12]=1
        self.overlay=None
        self.userLoadFunc=loadFunc
        self.loadFuncArgs=loadFuncArgs
        self.deactivatefn=deactivatefn#this can be set by the caller, eg to turn off buttons...
        
        self.win = QtW.QMainWindow()
        self.win.connect("destroy", self.quit)
        self.win.set_default_size(400,100)
        self.win.setWindowTitle(label)
        self.label=label
        self.vpane=QtW.QVBoxLayout()#VPaned()
        self.win.add(self.vpane)
        self.vbox = QtW.QVBoxLayout()
        #self.win.add(self.vbox)
        #self.vpane.pack2(self.vbox,resize=True)
        self.vpane.addWidget(self.vbox,True)
        self.vpane.mousePressEvent = self.buttonPress
        self.labelWidget=QtW.QLabel("")
        # self.labelWidget.set_justify(gtk.JUSTIFY_CENTER)
        #self.vpane.pack1(self.labelWidget,resize=True)
        self.vpane.addWidget(self.labelWidget,False)
        #self.toolbar = NavigationToolbar(self.canvas, self.win)
        #self.vbox.addWidget(self.toolbar, False, False)
        if usrtoolbar is None:
            self.mytoolbar=myToolbar(plotfn=self.plot,label=label,loadFunc=self.loadFunc)
        else:
            self.mytoolbar=usrtoolbar(plotfn=self.plot,label=label)
        #self.toolbar.save_figure=self.mytoolbar.mysave
        self.vbox.addWidget(self.mytoolbar.toolbar,False,False)
        self.win.show_all()
        #self.toolbar.hide()
        self.mytoolbar.toolbar.show()
        self.active=1#will be set to zero once quit or window closed.
        #self.toolbarVisible=1
        self.startedGtk=0
        self.update=0
        #self.plot()
        self.closeEvent = self.quit

    def quit(self,w=None,data=None):
        if self.deactivatefn is not None:
            d=self.deactivatefn
            self.deactivatefn=None
            d(self)
        self.active=0
        self.hide()
        self.destroy()
        if hasattr(self.mytoolbar,"stop"):
            self.mytoolbar.stop()

    def buttonPress(self,w,e,data=None):
        """If the user right clicks, we show or hide the toolbar..."""
        if e.button==3:
            if self.mytoolbar.toolbarVisible:
                #self.toolbar.hide()
                self.mytoolbar.toolbar.hide()
                self.mytoolbar.toolbarVisible=0
            else:
                #self.toolbar.show()
                self.mytoolbar.toolbar.show()
                self.mytoolbar.toolbarVisible=1

        return True

    def plot(self,data=None,copy=0,axis=None,overlay=None):
        """Plot new data... axis may be specified if 1d...
        """
        if self.active==0:
            self.active=1
            self.win.show()
        #if type(data)==numpy.ndarray:
        #    data=Numeric.array(data)
        if type(data)==type(""):
            self.data=data
        elif type(data)==numpy.ndarray:
            self.data=data.view("b").tobytes().strip().replace("\0"," ")
                #elif data.dtype.char=="d":
                #    self.data=data
                #else:
                #    self.data=data.astype("d")
        else:#data is None?
            pass
            #if type(self.data)==numpy.ndarray:
            #    self.data=Numeric.array(self.data)
        self.update=1
        #print "plot"
        #print type(axis)
        #if type(axis)!=type(None):
        #    print axis.shape
        self.labelWidget.setText(self.data)

class plotToolbar(myToolbar):
    def __init__(self,plotfn=None,label="",**kwargs):
        myToolbar.__init__(self,plotfn=plotfn,label=label,**kwargs)
        vbox=QtW.QVBoxLayout()
        hbox=QtW.QHBoxLayout()
        self.confighbox=hbox
        self.tbHbox=QtW.QHBoxLayout()
        self.tbList=[]
        self.tbVal=[]
        self.tbNames=[]
        b=QtW.QPushButton("Spawn")
        b.setToolTip("Start a new plot")
        hbox.addWidget(b,False)
        b.clicked.connect(self.spawn)
        b=QtW.QPushButton("Activate")
        b.setToolTip("Click to use the mangle text (actually, it will be used anyway, but this just gives people some reassurance)")
        hbox.addWidget(b,False)
        self.configdir=None

        self.combobox = QtW.QComboBox()

        self.combobox.currentIndexChanged.connect(self.comboChanged)
        self.filelist=[]
        self.frameWidget=QtW.QLabel()
        self.frameWidget.setAlignment(QtC.Qt.AlignLeft | QtC.Qt.AlignVCenter)
        vbox.addLayout(hbox)
        vbox.addLayout(self.tbHbox)
        vbox.addWidget(self.frameWidget)
        self.hbox2.addLayout(vbox)
        self.initialised=0

    def initialise(self,subscribeAction,configdir=None):
        """execute is a method called to execute the command"""
        self.initialised=1
        self.resubButton=QtW.QPushButton("Re")
        self.hbox.addWidget(self.resubButton)
        self.resubButton.setToolTip("Resubscribe to existing telemetry streams")
        self.resubButton.clicked.connect(lambda:subscribeAction("resubscribe"))
        self.resubButton.show()
        self.showStreams=QtW.QPushButton("Sub")
        self.showStreams.setToolTip("Show list of telemetry streams")
        self.hbox.addWidget(self.showStreams)
        self.showStreams.show()
        self.showStreams.clicked.connect(subscribeAction)
        self.configdir=configdir
        if self.configdir is not None:
            if len(self.configdir)==0:
                self.configdir="./"
            if self.configdir[-1]!='/':
                self.configdir+='/'
            sys.path.append(self.configdir)
            self.confighbox.addWidget(self.combobox)
            self.combobox.show()
            self.wm=WatchDir(self.configdir,"plot",".xml",self.comboUpdate,self.comboRemove)
            self.wm.start()
            self.comboPopped()

    def spawn(self,w=None,a=None):
        if sys.argv[0][-3:] == ".py":
            subprocess.Popen(["python3"]+sys.argv+["-i0"])#add index of zero so that we don't spawn lots of plots if the current one is a multiplot.
        else:
            subprocess.Popen(sys.argv+["-i0"])#add index of zero so that we don't spawn lots of plots if the current one is a multiplot.

    def userButtonToggled(self,w,a=None):
        a = self.sender().id
        self.tbVal[a]=int(w)

    def displayFileList(self,parentWin=None):
        print("showing file list")
        self.displayFileWidget=QtW.QWidget(parent=self)
        self.displayFileWidget.setWindowFlags(QtC.Qt.Window | QtC.Qt.WindowStaysOnTopHint)
        self.displayFileWidget.setWindowTitle("Choose plot configuration")
        v=QtW.QVBoxLayout()
        self.displayFileWidget.setLayout(v)
        self.filebuttonlist=[]
        print(self.filelist)
        for i,f in enumerate(self.filelist):
            if f is not None:
                b=QtW.QPushButton(f)
                b.clicked.connect(self.comboChosen)
                self.filebuttonlist.append(b)
                v.addWidget(b)
        self.displayFileWidget.show()

    def comboChosen(self,response):
        fname=self.configdir+self.sender().text()
        print("loading",fname)
        while len(self.tbVal)>0:
            self.removeUserButton()
        if self.loadFunc(fname,reposition=0)==0:
            self.displayFileWidget.close()
        
    def comboChanged(self,w,a=None):
        print(w)
        indx=w
        if indx>=0:
            if self.filelist[indx] is None:
                while len(self.tbVal)>0:
                    self.removeUserButton()
                self.loadFunc(None)
            else:
                fname=self.configdir+self.filelist[indx]
                print("loading",fname)
                while len(self.tbVal)>0:
                    self.removeUserButton()
                self.loadFunc(fname,reposition=0)

    def comboUpdate(self,fname):
        if fname not in self.filelist:
            self.filelist.append(fname)
            self.combobox.addItem(fname)

    def comboRemove(self,fname):
        if fname in self.filelist:
            indx=self.filelist.index(fname)
            self.combobox.removeItem(indx)
            self.filelist.pop(indx)

    def comboPopped(self,w=None):
        files=os.listdir(self.configdir)
        files.sort()
        self.filelist=[None]
        self.combobox.addItem("None")
        for fname in files:
            if fname[:4]=="plot" and fname[-4:]==".xml":
                self.filelist.append(fname)
                self.combobox.addItem(fname)

    def addUserButton(self,name=None,active=0):
        pos=len(self.tbList)
        if name is None:
            name="%d"%pos
        but=QtW.QPushButton(name)
        but.setCheckable(True)
        but.setChecked(active)
        but.id = pos
        but.toggled.connect(self.userButtonToggled)
        self.tbList.append(but)
        self.tbVal.append(active)
        self.tbNames.append(name)
        self.tbHbox.addWidget(but)
        but.show()

    def removeUserButton(self):
        self.tbVal.pop()
        self.tbNames.pop()
        but=self.tbList.pop()
        self.tbHbox.removeWidget(but)

    def setUserButtons(self,tbVal,names=None):
        if tbVal==self.tbVal and names==self.tbNames:
            return
        if tbVal is None:
            tbVal=[]
        if names is not None:
            l=len(names)
            ll=len(tbVal)
            if ll<l:
                tbVal=tbVal+[0]*(l-ll)
            else:
                tbVal=tbVal[:l]
        else:
            names=list(map(str,list(range(len(tbVal)))))
            names[:len(self.tbNames)]=self.tbNames[:len(tbVal)]
        while len(self.tbVal)>len(tbVal):
            self.removeUserButton()
        l=len(self.tbList)
        for i in range(l):#for existing buttons
            self.tbList[i].setChecked(tbVal[i])
            if names[i]!=self.tbNames[i]:
                self.tbList[i].setText(names[i])
                self.tbNames[i]=names[i]
        for i in range(l,len(tbVal)):#and add new if required.
            self.addUserButton(names[i],tbVal[i])


class RightClickableCheckBox(QtW.QCheckBox):
    mytoggled = QtC.pyqtSignal(bool,int)
    def mousePressEvent(self, event):
        if event.button() == QtC.Qt.LeftButton:
            self.toggle()
            self.mytoggled.emit(self.isChecked(),1)
        elif event.button() == QtC.Qt.RightButton:
            # self.toggle()
            self.mytoggled.emit(self.isChecked(),3)
        elif event.button() == QtC.Qt.MiddleButton:
            # self.toggle()
            self.mytoggled.emit(self.isChecked(),2)

class SubWid(QtW.QWidget):
    """Class which shows a list of streams and allows the user to choose which ones should be subscribed too.
    """
    def __init__(self,parentSubscribe=None,parentWin=None,parentGrab=None,parentDec=None,**kwargs):
        """parentSubscribe is a method with args (stream, active flag, decimate,change other decimates flag) which is called when a stream subscription is changed
        """
        super().__init__(**kwargs)
        self.setWindowFlags(QtC.Qt.Window)
        self.parentSubscribe=parentSubscribe
        self.parentGrab=parentGrab
        self.parentDec=parentDec
        self.streamDict={}
        self.move(QtG.QCursor().pos())
        self.setWindowTitle("Subscribe to...")
        self.table=QtW.QGridLayout()

        self.setLayout(self.table)

    def show(self,streamDict,subscribeDict):
        """put stream list in and show...
        streamDict has entries (short description, long description)
        subscribeDict has an entry for each stream subscribed too, which is
        (sub,decimation) where sub is a flag whether subscribed to or not and 
        decimation is the decimation rate.
        decDict is dictionary of decimations as returned by controlClient().GetDecimation()
        """
        print("showing subwid")
        if len(streamDict)==0:
            streamDict={"None":("None","None")}
        self.streamDict=streamDict

        for i in reversed(range(self.table.count())):
            self.table.takeAt(i).widget().deleteLater()
        l = QtW.QLabel("Stream ")
        l.mousePressEvent = self.resubscribe
        self.table.addWidget(l,0,0)
        self.table.addWidget(QtW.QLabel("decimate"),0,1)

        pos=1
        keys=list(streamDict.keys())
        keys.sort()
        self.streamWidgets={}
        for s in keys:
            print("S:",s)

            short,lng=streamDict[s]

            t=RightClickableCheckBox(short)
            t.id = s
            c=QtW.QPushButton()
            c.id = s
            e=QtW.QLineEdit()
            e.id = s

            self.streamWidgets[s] = e,t

            if len(short)!=3 and ("rtc" not in short or "Buf" not in short):
                t.setEnabled(False)
                c.setEnabled(False)
                e.setEnabled(False)


            e.setFixedWidth(4*8)

            t.setToolTip(lng)
            e.setToolTip("Plot decimation factor")

            c.setToolTip("Force local decimation rate to plot rate?")
            e.setText("100")

            if s in subscribeDict:
                sub,dec=subscribeDict[s][:2]
                e.setText("%d"%dec)#set decimation
                if sub:
                    t.setChecked(1)#subscribe to it

            args=(s,t,e,c)#,c,e2,e3)
            t.mytoggled.connect(self.substreamToggled)

            e.editingFinished.connect(self.substreamReturnPress)
            c.clicked.connect(self.substreamClicked)

            self.table.addWidget(t,pos,0)#,pos,pos+1)
            self.table.addWidget(e,pos,1)#,pos,pos+1)
            self.table.addWidget(c,pos,2)#,pos,pos+1)

            pos+=1
        super().show()

    def substreamToggled(self,response,button):
        stream = self.sender().id
        active = int(response)
        dec = int(self.streamWidgets[stream][0].text())

        if button==2 or button==3:
            if self.parentGrab is not None:
                self.parentGrab(stream,latest=(button==2))
        else:
            if self.parentSubscribe is not None:
                self.parentSubscribe((stream,active,dec))#,change,dec2,dec3))

    def substreamClicked(self,response):
        stream = self.sender().id
        dec = int(self.streamWidgets[stream][0].text())
        if self.parentDec is not None:
            self.parentDec(stream,dec)

    def substreamReturnPress(self):
        stream = self.sender().id
        dec = int(self.sender().text())
        active = int(self.streamWidgets[stream][1].isChecked())
        if self.parentSubscribe is not None:
            self.parentSubscribe((stream,active,dec))

    def resubscribe(self,w=None,a=None):
        """Resubscribe to all currently subscribed streams"""
        # print(self.streamWidgets)
        if self.parentSubscribe is not None:
            for stream,val in self.streamWidgets.items():
                if val[1].isChecked():
                    dec = int(val[0].text())
                    self.parentSubscribe((stream,0,dec))
                    self.parentSubscribe((stream,1,dec))

class PlotServer:
    def __init__(self,port,shmtag):
        self.port=port
        self.shmtag=shmtag
        #First, before doing anything else, connect to port.
        if self.makeConnection("localhost",port) is None:
            #connection failed, so exit...
            raise Exception("Couldn't connect to data server")
        #Now we're connected, wait for info to arrive...
        #Then once we have the stream list (which will come last), 
        #we can create the plot object and show it...
        subList=[]
        self.subapLocation=None#this is needed for plotting centroid overlays.  The centroid measurements are relative to this, rather than relative to the rtcSubLocBuf, which can change if in adaptive window mode.  So, the plotter needs a copy of the static subapLocation.
        self.subWid=None
        self.shmDict={}
        self.streamDict={}
        self.subscribeDict={}
        self.subscribeList=[]
        self.conndata=None
        self.mangle=""
        self.visible=1
        tbVal=None
        initDone=0
        size=pos=None
        while initDone==0:
            print("Plot reading message")
            msg=serialise.ReadMessage(self.conn)
            if msg is None:
                print("Plot read message failed - exiting")
                sys.exit(0)
            print("Plot got msg",msg)
            if msg[0]=="state":
                pos=msg[1]
                size=msg[2]
                self.visible=msg[3]
                self.mangle=msg[4]
                subList=msg[5]#list of things subscribed to... list of tuples of (stream, subscribe flag, decimate,change other decimates flag)
                tbVal=msg[6]#buttons...
                
            elif msg[0]=="streams":
                self.addStream(msg[1])
                initDone=1
            elif msg[0]=="subapLocation":
                self.subapLocation=msg[1]
                self.npxlx=msg[2]
                self.npxly=msg[3]
                self.nsub=msg[4]
                #self.nsuby=msg[5]
                self.subapFlag=msg[5]
        self.subscribe(subList)
        self.plot=plot(quitGtk=1,usrtoolbar=plotToolbar)
        if self.visible==0:
            class dummy:
                button=3
            self.plot.buttonPress(None,dummy())
        self.plot.mytoolbar.dataMangleEntry.setText(self.mangle)
        self.plot.mytoolbar.mangleTxt=self.mangle
            
        if size is not None:
            self.plot.win.set_default_size(size[0],size[1])
            self.plot.win.resize(size[0],size[1])
        if pos is not None:
            self.plot.win.move(pos[0],pos[1])
        self.plot.mytoolbar.setUserButtons(tbVal)
            #for i in range(min(len(self.plot.mytoolbar.tbList),len(tbVal))):
            #    v=tbVal[i]
            #    self.plot.mytoolbar.tbList[i].setChecked(v)
        self.subWid=SubWid(self.subscribe,self.plot.win)
        print("got the subwid")
        if len(self.subscribeList)==0:    
            #need to pop up the subscribbe widget...
            #the user can then decide what to sub to.
            self.subWid.show(self.streamDict,self.subscribeDict)
        self.plot.mytoolbar.initialise(self.showStreams)

    def showStreams(self,w=None,a=None):
        if self.subWid is not None:
            if a=="resubscribe":
                self.subWid.resubscribe()
            else:
                self.subWid.show(self.streamDict,self.subscribeDict)

    def makeConnection(self,host,port):
        self.conn=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            self.conn.connect((host,port))

            # self.sockID=gobject.io_add_watch(self.conn,gtk.gdk.INPUT_READ,self.handleData)
            self.sockID = WatchStream(self.conn,self.handleData)
            self.sockID.start()
        except:
            print("Plotter error - couldn't connect to %s %d"%(host,port))
            self.conn=None
            raise
        return self.conn

    def subscribe(self,slist):
        """slist is a list of tuples of (stream,subscribe flag,decimate,change other decimates flag).
        """
        if type(slist)!=type([]):
            slist=[slist]
        for s in slist:
            serialise.Send(["sub",s],self.conn)
            if s[1]:#subscribe to it
                self.subscribeDict[s[0]]=s[1:]
                if s not in self.subscribeList:
                    self.subscribeList.append(s)
            else:
                if s[0] in self.subscribeDict:
                    del(self.subscribeDict[s[0]])
                if s in self.subscribeList:
                    self.subscribeList.remove(s)

    def addStream(self,streamList):
        """Add streams.
        streamList is a list of tuples containing:
        (stream name, short description, long description)"""
        if type(streamList)!=type([]):
            streamList=[streamList]
        for stream in streamList:
            self.streamDict[stream[0]]=stream[1:]
        if self.subWid is not None and self.subWid.win.get_property("visible"):
            self.showStreams()

    def delStream(self,stream):
        if stream in self.streamDict:
            del(self.streamDict[stream])
        if stream in self.shmDict:
            del(self.shmDict[stream])
        if self.subWid is not None and self.subWid.win.get_property("visible"):
            self.showStreams()
    def updateStream(self,stream,data=None):
        """new data has arrived for this stream... so plot it."""
        if stream in [x[0] for x in self.subscribeList]:#we're subscribed to it...
            if data is None:
                data,fno,ftime=self.readSHM(stream)
            else:
                data,ftime,fno=data
            if data is not None:
                if stream not in self.plot.mytoolbar.streamTime or self.plot.mytoolbar.streamTime[stream]!=(fno,ftime):
                    #print "plotting...",fno,ftime
                    self.plot.mytoolbar.subapLocation=self.subapLocation
                    self.plot.mytoolbar.npxlx=self.npxlx
                    self.plot.mytoolbar.npxly=self.npxly
                    self.plot.mytoolbar.nsub=self.nsub
                    #self.plot.mytoolbar.nsuby=self.nsuby
                    self.plot.mytoolbar.subapFlag=self.subapFlag
                    
                    self.plot.mytoolbar.stream[stream]=data
                    self.plot.mytoolbar.streamName=stream
                    self.plot.mytoolbar.streamTime[stream]=fno,ftime
                    self.plot.mytoolbar.streamTimeTxt="%10d %9s%03d"%(fno,time.strftime("%H:%M:%S.",time.localtime(ftime)),(ftime%1)*1000)
                    if "rtcStatusBuf" in stream or stream=="Sta":
                        self.plot.mytoolbar.mangleTxtDefault="import darc;data=darc.statusBuf_tostring(data)"
                    else:
                        self.plot.mytoolbar.mangleTxtDefault=""
                    self.plot.plot(data)
                else:
                    #print "not replotting"
                    pass
                # I dont think we need to do owt bout overlays - are created by mangle each time, and stored in store if necessary.
            
    def readSHM(self,stream):
        """The shared memory has a 64 byte header, and then the data.
        The header contains: dtype(1),nd(1),deadflag(1),writingflag(1),6xdimensions(24), frame number (4), frame time (8), 24 spare.
        If writing flag is set, don't bother doing anything - this means the next bit data is being written, and we'll be informed in due course.
        If deadflag is set, means the shm is no longer in use, and should be closed, and possibly repoened.
        IF nd or shape change, then deadflag will be set.  IE nd and shape are constant for the lifetime of the shm.
        """
        data=None
        ftime=0.
        fno=0
        shm=self.shmDict.get(stream)
        if shm is None:
            #try opening it...
            shm=self.openSHM(stream)
            if shm is not None:
                self.shmDict[stream]=shm
        if shm is not None:
            hdr,data=shm
            if hdr[2]==1:#dead flag - data no longer valid
                data=None
                del(self.shmDict[stream])
                shm=self.openSHM(stream)
                if shm is not None:#have reopened successfully.
                    hdr,data=shm
                    self.shmDict[stream]=hdr,data
            if hdr[3]==1:#writing flag - data invalid this time.
                data=None
        if data is not None:
            fno=hdr[:64].view(numpy.int32)[7]
            ftime=hdr[:64].view(numpy.float64)[4]
            data=numpy.array(data)#copy from shm to array...
        return data,fno,ftime

    def openSHM(self,stream):
        """Attempt to open the SHM array
        Return None, or (shm,reformatted data)
        """
        try:
            hdr=numpy.memmap(devshm+self.shmtag+stream,dtype=numpy.uint8,mode="r",shape=(64,))
            if hdr[2]==1:#dead flag
                hdr=None
        except:
            hdr=None
        data=None
        if hdr is not None and hdr[1]>0:
            size=reduce(lambda x,y:x*y,hdr.view(numpy.int32)[1:1+hdr[1]])
            if size>0:
                elsize={'f':4,'d':8,'i':4,'h':2,'b':1,'H':2}[hdr[0].view('c')]
                try:
                    data=numpy.memmap(devshm+self.shmtag+stream,dtype=numpy.uint8,mode="r",shape=(64+size*elsize,))
                    if data[2]==1:#dead flag
                        data=None
                except:
                    data=None
                if not numpy.alltrue(hdr[:3]==data[:3]) or not numpy.alltrue(hdr[4:28]==data[4:28]):
                    data=None
        del(hdr)
        if data is not None:
            d=data[64:].view(data[0].view('c'))
            d.shape=data[:64].view(numpy.int32)[1:1+data[1]]
            data=(data,d)
        return data

            
            
    def process(self):#,readSock=1):
        try:
            self.conndata,valid=serialise.Recv(self.conn,self.conndata)
        except:#disconnected
            valid=0
            self.conn=None
            self.conndata=None
        if valid:
            data=self.conndata
            self.conndata=None
            data=serialise.Deserialise(data)[0]
            if type(data)==type(None):
                self.conn=None#disconnected
            else:
                if data[0]=="new":#new stream
                    self.addStream(data[1])
                elif data[0]=="upd":#new data from a stream
                    self.updateStream(data[1])
                elif data[0]=="del":#remove stream
                    self.delStream(data[1])
                elif data[0]=="sav":#save state of plot... (send to GUI)
                    pos=self.plot.win.get_position()
                    size=self.plot.win.get_size()
                    serialise.Send(["sav",pos,size,self.plot.mytoolbar.toolbarVisible,self.plot.mytoolbar.tbVal,self.plot.mytoolbar.mangleTxt,self.subscribeList],self.conn)
                elif data[0]=="end":
                    gtk.main_quit()
                elif data[0]=="sub":#a new subapLocation...
                    print("plot updating subaplocation")
                    self.subapLocation=data[1]
                    self.npxlx=data[2]
                    self.npxly=data[3]
                    self.nsub=data[4]
                    #self.nsuby=data[5]
                    self.subapFlag=data[5]
                elif data[0]=="dat":#this is only used on windoze where the shared memory stuff doesn't work - a quick fix - send the stream to each plot - even if they're not subscribed to it...
                    self.updateStream(data[1],data[2:5])
                    
    def handleData(self,source,condition):
        self.process()
        if self.conn is None:#connection has been closed
            print("Plotter connection closed remotely")
            if self.sockID is not None:
                gobject.source_remove(self.sockID)#gtk.input_remove(self.sockID)
                self.sockID.stop()
            self.sockID=None
        return self.conn is not None

class StdinServer(QtC.QObject):
    def __init__(self):
        self.go=1
        self.lastwin=0
        self.plotdict={}
        self.stdinwatcher = WatchStdIn(self.handleInput,self.quit)
        self.stdinwatcher.start()
        # gobject.io_add_watch(sys.stdin,gobject.IO_IN,self.handleInput)
        # gobject.io_add_watch(sys.stdin,gobject.IO_HUP,self.quit)
        self.data=None

    def quit(self):
        self.destroy()
        return True
        
    def newplot(self):
        p=plot(usrtoolbar=plotToolbar)
        p.buttonPress(None,3)
        p.txtPlot.hide()
        p.txtPlot.hide()
        p.image.hide()
        return p
    
    def handleInput(self):
        data=serialise.ReadMessage(sys.stdin)
        if type(data)==type([]):
            if len(data)>1:
                win=data[0]
                data=data[1]
            else:
                win=self.lastwin
                data=data[0]
            if win is None:
                win=self.lastwin
            self.lastwin=win
            if win not in self.plotdict or self.plotdict[win].active==0:
                self.plotdict[win]=self.newplot()
            p=self.plotdict[win]

            p.plot(data)
        return True

    def handleInputAsync(self,source,cbcondition,a=None):
        print("Handle input")
        #data=serialise.ReadMessage(sys.stdin)
        self.data,valid=serialise.Recv(source,self.data)
        if valid:
            data=serialise.Deserialise(self.data)[0]
            self.data=None
            if type(data)==type([]) and len(data)>0:
                data=data[0]
            self.p.plot(data)
        return True


class DarcReader(QtC.QObject):
    grabSignal = QtC.pyqtSignal()
    def __init__(self,streams,myhostname=None,prefix="",dec=25,configdir=None,withScroll=0,showPlots=1,window=None,qtapp=None):
        super().__init__()
        import darc
        self.paramTag=0
        self.streams=streams#[]
        self.prefix=prefix
        self.plotWaitingDict={}
        l=len(prefix)

        self.c=darc.Control(prefix)
        cnt=1
        while self.c.obj is None and cnt>0:
            cnt-=1
            time.sleep(1)
            self.c.connect()#=darc.Control(prefix)
        self.paramSubList=[]
        self.p=plot(usrtoolbar=plotToolbar,loadFunc=self.loadFunc,scrollWin=withScroll,label=prefix,qtapp=qtapp)
        self.p.rightMouseClick()
        self.p.mytoolbar.loadFunc=self.p.loadFunc
        self.p.mytoolbar.redrawFunc=self.p.plot
        self.p.txtPlot.hide()
        self.p.txtPlot.hide()
        self.p.image.hide()
        try:
            self.p.mytoolbar.subapLocation=self.c.Get("subapLocation")
            self.p.mytoolbar.npxlx=self.c.Get("npxlx")
            self.p.mytoolbar.npxly=self.c.Get("npxly")
            self.p.mytoolbar.nsub=self.c.Get("nsub")
            self.p.mytoolbar.prefix=prefix
            self.p.mytoolbar.darc=self.c
        #self.p.mytoolbar.nsuby=self.c.Get("nsuby")
            self.p.mytoolbar.subapFlag=self.c.Get("subapFlag")
        except:
            traceback.print_exc()
            print("Unable to get plot info - continuing")
        self.streamDict={}#Entries (short description, long description)
        #get the list of streams.
        try:
            keys=list(self.c.GetDecimation(local=0,withPrefix=0).keys())+list(self.c.GetDecimation(remote=0,withPrefix=0)['local'].keys())
            for k in keys:
                self.streamDict[k]=(k,k)
        except:
            traceback.print_exc()
            print("Unable to get stream list")
            
        self.subscribeDict={}#entry for each stream subscribed too, (sub,dec) where sub is a flag, whether subscribed or not and dec is the decimation
        for s in streams:
            self.subscribeDict[s]=(1,dec)
        self.p.mytoolbar.subscribeDict=self.subscribeDict
        self.subWid=SubWid(self.subscribe,self.p,self.grab,self.setLocalDec,parent=self.p)
        print("got the subwid")
        self.threadNotNeededList=[]
        print(streams,configdir)
        if len(streams)==0:    
            #need to pop up the subscribbe widget...
            #the user can then decide what to sub to.
            #self.subWid.show(self.streamDict,self.subscribeDict)
            if configdir is None:
                print("showing streams 1")
                self.showStreams()
            else:#show a list of files.
                pass

            self.threadStreamDict={}
        else:
            self.threadStreamDict={}
            try:
                self.subscribe([(x,1,dec) for x in self.streams])
            except:
                print("showing streams 2")
                self.showStreams()
                traceback.print_exc()
                print("Unable to subscribe - continuing...")
        self.p.mytoolbar.initialise(self.showStreams,configdir)
        if len(streams)==0 and configdir is not None and showPlots:
            #show a list of the plotfiles available.
            self.p.mytoolbar.displayFileList(self.p)

        self.ptgo = numpy.ones(1,dtype=int)
        self.pt = threading.Thread(target=self.paramThread,args=(self.ptgo,))
        self.pt.daemon = False
        self.pt.start()

        print("finished init of reader")

        self.grabSignal.connect(self.grabTrigger)
        self.p.plotClosedSignal.connect(self.quit)
    
    def quit(self):
        print("quitting darcreader:")
        self.ptgo[0] = 0
        self.c.Set("plotFlag",0)
        self.pt.join()
        slist = []
        for key in list(self.subscribeDict.keys()):
            slist.append((key,0,self.subscribeDict[key][1]))
        for key,val in self.threadStreamDict.items():
            print(key,val)
        self.subscribe(slist)
        for val in self.threadNotNeededList:
            print(val)
            val.join()
        if self.c.newconn is not None:
            self.c.newconn.close()
        self.c.conn.close()
        print(":finished quiting")

    def doplotTrigger(self):
        self.doplot(*self.doplotArgs)

    def grabTrigger(self):
        self.grab(*self.grabArgs)

    def paramThread(self,golist):
        """Watches params, and updates plots as necessary"""
        import darc
        while golist[0]:
            print("goparam",golist[0])
            reconnect=0
            restart=0
            try:
                print("watching param")
                self.paramTag,changed=self.c.WatchParam(self.paramTag,["subapLocation","npxlx","npxly","nsub","subapFlag","plotFlag"]+self.paramSubList)
                #print "plot WatchParam %s"%str(changed)#Note, this also wakes up if the rtc is stopped - ie all params changed since it has stopped.
                #At the moment, this only works for the first plot chosen (until one of the main parameters changes).
                print("param watched")
            except:
                time.sleep(1)
                traceback.print_exc()
                reconnect=1
            if reconnect==0:
                try:
                    nchanged=0
                    if "plotFlag" in changed:
                        if self.c.Get("plotFlag") == 0:
                            print("Ending WatchParam")
                            break
                    if "subapLocation" in changed:
                        self.p.mytoolbar.subapLocation=self.c.Get("subapLocation")
                        nchanged+=1#only the core things should add to this.
                    if "npxlx" in changed:
                        self.p.mytoolbar.npxlx=self.c.Get("npxlx")
                        nchanged+=1
                    if "npxly" in changed:
                        self.p.mytoolbar.npxly=self.c.Get("npxly")
                        nchanged+=1
                    if "nsub" in changed:
                        self.p.mytoolbar.nsub=self.c.Get("nsub")
                        nchanged+=1
                    if "subapFlag" in changed:
                        self.p.mytoolbar.subapFlag=self.c.Get("subapFlag")
                        nchanged+=1
                    if nchanged==5:#all change - may have been a restart.
                        restart=1
                    for par in self.paramSubList:
                        if par in changed:
                            try:
                                self.p.mytoolbar.store[par]=self.c.Get(par)
                            except:
                                if par in self.p.mytoolbar.store:
                                    del(self.p.mytoolbar.store[par])
                    if restart:
                        #resubscribe to the data
                        slist=[]
                        for key in list(self.subscribeDict.keys()):
                            slist.append((key,self.subscribeDict[key][0],self.subscribeDict[key][1]))
                        print("Resubscribing")
                        print(slist)
                        self.subscribe(slist)
                        keys=list(self.c.GetDecimation(local=0,withPrefix=0).keys())+list(self.c.GetDecimation(remote=0,withPrefix=0)['local'].keys())
                        for k in keys:
                            self.streamDict[k]=(k,k)


                except:
                    reconnect=1
                    traceback.print_exc()
            if reconnect:
                try:
                    self.c.echoString("Test")
                    reconnect=0
                except:
                    pass
            if reconnect:
                try:
                    self.c=darc.Control(self.prefix)
                    while self.c.obj is None:
                        time.sleep(1)
                        self.c.connect()#=darc.Control(self.prefix)
                    self.p.mytoolbar.darc=self.c
                    restart=1
                    if restart:
                        #resubscribe to the data
                        slist=[]
                        for key in list(self.subscribeDict.keys()):
                            slist.append([key,self.subscribeDict[key][0],self.subscribeDict[key][1]])
                        print("Resubscribing after connection")
                        self.subscribe(slist)
                        keys=list(self.c.GetDecimation(local=0,withPrefix=0).keys())+list(self.c.GetDecimation(remote=0,withPrefix=0)['local'].keys())
                        for k in keys:
                            self.streamDict[k]=(k,k)

                except:
                    traceback.print_exc()
        print("Param thread exiting")

    def setLocalDec(self,stream,dec):
        print("setting local decimation rate")
        import buffer
        if len(self.prefix)>0 and not stream.startswith(self.prefix):
            stream=self.prefix+stream
        cb=buffer.Circular("/"+stream)
        cb.freq[0]=dec

    def loadFunc(self,label,data=None,fname=None,args=None):
        if type(label)==type(""):
            #image data - do nothing
            theplot=None
        elif label is None:#want to unsubscribe from everything
            theplot=None
            self.paramSubList=[]
        else:
            #label is a plot list
            plotList=label
            #select the plot we want, return it, first subscribing as appropriate
            indx=0
            theplot=plotList[indx]
            sub=theplot[4]
            initcode=theplot[7]
            if len(theplot)>=8:
                self.paramSubList=theplot[8]#won't take effect until one of the existing parameters changes, unfortunately.
            if len(initcode)>0:
                d={"darc":self.c,"numpy":numpy,"prefix":self.prefix}
                print("Executing plot initialisation code...")
                try:
                    exec(initcode, d)
                except:
                    traceback.print_exc()
            
            if type(sub)!=type([]):
                sub=[sub]
            csub=[]
            for s in sub:
                s=list(s)
                csub.append(s)
            sub=csub
            slist=[x[0] for x in sub]
            #unsubscribe from everything we don't want...
            for s in list(self.threadStreamDict.keys()):
                if s not in slist:
                    sub.append((s,0,0))
            print(sub)
            self.subscribe(sub)
            #self.showStreams()
        return theplot

    def grab(self,stream,latest=0,t=None):
        if t is None:#start the thread to grab data
            if type(stream) is str:
                print("Starting grab thread:")
                t=threading.Thread(target=self.grab,args=(stream,latest,1))
                # t._Thread__args=(stream,latest,t)
                t.start()
            else:#end the thread.
                t=stream[3]
                t.join()
                self.doplot(stream[:3])
        else:#run the thread (grab the data)
            wholeBuffer=0
            if "rtcTimeBuf" in stream:
                wholeBuffer=1
            print("doing GetStream()")
            data=self.c.GetStream(stream,latest=latest,wholeBuffer=wholeBuffer)
            if wholeBuffer:
                data[0].shape=data[0].size
            self.doplot(["data",stream,data])
            # self.grabArgs = (["data",stream,data,t],)
            # self.grabSignal.emit()
            print(":Ending grab thread")

    def plotdata(self,data):
        rt=1-self.p.active
        if self.p.active:
            stream=data[1]
            if threading.currentThread() in self.threadNotNeededList:
                print("true")
                self.threadNotNeededList.remove(threading.currentThread())
                rt=1
                print("Thread not needed %s"%stream)
            elif stream in self.subscribeDict and self.subscribeDict[stream][0]==1:
                if self.plotWaitingDict.get(stream,None) is None:
                    self.plotWaitingDict[stream]=data
                    self.doplot(stream)#,data)
                else:
                    self.plotWaitingDict[stream]=data
            else:
                print("else")
                rt=1#unsibscribe from this stream.
                print("Unsubscribing %s"%stream)
        return rt

    def doplot(self,data):
        if type(data)==type(""):
            stream=data
            data=self.plotWaitingDict.get(data)
            self.plotWaitingDict[stream]=None
        if data is not None:
            stream=data[1]
            fno=data[2][2]
            ftime=data[2][1]
            data=data[2][0]
            #remove prefix - plot doesn't need to know about that...
            if stream.startswith(self.prefix):
                stream=stream[len(self.prefix):]

            self.p.mytoolbar.stream[stream]=data
            self.p.mytoolbar.streamName=stream
            self.p.mytoolbar.streamTime[stream]=fno,ftime
            self.p.mytoolbar.streamTimeTxt="%10d %9s%03d"%(fno,time.strftime("%H:%M:%S.",time.localtime(ftime)),(ftime%1)*1000)
            if "rtcStatusBuf" in stream or stream=="Sta":
                self.p.mytoolbar.mangleTxtDefault="import darc;data=darc.statusBuf_tostring(data)"
            else:
                self.p.mytoolbar.mangleTxtDefault=""
            self.p.plotArgs = (data,)
            self.p.plotSignal.emit()

    def showStreams(self,w=None,a=None):
        if self.subWid is not None:
            if a=="resubscribe":
                if len(self.subWid.streamDict)==0:
                    sl=[]
                    for key in list(self.subscribeDict.keys()):
                        sl.append((key,1,self.subscribeDict[key][1]))
                    self.subscribe(sl)
                else:
                    self.subWid.resubscribe()
            else:
                #should I update the list of streams here?
                orig=list(self.streamDict.keys())
                print("orig:",orig)
                try:
                    print("trying for decimation")
                    keys=list(self.c.GetDecimation(local=0,withPrefix=0).keys())
                    keys+=list(self.c.GetDecimation(remote=0,withPrefix=0)['local'].keys())
                    for k in keys:
                        self.streamDict[k]=(k,k)
                    for k in orig:
                        if k not in keys:
                            self.streamDict[k]=(k+" (dead?)",k+" (dead?)")
                    print("got decimation")
                except:
                    print("Plot error updating stream list - may be out of date")
                self.subWid.show(self.streamDict,self.subscribeDict)#,self.c.GetDecimation())

    def subscribe(self,slist):
        """slist is a list of tuples of (stream,subscribe flag,decimate).
        """
        if type(slist)!=type([]):
            slist=[slist]
        #print slist
        for s in slist:
            if s[1]:#subscribe to it
                #But - what if we're already subscribed?  How do we remove the thread.
                if s[0] in self.threadStreamDict:
                    self.threadNotNeededList.append(self.threadStreamDict[s[0]])
                print("doing GetStreamBlock()")
                self.threadStreamDict[s[0]]=self.c.GetStreamBlock([s[0]],-1,callback=self.plotdata,decimate=s[2],sendFromHead=1,returnthreadlist=1,resetDecimate=0)[0]
                self.subscribeDict[s[0]]=s[1:]
            else:#unsubscribe
                if s[0] in self.subscribeDict:
                    del(self.subscribeDict[s[0]])
                if s[0] in self.threadStreamDict:
                    self.threadNotNeededList.append(self.threadStreamDict[s[0]])
                    del(self.threadStreamDict[s[0]])
        self.p.mytoolbar.subscribeDict=self.subscribeDict


if __name__=="__main__":
    if len(sys.argv)==2 and sys.argv[1]=="STDIN":#assume stdin has data, serialised.
        app = QtW.QApplication(sys.argv)
        p=StdinServer()
        sys.exit(app.exec())
    else:
        port=None
        arglist=[]
        streams=[]
        dec=25
        prefix=""
        mangle=""
        configdir=os.path.split(__file__)[0]+"/../conf"
        if not os.path.exists(configdir):
            configdir=None
        withScroll=0
        fname=None
        index=None
        configdirset=0
        #myhostname=None
        i=0
        while i<len(sys.argv)-1:#for i in range(len(sys.argv)-1):#arg in sys.argv[1:]:
            i+=1
            arg=sys.argv[i]
            if arg[:2]=='-s':
                streams=arg[2:].split(",")
            elif arg[:2]=="-d":
                dec=int(arg[2:])
            elif arg[:2]=="-p":
                prefix=arg[2:]
            elif arg[:2]=="-m":
                mangle=arg[2:]
                if mangle=="" and len(sys.argv)>i+1:
                    i+=1
                    mangle=sys.argv[i]
            elif "--prefix=" in arg:
                prefix=arg[9:]
            elif "-c" in arg:
                configdirset=1
                configdir=arg[2:]
                if configdir=="" and len(sys.argv)>i+1:
                    i+=1
                    configdir=sys.argv[i]
            elif "--configdir=" in arg:
                configdirset=1
                configdir=arg[12:]
            elif "--with-scroll" in arg:
                withScroll=1
            elif arg[:2]=="-f":
                fname=arg[2:]#config file name
            elif arg[:2]=="-i":
                index=int(arg[2:])#index for plot in config file
            #elif arg[:2]=="-h":
            #    myhostname=arg[2:]
            else:
                arglist.append(arg)
        if len(arglist)>0:
            if os.path.exists(arglist[0]):#a config file
                fname=arglist.pop(0)
                if len(arglist)>0:
                    index=int(arglist.pop(0))
                #if len(arglist)>0:
                #    myhostname=arglist.pop(0)
                if len(arglist)>0:
                    if prefix=="":
                        prefix=arglist.pop(0)
                        try:
                            dec=int(prefix)
                            prefix=""
                        except:
                            pass
                if len(arglist)>0:
                    dec=int(arglist.pop(0))

            else:#or a list of streams
                streams+=arglist.pop(0).split(",")
                while len(arglist)>0:
                    arg=arglist.pop(0)
                    try:
                        dec=int(arg)
                    except:
                        if prefix=="":
                            prefix=arg
                        elif mangle=="":
                            mangle=arg
        if fname is not None and configdirset==0:
            configdir=os.path.split(fname)[0]
        app = QtW.QApplication(sys.argv)
        d=DarcReader(streams,None,prefix,dec,configdir,withScroll,showPlots=(fname is None),qtapp=app)
        if fname is not None:
            print("Loading %s"%fname)
            if index is None:
                #not specified, so load them all...
                with open(fname,'r') as xf:
                    nplots=len(plotxml.parseXml(xf.read()).getPlots())
                index=0
                for i in range(1,nplots):
                    #spawn the plots...
                    subprocess.Popen(sys.argv+["-i%d"%i])

            d.p.loadFunc(fname,index=index)
            d.subWid.hide()
        elif mangle is not None:
            d.p.mytoolbar.dataMangleEntry.setText(mangle)
            d.p.mytoolbar.mangleTxt=mangle
        sys.exit(app.exec())
        




"""For multiplot, can use something like:
import darc,plot,gtk,os
gtk.gdk.threads_init()
configdir=os.path.split(globals().get("__file__",""))[0]+"/../conf"
if not os.path.exists(configdir):
 if os.path.exists("/rtc/conf/"):
  configdir="/rtc/conf"
 else:
  configdir=None

w=QtW.QMainWindow()
v=QtW.QVBoxLayout()
f1=gtk.Frame()
f2=gtk.Frame()
v.addWidget(f1,True)
v.addWidget(f2,True)
w.add(v)
p1=plot.DarcReader([],configdir=configdir,withScroll=1,window=f1)
p2=plot.DarcReader([],configdir=configdir,withScroll=1,window=f2)
def quit(w,a=None):
 p1.p.quit(w)
 p2.p.quit(w)
 gtk.main_quit()

w.connect("delete-event",quit)
w.show_all()
gtk.main()#note - currently doesn't quit cleanly!
"""
