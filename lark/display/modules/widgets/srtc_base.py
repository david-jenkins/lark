import sys
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG
from lark.display.widgets.misc import ParameterTreeQt, ServiceChooser, ServiceFinder

from pyqtgraph.parametertree import ParameterTree


class SrtcFunctionList_base(QtW.QWidget):
    def __init__(self,parent=None):
        QtW.QWidget.__init__(self,parent=parent)

        self.menu = None

        self.execute_button = QtW.QPushButton("Run Once")
        self.apply_label = QtW.QLabel("Apply")
        self.apply_check = QtW.QCheckBox()
        self.begin_button = QtW.QPushButton("Start")
        self.period_label = QtW.QLabel("Period:")
        self.period_input = QtW.QDoubleSpinBox()
        self.period_input.setSuffix(" s")
        self.period_input.setRange(0.0,3600.0)
        self.period_input.setDecimals(1)
        
        self.stop_button = QtW.QPushButton("Stop")

        self.setvalues_button = QtW.QPushButton("Set Values")

        self.func_list = QtW.QListWidget(self)

        self.param_tree = ParameterTreeQt("One time params",parent=self)

        self.hlay = QtW.QHBoxLayout()
        self.vlay = QtW.QVBoxLayout()
        self.glay = QtW.QGridLayout()

        self.glay.addWidget(self.execute_button,0,0)
        self.glay.addWidget(self.apply_label,0,1)
        self.glay.addWidget(self.apply_check,0,2)
        self.glay.addWidget(self.begin_button,0,3)
        self.glay.addWidget(self.period_label,0,4)
        self.glay.addWidget(self.period_input,0,5)
        self.glay.addWidget(self.stop_button,0,6)
        self.glay.addWidget(self.setvalues_button,0,7)

        self.hlay.addWidget(self.func_list)
        self.hlay.addWidget(self.param_tree)

        self.vlay.addLayout(self.glay)
        self.vlay.addLayout(self.hlay)

        self.setLayout(self.vlay)

class SrtcControl_base(QtW.QWidget):
    def __init__(self,parent=None):
        QtW.QWidget.__init__(self,parent=parent)

        self.menu = None

        self.srtcname_finder = ServiceFinder("SRTC","SRTC",self)

        self.srtcname_chooser = ServiceChooser("SRTC name", self)

        self.startsrtc_button = QtW.QPushButton("Start SRTC")
        self.stopsrtc_button = QtW.QPushButton("Stop SRTC")
        self.resetsrtc_button = QtW.QPushButton("Reset SRTC")
        self.statussrtc_button = QtW.QPushButton("Status")
        self.status_label = QtW.QTextEdit()
        self.status_label.setReadOnly(True)

        self.hlay2 = QtW.QHBoxLayout()
        self.vlay = QtW.QVBoxLayout()
        # self.glay = QtW.QGridLayout()

        # self.glay.addWidget(self.srtcname_label,0,0,1,1)
        # self.glay.addWidget(self.srtcname_input,0,1,1,1)
        # self.glay.addWidget(self.srtcselect_button,0,2,1,1)
        # self.glay.addWidget(self.startsrtc_button,1,0,1,1)
        # self.glay.addWidget(self.stopsrtc_button,1,1,1,1)
        # self.glay.addWidget(self.statussrtc_button,1,2,1,1)
        # self.glay.addWidget(self.status_label,2,0,1,3)

        # self.setLayout(self.glay)

        # self.hlay2.addWidget(self.startsrtc_button)
        # self.hlay2.addWidget(self.stopsrtc_button)
        self.hlay2.addWidget(self.resetsrtc_button)
        self.hlay2.addWidget(self.statussrtc_button)
        self.hlay2.addStretch()
        self.vlay.addWidget(self.srtcname_finder)
        self.vlay.addWidget(self.srtcname_chooser)
        self.vlay.addLayout(self.hlay2)
        self.vlay.addWidget(self.status_label)

        self.setLayout(self.vlay)
