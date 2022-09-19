
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC

from lark.display.widgets.main_base import LarkTab

from .misc import DaemonDarcList, HostChooser, ParameterTreeQt, ParamSetterQt, PrefixChooser, ServiceFinder

class Daemon_base(LarkTab):
    def __init__(self, parent:QtW.QWidget = None):
        super().__init__(parent=parent)

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
        self.chosenconfig_label = QtW.QLabel("Using config file: ")

        # define buttons
        self.startdarc_button = QtW.QPushButton("Start Darc")
        self.stopdarc_button = QtW.QPushButton("Stop Darc")
        self.status_button = QtW.QPushButton("Get Status")
        self.selectconfig_button = QtW.QPushButton("Choose Folder")
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
        self.darc_chooser = DaemonDarcList(parent=self)
        self.daemon_chooser = ServiceFinder("Daemon on NameServer","_DAEMON",self)
        self.host_setter = HostChooser(self)
        self.prefix_setter = PrefixChooser(self)
        self.options_tree = ParameterTreeQt("lark options",parent=self)
        self.param_tree = ParameterTreeQt("darc params",readonly=True,parent=self)
        self.param_setter = ParamSetterQt(self)
        self.param_setter.setWindowFlags(QtC.Qt.Window | QtC.Qt.Dialog)
        # self.param_tree = DataTreeWidget()

        # configure widgets
        self.param_tree.setWindowFlags(QtC.Qt.Window | QtC.Qt.Dialog)
        self.param_setter.setWindowFlags(self.param_setter.windowFlags() | QtC.Qt.Dialog)

        # define layout
        self.mainlay = QtW.QVBoxLayout()
        self.hlay = QtW.QHBoxLayout()
        self.glay = QtW.QGridLayout()
        self.config_lay = QtW.QHBoxLayout()
        self.button_lay1 = QtW.QHBoxLayout()
        self.button_lay2 = QtW.QHBoxLayout()

        # build layout
        self.glay.addWidget(self.daemon_chooser,0,0,1,3)
        self.glay.addWidget(self.host_setter,1,0,1,3)
        self.glay.addWidget(self.darc_chooser,2,0,1,3)
        self.glay.addWidget(self.prefix_setter,3,0,1,3)

        self.glay.addLayout(self.config_lay,4,0,1,3)
        self.glay.addWidget(self.chosenconfig_label,5,0,1,3)
        self.glay.addLayout(self.button_lay1,6,0,1,3)
        self.glay.addLayout(self.button_lay2,7,0,1,3)

        self.glay.addWidget(self.options_tree,8,0,1,3)

        self.config_lay.addWidget(self.config_label)
        self.config_lay.addWidget(self.config_menu)
        self.config_lay.addWidget(self.selectconfig_button)

        self.button_lay1.addWidget(self.viewparams_button)
        self.button_lay1.addWidget(self.refreshparams_button)
        self.button_lay1.addWidget(self.saveparams_button)

        self.button_lay2.addWidget(self.startdarc_button)
        self.button_lay2.addWidget(self.stopdarc_button)
        self.button_lay2.addWidget(self.status_button)

        self.hlay.addLayout(self.glay)
        self.hlay.addWidget(self.status_text)

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

class DarcControl_base(LarkTab):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.prefix_chooser = ServiceFinder("Darc on NameServer","CONTROL",self)
        self.prefix_setter = PrefixChooser(self)

        self.stop_button = QtW.QPushButton("Stop")
        self.reset_button = QtW.QPushButton("Reset")
        self.status_button = QtW.QPushButton("Status")
        self.refresh_button = QtW.QPushButton("Refresh Param Viewer")

        self.param_setter = ParamSetterQt(self)

        self.param_tree = ParameterTreeQt("darc params",readonly=True,parent=self)

        self.status_text = QtW.QPlainTextEdit()
        self.status_text.setReadOnly(True)

        self.glay  = QtW.QGridLayout()
        self.hlay = QtW.QHBoxLayout()
        self.topframe = QtW.QFrame()
        self.vsplit = QtW.QSplitter(QtC.Qt.Vertical)
        self.vlay = QtW.QVBoxLayout()

        self.glay.addWidget(self.prefix_chooser,0,0,1,3)
        self.glay.addWidget(self.prefix_setter,1,0,1,3)
        self.glay.addWidget(self.stop_button,2,0,1,1)
        self.glay.addWidget(self.reset_button,2,1,1,1)
        self.glay.addWidget(self.status_button,2,2,1,1)
        self.glay.addWidget(self.param_setter,3,0,1,3)
        self.glay.addWidget(self.refresh_button,4,0,1,3)
        self.glay.setRowStretch(3,1)

        self.hlay.addLayout(self.glay)
        self.hlay.addWidget(self.status_text)

        self.topframe.setLayout(self.hlay)
        self.vsplit.addWidget(self.topframe)
        self.vsplit.addWidget(self.param_tree)
        self.vsplit.setStretchFactor(1,1)

        self.vlay.addWidget(self.vsplit)

        self.setLayout(self.vlay)

class AOControl_base(LarkTab):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

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
        self.loadreconmat_button = QtW.QPushButton("Load ReconMat")

        # define check
        self.cameraopen_check = QtW.QCheckBox()
        self.mirroropen_check = QtW.QCheckBox()

        # build layout
        cnt = -1
        self.lay = QtW.QGridLayout()
        self.lay.addWidget(self.loadreconmat_button,cnt:=cnt+1,0)
        self.lay.addWidget(self.openloop_button,cnt:=cnt+1,0)
        self.lay.addWidget(self.closeloop_button,cnt,1)
        self.lay.addWidget(self.cameraopen_label,cnt:=cnt+1,0)
        self.lay.addWidget(self.cameraopen_check,cnt,1)
        self.lay.addWidget(self.mirroropen_label,cnt:=cnt+1,0)
        self.lay.addWidget(self.mirroropen_check,cnt,1)
        self.lay.addWidget(self.gain_label,cnt:=cnt+1,0)
        self.lay.addWidget(self.gain_spin,cnt,1)
        self.lay.addWidget(self.leak_label,cnt:=cnt+1,0)
        self.lay.addWidget(self.leak_spin,cnt,1)

        self.setLayout(self.lay)




