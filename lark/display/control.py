
import copy
from pathlib import Path, PurePath
import sys
import time
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG
from lark import LarkConfig
from lark.display.widgets.plotting import PlotText, Plotter
from lark.rpyclib.interface import get_registry_parameters
import numpy
from .. import NoLarkError, daemon
from ..interface import connectDaemon
from .. import control
from .. import check
from .. import utils
from .widgets.control_base import Daemon_base, DarcControl_base, AOControl_base
from ..configLoader import get_lark_config
from .widgets.main_base import SubTabWidget
from .widgets.misc import DarcSelector, LocalFileFollower
from lark.display.widgets.misc import LogFileTailer

class Params(QtW.QWidget):
    def __init__(self,parent=None):
        QtW.QWidget.__init__(self,parent=parent)

class DaemonWidget(Daemon_base):
    larkConnected = QtC.pyqtSignal()
    larkDisconnected = QtC.pyqtSignal()
    def __init__(self, larkconfig:LarkConfig, parent=None):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig

        # connect menu
        self.hardresetAction.triggered.connect(self.resetDaemon)
        self.openconfigAction.triggered.connect(self.selectconfig_callback)
        self.setparamAction.triggered.connect(self.setparam_callback)

        # connect buttons
        self.prefix_setter.valueSet.connect(self.prefix_callback)
        self.host_setter.valueSet.connect(self.host_callback)
        self.startdarc_button.clicked.connect(self.startdarc_callback)
        self.stopdarc_button.clicked.connect(self.stopdarc_callback)
        self.refreshparams_button.clicked.connect(self.refreshparams_callback)
        self.saveparams_button.clicked.connect(self.saveparams_callback)
        self.status_button.clicked.connect(self.status_callback)
        self.viewparams_button.clicked.connect(self.viewparams_callback)
        self.selectconfig_button.clicked.connect(self.selectconfig_callback)

        # connect other widgets
        self.daemon_chooser.serviceChosen.connect(self.daemon_callback)
        self.darc_chooser.serviceChosen.connect(self.darc_callback)
        self.config_menu.activated.connect(self.config_callback)
        # self.config_menu.currentIndexChanged.connect(self.config_callback)
        # self.config_menu.highlighted.connect(self.config_callback)
        self.param_setter.parameterSet.connect(self.parameterSet_callback)

        # parameter tree
        self.darc_options = {
            "darcmain": {
                "darcaffinity":0,
                "nhdr":0,
                "bufsize":0,
                "circBufMaxMemSize":0,
                "numaSize":0,
            },
        }
        self.options_tree.setData(self.darc_options)
        self.options_tree.installEventFilter(self)
        self.prefix_setter.set_value(get_lark_config().DEFAULT_PREFIX)
        host = get_registry_parameters().RPYC_HOSTNAME
        self.host_setter.set_value(host)

        self.larkconfig.prefix = get_lark_config().DEFAULT_PREFIX
        self.larkconfig.hostname = host
        self.connected = 0

        self.params = None
        self.configs = []

        # self.show_config(False)
        self.show_param(False)
        self.show_darc(False)
        self.config_dir = Path(get_lark_config().CONFIG_DIR)
        self.setup_config()

        # install event filters
        self.installEventFilter(self)

    def closeEvent(self, event):
        try:
            self.larkconfig.getlark()
        except NoLarkError:
            print("No lark available")
        else:
            self.param_tree.close()
            self.param_setter.close()
            self.larkconfig.closelark()
        return super().closeEvent(event)

    def eventFilter(self, obj, event):
        return super().eventFilter(obj, event)

    def daemon_callback(self, value):
        self.host_setter.set_value(value, True)

    def darc_callback(self, value):
        print("chosen prefix",value)
        self.prefix_setter.set_value(value, True)

    def prefix_callback(self, value):
        self.larkconfig.closelark()
        self.larkconfig.prefix = value
        try:
            print("trying to connect to", self.larkconfig.prefix)
            self.larkconfig.getlark()
        except NoLarkError as e:
            self.print(e)
            self.connected = 0
            if self.params is None:
                self.show_param(False)
                self.show_darc(False)
            else:
                self.show_param(True)
                self.show_darc(False)
                self.switch_startdarc(True)
                self.startdarc_button.setEnabled(True)
            self.show_config()
        else:
            self.print(f"Connected to existing {self.larkconfig.prefix}")
            self.on_connect()

    def host_callback(self, value):
        self.larkconfig.hostname = value
        self.darc_chooser.set_host(value)

    def on_connect(self):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            self.connected = 1
            self.params = lrk.getAll()
            self.config_callback()
            self.larkConnected.emit()

    def show_config(self,show=True):
        self.config_menu.setEnabled(show)
        self.selectconfig_button.setEnabled(show)

    def setup_config(self):
        if not self.config_dir.exists():
            print("Config dir not existing")
            return
        self.configs = []
        def addConfigs(dir):
            files = dir.iterdir()
            for file in files:
                if file.is_dir() and file.stem[0] != "_":
                    addConfigs(file)
                elif file.suffix == ".py" and file.stem[:6] == "config":
                    self.configs.append(file)
                    self.config_menu.addItem(file.stem[6:])
        addConfigs(self.config_dir)

    def config_callback(self,event=None):
        if event is not None:
            if event < len(self.configs):
                self.params = control.processConfigFile(self.larkconfig.prefix,self.configs[event])
                self.chosenconfig_label.setText(f"Using Config File: {self.configs[event].name}")
        else:
            self.chosenconfig_label.setText(f"Using Config File: {PurePath(self.params.get('configfile','')).name}")
        self.params = check.inventAndCheck(self.params)
        self.param_tree.setData(self.params)
        if self.config_menu.count() == len(self.configs):
            self.config_menu.addItem("Current Params")
        self.config_menu.setCurrentIndex(self.config_menu.count()-1)

        self.show_param()
        self.show_darc()
        if self.connected:
            self.switch_startdarc(start=False)
        else:
            self.stopdarc_button.setEnabled(False)
            self.status_button.setEnabled(False)

    def switch_startdarc(self, start=True):
        if start:
            if self.startdarc_button.text() != "Start Darc":
                self.startdarc_button.setText("Start Darc")
                self.startdarc_button.clicked.disconnect(self.reinit_callback)
                self.startdarc_button.clicked.connect(self.startdarc_callback)
        else:
            if self.startdarc_button.text() != "Re-init Params":
                self.startdarc_button.setText("Re-init Params")
                self.startdarc_button.clicked.disconnect(self.startdarc_callback)
                self.startdarc_button.clicked.connect(self.reinit_callback)

    def show_param(self,show=True):
        self.viewparams_button.setEnabled(show)
        self.refreshparams_button.setEnabled(show)

    def viewparams_callback(self):
        self.param_tree.setData(self.params)
        self.param_tree.resize(400,600)
        self.param_tree.show()

    def refreshparams_callback(self):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError:
            print("No lark available")
        else:
            self.param_tree.clear()
            QtC.QCoreApplication.processEvents()
            self.params = lrk.getAll()
            self.param_tree.setData(self.params)

    def saveparams_callback(self):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            lrk.save()

    def show_darc(self,show=True):
        self.startdarc_button.setEnabled(show)
        self.stopdarc_button.setEnabled(show)
        self.status_button.setEnabled(show)

    def startdarc_callback(self):
        try:
            self.larkconfig.startlark(params=self.params)
        except ConnectionError as e:
            self.print(e,"Can't connect to Daemon, change hostname?")
        else:
            self.show_darc()
            self.print(f"Started: {self.larkconfig.prefix}")
            self.on_connect()

    def reinit_callback(self):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            lrk.configure_from_dict(self.params)

    def setparam_callback(self):
        self.param_setter.show()

    def getparam_callback(self):
        self.param_viewer.show()

    def parameterSet_callback(self, name, value):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            retval = lrk.set(name, value)
            if isinstance(retval, str):
                self.print(f"Error: {retval}")
                return
            self.params[name] = value
            try:
                self.param_tree.update(name,value)
            except KeyError as e:
                print(e)

    def stopdarc_callback(self):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            err = ""
            try:
                lrk.stop()
            except EOFError as e:
                err = e
            self.larkconfig.closelark()
            self.connected = 0
            self.show_darc(False)
            self.switch_startdarc(True)
            self.startdarc_button.setEnabled(True)
            self.print(f"Stopped: {self.larkconfig.prefix} {err}")
        self.larkDisconnected.emit()

    def selectconfig_callback(self):
        # choose file
        # get_name = QtW.QFileDialog.getOpenFileName(self, 'Open Config', (str(self.config_dir)),"Python Files (*.py)",options=QtW.QFileDialog.DontUseNativeDialog)
        # fname = get_name[0]
        # if fname != "":
        #     file = Path(fname)
        #     if file.suffix == ".py" and file.stem[:6] == "config":
        #         self.configs.append(file)
        #         self.config_menu.addItem(file.stem[6:])
        #         self.config_menu.setCurrentIndex(self.configs.index(file))
        #         self.config_callback(self.config_menu.currentIndex())
        #         self.show_config()
        get_dir = QtW.QFileDialog.getExistingDirectory(self, "Choose Config Directory", str(Path.home()))
        if get_dir == "":
            return
        self.config_dir = Path(get_dir)
        self.setup_config()

    def validateparams_callback(self):
        pass

    def status_callback(self):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            try:
                data = lrk.getStreamBlock("rtcStatusBuf",1)
            except EOFError as e:
                self.print(e)
                self.stopdarc_callback()
            else:
                if data is not None:
                    txt = utils.statusBuf_tostring(data[0][0])
                    self.print(txt)
                else:
                    self.print("No status received")

    def print(self,*args):
        self.status_text.clear()
        for arg in args:
            if isinstance(arg, str):
                self.status_text.appendPlainText(arg)
            else:
                self.status_text.appendPlainText(str(arg))

    def resetDaemon(self):
        c = QtW.QMessageBox.question(self,"Hard Reset Lark Daemon","WARNING: This will close ALL darcs and reset. Confirm?")
        if c == QtW.QMessageBox.Yes:
            daemonhost = connectDaemon(self.larkconfig.hostname)
            daemonhost.shutdown()

class DarcControlWidget(DarcControl_base):
    larkConnected = QtC.pyqtSignal()
    larkDisconnected = QtC.pyqtSignal()
    def __init__(self, larkconfig: LarkConfig, parent=None):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig

        self.prefix_chooser.serviceChosen.connect(self.prefixChosen_callback)
        self.prefix_setter.valueSet.connect(self.prefix_callback)

        self.status_button.clicked.connect(self.status_callback)

        self.stop_button.clicked.connect(self.stopdarc_callback)
        self.refresh_button.clicked.connect(self.refresh_callback)

        self.param_setter.getParams = self.getParams
        self.param_setter.parameterSet.connect(self.paramsetter_callback)

        self.params = {}

    def prefixChosen_callback(self, value):
        self.prefix_setter.set_value(value,True)

    def prefix_callback(self, value):
        self.larkconfig.closelark()
        self.larkconfig.prefix = value
        try:
            self.larkconfig.getlark()
        except NoLarkError as e:
            self.print(e)
        else:
            self.print(f"Connected to {self.larkconfig.prefix}")
            self.on_connect()

    def print(self, *args, clear=True):
        if clear:
            self.status_text.clear()
        for arg in args:
            if isinstance(arg, str):
                self.status_text.appendPlainText(arg)
            else:
                self.status_text.appendPlainText(str(arg))

    def on_connect(self):
        self.status_callback()
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            self.params = lrk.getAll()
            self.param_tree.setData(self.params)
            self.larkConnected.emit()

    def on_first_start(self):
        try:
            self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            self.prefix_setter.set_value(self.larkconfig.prefix,True)

    def status_callback(self):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            try:
                data = lrk.getStreamBlock("rtcStatusBuf",1)
            except EOFError as e:
                self.print(e)
                self.stopdarc_callback()
            else:
                if data is not None:
                    txt = utils.statusBuf_tostring(data[0][0])
                    self.print(txt)
                else:
                    self.print("No status received")

    def stopdarc_callback(self):
        qm = QtW.QMessageBox()
        ans = qm.question(self,'', "Are you sure you want to stop DARC?", qm.Yes | qm.No)
        if ans == qm.Yes:
            try:
                lrk = self.larkconfig.getlark()
            except NoLarkError as e:
                self.print(e)
            else:
                err = ""
                try:
                    lrk.stop()
                except EOFError as e:
                    err = e
                self.larkconfig.closelark()
                self.print(f"Stopped: {self.larkconfig.prefix}",err)
            self.larkDisconnected.emit()

    def paramsetter_callback(self, name, value):
        self.print("setting",name,"to",value)
        self.print("setting",type(name),"to",type(value),clear=False)
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            self.print(e)
        else:
            retval = lrk.set(name,value)
            if isinstance(retval,str):
                self.print(f"Error: {retval}",clear=False)
                return
            self.params[name] = value
            try:
                self.param_tree.update(name,value)
            except KeyError as e:
                print(e)

        self.print(self.params["rmx"],clear=False)

    def closeloop_callback(self):
        pass

    def openloop_callback(self):
        pass

    def getParams(self):
        return self.params

    def refresh_callback(self):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            self.params = lrk.getAll()
            self.param_tree.clear()
            self.param_tree.setData(self.params)

class AOControlWidget(AOControl_base):
    def __init__(self,larkconfig,parent=None):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig
        self.loadreconmat_button.clicked.connect(self.loadreconmat_callback)

    def loadreconmat_callback(self):
        # open file picker
        # based on suffix, load file as numpy
        # check dims
        # get correct dims from darc
        # if incorrect ask if matrix can be sliced and/or padded with zeros
        pass

    def on_connect(self):
        print("Connecting AO Control")

    def status_callback(self):
        pass

    def closeloop_callback(self):
        pass

    def openloop_callback(self):
        pass


class DarcMainPrint(LocalFileFollower):
    def __init__(self, larkconfig: LarkConfig, parent=None):
        fpath = Path("/dev/shm")/f"{larkconfig.prefix}rtcStdout0"
        super().__init__(file_name=fpath,parent=parent)

class ControlGui(SubTabWidget):
    def __init__(self, larkconfig, parent=None, daemon_controls=True):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig

        self.menu.setTitle("DARC")
        
        if daemon_controls:
            self.daemon = DaemonWidget(self.larkconfig, parent=self)
            self.addWidget(self.daemon, "Daemon")

        self.control = DarcControlWidget(self.larkconfig, parent=self)
        self.ao = AOControlWidget(self.larkconfig, parent=self)
        # self.print = DarcMainPrint(self.larkconfig,parent=self)
        host = get_registry_parameters().RPYC_HOSTNAME
        self.print = LogFileTailer(host, dir="/dev/shm", filter=".log")
        self.logprint = LogFileTailer(host, parent=self)

        self.addWidget(self.control, "Control")
        self.addWidget(self.ao, "AO Control")
        self.addWidget(self.print, "darcmain")
        self.addWidget(self.logprint, "Logging")

    def on_first_start(self):
        self.control.on_first_start()
        
    def on_connect(self):
        self.ao.on_connect()

def main():
    from .widgets.main_base import MainWindow
    app = QtW.QApplication(sys.argv)
    widg = ControlGui()
    win = MainWindow()
    win.setCentralWidget(widg)
    win.setWindowTitle("Control")
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()