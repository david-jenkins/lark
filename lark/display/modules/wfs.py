from concurrent.futures import thread
from pathlib import Path
import sys
import logging
import subprocess
import time
import datetime
import inspect

from lark import LarkConfig
import lark
from lark.darcconfig import gen_subapParams
from lark.display.widgets.toolbar import CircleItem, LineItem, PlotToolbar
from lark.rpyclib.interface import connectClient
from lark.rpyclib.rpyc_brine import copydict
import numpy
from lark.darc import FITS
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG
from lark.display.wfs import WfsImages
from lark.display.widgets.main_base import SubTabWidget, TabWidget
from lark.utils import generatePyrParams, statusBuf_tostring

import pyqtgraph as pg

from lark.display.widgets.plotting import FRAMERATE, Plot2D, Plotter

FRAMERATE = 1

from astropy.io import fits
import os

class CalibrationWindowBoth(QtW.QWidget):
    def __init__(self, pyrconfig:LarkConfig, scoringconfig:LarkConfig, parent=None):
        super().__init__()
        
        self.pyrconfig = pyrconfig
        self.scoringconfig = scoringconfig

        self.parent = parent

        self.vlay = QtW.QVBoxLayout()
        self.setLayout(self.vlay)

        self.hlays = []

        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])

        self.ocamfpslabel = QtW.QLabel("OCAM FPS:")
        self.evtfpslabel = QtW.QLabel("EVT FPS:")
        self.ocamfpsbox = QtW.QSpinBox()
        self.ocamfpsbox.valueChanged.connect(self.update_filenamepreview)
        self.evtfpsbox = QtW.QSpinBox()
        self.evtfpsbox.valueChanged.connect(self.update_filenamepreview)

        self.ocamgainlabel = QtW.QLabel("OCAM GAIN:")
        self.evtgainlabel = QtW.QLabel("EVT GAIN:")
        self.ocamgainbox = QtW.QSpinBox()
        self.ocamgainbox.valueChanged.connect(self.update_filenamepreview)
        self.evtgainbox = QtW.QSpinBox()
        self.evtgainbox.valueChanged.connect(self.update_filenamepreview)

        self.hlays[-1].addWidget(self.ocamfpslabel)
        self.hlays[-1].addWidget(self.ocamfpsbox,2)
        self.hlays[-1].addStretch(1)
        self.hlays[-1].addWidget(self.evtfpslabel)
        self.hlays[-1].addWidget(self.evtfpsbox,2)
        self.hlays[-1].addStretch(1)
        self.hlays[-1].addWidget(self.ocamgainlabel)
        self.hlays[-1].addWidget(self.ocamgainbox,2)
        self.hlays[-1].addStretch(1)
        self.hlays[-1].addWidget(self.evtgainlabel)
        self.hlays[-1].addWidget(self.evtgainbox,2)

        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        self.takedarksbutton = QtW.QPushButton("Take DARK Images")
        self.takedarksbutton.clicked.connect(self.takedarks_callback)
        self.saveimstext = QtW.QLineEdit()
        self.saveimstext.setToolTip("Files saved to darc_images folder")
        self.saveimstext.textChanged.connect(self.update_filenamepreview)
        self.saveimsspin = QtW.QSpinBox()
        self.saveimsspin.setRange(1, 500)
        self.saveimsspin.setValue(100)
        self.saveimslabel = QtW.QLabel("Filename:")
        self.ds9button = QtW.QPushButton("Open DS9")
        self.ds9button.clicked.connect(self.opends9_callback)
        self.hlays[-1].addWidget(self.takedarksbutton)
        self.hlays[-1].addWidget(self.saveimslabel)
        self.hlays[-1].addWidget(self.saveimstext)
        self.hlays[-1].addWidget(self.saveimsspin)
        self.hlays[-1].addWidget(self.ds9button)

        self.filenamepreview = QtW.QLabel("Filename preview:\n")

        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        self.applybutton = QtW.QPushButton("Apply DARK Calibration")
        self.applybutton.clicked.connect(self.apply_callback)
        self.loadbutton = QtW.QPushButton("Load DARK Image")
        self.loadbutton.clicked.connect(self.load_image_callback)
        self.fnamelabel = QtW.QLabel()

        self.hlays[-1].addWidget(self.applybutton)
        self.hlays[-1].addWidget(self.fnamelabel)
        self.hlays[-1].addWidget(self.loadbutton)

        # self.filenamelabel = QtW.QLabel("Filename:")
        # self.hlays.append(QtW.QHBoxLayout)
        # self.vlay.addLayout(self.hlays[-1])
        # self.hlays[-1].addWidget(self.filenamelabel)
        self.vlay.addWidget(self.filenamepreview)

        self.ocam_dark = None
        self.evt_dark = None

        self.dir_path = Path("~/darc_images/dark_frames/").expanduser()
        self.dir_path.mkdir(parents=True, exist_ok=True)
        self.update_filenamepreview()

    def takedarks_callback(self):
        try:
            ocamfps = self.ocamfpsbox.value()
            evtfps = self.evtfpsbox.value()
            ocamgain = self.ocamgainbox.value()
            evtgain = self.evtgainbox.value()

            self.parent.setfpsspin.setValue(ocamfps)
            self.parent.setfpsspin2.setValue(evtfps)
            self.parent.setgainspin.setValue(ocamgain)
            self.parent.setgainspin2.setValue(evtgain)

            self.parent.setocamfps_callback()
            self.parent.setevtfps_callback()
            self.parent.setocamgain_callback()
            self.parent.setevtgain_callback()

            this_darc = self.pyrconfig.getlark()

            N = self.saveimsspin.value()

            ims = this_darc.getStreamBlock("rtcPxlBuf",N)["rtcPxlBuf"][0].mean(0)

            npxlx = this_darc.Get("npxlx")
            npxly = this_darc.Get("npxly")

            self.ocam_dark = ims[:npxlx[0]*npxly[0]]
            self.evt_dark = ims[npxlx[0]*npxly[0]:]
            print(self.ocam.shape, self.evt.shape)
            self.ocam.shape = npxly[0],npxlx[0]
            self.evt.shape = npxly[1],npxlx[1]

            self.update_filenamepreview()
            self.curr_name = self.fname

            # fits.writeto(f'{fname}.fits', ims)

            # FITS.Write(ocam,fname1)
            fits.writeto(self.curr_name+"_ocam.fits",self.ocam)
            # FITS.Write(evt,fname2)
            fits.writeto(self.curr_name+"_evt.fits",self.evt)

            self.opends9_callback(fname=self.curr_name+"_ocam.fits")
            self.opends9_callback(fname=self.curr_name+"_evt.fits")
            self.fnamelabel.setText(self.curr_name)
        except Exception as e:
            print(e)

    def opends9_callback(self,event=False,fname=None):
        self.parent.opends9_callback(fname=fname)

    def apply_callback(self):
        try:
            fname = self.curr_name
            if fname == "":
                return None
            this_darc = self.pyrconfig.getlark()
            npxlx = this_darc.Get("npxlx")
            npxly = this_darc.Get("npxly")
            if self.ocam_dark is None:
                if os.path.exists(fname+"_ocam.fits"):
                    self.ocam_dark = fits.getdata(fname+"_ocam.fits").flatten()
                else:
                    self.ocam_dark = numpy.zeros(npxlx[0]*npxly[0])
            if self.evt_dark is None:
                if os.path.exists(fname+"_evt.fits"):
                    self.evt_dark = fits.getdata(fname+"_evt.fits").flatten()
                else:
                    self.evt_dark = numpy.zeros(npxlx[0]*npxly[0])
            dark = numpy.empty(npxlx[0]*npxly[0]+npxlx[1]*npxly[1],dtype=float)
            dark[:npxly[0]*npxlx[0]] = self.ocam_dark.astype(float)
            dark[npxly[0]*npxlx[0]:] = self.evt_dark.astype(float)
            this_darc.set("bgImage",dark)
        except Exception as e:
            print(e)

    def load_image_callback(self):
        fname = QtW.QFileDialog.getOpenFileName(self, 'Open file', str(self.dir_path),"FITS files (*.fits)",options=QtW.QFileDialog.DontUseNativeDialog)[0]
        fname = fname.split("_ocam.fits")[0]
        fname = fname.split("_evt.fits")[0]

        this_darc = self.pyrconfig.getlark()
        npxlx = this_darc.Get("npxlx")
        npxly = this_darc.Get("npxly")

        if os.path.exists(fname+"_ocam.fits"):
            self.ocam_dark = fits.getdata(fname+"_ocam.fits").flatten()
        else:
            self.ocam_dark = numpy.zeros(npxlx[0]*npxly[0])
        if os.path.exists(fname+"_evt.fits"):
            self.evt_dark = fits.getdata(fname+"_evt.fits").flatten()
        else:
            self.evt_dark = numpy.zeros(npxlx[0]*npxly[0])

        self.curr_name = fname

        self.fnamelabel.setText(self.curr_name)

    def update_filenamepreview(self):
        ocamfps = self.ocamfpsbox.value()
        evtfps = self.evtfpsbox.value()
        ocamgain = self.ocamgainbox.value()
        evtgain = self.evtgainbox.value()
        now = datetime.datetime.now()
        text = self.filenamepreview.text().split("\n")[0] + "\n"
        fname = self.saveimstext.text()
        if fname != "":
            fname += "_"
        self.fname = str(self.dir_path / fname)
        self.fname += f"oc{ocamfps}-{ocamgain}evt{evtfps}-{evtgain}_"
        self.fname += f"{now.year:0>4}-{now.month:0>2}-{now.day:0>2}T{now.hour:0>2}{now.minute:0>2}{now.second:0>2}"
        text += self.fname
        self.filenamepreview.setText(text)

class CamControl_base(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        
        self.vlay = QtW.QVBoxLayout()
        self.hlays = []
        
        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        self.setfpsbutton = QtW.QPushButton("Set OCAM FPS")
        self.setfpsspin = QtW.QSpinBox()
        self.setfpsspin.setRange(0, 1500)
        self.setfpsspin.setValue(100)
        self.hlays[-1].addWidget(self.setfpsbutton,1)
        self.hlays[-1].addWidget(self.setfpsspin,1)

        self.hlays[-1].addStretch(1)

        self.setfpsbutton2 = QtW.QPushButton("Set Scoring FPS")
        self.setfpsspin2 = QtW.QSpinBox()
        self.setfpsspin2.setRange(0, 1500)
        self.setfpsspin2.setValue(100)
        self.hlays[-1].addWidget(self.setfpsbutton2,1)
        self.hlays[-1].addWidget(self.setfpsspin2,1)

        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        self.setgainbutton = QtW.QPushButton("Set OCAM GAIN")
        self.setgainspin = QtW.QSpinBox()
        self.setgainspin.setRange(1, 600)
        self.setgainspin.setValue(1)
        self.hlays[-1].addWidget(self.setgainbutton,1)
        self.hlays[-1].addWidget(self.setgainspin,1)

        self.hlays[-1].addStretch(1)

        self.setgainbutton2 = QtW.QPushButton("Set Scoring GAIN")
        self.setgainspin2 = QtW.QSpinBox()
        self.setgainspin2.setRange(1, 10000)
        self.setgainspin2.setValue(1)
        self.hlays[-1].addWidget(self.setgainbutton2,1)
        self.hlays[-1].addWidget(self.setgainspin2,1)

        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])

        self.showcalibwinbutton = QtW.QPushButton("Image Calibration")

        self.hlays[-1].addWidget(self.showcalibwinbutton,1)

        self.hlays[-1].addStretch(2)

        self.setexpbutton = QtW.QPushButton("Set Scoring EXPOSURE")
        self.setexpspin = QtW.QSpinBox()
        self.setexpspin.setRange(1, 1000000)
        self.setexpspin.setValue(10000)
        self.hlays[-1].addWidget(self.setexpbutton,1)
        self.hlays[-1].addWidget(self.setexpspin,1)
        
        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        
        self.useshutter_button = QtW.QPushButton("Use Shutter")
        self.noshutter_button = QtW.QPushButton("Shutter Off")
        self.hlays[-1].addWidget(self.useshutter_button,1)
        self.hlays[-1].addWidget(self.noshutter_button,1)
        self.hlays[-1].addStretch(3)
        
        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        
        self.intread_button = QtW.QPushButton("Internal Read-out")
        self.extread_button = QtW.QPushButton("External Read-out")
        self.hlays[-1].addWidget(self.intread_button,1)
        self.hlays[-1].addWidget(self.extread_button,1)
        self.hlays[-1].addStretch(3)

        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        self.saveimsbutton = QtW.QPushButton("Save Images")
        self.saveimstext = QtW.QLineEdit()
        self.saveimstext.setToolTip("Files saved to darc_images folder")
        self.saveimsspin = QtW.QSpinBox()
        self.saveimsspin.setRange(1, 100)
        self.saveimsspin.setValue(10)
        self.saveimslabel = QtW.QLabel("Filename:")
        self.ds9button = QtW.QPushButton("Open DS9")
        self.hlays[-1].addWidget(self.saveimsbutton)
        self.hlays[-1].addWidget(self.saveimslabel)
        self.hlays[-1].addWidget(self.saveimstext)
        self.hlays[-1].addWidget(self.saveimsspin)
        self.hlays[-1].addWidget(self.ds9button)
        
        self.setLayout(self.vlay)

        self.menu = QtW.QMenu("OCAM",self)

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

class CamControl(CamControl_base):
    def __init__(self, pyrconfig:LarkConfig, scoringconfig:LarkConfig, iportsrtc, parent=None):
        super().__init__(parent=parent)
        
        self.pyrconfig = pyrconfig
        self.scoringconfig = scoringconfig
        self.iportsrtc_name = iportsrtc
        
        self.setfpsbutton.clicked.connect(self.setocamfps_callback)

        self.setfpsbutton2.clicked.connect(self.setevtfps_callback)

        self.setgainbutton.clicked.connect(self.setocamgain_callback)

        self.setgainbutton2.clicked.connect(self.setevtgain_callback)

        self.calwin = CalibrationWindowBoth(pyrconfig, scoringconfig, self)
        self.calwin.installEventFilter(self)
        self.showcalibwinbutton.clicked.connect(self.calwin.show)
        self.showcalibwinbutton.setEnabled(False)
        
        self.noshutter_button.clicked.connect(self.noshutter_callback)
        self.useshutter_button.clicked.connect(self.useshutter_callback)
        
        self.intread_button.clicked.connect(self.intread_callback)
        self.extread_button.clicked.connect(self.extread_callback)

        self.setexpbutton.clicked.connect(self.setevtexp_callback)

        self.saveimsbutton.clicked.connect(self.saveims_callback)

        self.ds9button.clicked.connect(self.opends9_callback)

        self.menu = QtW.QMenu("OCAM",self)
        
        self.dir_path = Path(lark.configLoader.DATA_DIR)
        
        self.ds9processes = []

    def on_connect(self):
        print("connecting ocamcontrol")
        try:
            self.iportsrtc = lark.getservice(self.iportsrtc_name)
        except Exception as e:
            self.iportsrtc = None
            print(e)
        
    def eventFilter(self, obj, event):
        if obj is self and event.type() == QtC.QEvent.Close:
            logging.info("Closing....")
            self.calwin.close()
        elif obj is self.calwin and event.type() == QtC.QEvent.Show:
            logging.info("Showing calwin")
            self.calwin.ocamfpsbox.setRange(self.setfpsspin.minimum(),self.setfpsspin.maximum())
            self.calwin.ocamfpsbox.setValue(self.setfpsspin.value())
            self.calwin.evtfpsbox.setRange(self.setfpsspin2.minimum(),self.setfpsspin2.maximum())
            self.calwin.evtfpsbox.setValue(self.setfpsspin2.value())

            self.calwin.ocamgainbox.setRange(self.setgainspin.minimum(),self.setgainspin.maximum())
            self.calwin.ocamgainbox.setValue(self.setgainspin.value())
            self.calwin.evtgainbox.setRange(self.setgainspin2.minimum(),self.setgainspin2.maximum())
            self.calwin.evtgainbox.setValue(self.setgainspin2.value())
        return super().eventFilter(obj,event)
        
    def useshutter_callback(self):
        self.iportsrtc.iPortSerial.run(command=f"shutter external")
        self.iportsrtc.iPortSerial.run(command=f"shutter blockonread 0")
        self.iportsrtc.iPortSerial.run(command=f"shutter correctglitch 1")
        self.iportsrtc.iPortSerial.run(command=f"shutter on")
    
    def noshutter_callback(self):
        self.iportsrtc.iPortSerial.run(command=f"shutter off")
        self.iportsrtc.iPortSerial.run(command=f"shutter blockonread 0")
        self.iportsrtc.iPortSerial.run(command=f"shutter correctglitch 0")
    
    def intread_callback(self):
        print("setting synchro off")
        self.iportsrtc.iPortSerial.run(command=f"synchro off")
    
    def extread_callback(self):
        print("setting synchro on")
        self.iportsrtc.iPortSerial.run(command=f"synchro on")
        self.iportsrtc.iPortSerial.run(command=f"fps 0")

    def setocamfps_callback(self):
        fps = self.setfpsspin.value()
        self.iportsrtc.iPortSerial.run(command=f"fps {fps}")
        logging.info(f"Set OCAM FPS to {fps}")

    def setevtfps_callback(self):
        this_darc = self.scoringconfig.getlark()
        fps = self.setfpsspin2.value()
        this_darc.set("aravisCmd0",f"FrameRate={fps};")
        # cmd = '-string="FrameRate={};"'.format(fps)
        # print(cmd)
        # darcmagic --prefix=canapy set -name=aravisCmd1 -string="FrameRate=100;"
        # setprocess = QtC.QProcess()
        # setprocess.start("darcmagic --prefix=canapy set aravisCmd1 -string=\"\"\"FrameRate={};\"\"\"".format(fps))
        # setprocess.waitForFinished()
        # subprocess.Popen(["darcmagic","--prefix=canapy","set","-name=aravisCmd1",cmd])
        logging.info(f"Set EVT FPS to {fps}")

    def setocamgain_callback(self):
        gain = self.setgainspin.value()
        self.iportsrtc.iPortSerial.run(command=f"gain {gain}")

    def setevtgain_callback(self):
        this_darc = self.scoringconfig.getlark()
        gain = self.setgainspin2.value()
        this_darc.set("aravisCmd0",f"Gain={gain};")
        # subprocess.Popen(["darcmagic","--prefix=canapy","set","-name=aravisCmd1","-string=\"Gain={};\"".format(gain)])

    def setevtexp_callback(self):
        this_darc = self.scoringconfig.getlark()
        exp = self.setexpspin.value()
        this_darc.set("aravisCmd0",f"Exposure={exp};")
        # subprocess.Popen(["darcmagic","--prefix=canapy","set","-name=aravisCmd1","-string=\"Expsoure={};\"".format(exp)])

    def saveims_callback(self):
        logging.info(f"Called: {inspect.stack()[1].function}")
        pyr_darc = self.pyrconfig.getlark()
        pyr_npxlx = pyr_darc.get("npxlx")[0]
        pyr_npxly = pyr_darc.get("npxly")[0]
        sco_darc = self.scoringconfig.getlark()
        sco_npxlx = sco_darc.get("npxlx")[0]
        sco_npxly = sco_darc.get("npxly")[0]
        nim = self.saveimsspin.value()
        fname = str(self.saveimstext.text())
        if fname == "":
            fname = "darc_ims"
        now = datetime.datetime.now()
        fname += "-{:0>2}{:0>2}{:0>2}".format(now.hour,now.minute,now.second)
        from lark.parallel import threadSynchroniser
        ims = threadSynchroniser([pyr_darc.getStreamBlock,sco_darc.getStreamBlock],args=[("rtcPxlBuf",nim),("rtcPxlBuf",nim)])
        # ims = this_darc.GetStreamBlock("rtcPxlBuf",nim)["rtcPxlBuf"][0]
        ocam = ims[0][0]
        evt = ims[1][0]
        print(ocam.shape, evt.shape)
        ocam.shape = ocam.shape[0],pyr_npxly,pyr_npxlx
        evt.shape = evt.shape[0],sco_npxly,sco_npxlx

        print(self.dir_path)
        fname1 = str(self.dir_path/(fname + "_ocam.fits"))
        FITS.Write(ocam,fname1)
        fname2 = str(self.dir_path/(fname + "_evt.fits"))
        FITS.Write(evt,fname2)

        self.opends9_callback(fname=fname1)
        self.opends9_callback(fname=fname2)

        # print(ims.shape)
        # print(npxlx,npxly,npxlx*npxly)
        # from matplotlib import pyplot
        # pyplot.imshow(ims[0],cmap='gray')
        # pyplot.show()

    def opends9_callback(self,event=False,fname=None):
        logging.info(f"Called: opends9_callback(self,event={event},fname={fname})")
        print("fname = ", fname)
        if fname is None:
            get_name = QtW.QFileDialog.getOpenFileName(self, 'Open file', str(self.dir_path),"FITS files (*.fits)",options=QtW.QFileDialog.DontUseNativeDialog)
            fname = get_name[0]
        print(fname)
        if fname != '':
            self.ds9processes.append(QtC.QProcess(self))
            self.ds9processes[-1].start("ds9",[fname])

    def closeds9s_callback(self):
        logging.info("Called: closeds9_callback(self)")
        for d in self.ds9processes:
            d.kill()


class PupilControl(QtW.QWidget):
    def __init__(self, larkconfig, parent=None):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig
        self.mainlay = QtW.QGridLayout()
        
        self.xoff_label = QtW.QLabel("xoff")
        self.xoff_spin = QtW.QSpinBox()
        self.yoff_label = QtW.QLabel("yoff")
        self.yoff_spin = QtW.QSpinBox()
        self.xsep_label = QtW.QLabel("xsep")
        self.xsep_spin = QtW.QSpinBox()
        self.xsep_spin.setRange(0,1000)
        self.ysep_label = QtW.QLabel("ysep")
        self.ysep_spin = QtW.QSpinBox()
        self.ysep_spin.setRange(0,1000)
        self.diam_label = QtW.QLabel("diam")
        self.diam_spin = QtW.QSpinBox()
        
        self.mainlay.addWidget(self.xoff_label,0,0)
        self.mainlay.addWidget(self.xoff_spin,0,1)
        self.mainlay.addWidget(self.yoff_label,1,0)
        self.mainlay.addWidget(self.yoff_spin,1,1)
        self.mainlay.addWidget(self.xsep_label,0,2)
        self.mainlay.addWidget(self.xsep_spin,0,3)
        self.mainlay.addWidget(self.ysep_label,1,2)
        self.mainlay.addWidget(self.ysep_spin,1,3)
        self.mainlay.addWidget(self.diam_label,2,0)
        self.mainlay.addWidget(self.diam_spin,2,1)
        
        self.get_button = QtW.QPushButton("Get from plot")
        self.set_button = QtW.QPushButton("Set to RTC")
        
        self.get_button.clicked.connect(self.get_callback)
        self.set_button.clicked.connect(self.set_callback)
        
        self.mainlay.addWidget(self.get_button,3,0)
        self.mainlay.addWidget(self.set_button,3,2)
        
        self.setLayout(self.mainlay)
        self.setWindowFlags(QtC.Qt.Window)
        
    def on_connect(self):
        self.lark = self.larkconfig.getlark()
        
    def get_callback(self):
        circs = self.parent().circs[0]
        rad = numpy.amax(circs[:,2])
        # xp1 = numpy.mean(circs[[0,2],0])
        xp1 = circs[0,0]
        xp2 = numpy.mean(circs[[1,3],0])
        # yp1 = numpy.mean(circs[[0,1],1])
        yp1 = circs[0,1]
        yp2 = numpy.mean(circs[[2,3],1])
        diam = int(2*rad)
        self.diam_spin.setValue(diam)
        xoff = int(xp1-rad)
        self.xoff_spin.setValue(xoff)
        yoff = int(yp1-rad)
        self.yoff_spin.setValue(yoff)
        xsep = int(xp2-xp1)
        self.xsep_spin.setValue(xsep)
        ysep = int(yp2-yp1)
        self.ysep_spin.setValue(ysep)
        
    def set_callback(self):
        param_names = ["nsubx","ncamThreads","npxlx","npxly","ncam","pyramidMode"]
        params1 = self.lark.getMany(param_names)
        # params = {k:v for k,v in params.items()}
        print(params1)
        nsubx = numpy.zeros([params1["ncam"]],dtype=numpy.int32)
        nsubx[0] = self.diam_spin.value()
        params = gen_subapParams(
            nsubx=nsubx,
            nthreads=params1["ncamThreads"].sum(),
            npxlx=params1["npxlx"],
            npxly=params1["npxly"],
            ncam=params1["ncam"],
            pyramidMode=params1["pyramidMode"],
            xoff=[self.xoff_spin.value()],
            yoff=[self.yoff_spin.value()],
            xsep=[self.xsep_spin.value()],
            ysep=[self.ysep_spin.value()]
        )
        print(params)
        if nsubx[0] != int(params1["nsubx"]):
            nacts = self.lark.get("nacts")
            params["rmx"] = numpy.random.random((nacts,params["ncents"])).astype("f")
        params = copydict(params)
        self.lark.setMany(params,check=1,switch=1)

class PyCircles(QtW.QWidget):
    def __init__(self, larkconfig, srtc_name, parent=None):
        super().__init__(parent=parent)
        self.menu = None
        self.srtc_name = srtc_name
        
        self.mainlayout = QtW.QHBoxLayout()
        self.vlay = QtW.QVBoxLayout()

        self.update_timer = QtC.QTimer()
        self.update_timer.timeout.connect(self.update_plot)

        self.framerate = 1
        
        self._data = None
        self.data = None
        self.scale_lim = (0,0)
        self.circ_items = []
        self.text_items = []
        self.line_items = []

        # define other widgets
        self.plotter = Plot2D(self)
        self.toolbar = PlotToolbar(self.plotter,self.vlay,parent=self)
        
        custom_layout = QtW.QHBoxLayout()
        self.plotscale_button = QtW.QPushButton("Use Plot Scaling")
        self.plotscale_button.setCheckable(True)
        self.autoscale_button = QtW.QPushButton("Use Auto Scaling")
        self.autoscale_button.setCheckable(True)
        self.showpupil_button = QtW.QPushButton("Show Pupil controls")
        custom_layout.addWidget(self.plotscale_button)
        custom_layout.addWidget(self.autoscale_button)
        custom_layout.addWidget(self.showpupil_button)
        
        self.pupilcontrol = PupilControl(larkconfig,self)
        self.showpupil_button.clicked.connect(self.pupilcontrol.show)
        
        self.toolbar.addCustomLayout(custom_layout)

        # populate layout
        self.vlay.addWidget(self.plotter)
        self.vlay.addWidget(self.toolbar)
        self.mainlayout.addLayout(self.vlay)

        # set layout
        self.setLayout(self.mainlayout)
        self.res = None
        self.srtc = None
        
    def on_connect(self):
        try:
            self.srtc = connectClient(self.srtc_name+"SRTC")
        except ConnectionError as e:
            print(e)
            self.srtc = None
        self.pupilcontrol.on_connect()
        self.init_plot()
            
    def init_plot(self):
        for i in range(4):
            self.circ_items.append(CircleItem((0,0),1,"r",2,draw_centre=1))
            self.plotter._addItem(self.circ_items[-1])
            self.text_items.append(pg.TextItem(f"{0.00:.3f}",color="red"))
            self.plotter._addItem(self.text_items[-1])
            self.line_items.append(LineItem((0,0),(0,1),"g",2))
            self.plotter._addItem(self.line_items[-1])
        for i in range(4):
            self.text_items.append(pg.TextItem(f"{0.00:.3f}",color="green"))
            self.plotter._addItem(self.text_items[-1])
        self.text_items.append(pg.TextItem(f"{0.000:.3f}",color="white"))
        self.plotter._addItem(self.text_items[-1])
        
    def update_plot(self):
        # while len(self.circ_items) != 0:
        #     c = self.circ_items.pop()
        #     self.plotter._removeItem(c)
        # while len(self.text_items) != 0:
        #     f = self.text_items.pop()
        #     self.plotter._removeItem(f)
        # while len(self.line_items) != 0:
        #     f = self.line_items.pop()
        #     self.plotter._removeItem(f)

        self.res = self.srtc.getResult("pyr_quadcell")
        self.update_plot2()
        
    def update_plot2(self):
        if self.res is not None:
            self.im, self.pups, self.circs, self.flux = self.res
        else:
            return
        print(f"self.circs = {self.circs[0]}")
        print(f"self.flux = {self.flux}")
        print(f"sum(self.flux) = {sum(self.flux)}")
        self.plot(self.im.T)
        for i,c in enumerate(self.circs[0]):
            self.circ_items[i].update(c[:2],c[2],"r",2,draw_centre=1)
            self.text_items[i].setText(f"{self.flux[i]:.3f}")
            self.text_items[i].setPos(c[0]+c[2],c[1])
            

        qs = [[0,1,[1,0]],[1,3,[0,1]],[3,2,[-1,0]],[2,0,[0,-1]]]
        
        angles = []
        ti=4
        for i,(c1,c2,c3) in enumerate(qs):
            
            self.line_items[i].update(self.circs[0,c1,:2],self.circs[0,c2,:2],"g",2)
            
            vector_1 = self.circs[0,c2,:2] - self.circs[0,c1,:2]
            unit_vector_1 = vector_1 / numpy.linalg.norm(vector_1)
            dot_product = numpy.dot(unit_vector_1, c3)
            angle = 180.*numpy.arccos(dot_product)/numpy.pi
            self.text_items[ti+i].setText(f"{angle:.3f}")
            pos = self.circs[0,c1,:2]+vector_1/2
            self.text_items[ti+i].setPos(pos[0],pos[1])
            angles.append(angle)
            
        angle = numpy.mean(angles)
        self.text_items[8].setText(f"{angle:.3f}")
        pos = self.im.shape[0]//2, self.im.shape[1]//2
        self.text_items[8].setPos(pos[0],pos[1])
        
        # self.line_items.append(LineItem(self.circs[0,1,:2],self.circs[0,3,:2],"g",2))
        # self.plotter._addItem(self.line_items[-1])
        
        # vector_1 = self.circs[0,3,:2] - self.circs[0,1,:2]
        # unit_vector_1 = vector_1 / numpy.linalg.norm(vector_1)
        # dot_product = numpy.dot(unit_vector_1, v)
        # angle = 180.*numpy.arccos(dot_product)/numpy.pi
        # self.text_items.append(pg.TextItem(f"{angle:.3f}",color="red"))
        # self.plotter._addItem(self.text_items[-1])
        # pos = self.circs[0,1,:2]+vector_1/2
        # self.text_items[-1].setPos(pos[0],pos[1])
        
        # self.line_items.append(LineItem(self.circs[0,3,:2],self.circs[0,2,:2],"g",2))
        # self.plotter._addItem(self.line_items[-1])
        
        # vector_1 = self.circs[0,3,:2] - self.circs[0,1,:2]
        # unit_vector_1 = vector_1 / numpy.linalg.norm(vector_1)
        # dot_product = numpy.dot(unit_vector_1, v)
        # angle = 180.*numpy.arccos(dot_product)/numpy.pi
        # self.text_items.append(pg.TextItem(f"{angle:.3f}",color="red"))
        # self.plotter._addItem(self.text_items[-1])
        # pos = self.circs[0,1,:2]+vector_1/2
        # self.text_items[-1].setPos(pos[0],pos[1])
        
        # self.line_items.append(LineItem(self.circs[0,2,:2],self.circs[0,0,:2],"g",2))
        # self.plotter._addItem(self.line_items[-1])
        
        # vector_1 = self.circs[0,3,:2] - self.circs[0,1,:2]
        # unit_vector_1 = vector_1 / numpy.linalg.norm(vector_1)
        # dot_product = numpy.dot(unit_vector_1, v)
        # angle = 180.*numpy.arccos(dot_product)/numpy.pi
        # self.text_items.append(pg.TextItem(f"{angle:.3f}",color="red"))
        # self.plotter._addItem(self.text_items[-1])
        # pos = self.circs[0,1,:2]+vector_1/2
        # self.text_items[-1].setPos(pos[0],pos[1])
        
    def plot(self,data):
        if self.toolbar.freeze:
            return
        this_min = 1000000
        this_max = -1000000
        if self.toolbar.autoscale:
            d = data
            this_min = min(this_min,numpy.nanmin(d))
            this_max = max(this_max,numpy.nanmax(d))
            self.scale_lim = min(this_min,self.scale_lim[0]),max(this_max,self.scale_lim[1])
            scale = self.scale_lim
            self.toolbar.setScaleRange(self.scale_lim)
        else:
            self.scale_lim = (0,0)
            scale = self.toolbar.scale
        if scale==(0,0): scale=(-1.,1.)
        self.plotter.plot(data,autoLevels=False,levels=scale)

    def plot(self,data):
        if self.toolbar.freeze:
            return
        this_min = 1000000
        this_max = -1000000
        if self.autoscale_button is not None and self.autoscale_button.isChecked():
            d = data
            this_min = min(this_min,numpy.nanmin(d))
            this_max = max(this_max,numpy.nanmax(d))
            self.plotter.plot(data,autoLevels=False,levels=(this_min,this_max))
            return
        if self.plotscale_button is None or not self.plotscale_button.isChecked():
            if self.toolbar.autoscale:
                d = data
                this_min = min(this_min,numpy.nanmin(d))
                this_max = max(this_max,numpy.nanmax(d))
                self.scale_lim = min(this_min,self.scale_lim[0]),max(this_max,self.scale_lim[1])
                scale = self.scale_lim
                self.toolbar.setScaleRange(self.scale_lim)
            else:
                self.scale_lim = (0,0)
                scale = self.toolbar.scale
            if scale==(0,0): scale=(-1.,1.)
            self.plotter.plot(data,autoLevels=False,levels=scale)
        else:
            self.plotter.plot(data,autoLevels=False)
        
    def showEvent(self, event):
        print("showing Pycirc")
        if self.toolbar.isStuck():
            self.toolbar.show()
        if self.srtc is not None:
            self._startUpdates()
            self.update_timer.start(1000//self.framerate)
        super().showEvent(event)
        
    def _startUpdates(self):
        if self.srtc is not None:
            print("starting callbacks")
            self.srtc.getPlugin("pyr_quadcell").start(_period=1)

    def hideEvent(self, event):
        print("hiding Plotter")
        if self.toolbar.isStuck():
            self.toolbar.hide()
        self.update_timer.stop()
        self._stopUpdates()
        super().hideEvent(event)

    def _stopUpdates(self):
        if self.srtc is not None:
            try:
                self.srtc.getPlugin("pyr_quadcell").stop()
            except EOFError as e:
                print("Service has been stopped: ",e)

    def closeEvent(self, event):
        if not self.isHidden():
            self.hide()
        self._data = None
        self._stopUpdates()
        if self.srtc is not None:
            self.srtc.conn.close()
        self.srtc = None
        super().closeEvent(event)
