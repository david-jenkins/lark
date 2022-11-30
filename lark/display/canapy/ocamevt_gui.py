#!/usr/bin/env python3

from __future__ import print_function
import sys
import os
import time
import numpy
import darc
import PyQt5
from PyQt5 import QtGui as QtG
from PyQt5 import QtCore as QtC
from PyQt5 import QtWidgets as QtW
import subprocess
from lark.darc import FITS
from lark.utils import get_datetime_stamp
from collections import deque
import logging
import inspect

from astropy.io import fits

import pathlib

class Logger(logging.Handler, QtC.QObject):
    appendSignal = QtC.pyqtSignal(str)
    def __init__(self,parent=None):
        super().__init__()
        QtC.QObject.__init__(self)
        self.widget = QtW.QPlainTextEdit()
        self.widget.setReadOnly(True)
        self.appendSignal.connect(self.widget.appendPlainText)

        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        msg = self.format(record)
        self.appendSignal.emit(msg)

class CalibrationWindowBoth(QtW.QWidget):
    def __init__(self,parent=None):
        super().__init__()

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

        self.dir_path = pathlib.Path("~/darc_images/dark_frames/").expanduser()
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

            this_darc = darc.Control("canapy")

            N = self.saveimsspin.value()

            ims = this_darc.GetStreamBlock("rtcPxlBuf",N)["rtcPxlBuf"][0].mean(0)

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
            this_darc = darc.Control("canapy")
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

        this_darc = darc.Control("canapy")
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
        now = get_datetime_stamp()
        text = self.filenamepreview.text().split("\n")[0] + "\n"
        fname = self.saveimstext.text()
        if fname != "":
            fname += "_"
        self.fname = str(self.dir_path / fname)
        self.fname += f"oc{ocamfps}-{ocamgain}evt{evtfps}-{evtgain}_"
        self.fname += now
        text += self.fname
        self.filenamepreview.setText(text)

class ControlWindowBoth(QtW.QWidget):
    def __init__(self):
        super(ControlWindowBoth,self).__init__()
        self.show()

        self.vlay = QtW.QVBoxLayout()
        self.setLayout(self.vlay)

        self.hlays = []
        
        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        self.startbutton = QtW.QPushButton("Start DARC")
        self.startbutton.clicked.connect(self.startdarc_callback)
        self.hlays[-1].addWidget(self.startbutton,3)

        self.hlays[-1].addStretch(1)

        self.stopbutton = QtW.QPushButton("Stop DARC")
        self.stopbutton.clicked.connect(self.stopdarc_callback)
        self.hlays[-1].addWidget(self.stopbutton,3)

        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        self.connectbutton = QtW.QPushButton("Connect Cameras")
        self.connectbutton.clicked.connect(self.connect_callback)
        self.connectbutton.mystate = 1
        self.hlays[-1].addWidget(self.connectbutton,3)

        self.hlays[-1].addStretch(1)

        self.opencambutton = QtW.QPushButton("Open Cameras")
        self.opencambutton.clicked.connect(self.opencam_callback)
        self.hlays[-1].addWidget(self.opencambutton,3)

        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        self.statusbutton = QtW.QPushButton("DARC Status")
        self.statusbutton.clicked.connect(self.statusdarc_callback)
        self.hlays[-1].addWidget(self.statusbutton,3)
        self.hlays[-1].addStretch(1)

        self.iportdaemonbutton = QtW.QPushButton("Start iPort Daemon")
        self.iportdaemonbutton.clicked.connect(self.startdaemon_callback)
        self.hlays[-1].addWidget(self.iportdaemonbutton,3)

        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        self.setfpsbutton = QtW.QPushButton("Set OCAM FPS")
        self.setfpsbutton.clicked.connect(self.setocamfps_callback)
        self.setfpsspin = QtW.QSpinBox()
        self.setfpsspin.setRange(10, 1500)
        self.setfpsspin.setValue(100)
        self.hlays[-1].addWidget(self.setfpsbutton,1)
        self.hlays[-1].addWidget(self.setfpsspin,1)

        self.hlays[-1].addStretch(1)

        self.setfpsbutton2 = QtW.QPushButton("Set Scoring FPS")
        self.setfpsbutton2.clicked.connect(self.setevtfps_callback)
        self.setfpsspin2 = QtW.QSpinBox()
        self.setfpsspin2.setRange(10, 1500)
        self.setfpsspin2.setValue(100)
        self.hlays[-1].addWidget(self.setfpsbutton2,1)
        self.hlays[-1].addWidget(self.setfpsspin2,1)

        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        self.setgainbutton = QtW.QPushButton("Set OCAM GAIN")
        self.setgainbutton.clicked.connect(self.setocamgain_callback)
        self.setgainspin = QtW.QSpinBox()
        self.setgainspin.setRange(1, 600)
        self.setgainspin.setValue(1)
        self.hlays[-1].addWidget(self.setgainbutton,1)
        self.hlays[-1].addWidget(self.setgainspin,1)

        self.hlays[-1].addStretch(1)

        self.setgainbutton2 = QtW.QPushButton("Set Scoring GAIN")
        self.setgainbutton2.clicked.connect(self.setevtgain_callback)
        self.setgainspin2 = QtW.QSpinBox()
        self.setgainspin2.setRange(1, 10000)
        self.setgainspin2.setValue(1)
        self.hlays[-1].addWidget(self.setgainbutton2,1)
        self.hlays[-1].addWidget(self.setgainspin2,1)

        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])

        self.calwin = CalibrationWindowBoth(self)
        self.calwin.installEventFilter(self)
        self.showcalibwinbutton = QtW.QPushButton("Image Calibration")
        self.showcalibwinbutton.clicked.connect(self.calwin.show)

        self.hlays[-1].addWidget(self.showcalibwinbutton,1)

        self.hlays[-1].addStretch(2)

        self.setexpbutton = QtW.QPushButton("Set Scoring EXPOSURE")
        self.setexpbutton.clicked.connect(self.setevtexp_callback)
        self.setexpspin = QtW.QSpinBox()
        self.setexpspin.setRange(1, 1000000)
        self.setexpspin.setValue(10000)
        self.hlays[-1].addWidget(self.setexpbutton,1)
        self.hlays[-1].addWidget(self.setexpspin,1)

        self.hlays.append(QtW.QHBoxLayout())
        self.vlay.addLayout(self.hlays[-1])
        self.saveimsbutton = QtW.QPushButton("Save Images")
        self.saveimsbutton.clicked.connect(self.saveims_callback)
        self.saveimstext = QtW.QLineEdit()
        self.saveimstext.setToolTip("Files saved to darc_images folder")
        self.saveimsspin = QtW.QSpinBox()
        self.saveimsspin.setRange(1, 100)
        self.saveimsspin.setValue(10)
        self.saveimslabel = QtW.QLabel("Filename:")
        self.ds9button = QtW.QPushButton("Open DS9")
        self.ds9button.clicked.connect(self.opends9_callback)
        self.hlays[-1].addWidget(self.saveimsbutton)
        self.hlays[-1].addWidget(self.saveimslabel)
        self.hlays[-1].addWidget(self.saveimstext)
        self.hlays[-1].addWidget(self.saveimsspin)
        self.hlays[-1].addWidget(self.ds9button)

        self.outlabel = QtW.QPlainTextEdit()
        self.outlabel.setReadOnly(True)
        self.vlay.addWidget(self.outlabel,2)


        self.logger = Logger()
        logging.getLogger().addHandler(self.logger)
        logging.getLogger().setLevel(logging.DEBUG)
        self.vlay.addWidget(self.logger.widget,1)

        self.daemonprocess = QtC.QProcess(self)
        self.daemonprocess.readyRead.connect(self.daemondataOut)
        
        # self.daemonprocess.started.connect(lambda: self.iportdaemonbutton.setEnabled(False))
        # self.daemonprocess.finished.connect(lambda: self.iportdaemonbutton.setEnabled(True))
        self.daemonprocess.started.connect(self.changedaemonbutton)
        self.daemonprocess.finished.connect(self.changedaemonbutton)

        self.statusprocess = QtC.QProcess(self)
        self.statusprocess.readyRead.connect(self.statusdataOut)

        self.darcprocess = QtC.QProcess(self)
        self.darcprocess.readyRead.connect(self.darcdataOut)
        self.darcprocess.started.connect(lambda: self.startbutton.setEnabled(False))
        self.darcprocess.finished.connect(lambda: self.startbutton.setEnabled(True))

        self.plotprocesses = deque()
        self.ds9processes = deque()

        self.darcoutputwidget = QtW.QPlainTextEdit(self)
        self.darcoutputwidget.setReadOnly(True)
        self.darcoutputwidget.setWindowFlags(QtC.Qt.Window)
        
        self.darcstatuswidget = QtW.QPlainTextEdit(self)
        self.darcstatuswidget.setReadOnly(True)
        self.darcstatuswidget.setWindowFlags(QtC.Qt.Window)

        # self.omniprocess = QtC.QProcess(self)
        # self.omniprocess.start("omniNames", ["-logdir", "/home/laserlab/logs"])
        # self.rpycprocess = QtC.QProcess(self)
        # self.rpycprocess.start("darcNames")

        self.installEventFilter(self)
        self.darcrunning = 0

        self.dir_path = pathlib.Path("~/darc_images/").expanduser()
        self.dir_path.mkdir(parents=True, exist_ok=True)

    def eventFilter(self, obj, event):
        if obj is self and event.type() == QtC.QEvent.Close:
            logging.info("Closing....")
            self.calwin.close()
            if self.darcrunning:
                self.stopdarc_callback()
            self.darcoutputwidget.close()
            self.darcstatuswidget.close()
            subprocess.Popen(["pkill","-f","darcNames"])
            # self.rpycprocess.waitForFinished()
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

    def darcdataOut(self):
        # cursor = self.darcoutputwidget.textCursor()
        # cursor.movePosition(cursor.End)
        # cursor.insertText(self.darcprocess.readAll().data().decode())
        # self.darcoutputwidget.ensureCursorVisible()
        self.darcoutputwidget.appendPlainText(self.darcprocess.readAll().data().decode())
        QtC.QCoreApplication.processEvents()

    def statusdataOut(self):
        self.darcstatuswidget.setPlainText(self.statusprocess.readAll().data().decode())
        # cursor = self.darcstatuswidget.textCursor()
        # cursor.movePosition(cursor.End)
        # cursor.insertText()
        # self.darcstatuswidget.ensureCursorVisible()
        QtC.QCoreApplication.processEvents()

    def daemondataOut(self):
        # cursor = self.outlabel.textCursor()
        # cursor.movePosition(cursor.End)
        # cursor.insertText(str(self.daemonprocess.readAll()))
        # self.outlabel.ensureCursorVisible()
        self.outlabel.appendPlainText(self.daemonprocess.readAll().data().decode())

    def startdarc_callback(self):
        self.darcoutputwidget.show()
        # self.darcprocess.start('python',["-u","/opt/darc/bin/darccontrol","--prefix=canapy","/home/laserlab/Downloads/configOcamTest.py","-o"])
        self.darcprocess.start('python3',["-u","/opt/darc/bin/darccontrol","--prefix=canapy","/home/laserlab/git/canapy-rtc/config/configOcamEvtTest.py","-o"])
        logging.info("Started darc...")
        self.darcrunning = 1
        # time.sleep(5)
        # self.darc_obj = darc.Control("canapy")

    def stopdarc_callback(self):
        self.closecams_callback()
        subprocess.Popen(["darcmagic","--prefix=canapy","stop","-c"])
        self.darcprocess.waitForFinished()
        self.darcrunning = 0
        # self.connectbutton.setEnabled(True)
        self.stopdaemon_callback()
        logging.info("Stopped darc...")

    def statusdarc_callback(self):
        self.darcstatuswidget.show()
        # self.statusprocess.start("darcmagic",["--prefix=canapy","status"])
        this_darc = darc.Control("canapy")
        data,ftime,fno=this_darc.GetStream("rtcStatusBuf")
        self.darcstatuswidget.setPlainText(darc.statusBuf_tostring(data))
        logging.info("Got darc status...")

    def connect_callback(self):
        this_darc = darc.Control("canapy")
        this_darc.set("camerasOpen",1)
        self.connectbutton.setEnabled(False)
        QtC.QTimer.singleShot(2000,self.startdaemon_callback)
        logging.info("Cameras connected...")

    def disconnect_callback(self):
        this_darc = darc.Control("canapy")
        this_darc.set("camerasOpen",0)
        self.closecams_callback()
        logging.info("Cameras disconnected...")

    def opencam_callback(self):
        self.plotprocesses.append(QtC.QProcess(self))
        self.plotprocesses[-1].start("darcplot",["--prefix=canapy","-f/opt/darc/conf/plotRawPxls.xml","-i0"])
        logging.info("Opening display...")

    def closecams_callback(self):
        for p in self.plotprocesses:
            p.kill()
        logging.info("Killing displays...")

    def startdaemon_callback(self):
        self.daemonprocess.start("iportDaemonL",["canapy"])
        logging.info("iPort Daemon started...")
        time.sleep(1)
        # self.initcameras()
        
    # def initcameras(self):
        # self.setocamfps_callback()
        # self.setevtfps_callback()
        # time.sleep(1)
        # self.setocamgain_callback()
        # self.setevtgain_callback()
        # time.sleep(1)
        # self.setevtexp_callback()

    def stopdaemon_callback(self):
        self.daemonprocess.kill()
        logging.info("iPort Daemon stopped...")

    def changedaemonbutton(self):
        if self.iportdaemonbutton.text() == "Start iPort Daemon":
            self.iportdaemonbutton.setText("Stop iPort Daemon")
            self.iportdaemonbutton.clicked.disconnect(self.startdaemon_callback)
            self.iportdaemonbutton.clicked.connect(self.stopdaemon_callback)
        else:
            self.iportdaemonbutton.setText("Start iPort Daemon")
            self.iportdaemonbutton.clicked.disconnect(self.stopdaemon_callback)
            self.iportdaemonbutton.clicked.connect(self.startdaemon_callback)

    def setocamfps_callback(self):
        fps = self.setfpsspin.value()
        subprocess.Popen(["iportSerialL","--prefix=canapy","fps","{}".format(fps)])
        logging.info(f"Set OCAM FPS to {fps}")

    def setevtfps_callback(self):
        this_darc = darc.Control("canapy")
        fps = self.setfpsspin2.value()
        this_darc.set("aravisCmd1",f"FrameRate={fps};")
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
        subprocess.Popen(["iportSerialL","--prefix=canapy","gain","{}".format(gain)])

    def setevtgain_callback(self):
        this_darc = darc.Control("canapy")
        gain = self.setgainspin2.value()
        this_darc.set("aravisCmd1",f"Gain={gain};")
        # subprocess.Popen(["darcmagic","--prefix=canapy","set","-name=aravisCmd1","-string=\"Gain={};\"".format(gain)])

    def setevtexp_callback(self):
        this_darc = darc.Control("canapy")
        exp = self.setexpspin.value()
        this_darc.set("aravisCmd1",f"Exposure={exp};")
        # subprocess.Popen(["darcmagic","--prefix=canapy","set","-name=aravisCmd1","-string=\"Expsoure={};\"".format(exp)])

    def saveims_callback(self):
        logging.info(f"Called: {inspect.stack()[1].function}")
        this_darc = darc.Control("canapy")
        npxlx = this_darc.Get("npxlx")
        npxly = this_darc.Get("npxly")
        print(npxlx,npxly)
        nim = self.saveimsspin.value()
        fname = str(self.saveimstext.text())
        if fname == "":
            fname = "darc_ims"
        date_now, time_now = get_datetime_stamp(split=True)
        fname += "-" + time_now

        ims = this_darc.GetStreamBlock("rtcPxlBuf",nim)["rtcPxlBuf"][0]
        print(ims.shape)
        ocam = ims[:,:npxlx[0]*npxly[0]]
        evt = ims[:,npxlx[0]*npxly[0]:]
        print(ocam.shape, evt.shape)
        ocam.shape = ims.shape[0],npxly[0],npxlx[0]
        evt.shape = ims.shape[0],npxly[1],npxlx[1]

        
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


def main():
    logging.basicConfig(level=logging.DEBUG)
    app = QtW.QApplication(sys.argv)
    cw = ControlWindowBoth()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
