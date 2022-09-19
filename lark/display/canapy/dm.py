#!/usr/bin/env python3

'''
Python code for the ESO CaNaPy Project, Copyright David Jenkins, ESO

All GUI widgets relating to DMs
'''

import sys
from PyQt5 import QtGui as QtG
from PyQt5 import QtCore as QtC
from PyQt5 import QtWidgets as QtW
import pyqtgraph as pg
from pyqtgraph import GradientWidget
from pyqtgraph.colormap import ColorMap
import numpy
from lark import LarkConfig, NoLarkError
import time
import logging
from lark.tools.zenturgen import AtmosphereGenerator
import scipy.io
import datetime
from pathlib import Path
from astropy.io import fits

logging.basicConfig(level=logging.DEBUG)

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
# pg.setConfigOption('imageAxisOrder', 'row-major')

HOME = str(Path.home())

# number of pixels per act to display:
NPIXELS = 5
SLIDER_SCALE = 100

MAX_SCALE = 0.4

V = 5.#,15.]                  #wind speed
D = 1.                  #telescope diameter
N = 1000               #number of frames
nacts = 97              #number of actuators
Zn = 30#96                #number of zernike modes, does NOT include piston, Zernike modes 2->(Zn+1)
r_0 = 0.137             #fried parameter
wl = 0.589              #wavelength
f = 500               #frequency

ALPAO9715_config = {
    "nacts" : 97,
    "actx" : 11,
    "offset" : 0.0,
    "minVal" : -1.0,
    "maxVal" : 1.0,
    "midVal" : 0.,
    "pokeVal" : 0.02,
    "scale" : lambda x: x,
    "flat" : [0]*97,
    "actMap" : [[0,0,0,1,1,1,1,1,0,0,0],
                [0,0,1,1,1,1,1,1,1,0,0],
                [0,1,1,1,1,1,1,1,1,1,0],
                [1,1,1,1,1,1,1,1,1,1,1],
                [1,1,1,1,1,1,1,1,1,1,1],
                [1,1,1,1,1,1,1,1,1,1,1],
                [1,1,1,1,1,1,1,1,1,1,1],
                [1,1,1,1,1,1,1,1,1,1,1],
                [0,1,1,1,1,1,1,1,1,1,0],
                [0,0,1,1,1,1,1,1,1,0,0],
                [0,0,0,1,1,1,1,1,0,0,0]
                ]
}

Boston_config = {
    "nacts" : 492,
    "actx" : 24,
    "offset" : 0.0,
    "minVal" : 0.0,
    "maxVal" : 1.0,
    "midVal" : 0.65,
    "scale" : lambda x: x,
    "mapping" : [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 29, 30, 31, 32, 33, 34, 35,
     36, 37, 38, 39, 40, 41, 42, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 
     66, 67, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 98, 
     99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 
     116, 117, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 
     136, 137, 138, 139, 140, 141, 142, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 
     154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 
     171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 
     188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 
     205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 
     222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 
     239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 
     256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 
     273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 
     290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 
     307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 
     324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 
     341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357,
     358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 
     375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 
     392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 
     409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 
     426, 427, 428, 429, 430, 431, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 
     444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 458, 459, 460, 461, 462, 463, 
     464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 483, 484, 485, 
     486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 508, 509, 
     510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 533, 534, 535, 
     536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 558, 559, 560, 561, 562, 563, 
     564, 565, 566, 567, 568, 569],
    "actMap" : [[0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0], 
                [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
                [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
                [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
                [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
                [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
                [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0]]
}

def getPyQtColour(colour):
    valid_col_words = {'white':(255,255,255),'w':(255,255,255),'black':(0,0,0),'k':(0,0,0),'red':(255,0,0),'r':(255,0,0),'blue':(0,0,255),'b':(0,0,255),'green':(0,255,0),'g':(0,255,0)}#,'yellow','purple','orange'}
    if type(colour) is str:
        return QtG.QColor(*valid_col_words.get(colour,(255,255,255)))
    elif type(colour) is tuple:
        return QtG.QColor(*colour)

class Dm(object):
    def __init__(self,config,prefix=""):
        self.prefix = prefix
        self.config = config
        try:
            self.darc = LarkConfig(self.prefix).getlark()
            a = self.darc.get("actuators")
            if a is not None:
                if a.shape[0] != self.config['nacts']:
                    print("Error, wrong shape, DARC expects %d actuators",a.shape)
                    self.close()
        except NoLarkError as e:
            print("No darc available: ",e)
            self.darc = None

        # pistonvalue is a single offset applied to all actuators
        self.pistonvalue = self.config['midVal']
        self.flat = numpy.zeros((self.config['nacts']))
        # actvals are the *relative* differences of each actuator
        self.actvals = numpy.zeros((self.config['nacts']))
        self.acts = numpy.zeros((self.config['nacts']))
        self.zcoeffs = numpy.zeros_like(self.actvals)
        # when acts are sent to the DM, pistonvalue and actvals are added together

    def set_darc(self):
        if self.darc is not None:
            self.acts[:] = self.actvals+self.flat+self.pistonvalue
            if (self.acts>MAX_SCALE*self.config['maxVal']).any():
                print("Some acts saturating (high)!")
            if (self.acts<MAX_SCALE*self.config['minVal']).any():
                print("Some acts saturating (low)!")
            self.acts[numpy.where(self.acts>MAX_SCALE*self.config['maxVal'])] = MAX_SCALE*self.config['maxVal']
            self.acts[numpy.where(self.acts<MAX_SCALE*self.config['minVal'])] = MAX_SCALE*self.config['minVal']

            self.print_vals(self.acts)
            self.darc.set("actuators",self.acts)

    def print_vals(self,acts):
        printarr = numpy.array(self.config['actMap'],dtype=float)
        printarr[numpy.where(printarr==1)] = acts
        print("sending to darc")
        print(printarr)

    def save_flat(self,fname):
        if fname != '':
            numpy.savetxt(fname,self.actvals+self.flat+self.pistonvalue)
            self.set_darc()

    def load_flat(self,fname):
        if fname != '':
            flat = numpy.loadtxt(fname)
            self.flat[:] = flat
            self.set_darc()

class DoubleSpinBox(QtW.QDoubleSpinBox):
    stepChanged = QtC.pyqtSignal()
    def stepBy(self, step):
        value = self.value()
        super(DoubleSpinBox, self).stepBy(step)
        if self.value() != value:
            self.stepChanged.emit()


def gkern(sig=2.):
    """\
    creates gaussian kernel with side length `l` and a sigma of `sig`
    """
    ax = numpy.linspace(-(NPIXELS*3 - 1) / 2., (NPIXELS*3 - 1) / 2., NPIXELS*3)
    gauss = numpy.exp(-0.5 * numpy.square(ax) / numpy.square(sig))
    kernel = numpy.outer(gauss, gauss)
    return kernel / numpy.max(numpy.abs(kernel))

class DmControl(Dm,QtW.QWidget):
    set_signal = QtC.pyqtSignal(bool)
    enterPressed = QtC.pyqtSignal()
    actsignal = QtC.pyqtSignal(float)
    updateplot = QtC.pyqtSignal()
    def __init__(self,config,prefix=""):
        Dm.__init__(self,config,prefix)
        QtW.QWidget.__init__(self)

        self.menuBar = QtW.QMenuBar(self)
        fileMenu = self.menuBar.addMenu ("File")
        exitAction = QtW.QAction('Exit', self)
        saveflatAction = QtW.QAction('Save Shape', self)
        loadflatAction = QtW.QAction('Load Flat', self)
        plotactsAction = QtW.QAction('Plot Acts', self)
        fileMenu.addAction(exitAction)
        fileMenu.addAction(saveflatAction)
        fileMenu.addAction(loadflatAction)
        fileMenu.addAction(plotactsAction)
        exitAction.triggered.connect(self.close)
        exitAction.setShortcut('Ctrl+Q')
        saveflatAction.triggered.connect(self.saveFlat)
        loadflatAction.triggered.connect(self.loadFlat)
        plotactsAction.triggered.connect(self.showactplot)

        pokeMenu = self.menuBar.addMenu ("Poke")
        self.pokeAction = QtW.QAction('Poke Actuators', self, checkable=True)
        self.zernikeAction = QtW.QAction('Poke Zernikes', self, checkable=True)
        self.karhunenAction = QtW.QAction('Poke KL Modes', self, checkable=True)
        self.atmosAction = QtW.QAction('Play Atmos', self, checkable=True)
        pokeMenu.addAction(self.pokeAction)
        pokeMenu.addAction(self.karhunenAction)
        pokeMenu.addAction(self.zernikeAction)
        pokeMenu.addAction(self.atmosAction)

        self.pokegroup = QtW.QActionGroup(self)
        self.pokegroup.addAction(self.pokeAction)
        self.pokegroup.addAction(self.karhunenAction)
        self.pokegroup.addAction(self.zernikeAction)
        self.pokegroup.addAction(self.atmosAction)

        self.pokeAction.triggered.connect(self.set_poke)
        self.karhunenAction.triggered.connect(self.set_poke)
        self.zernikeAction.triggered.connect(self.set_poke)
        self.atmosAction.triggered.connect(self.set_poke)

        # self.colourmap = pg.colormap.get('magma')
        # self.colourmap = ColorMap(numpy.array([0,0.25,0.5,0.75,1]), numpy.array(((0,0,0),(75,20,120),(230,90,90),(180,50,120),(250,240,180)), dtype=numpy.ubyte))
        self.colourmap = ColorMap(numpy.array([0,1]), numpy.array(((0,0,0),(255,255,255)), dtype=numpy.ubyte))
        self.toplayout = QtW.QHBoxLayout()
        self.botlayout = QtW.QHBoxLayout()
        self.layout = QtW.QVBoxLayout()
        self.layout.addWidget(self.menuBar)
        self.layout.addLayout(self.toplayout)
        self.layout.addLayout(self.botlayout)

        # self.graphicslay = pg.ImageView()
        self.graphicslay = pg.GraphicsLayoutWidget()
        # self.viewbox = self.graphicslay.getView()
        self.viewbox = pg.ViewBox()
        self.image = pg.ImageItem()
        # self.histogram = pg.HistogramLUTWidget(orientation='vertical',gradientPosition='right')
        self.gradient = pg.GradientWidget(orientation='right')
        self.gradient.setColorMap(self.colourmap)
        self.ticks = [t[0] for t in self.gradient.listTicks()]
        self.gradient.sigGradientChanged.connect(self.updateImage)
        
        
        # self.image = self.graphicslay.getImageItem()
        self.viewbox.setMenuEnabled(False)
        # self.image.setLookupTable(self.colourmap.getLookupTable())
        self.image.setColorMap(self.colourmap)
        self.image.setLevels((0.0,self.config['maxVal']-self.config['minVal']))
        self.viewbox.addItem(self.image)
        self.viewbox.setAspectLocked(True)
        self.graphicslay.setCentralItem(self.viewbox)
        # self.viewbox.setMenuEnabled(False)
        self.graphicslay.setMouseTracking(True)
        # self.graphicslay.installEventFilter(self)
        self.graphicslay.viewport().installEventFilter(self)
        # self.graphicslay.installEventFilter(self)
        self.toplayout.addWidget(self.graphicslay,6)
        self.toplayout.addWidget(self.gradient)

        self.actcontrolLayout = QtW.QVBoxLayout()
        self.sliderLayout = QtW.QHBoxLayout()
        self.sliderscale = SLIDER_SCALE/(self.config['maxVal']-self.config['minVal'])

        self.pistonLabel = pg.widgets.VerticalLabel.VerticalLabel("Piston")
        self.pistonLabel.setAlignment(QtC.Qt.AlignHCenter)
        self.sliderLayout.addWidget(self.pistonLabel)

        self.pistonSlider = QtW.QSlider(QtC.Qt.Vertical)
        self.pistonSlider.setRange(0,100)
        # self.pistonSlider.valueChanged.connect(self.pistonSlider_callback)
        self.pistonSlider_proxy = pg.SignalProxy(self.pistonSlider.valueChanged,delay=0.01,rateLimit=2,slot=self.pistonSlider_callback)
        self.sliderLayout.addWidget(self.pistonSlider)

        self.pistonGLW = pg.GraphicsLayoutWidget()
        self.pistonGLW.setMaximumWidth(50)
        self.pistonVB = self.pistonGLW.addViewBox(lockAspect=True,enableMouse=False,defaultPadding=0)
        self.pistonMap = pg.ImageItem(pg.colormap.modulatedBarData().T)
        self.pistonMap.setLookupTable(self.colourmap.getLookupTable())
        self.pistonVB.addItem(self.pistonMap)
        self.sliderLayout.addWidget(self.pistonGLW)

        self.actuatorLabel = pg.widgets.VerticalLabel.VerticalLabel("Poke")
        self.actuatorLabel.setAlignment(QtC.Qt.AlignHCenter)
        self.sliderLayout.addWidget(self.actuatorLabel)

        self.actuatorSlider = QtW.QSlider(QtC.Qt.Vertical)
        self.actuatorSlider.setRange(0,100)
        self.actuatorSlider.valueChanged.connect(self.actuatorSlider_callback)
        # self.actuatorSlider_proxy = pg.SignalProxy(self.actuatorSlider.valueChanged,delay=0.01,rateLimit=5,slot=self.actuatorSlider_callback)
        self.sliderLayout.addWidget(self.actuatorSlider)

        self.actcontrolLayout.addLayout(self.sliderLayout)

        self.actspinLayout = QtW.QHBoxLayout()

        self.pistonSpin = DoubleSpinBox()
        self.pistonSpin.setRange(self.config['minVal'],self.config['maxVal'])
        self.pistonSpin.setSingleStep(0.01)
        self.pistonSpin.editingFinished.connect(self.pistonSpin_callback)
        self.pistonSpin.stepChanged.connect(self.pistonSpin_callback)
        self.actspinLayout.addWidget(self.pistonSpin)
        self.actSpin = DoubleSpinBox()
        self.actSpin.setAccelerated(False)
        self.actSpin.setDecimals(3)
        self.actSpin.setRange(self.config['minVal'],self.config['maxVal'])
        self.actSpin.setSingleStep(0.001)
        self.actSpin.setStepType(QtW.QAbstractSpinBox.DefaultStepType)
        print(self.actSpin.stepType)
        self.actSpin.editingFinished.connect(self.actuatorSpin_callback)
        self.actSpin.stepChanged.connect(self.actuatorSpin_callback)
        self.actsignal.connect(self.actuator_callback)
        self.actspinLayout.addWidget(self.actSpin)

        self.actcontrolLayout.addLayout(self.actspinLayout)

        self.toplayout.addLayout(self.actcontrolLayout,1)

        self.toplayout.addStretch()

        

        # self.actuatorLayout = QtW.QVBoxLayout()
        # self.actuatorLabel = QtW.QLabel('0')
        
        # # self.actuatorLayout.addWidget(self.actuatorLabel)
        # self.actuatorLayout.addWidget(self.actuatorSlider)
        # self.toplayout.addLayout(self.actuatorLayout,1)


        self.continuousCheck = QtW.QPushButton("Continuous")
        self.continuousCheck.setCheckable(True)
        self.continuousCheck.toggle()

        self.setButton = QtW.QPushButton("Set")
        self.setButton.clicked.connect(self.set_callback)
        self.resetButton = QtW.QPushButton("Reset")
        self.resetButton.clicked.connect(self.reset_callback)
        self.deselectButton = QtW.QPushButton("Deselect")
        self.deselectButton.clicked.connect(self.deselect_callback)
        self.pokeButton = QtW.QPushButton("Start Poking")
        self.pokeButton.setCheckable(True)
        self.pokeButton.clicked.connect(self.poke_callback)
        self.pokeSpin = QtW.QDoubleSpinBox()
        self.pokeSpin.setRange(0,10)
        self.pokeSpin.setSingleStep(0.1)
        self.loadButton = QtW.QPushButton("Load File")
        self.loadButton.clicked.connect(self.load_callback)
        self.loadButton.setEnabled(False)
        self.playButton = QtW.QPushButton("Play File")
        self.playButton.clicked.connect(self.play_callback)
        self.playButton.setEnabled(False)
        self.botlayout.addWidget(self.continuousCheck)
        self.botlayout.addWidget(self.setButton)
        self.botlayout.addWidget(self.resetButton)
        self.botlayout.addWidget(self.deselectButton)
        self.botlayout.addWidget(self.pokeButton)
        self.botlayout.addWidget(self.pokeSpin)
        self.botlayout.addWidget(self.loadButton)
        self.botlayout.addWidget(self.playButton)
        self.setLayout(self.layout)

        # the image to display
        self.imagebuf = numpy.zeros((NPIXELS*self.config['actx'],NPIXELS*self.config['actx']))

        self.selected = []
        self.selectedactval = self.config.get("pokeVal",(self.config['maxVal']-self.config['minVal'])/20.)
        self.pokeSpin.setValue(0)
        # self.set_time = time.time()
        self.last_send = None
        self.set_signal_proxy = pg.SignalProxy(self.set_signal,delay=0.2,rateLimit=5,slot=self.set_callback)
        self.poker = ActPlayer(self)

        self.poke_thread = QtC.QThread()
        # Step 4: Move worker to the thread
        self.poker.moveToThread(self.poke_thread)
        # Step 5: Connect signals and slots
        self.poke_thread.started.connect(self.poker.run)
        self.poker.finished.connect(self.poke_thread.quit)
        # self.poker.finished.connect(self.poker.deleteLater)
        # self.poke_thread.finished.connect(self.poke_thread.deleteLater)


        self.poker.update.connect(self.update_image)
        self.poker.finished.connect(self.poke_finished)
        self.pokeType = "zonal"
        self.pokeAction.toggle()
        self.z2c = None
        self.kl2c = None
        # self.mapping = self.config['mapping']

        # mat = scipy.io.loadmat('/home/canapyrtc/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C-noll.mat')
        # mat = scipy.io.loadmat('/home/laserlab/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C-noll.mat')
        # mat = scipy.io.loadmat('/home/canapyrtc/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C.mat')
        # mat = scipy.io.loadmat('/Users/djenkins/OneDrive - ESO/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C-noll.mat')
        # self.alpao_zmat = mat['Z2C'][:,:]

        self.atmos = AtmosphereGenerator(D=D,wl=wl,N=N)
        self.atmos.readConfig(Zn=Zn,f=f,r_0=r_0,V=V)
        self.atmos.generateTurbulence()
        # self.player = ActPlayer(self)
        # self.player.update.connect(self.update_image)
        # self.player.finished.connect(self.poke_finished)
        self.setup_acts()
        self.installEventFilter(self)
        self.prevvals = numpy.zeros_like(self.actvals)

        self.plot = pg.PlotWidget()
        self.plot.installEventFilter(self)
        # self.plot = self.plot_win.addPlot()

    def eventFilter(self,obj,event):
        # print(event.type(),obj)
        if event.type() == QtC.QEvent.MouseButtonPress and obj is self.graphicslay.viewport():
            if event.buttons() == QtC.Qt.LeftButton:
                self.buttonPress(event)
            elif event.buttons() == QtC.Qt.RightButton:
                self.buttonPress(event)
        elif event.type() == QtC.QEvent.KeyPress and obj is self:
            if event.key() == QtC.Qt.Key_Return:
                self.poker.next_iter.emit()
            elif event.key() == QtC.Qt.Key_Backspace:
                self.poker.prev_iter.emit()
        elif event.type() == QtC.QEvent.Wheel and obj is self.graphicslay.viewport():
            return True
        elif event.type() == QtC.QEvent.Close and obj is self.plot:
            if self.plot.isVisible():
                self.updateplot.disconnect(self.plotacts)
        # elif event.type() == QtC.QEvent.MouseButtonDblClick and obj is self.graphicslay.viewport():
        #     self.viewbox.autoRange()
        # elif event.type() == QtC.QEvent.MouseMove and obj is self.graphicslay.viewport():
        #     self.mousemove(event)
        # elif event.type() == QtC.QEvent.Leave and obj is self.graphicslay.viewport():
        #     self.mousefocusout(event)
        elif event.type() == QtC.QEvent.Close and obj is self:

            self.plot.close()
            self.exit()
        return super().eventFilter(obj, event)

    def showactplot(self):
        self.plot.show()
        self.updateplot.connect(self.plotacts)

    def plotacts(self):
        self.plot.clear()
        self.plot.plot(numpy.arange(self.config['nacts']+1), self.actvals+self.flat+self.pistonvalue, stepMode="center", fillLevel=0, fillOutline=True, brush=(0,0,255,150))

    def setup_acts(self):
        self.actItems = []
        self.textItems = []
        # self.actmap = numpy.array(self.config['actMap'])
        self.actmap = numpy.zeros((self.config['actx'],self.config['actx'],2))
        self.actmap[:,:,0] = self.config['actMap']
        pen = QtG.QPen(QtC.Qt.white,0.5)
        cnt=0
        for i in range(self.config['actx']):
            for j in range(self.config['actx']):
                if self.actmap[i,j,0] == 1:
                    self.actItems.append(QtW.QGraphicsRectItem(i*NPIXELS,j*NPIXELS,NPIXELS,NPIXELS))
                    self.actItems[-1].setPen(pen)
                    self.viewbox.addItem(self.actItems[-1])
                    self.actmap[i,j,1] = i*self.config['actx']+j

        self.actmap = numpy.transpose(self.actmap,axes=(1,0,2))
        self.actmap = numpy.rot90(self.actmap,2)

        self.transform = numpy.reshape(self.actmap,(self.config['actx']*self.config['actx'],2)).astype(int)
        self.mapping  = numpy.where((self.transform==1))[0]
        self.transform =  self.transform[self.mapping,1]

        for i in range(self.config['actx']):
            for j in range(self.config['actx']):
                if self.actmap[i,j,0] == 1:
                    # self.transform.append(self.actmap[i,j,1])
                    act = numpy.where(self.transform == i*self.config['actx']+j)[0][0]
                    ti = pg.TextItem(str(act),color=getPyQtColour('green'))
                    fi = QtG.QFont()
                    fi.setPointSize(int(14))
                    ti.setFont(fi)
                    self.textItems.append(ti)
                    self.viewbox.addItem(ti)
                    ti.setPos((i)*NPIXELS,(j+1)*NPIXELS)

        self.init_callback()
        self.update_image()

    def saveFlat(self):
        now  = datetime.datetime.now()
        fname = HOME+"/data/"+f"flat{now.day:02}{now.month:02}{now.hour:02}{now.minute:02}.txt"
        get_name = QtW.QFileDialog.getSaveFileName(self, 'Save Shape', fname,"Text files (*.txt)",options=QtW.QFileDialog.DontUseNativeDialog)
        fname = get_name[0]
        if fname != "":
            self.save_flat(fname)

    def loadFlat(self):
        get_name = QtW.QFileDialog.getOpenFileName(self, 'Open Flat', (HOME+"/data"),"Text files (*.txt)",options=QtW.QFileDialog.DontUseNativeDialog)
        fname = get_name[0]
        if fname != "":
            self.load_flat(fname)
        self.reset_callback()

    def buttonPress(self,event):
        pos = event.pos()
        if self.image.sceneBoundingRect().contains(pos):
            mousePoint = self.viewbox.mapSceneToView(pos)
            indx = int(self.config['actx']*(mousePoint.x()//NPIXELS) + mousePoint.y()//NPIXELS)
            act = numpy.where(self.transform==indx)[0][0]
            indx = numpy.where(self.mapping==indx)[0][0]
            if self.pokeType == "zonal":
                if len(self.selected) == 0:
                    if event.buttons() == QtC.Qt.LeftButton:#left click
                        self.actuatorSlider.valueChanged.disconnect(self.actuatorSlider_callback)
                        # self.actuatorSlider_proxy.sigDelayed.disconnect(self.actuatorSlider_callback)
                        self.actuatorSlider.setValue(int((self.pistonvalue-self.config['minVal']+self.actvals[act])*self.sliderscale))
                        self.actuatorSlider.valueChanged.connect(self.actuatorSlider_callback)
                        # self.actuatorSlider_proxy.sigDelayed.connect(self.actuatorSlider_callback)
                        self.actSpin.setValue(self.pistonvalue+self.actvals[act])
                        self.selectedactval = self.actvals[act]
                        self.prevvals[act] = self.actvals[act]
                if (indx,act) not in self.selected:
                    self.actItems[indx].setPen(QtG.QPen(QtC.Qt.green))
                    self.selected.append((indx,act))
                    self.prevvals[act] = self.actvals[act]
                    self.actvals[act] = self.selectedactval
                else:
                    self.actItems[indx].setPen(QtG.QPen(QtC.Qt.white,0.5))
                    if event.buttons() == QtC.Qt.LeftButton:
                        self.actvals[act] = self.prevvals[act]
                    self.selected.remove((indx,act))
            elif self.pokeType == "zernike" or self.pokeType == "karhunen":
                print("click, setting mode: ",act,self.zcoeffs[act])
                if len(self.selected) == 0:
                    if event.buttons() == QtC.Qt.LeftButton:#left click
                        self.selectedZval = self.zcoeffs[act]
                        self.actuatorSlider.valueChanged.disconnect(self.actuatorSlider_callback)
                        # self.actuatorSlider_proxy.sigDelayed.disconnect(self.actuatorSlider_callback)
                        self.actuatorSlider.setValue(int((self.selectedZval-self.config['minVal'])*self.sliderscale))
                        self.actuatorSlider.valueChanged.connect(self.actuatorSlider_callback)
                        # self.actuatorSlider_proxy.sigDelayed.connect(self.actuatorSlider_callback)
                        self.actSpin.setValue(self.selectedZval)
                if (indx,act) not in self.selected:
                    self.actItems[indx].setPen(QtG.QPen(QtC.Qt.green))
                    self.selected.append((indx,act))
                    self.prevvals[act] = self.zcoeffs[act]
                    self.zcoeffs[act] = self.selectedZval
                    self.calcActs()
                else:
                    self.actItems[indx].setPen(QtG.QPen(QtC.Qt.white,0.5))
                    if event.buttons() == QtC.Qt.LeftButton:
                        self.zcoeffs[act] = self.prevvals[act]
                        self.calcActs()
                    self.selected.remove((indx,act))
                # if (indx,act) in self.selected:
                #     self.actItems[indx].setPen(QtG.QPen(QtC.Qt.white,0.5))
                #     self.selected.remove((indx,act))
                # else:
                #     for sel in self.selected:
                #         self.actItems[sel[0]].setPen(QtG.QPen(QtC.Qt.white,0.5))
                #     self.selected = []
                #     self.selectedZval = self.zcoeffs[act]
                #     self.actuatorSlider.valueChanged.disconnect(self.actuatorSlider_callback)
                #     # self.actuatorSlider_proxy.sigDelayed.disconnect(self.actuatorSlider_callback)
                #     self.actuatorSlider.setValue(int((self.selectedZval-self.config['minVal'])*self.sliderscale))
                #     self.actuatorSlider.valueChanged.connect(self.actuatorSlider_callback)
                #     # self.actuatorSlider_proxy.sigDelayed.connect(self.actuatorSlider_callback)
                #     self.actSpin.setValue(self.selectedZval)
                #     self.actItems[indx].setPen(QtG.QPen(QtC.Qt.green))
                #     self.selected.append((indx,act))
                print(self.zcoeffs)
            self.update_image(check=True)

    def pistonSlider_callback(self,value):
        value = value[0]/self.sliderscale + self.config['minVal']
        self.pistonSpin.setValue(value)

        self.actuatorSlider.valueChanged.disconnect(self.actuatorSlider_callback)
        # self.actuatorSlider_proxy.sigDelayed.disconnect(self.actuatorSlider_callback)
        self.actuatorSlider.setValue(int((value-self.config['minVal']+self.selectedactval)*self.sliderscale))
        self.actuatorSlider.valueChanged.connect(self.actuatorSlider_callback)
        # self.actuatorSlider_proxy.sigDelayed.connect(self.actuatorSlider_callback)
        
        self.actSpin.setValue(value+self.selectedactval)
        self.piston_callback(value)

    def pistonSpin_callback(self):
        value = self.pistonSpin.value()
        # value = value#/self.sliderscale + self.config['minVal']
        self.pistonvalue = value
        # self.pistonSlider.valueChanged.disconnect(self.pistonSlider_callback)
        self.pistonSlider_proxy.sigDelayed.disconnect(self.pistonSlider_callback)
        self.pistonSlider.setValue(int((value-self.config['minVal'])*self.sliderscale))
        # self.pistonSlider.valueChanged.connect(self.pistonSlider_callback)
        self.pistonSlider_proxy.sigDelayed.connect(self.pistonSlider_callback)
        self.actuatorSlider.valueChanged.disconnect(self.actuatorSlider_callback)
        # self.actuatorSlider_proxy.sigDelayed.disconnect(self.actuatorSlider_callback)
        self.actuatorSlider.setValue(int((value-self.config['minVal']+self.selectedactval)*self.sliderscale))
        self.actuatorSlider.valueChanged.connect(self.actuatorSlider_callback)
        # self.actuatorSlider_proxy.sigDelayed.connect(self.actuatorSlider_callback)
        
        self.actSpin.setValue(value+self.selectedactval)

        self.piston_callback(value)


    def piston_callback(self,value):
        self.pistonvalue = value
        self.update_image()

    def actuatorSlider_callback(self,value):
        logging.debug("actuatorSlider_callback")
        value = float(value/self.sliderscale + self.config['minVal'])
        self.actSpin.setValue(value)
        # self.actuator_callback(value)
        self.actsignal.emit(value)

    def actuatorSpin_callback(self):
        logging.debug("actuatorSpin_callback")
        value = self.actSpin.value()
        self.actuatorSlider.valueChanged.disconnect(self.actuatorSlider_callback)
        # self.actuatorSlider_proxy.sigDelayed.disconnect(self.actuatorSlider_callback)
        self.actuatorSlider.setValue(int((value-self.config['minVal'])*self.sliderscale))
        self.actuatorSlider.valueChanged.connect(self.actuatorSlider_callback)
        # self.actuatorSlider_proxy.sigDelayed.connect(self.actuatorSlider_callback)
        # self.actuator_callback(value)
        self.actsignal.emit(value)

    def actuator_callback(self,value):
        logging.debug("actuator_callback")
        if self.pokeType == "zonal":
            logging.debug("zonal poke")
            self.selectedactval = value - self.pistonvalue
            for indx in self.selected:
                self.actvals[indx[1]] = value - self.pistonvalue
        elif self.pokeType == "zernike" or self.pokeType == "karhunen":
            logging.debug("modal poke")
            self.selectedZval = value
            for indx in self.selected:
                print("setting mode: ",indx[1],self.selectedZval)
                self.zcoeffs[indx[1]] = self.selectedZval
                self.calcActs()
                self.print_vals(self.actvals+self.flat+self.pistonvalue)
            print(self.zcoeffs)
        self.update_image(check=True)

    def calcActs(self):
        if self.pokeType == "zernike":
            self.actvals[:] = numpy.dot(self.zcoeffs[:self.z2c.shape[0]],self.z2c)
        elif self.pokeType == "karhunen":
            self.actvals[:] = numpy.dot(self.zcoeffs[:self.kl2c.shape[0]],self.kl2c)

    def set_actuator(self,act,val):
        # act = self.config['transform'][act]
        act = self.transform[act]
        self.actvals[act] = val - self.pistonvalue

    def update_image(self,set_darc=True,check=False):
        self.updateplot.emit()
        self.imagebuf[:,:] = 0
        for i in range(self.config['nacts']):
            x = self.mapping[i]//self.config['actx']
            y = self.mapping[i]%self.config['actx']
            # act = self.config['transform'].index(self.mapping[i])
            act = numpy.where(self.transform==self.mapping[i])[0][0]
            # self.imagebuf[x*NPIXELS:x*NPIXELS+NPIXELS,y*NPIXELS:y*NPIXELS+NPIXELS] = self.actvals[act]+self.pistonvalue-self.config['minVal']
            gauss = ((self.actvals[act]+self.pistonvalue))*gkern(3)
            x0 = x*NPIXELS-NPIXELS
            x1 = min(x*NPIXELS+2*NPIXELS,self.imagebuf.shape[0])
            y0 = y*NPIXELS-NPIXELS
            y1 = min(y*NPIXELS+2*NPIXELS,self.imagebuf.shape[1])
            x3 = 0
            y3 = 0
            if x0<0:
                x0 = 0
                x3 = NPIXELS
            if y0<0:
                y0 = 0
                y3 = NPIXELS
            self.imagebuf[x0:x1,y0:y1] += gauss[x3:x1-x0+x3,y3:y1-y0+y3]
        self.imagebuf -= self.config['minVal']
        self.image.setImage(self.imagebuf)#,autoLevels=True)
        # self.image.setLevels((0,self.config['maxVal']-self.config['minVal']))
        self.updateImage()
        self.viewbox.update()
        if self.continuousCheck.isChecked() and set_darc:
            self.set_signal.emit(check)

    def updateImage(self,obj=None):
        white = self.gradient.tickValue(self.ticks[0])
        black = self.gradient.tickValue(self.ticks[1])
        self.gradient.sigGradientChanged.disconnect(self.updateImage)
        self.gradient.setTickValue(self.ticks[1],1-white)
        self.gradient.setTickValue(self.ticks[0],1-black)
        self.gradient.sigGradientChanged.connect(self.updateImage)
        white *= (self.config['maxVal']-self.config['minVal'])
        black *= (self.config['maxVal']-self.config['minVal'])
        # lut = self.gradient.getLookupTable(512,alpha=None)
        # self.image.setImage(self.imagebuf,white=white,black=black)
        # self.image.setLookupTable(lut)
        self.image.setLevels((white,black))

    def set_callback(self,check=True):
        # if force:
            # print("sending to darc")
            # print(self.actvals+self.pistonvalue)
        if check:
            if not (self.last_send != self.actvals+self.pistonvalue).any():
                return None
        self.set_darc()
        # self.last_send = self.actvals+self.pistonvalue
        # elif time.time()-self.set_time>0.1:
        #     self.set_callback(True)
        #     self.set_time = time.time()

    def init_callback(self):
        self.deselect_callback()
        self.actvals[:] = 0
        self.zcoeffs[:] = 0
        self.pistonvalue = self.config['midVal']
        self.selectedactval = self.config.get("pokeVal",(self.config['maxVal']-self.config['minVal'])/20.)
        self.pistonSpin.setValue(self.config['midVal'])
        self.pistonSpin.editingFinished.emit()
        self.actSpin.editingFinished.emit()
        self.update_image()

    def reset_callback(self):
        logging.debug("reset_callback")
        if self.poke_thread.isRunning():
            self.pokeButton.setChecked(False)
            self.pokeButton.setText("Start Poking")
            self.poker.stop()
        self.init_callback()
        self.set_callback()

    def deselect_callback(self):
        for indx in self.selected:
            self.actItems[indx[0]].setPen(QtG.QPen(QtC.Qt.white,0.5))
        self.selected = []
        self.viewbox.update()

    def poke_callback(self):
        logging.debug("poke_callback")
        if self.poke_thread.isRunning():
            self.pokeButton.setChecked(False)
            self.pokeButton.setText("Start Poking")
            self.poker.stop()
        else:
            self.pokeButton.setChecked(True)
            self.pokeButton.setText("Stop Poking")
            if self.pokeType == "zonal":
                commands = numpy.diag(numpy.ones(self.config['nacts']))*self.selectedactval
                if len(self.selected) > 0:
                    self.poker.iter = self.selected[0][1]
                    self.deselect_callback()
                else:
                    self.poker.iter = None
            elif self.pokeType == "zernike":
                commands = self.zernikePoke()
                if len(self.selected) > 0:
                    self.poker.iter = self.selected[0][1]
                    self.deselect_callback()
                else:
                    self.poker.iter = None
            elif self.pokeType == "karhunen":
                commands = self.karhunenPoke()
                if len(self.selected) > 0:
                    self.poker.iter = self.selected[0][1]
                    self.deselect_callback()
                else:
                    self.poker.iter = None
            elif self.pokeType == "atmos":
                commands = self.atmos.Z2DM(self.z2c)+self.selectedactval
            self.poker.setCommands(commands)
            self.poker.setPeriodRest(self.pokeSpin.value(),0)
            self.poke_thread.start()

    def poke_finished(self):
        self.pokeButton.setChecked(False)
        self.pokeButton.setText("Start Poking")

    def load_callback(self):
        pass

    def play_callback(self):
        pass

    def zonalPoke(self):
        commands = numpy.diag(numpy.ones(self.config['nacts']))

    def zernikePoke(self):
        if self.z2c is None:
            raise Exception("error no zernike2command matrix")
        n_zern = self.z2c.shape[0]
        z_coeffs = numpy.diag(numpy.ones(n_zern))*self.selectedZval
        commands = numpy.dot(z_coeffs,self.z2c)
        return commands

    def karhunenPoke(self):
        if self.kl2c is None:
            raise Exception("error no kl2command matrix")
        n_zern = self.kl2c.shape[0]
        z_coeffs = numpy.diag(numpy.ones(n_zern))*self.selectedZval
        commands = numpy.dot(z_coeffs,self.kl2c)
        return commands

    def set_poke(self,action):
        if self.pokegroup.checkedAction() == self.pokeAction:
            print("Poke")
            self.pokeType = "zonal"
            return None
        if self.pokegroup.checkedAction() == self.karhunenAction:
            print("KL Modes")
            self.pokeType = "karhunen"
            self.selectedZval = self.selectedactval
            return None
        if self.pokegroup.checkedAction() == self.zernikeAction:
            print("Zernike")
            self.pokeType = "zernike"
            self.selectedZval = self.selectedactval
            return None
        if self.pokegroup.checkedAction() == self.atmosAction:
            print("Atmos")
            self.pokeType = "atmos"
            return None

    def exit(self):
        self.poker.stop()
        self.poker.deleteLater()
        self.poke_thread.deleteLater()

# class ZonalPoker(QtC.QThread):
#     update = QtC.pyqtSignal(bool)
#     finished = QtC.pyqtSignal()
#     def __init__(self,parent):
#         super().__init__()
#         self.parent = parent
#         self.pokeval = 0.0
#         self.period = 0.0
#     def run(self):
#         self.go = 1
#         for i in range(self.parent.config['nacts']):
#             if self.go:
#                 self.parent.actvals[i] += self.pokeval
#                 self.parent.set_callback()
#                 self.update.emit(False)
#                 time.sleep(self.period)
#                 self.parent.actvals[i] -= self.pokeval
#                 # self.parent.set_callback()
#                 self.update.emit(False)
#             else:
#                 break
#         self.finished.emit()
#     def stop(self):
#         self.go = 0

class ActPlayer(QtC.QObject):
    update = QtC.pyqtSignal(bool)
    finished = QtC.pyqtSignal()
    next_iter = QtC.pyqtSignal()
    prev_iter = QtC.pyqtSignal()
    def __init__(self,parent,zero=0):
        super().__init__()
        self.parent = parent
        self.commands = None
        self.period = 0.0
        self.rest = 0.01
        self.iter = None
        self.go = 0
        self.zero = zero
    def run(self):
        if self.commands is None:
            self.finished.emit()
            return None
        if self.iter is None:
            self.iter = 0
            self.parent.actvals[:self.commands[self.iter].shape[0]] += self.commands[self.iter][:self.parent.actvals.shape[0]]
        indx = self.parent.mapping[self.iter]
        act = numpy.where(self.parent.transform==indx)[0][0]
        self.parent.actItems[act].setPen(QtG.QPen(QtC.Qt.red,0.5))
        self.parent.set_darc()
        self.update.emit(False)
        self.iter += 1
        if float(self.period) == 0.0:
            self.go = 2
            self.next_iter.connect(self.iterate)
            self.prev_iter.connect(self.reverse)
            return None
        else:
            self.go = 1
            time.sleep(self.period)
            while self.iter < self.commands.shape[1] and self.go == 1:
                self.iterate()
                time.sleep(self.period)
            self.finish()

    def iterate(self):
        self.parent.actvals[:self.commands[self.iter-1].shape[0]] -= self.commands[self.iter-1][:self.parent.actvals.shape[0]]
        indx = self.parent.mapping[self.iter-1]
        act = numpy.where(self.parent.transform==indx)[0][0]
        self.parent.actItems[act].setPen(QtG.QPen(QtC.Qt.white,0.5))
        if self.zero:
            self.parent.set_darc()
            time.sleep(self.rest)
        self.parent.actvals[:self.commands[self.iter].shape[0]] += self.commands[self.iter][:self.parent.actvals.shape[0]]
        self.parent.set_darc()
        indx = self.parent.mapping[self.iter]
        act = numpy.where(self.parent.transform==indx)[0][0]
        self.parent.actItems[act].setPen(QtG.QPen(QtC.Qt.red))
        self.update.emit(False)
        self.iter += 1

    def reverse(self):
        if self.iter <= 1:
            return
        self.iter -= 1
        self.parent.actvals[:self.commands[self.iter].shape[0]] -= self.commands[self.iter][:self.parent.actvals.shape[0]]
        indx = self.parent.mapping[self.iter]
        act = numpy.where(self.parent.transform==indx)[0][0]
        self.parent.actItems[act].setPen(QtG.QPen(QtC.Qt.white,0.5))
        if self.zero:
            self.parent.set_darc()
            time.sleep(self.rest)
        self.parent.actvals[:self.commands[self.iter-1].shape[0]] += self.commands[self.iter-1][:self.parent.actvals.shape[0]]
        indx = self.parent.mapping[self.iter-1]
        act = numpy.where(self.parent.transform==indx)[0][0]
        self.parent.actItems[act].setPen(QtG.QPen(QtC.Qt.red,0.5))
        self.parent.set_darc()
        self.update.emit(False)

    def setPeriodRest(self,period,rest=0.01):
        self.period = period
        self.rest = rest
        if self.rest == 0:
            self.zero = 0

    def setCommands(self,commands):
        self.commands = commands

    def stop(self):
        if self.go == 1:
            self.go = 0
        elif self.go == 2:
            self.go = 0
            self.next_iter.disconnect(self.iterate)
            self.prev_iter.disconnect(self.reverse)
            print("stopping poker")
            self.parent.actvals[:self.commands[self.iter-1].shape[0]] -= self.commands[self.iter-1][:self.parent.actvals.shape[0]]
            self.parent.set_darc()
            indx = self.parent.mapping[self.iter-1]
            act = numpy.where(self.parent.transform==indx)[0][0]
            self.parent.actItems[act].setPen(QtG.QPen(QtC.Qt.white,0.5))
        self.finished.emit()

    def finish(self):
        self.iter = 0
        self.parent.actvals[:self.commands[self.iter-1].shape[0]] -= self.commands[self.iter-1][:self.parent.actvals.shape[0]]
        self.parent.set_callback()
        self.update.emit(False)
        self.finished.emit()

def main():
    print(HOME)
    prefix = "canapy"
    app = QtW.QApplication(sys.argv)
    dp = DmControl(ALPAO9715_config,prefix)
    # dp = DmControl(Boston_config,prefix)
    # dp.z2c = numpy.random.random(30*492)
    # dp.z2c.shape = 30,492
    ALPAO_KL2C = 1000.0*fits.getdata(HOME+'/git/canapy-rtc/config/AlpaoConfig/m2c_new.fits').T
    mat = scipy.io.loadmat(HOME+'/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C-noll.mat')
    # mat = scipy.io.loadmat(HOME+'/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C.mat')
    ALPAO_Z2C = mat['Z2C'][:,:]
    dp.z2c = ALPAO_Z2C
    dp.kl2c = ALPAO_KL2C
    dp.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
    mat = scipy.io.loadmat(HOME+'/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C-noll.mat')
    # mat = scipy.io.loadmat(HOME+'/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C.mat')
    ALPAO_Z2C = mat['Z2C'][:,:]
    print(ALPAO_Z2C.shape)
    mat = fits.getdata(HOME+'/git/canapy-rtc/config/AlpaoConfig/m2c.fits').T
    print(mat.shape)
    
    # ALPAO_KL2C = 
