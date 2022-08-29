
import ast
from pathlib import PosixPath
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from pyqtgraph.parametertree import Parameter, ParameterTree, ParameterItem, registerParameterType
from pyqtgraph import DataTreeWidget
import numpy

from ..misc import ParameterTreeQt, ParamSetterQt, PrefixChooser


class DaemonQt_base(QtW.QWidget):
    def __init__(self, parent=None):
        QtW.QWidget.__init__(self, parent=parent)

        # define menu
        self.menu = QtW.QMenu("&Daemon")
        self.openconfigAction = QtW.QAction('Open Config File')
        self.setparamAction = QtW.QAction('Set Parameter')
        self.hardresetAction = QtW.QAction('Hard Reset')
        self.menu.addAction(self.openconfigAction)
        self.menu.addAction(self.setparamAction)
        self.menu.addAction(self.hardresetAction)

        # define labels
        self.config_label = QtW.QLabel("Choose config:")

        # define buttons
        self.startdarc_button = QtW.QPushButton("Start Darc")
        self.stopdarc_button = QtW.QPushButton("Stop Darc")
        self.status_button = QtW.QPushButton("Get Status")
        self.selectconfig_button = QtW.QPushButton("Open Other File")
        self.viewparams_button = QtW.QPushButton("Inspect Parameters")
        self.refreshparams_button = QtW.QPushButton("Refresh Parameters")
        self.saveparams_button = QtW.QPushButton("Save ParamBuf")

        # define text input

        # define text display
        self.status_text  = QtW.QPlainTextEdit()
        self.status_text.setReadOnly(True)

        # define dropdown menu
        self.config_menu = QtW.QComboBox()

        # define other widgets
        self.prefix_setter = PrefixChooser(self)
        self.options_tree = ParameterTreeQt("lark options",parent=self)
        self.param_tree = ParameterTreeQt("darc params",readonly=True,parent=self)
        self.param_setter = ParamSetterQt(self)
        # self.param_tree = DataTreeWidget()

        # configure widgets
        self.param_tree.setWindowFlags(QtC.Qt.Window | QtC.Qt.Dialog)
        self.param_setter.setWindowFlags(self.param_setter.windowFlags() | QtC.Qt.Dialog)

        # define layout
        self.mainlay = QtW.QVBoxLayout()
        self.hlay = QtW.QHBoxLayout()
        self.vlay = QtW.QVBoxLayout()
        self.config_lay = QtW.QHBoxLayout()
        self.button_lay1 = QtW.QHBoxLayout()
        self.button_lay2 = QtW.QHBoxLayout()

        # build layout
        self.vlay.addWidget(self.prefix_setter)

        self.vlay.addLayout(self.config_lay)
        self.vlay.addLayout(self.button_lay1)
        self.vlay.addLayout(self.button_lay2)

        self.vlay.addWidget(self.status_text)

        self.config_lay.addWidget(self.config_label)
        self.config_lay.addWidget(self.config_menu)
        self.config_lay.addWidget(self.selectconfig_button)

        self.button_lay1.addWidget(self.viewparams_button)
        self.button_lay1.addWidget(self.refreshparams_button)
        self.button_lay1.addWidget(self.saveparams_button)

        self.button_lay2.addWidget(self.startdarc_button)
        self.button_lay2.addWidget(self.stopdarc_button)
        self.button_lay2.addWidget(self.status_button)

        self.hlay.addLayout(self.vlay)
        self.hlay.addWidget(self.options_tree)

        # add menu
        if parent is None:
            self.menuBar = QtW.QMenuBar()
            self.menuBar.addMenu(self.menu)
            self.mainlay.addWidget(self.menuBar)

        # set layout
        self.mainlay.addLayout(self.hlay)
        self.setLayout(self.mainlay)

        # parameter tree
        # start button
        # stop button
        # open config button
        # validate params button
        # check status
        # config dropdown
        # startup options, like darccontrol options, parametertree?


class ControlQt_base(QtW.QWidget):
    def __init__(self,parent=None):
        QtW.QWidget.__init__(self,parent=parent)

        # define menu
        self.menu = QtW.QMenu("&Control")

        # define labels
        self.cameraopen_label = QtW.QLabel("Camera open:")
        self.mirroropen_label = QtW.QLabel("Mirror open:")
        self.gain_label = QtW.QLabel("Global gain")
        self.leak_label = QtW.QLabel("Global leak")

        # define textinput

        # define spinbox
        self.gain_spin = QtW.QDoubleSpinBox()
        self.gain_spin.setDecimals(4)
        self.gain_spin.setRange(0.0,1.0)
        self.gain_spin.setSingleStep(0.001)
        self.leak_spin = QtW.QDoubleSpinBox()
        self.leak_spin.setDecimals(4)
        self.leak_spin.setRange(0.0,1.0)
        self.leak_spin.setSingleStep(0.001)

        # define buttons
        self.openloop_button = QtW.QPushButton("Open Loop")
        self.closeloop_button = QtW.QPushButton("Close Loop")

        # define check
        self.cameraopen_check = QtW.QCheckBox()
        self.mirroropen_check = QtW.QCheckBox()

        # build layout
        self.lay = QtW.QGridLayout()
        self.lay.addWidget(self.openloop_button,0,0)
        self.lay.addWidget(self.closeloop_button,0,1)
        self.lay.addWidget(self.cameraopen_label,1,0)
        self.lay.addWidget(self.cameraopen_check,1,1)
        self.lay.addWidget(self.mirroropen_label,2,0)
        self.lay.addWidget(self.mirroropen_check,2,1)
        self.lay.addWidget(self.gain_label,3,0)
        self.lay.addWidget(self.gain_spin,3,1)
        self.lay.addWidget(self.leak_label,4,0)
        self.lay.addWidget(self.leak_spin,4,1)

        self.setLayout(self.lay)




