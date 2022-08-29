

from PyQt5 import QtWidgets as QtW

from astropy.io import fits

from pathlib import Path

import datetime

from lark import LarkConfig

import numpy

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
