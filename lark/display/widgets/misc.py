
import copy
from pathlib import Path, PosixPath
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtGui as QtG
from PyQt5 import QtCore as QtC
from lark.daemon import LarkDaemon
from lark.display.widgets.plotting import PlotText
from lark.display.widgets.remote_files import DaemonFilePicker
from lark.interface import ControlClient, connectDaemon
from lark.interface import get_registrar, get_registry_parameters
from pyqtgraph.parametertree import Parameter, ParameterTree, parameterTypes as pTypes
import numpy

from lark.configLoader import get_lark_config
from lark.utils import statusBuf_tostring

import importlib.resources

def print_ndarray(arr):
    if sum(arr.shape) > 10:
        return f"ndarray({arr.shape}, dtype={arr.dtype})"
    else:
        return numpy.array_repr(arr)

class ValueChooser(QtW.QWidget):
    valueSet = QtC.pyqtSignal(str)
    def __init__(self, _name="Value", parent=None):
        QtW.QWidget.__init__(self, parent=parent)
        self._name = _name

        # define labels
        self.value_label = QtW.QLabel(f"Enter {self._name}:")
        self.status_label = QtW.QLabel(f"{self._name} set to: ")

        # define buttons
        self.value_button = QtW.QPushButton(f"Accept {self._name}")

        # define text input
        self.value_input = QtW.QLineEdit()

        # define layout
        self.lay = QtW.QGridLayout()

        # add to layout
        self.lay.addWidget(self.value_label,0,0)
        self.lay.addWidget(self.value_input,0,1)
        self.lay.addWidget(self.value_button,0,2)
        self.lay.addWidget(self.status_label,1,0,1,3)

        # set layout
        self.setLayout(self.lay)

        # connect signals
        self.value_input.returnPressed.connect(self.value_callback)
        self.value_button.clicked.connect(self.value_callback)

    def value_callback(self):
        value = self.value_input.text()
        self.valueSet.emit(value)
        self.status_label.setText(f"{self._name} set to: {value}")

    def set_value(self, value, cascade=False):
        self.value_input.setText(value)
        self.status_label.setText(f"{self._name} set to: {value}")
        if cascade:
            self.value_callback()

class PrefixChooser(ValueChooser):
    def __init__(self, parent=None):
        super().__init__("Prefix", parent=parent)

class HostChooser(ValueChooser):
    def __init__(self, parent=None):
        super().__init__("Hostname", parent=parent)

class ServiceChooser(ValueChooser):
    def __init__(self, name, parent=None):
        super().__init__(name, parent=parent)

class ServiceFinder(QtW.QPushButton):
    """Find a service on the nameserver with a specified suffix"""
    serviceChosen = QtC.pyqtSignal(str)
    def __init__(self, name="Service", suffix="SERVICE", parent=None):
        self.name = name
        self.suffix = suffix
        super().__init__(f"Find {self.name}", parent=parent)
        self.clicked.connect(self.callback)

    def callback(self):
        reg = get_registrar()
        services = [key[:-len(self.suffix)] for key in reg.list() if key.endswith(self.suffix)]
        serv_list = ListSelector(services, "Service", self)
        if serv_list.exec():
            self.serviceChosen.emit(serv_list.selectedOption)

class DaemonDarcList(QtW.QPushButton):
    """Choose a darc from a Daemon"""
    serviceChosen = QtC.pyqtSignal(str)
    def __init__(self, hostname="localhost", parent=None):
        self.hostname = hostname
        super().__init__("Find DARC on Daemon", parent=parent)
        self.clicked.connect(self.callback)

    def set_host(self, hostname):
        self.hostname = hostname

    def callback(self):
        print(f"self.hostname = {self.hostname}")
        daemon: LarkDaemon = connectDaemon(self.hostname)
        status = daemon.larkstatus()
        print(status)
        services = [key for key,value in daemon.larkstatus().items() if value[0]]
        serv_list = ListSelector(services, "DARC", self)
        if serv_list.exec():
            self.serviceChosen.emit(serv_list.selectedOption)

class StrListGroup(pTypes.GroupParameter):
    def __init__(self, **opts):
        opts['type'] = 'group'
        opts['addText'] = "Add"
        super().__init__(**opts)
        self.sigChildRemoved.connect(self.emitChange)

    def addNew(self, value=""):
        name = "Item %d" % (len(self.childs)+1)
        self.addChild(dict(name=name, type="str", value=value, removable=True, renamable=False))
        self.param(name).sigValueChanged.connect(self.emitChange)

    def emitChange(self, event):
        self.setValue([c.value() for c in self.childs])
        self.sigValueChanged.emit(self,self.value())

class DictGroup(pTypes.GroupParameter):
    def __init__(self, init_dict={}, expandable=True, **opts):
        opts['type'] = 'group'
        if expandable:
            opts.setdefault('addText', "Add")
            opts.setdefault('addList', ['str','int','float'])
        super().__init__(**opts)
        self.addParams(init_dict)
        self.sigChildRemoved.connect(self._childRemoved)
        
    def addNew(self, typ):
        val = {'str':'','int':0,'float':0.0}[typ]
        param = {
            'name': f"Param {(len(self.childs)+1)}",
            'type': typ,
            'value': val,
            'removable': True,
            'renamable': True
        }
        self.addChild(param)

    def addParam(self, name, value):
        # if isinstance(value,dict):
        #     group = {
        #         "name":key,
        #         "type":"group",
        #         "children":[]
        #     }
        #     addParams(value,group["children"])
        #     plist.append(group)
        if isinstance(value,dict):
            param = DictGroup(value, name=name)
        elif isinstance(value,list):
            print("Adding list ",value)
            # children = [{'name': f"ListItem {i}", "type":type(v).__name__, "value": v, "readonly":self.readonly} for i,v in enumerate(value)]
            param = StrListGroup(
                name=name,
                tip='Click to add children, right click to remove',
                )
            for i in value:
                param.addNew(i)
        elif isinstance(value, numpy.ndarray):
            param = {
                "name":name,
                "type":"str",
                # "value":f"ndarray, shape={value.shape}, dtype={value.dtype}",
                "value":repr(value)+f", shape={value.shape}",
                "readonly":True,
                "dontset":True
            }
        elif isinstance(value, numpy.number):
            param = {
                "name":name,
                "type":"str",
                "value":f"ndvalue={value}, dtype={value.dtype}",
                "readonly":True,
                "dontset":True
            }
        elif isinstance(value,PosixPath):
            param = {
                "name":name,
                "type":"str",
                "value":str(value),
                "dontset":True
            }
        elif value is None:
            param = {
                "name":name,
                "type":"str",
                "value":"NONE",
                "readonly":True,
                "dontset":True
            }
        else:
            param = {
                "name":name,
                "type":type(value).__name__,
                "value":value,
                "readonly":self.readonly()
            }
        self.addChild(param)
        
    def addChild(self, child, autoIncrementName=None):
        if isinstance(child, dict):
            name = child["name"]
            child.setdefault("dontset",False)
        else:
            name = child.name()
            child.opts.setdefault("dontset",False)
        retval = super().addChild(child, autoIncrementName)
        self.param(name).sigStateChanged.connect(self.emitChange)
        return retval

    def addParams(self, pdict:dict):
        for key, value in pdict.items():
            self.addParam(key, value)
            
    def _childRemoved(self, child):
        # child.sigStateChanged.disconnect(self.emitChange)
        self.emitChange(child)

    def emitChange(self, event, info=None):
        self.setValue({c.name():c.value() for c in self.childs})
        self.sigValueChanged.emit(self,self.value())

class ParameterTreeQt(QtW.QWidget):
    parameterChanged = QtC.pyqtSignal(str,object)
    def __init__(self,name="params",params=None,readonly=False,parent=None):
        QtW.QWidget.__init__(self,parent=parent)
        self.vlay = QtW.QVBoxLayout()
        self.parametertree = ParameterTree()
        self.vlay.addWidget(self.parametertree,1)
        # self.datatree = DataTreeWidget()
        # self.vlay.addWidget(self.datatree,1)
        # self.datatree.hide()
        self.setLayout(self.vlay)
        self.name = name
        self.readonly = readonly
        if params is not None:
            self.setData(params)

    def clear(self):
        self.parametertree.clear()

    def setData(self,params):
        self.input_dict = {copy.copy(key):copy.copy(value) for key,value in params.items()}
        self.parameters = []
        self.dontset = []
        # self.parameters.append({
        #     "name":"Use These Values",
        #     "type":"action",
        #     "tip":"Store current params into dictionary",
        # })
        # self.paramgroup = Parameter.create(name=self.name, type='group', children=self.parameters)
        self.paramgroup = DictGroup(dict(sorted(params.items())), name=self.name, expandable=False)
        # self.paramgroup.param("Use These Values").sigActivated.connect(self.usevalues_callback)
        def connectparams(pdict,pgroup):
            for key,value in pdict.items():
                if isinstance(value,dict):
                    connectparams(value,pgroup.param(key))
                pgroup.param(key).sigValueChanged.connect(self.storeparams_callback)
        connectparams(self.input_dict,self.paramgroup)
        self.parametertree.setParameters(self.paramgroup)
        # if self.arrays != {}:
        #     self.datatree.setData(self.arrays)
        #     self.datatree.show()
        # else:
        #     self.datatree.hide()

    def storeparams_callback(self, event=None, value=None):
        print("STOREPARAMS")
        print(event.name())
        print(event.value())
        print(value)
        def storeparam(event,pdict):
            pdict[event.name()] = event.value()
        if event is not None:
            if event.parent().name() != self.paramgroup.name():
                self.input_dict[event.parent().name()][event.name()] = event.value()
            elif event.parent().name() == self.paramgroup.name():
                self.input_dict[event.name()] = event.value()
            self.parameterChanged.emit(event.name(),event.value())

    def usevalues_callback(self, event=None):
        def grab_values(pdict,pgroup):
            for key,value in pdict.items():
                if isinstance(value,dict):
                    grab_values(value,pgroup.param(key))
                else:
                    # if key not in self.dontset:
                    if not pgroup.param(key).opts["dontset"]:
                        pdict[key] = pgroup.param(key).value()
        grab_values(self.input_dict,self.paramgroup)

    def get_values(self):
        return self.input_dict

    def update(self,name,value,nested=None):
        print("UPDATING",name)
        print(type(value),value)
        if nested is not None:
            param = self.paramgroup.param(nested[0])
            for key in nested[1:]:
                param = param.param(key)
            param.param(name).setValue(value)
        else:
            if isinstance(value,numpy.ndarray):
                self.paramgroup.param(name).setValue(repr(value)+f", shape={value.shape}")
            else:
                self.paramgroup.param(name).setValue(value)

class ParamSetterQt(QtW.QWidget):
    parameterSet = QtC.pyqtSignal(str,object)
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.main_label = QtW.QLabel("Set Paramter:")

        self.name_label = QtW.QLabel("Name")
        self.value_label = QtW.QLabel("Value")

        self.name_box = QtW.QLineEdit()
        self.value_box = QtW.QLineEdit()

        self.status_bar = QtW.QLabel()

        self.help_dialogue = QtW.QLabel(
"Type a python literal into the value box\n\
Strings need \"quotes\"\nnumpy also works\ne.g. numpy.zeros((4,5))\n\
The name is just a string and doesn't need quotes",parent=self)
        self.help_dialogue.setWindowFlags(self.help_dialogue.windowFlags() | QtC.Qt.Dialog)
        self.help_dialogue.resize(400,100)

        self.set_button = QtW.QPushButton("Set")
        self.help_button = QtW.QPushButton("Help")

        self.glay = QtW.QGridLayout()

        self.glay.addWidget(self.main_label,0,0)
        self.glay.addWidget(self.name_label,1,0)
        self.glay.addWidget(self.value_label,1,1)
        self.glay.addWidget(self.name_box,2,0)
        self.glay.addWidget(self.value_box,2,1)
        self.glay.addWidget(self.set_button,3,0)
        self.glay.addWidget(self.help_button,3,1)
        self.glay.addWidget(self.status_bar,4,0,1,2)
        self.glay.setRowStretch(4,1)

        self.set_button.clicked.connect(self.set_callback)
        self.help_button.clicked.connect(self.help_callback)
        self.value_box.returnPressed.connect(self.set_callback)

        self.setLayout(self.glay)

    def set_callback(self):
        name = self.name_box.text()
        if name == "":
            self.status_bar.setText("name is empty")
            return
        txt = self.value_box.text()
        if txt == "":
            self.status_bar.setText("value is empty")
            return

        try:
            value = eval(txt, globals(), self.getParams())
        except Exception as e:
            self.status_bar.setText(f"eval error {e}")
            return
        # else:
        # else:
        #     try:
        #         value = ast.literal_eval(txt)
        #     except ValueError as e:
        #         self.status_bar.setText("strings need quotes")
        #         return
        numpy.set_string_function(print_ndarray,False)
        message = f"{name} set to: {value}"
        print("type object = ",type(value))
        numpy.set_string_function(None)
        if len(message) > 100:
            message = message[:100] + "..."
        self.status_bar.setText(message)
        self.parameterSet.emit(name,value)

    def getParams(self):
        return self.parent().params

    def help_callback(self):
        self.help_dialogue.show()


class DarcSelector(QtW.QDialog):
    def __init__(self, darcs, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Select DARC")

        self.layout = QtW.QVBoxLayout()

        self.list = QtW.QListWidget()

        for prefix,status in darcs.items():
            if status[0]==True and status[1]==1:
                self.list.addItem(prefix)

        self.list.setCurrentRow(0)

        self.list.itemDoubleClicked.connect(self.accept)

        self.layout.addWidget(self.list)

        QBtn = QtW.QDialogButtonBox.Ok | QtW.QDialogButtonBox.Cancel
        self.buttonBox = QtW.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

        self.setLayout(self.layout)

class ListSelector(QtW.QDialog):
    def __init__(self, options: list, name="Option", parent=None):
        super().__init__(parent)

        self.setWindowTitle(f"Select {name}")

        self.layout = QtW.QVBoxLayout()

        self.list = QtW.QListWidget()

        for string in options:
            self.list.addItem(string)

        self.list.setCurrentRow(0)

        self.list.itemDoubleClicked.connect(self.callback)

        self.layout.addWidget(self.list)

        QBtn = QtW.QDialogButtonBox.Ok | QtW.QDialogButtonBox.Cancel
        self.buttonBox = QtW.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.callback)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

        self.setLayout(self.layout)

    def callback(self):
        item = self.list.currentItem()
        if item is not None:
            self.selectedOption = item.text()
            self.accept()
        else:
            self.reject()


class DarcOpener(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle("Choose Darc")

        self.daemon_label = QtW.QLabel("Daemon:")
        self.daemon_input = QtW.QLineEdit(get_registry_parameters().RPYC_HOSTNAME)
        self.daemon_button = QtW.QPushButton("Accept")
        self.daemon_choice = QtW.QLabel("Using Daemon:")

        self.prefix_list = QtW.QTreeWidget()
        self.prefix_list.setHeaderLabel("Available Larks:")

        self.new_button = QtW.QPushButton("New...")
        self.open_button = QtW.QPushButton("Open")
        self.stop_button = QtW.QPushButton("Stop")

        self.info_box = QtW.QTextEdit()
        self.info_box.setReadOnly(True)

        self.daemon_button.clicked.connect(self.daemon_callback)
        self.daemon_input.editingFinished.connect(self.daemon_callback)
        self.prefix_list.itemSelectionChanged.connect(self.prefix_callback)
        self.glay1 = QtW.QGridLayout()
        self.glay2 = QtW.QGridLayout()

        self.glay1.addWidget(self.daemon_label,0,0)
        self.glay1.addWidget(self.daemon_input,0,1,1,1)
        self.glay1.addWidget(self.daemon_button,0,2)
        self.glay1.addWidget(self.daemon_choice,1,0,1,3)
        self.glay2.addWidget(self.prefix_list,0,0,2,2)
        self.glay2.addWidget(self.new_button,0,2)
        self.glay2.addWidget(self.open_button,0,3)
        self.glay2.addWidget(self.stop_button,0,4)
        self.glay2.addWidget(self.info_box,1,2,1,4)
        self.glay1.setColumnStretch(3,1)
        self.glay2.setColumnStretch(5,1)
        # self.glay.setColumnStretch(3,1)
        # self.glay.setColumnStretch(4,1)
        self.vlay = QtW.QVBoxLayout()

        self.vlay.addLayout(self.glay1)
        self.vlay.addLayout(self.glay2)

        self.setLayout(self.vlay)

    def daemon_callback(self):
        self.stop_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.prefix_list.clear()
        self.info_box.clear()
        self.daemon_name = self.daemon_input.text()
        self.daemon_choice.setText(f"Using Daemon: {self.daemon_name}")
        try:
            daemon = connectDaemon(self.daemon_name)
        except Exception as e:
            print(e)
            self.info_box.setPlainText("No Daemon found with this name")
        else:
            prefixes = daemon.larkstatus()
            for key,value in prefixes.items():
                if value[0]:
                    item = QtW.QTreeWidgetItem(self.prefix_list,(key,))
                    # self.prefix_list.addTopLevelItem(item)

    def prefix_callback(self):
        self.stop_button.setEnabled(True)
        self.open_button.setEnabled(True)
        prefix = self.prefix_list.currentItem().text(0)
        lark = ControlClient(prefix)
        cfg_file = lark.get("configfile")
        status = lark.getStreamBlock("rtcStatusBuf",1)[0][0]
        print(status)
        self.info_box.setPlainText(cfg_file)
        self.info_box.append(statusBuf_tostring(status))

    def new_callback(self):
        pass

    def open_callback(self):
        pass

    def stop_callback(self):
        pass

class ModeItem(QtW.QWidget):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        with importlib.resources.path("lark.display.icons","accept.png") as f:
            self.go_icon = QtG.QPixmap(str(f)).scaledToHeight(40)
        with importlib.resources.path("lark.display.icons","minus-button.png") as f:
            self.unsure_icon = QtG.QPixmap(str(f)).scaledToHeight(40)
        with importlib.resources.path("lark.display.icons","power.png") as f:
            self.stop_icon = QtG.QPixmap(str(f)).scaledToHeight(40)
        myFont=QtG.QFont()
        myFont.setBold(True)
        self.name_label = QtW.QLabel("None")
        self.name_label.setFont(myFont)
        self.status_label = QtW.QLabel("None")
        self.icon_label = QtW.QLabel()
        self.icon_label.setPixmap(self.go_icon)
        self.glay = QtW.QGridLayout()
        self.glay.addWidget(self.icon_label,0,0,2,1)
        self.glay.addWidget(self.name_label,0,1,1,1)
        self.glay.addWidget(self.status_label,1,1,1,1)
        self.glay.setColumnStretch(1,1)
        self.setLayout(self.glay)

    def setName(self, name):
        self.name_label.setText(name)

    def name(self):
        return self.name_label.text()

    def setStatus(self, running:bool, on_file=True):
        if running:
            if on_file:
                self.icon_label.setPixmap(self.go_icon)
                self.status_label.setText("Running")
            else:
                self.icon_label.setPixmap(self.unsure_icon)
                self.status_label.setText("Running (remote)")
        else:
            self.icon_label.setPixmap(self.stop_icon)
            self.status_label.setText("Stopped")

class OptionsItem(QtW.QWidget):
    clicked = QtC.pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        with importlib.resources.path("lark.display.icons","menu.png") as f:
            self.menu_icon = QtG.QPixmap(str(f)).scaledToHeight(30)
        myFont=QtG.QFont()
        myFont.setBold(True)
        self.name = QtW.QLabel("Options")
        self.name.setFont(myFont)
        self.icon = QtW.QLabel()
        self.icon.setPixmap(self.menu_icon)
        self.glay = QtW.QGridLayout()
        self.glay.addWidget(self.icon,0,0,1,1)
        self.glay.addWidget(self.name,0,1,1,1)
        self.glay.setColumnStretch(1,1)
        self.setLayout(self.glay)
        self.setAutoFillBackground(True)

    def mousePressEvent(self, a0: QtG.QMouseEvent) -> None:
        self.clicked.emit()
        p = self.palette()
        p.setColor(self.backgroundRole(), QtG.QColor(0, 0, 224, 50))
        self.setPalette(p)
        return super().mousePressEvent(a0)

    def unselect(self):
        p = self.palette()
        p.setColor(self.backgroundRole(), QtG.QColor(0,0,0,0))
        self.setPalette(p)

class OptionsWidget(QtW.QWidget):
    modeDirChanged = QtC.pyqtSignal(str)
    resetDaemonClicked = QtC.pyqtSignal(str)
    def __init__(self,parent=None):
        super().__init__(parent=parent)

        self.modedir_label = QtW.QPushButton("Choose Directory")
        self.modedir_input = QtW.QLineEdit()

        self.resetdaemon_button = QtW.QPushButton("Full Reset")
        self.resetdaemon_input = QtW.QLineEdit()

        self.resetdaemon_button.clicked.connect(self.resetdaemon_callback)

        self.modedir_input.returnPressed.connect(self.modedir_callback)
        self.modedir_label.clicked.connect(self.modedir_clicked)

        self.glay = QtW.QGridLayout()
        self.glay.addWidget(self.modedir_label,0,0,1,1)
        self.glay.addWidget(self.modedir_input,0,1,1,1)
        self.glay.addWidget(self.resetdaemon_button,1,0,1,1)
        self.glay.addWidget(self.resetdaemon_input,1,1,1,1)
        self.glay.setRowStretch(2,1)

        self.setLayout(self.glay)

    def modedir_callback(self):
        self.mode_dir = self.modedir_input.text()
        self.modeDirChanged.emit(self.mode_dir)

    def modedir_clicked(self):
        dir = QtW.QFileDialog.getExistingDirectory(None, "Choose Directory",str(Path.home()))
        if dir:
            self.mode_dir = dir
            self.modeDirChanged.emit(self.mode_dir)

    def resetdaemon_callback(self, event):
        self.resetDaemonClicked.emit(self.resetdaemon_input.text())

    def setModeDir(self, mode_dir):
        self.modedir_input.setText(str(mode_dir))

    def setDaemonHost(self, hostname):
        self.resetdaemon_input.setText(hostname)

    def mousePressEvent(self, a0: QtG.QMouseEvent) -> None:
        print("mouse pressed")
        return super().mousePressEvent(a0)


class LocalFileFollower(PlotText):
    gotLine = QtC.pyqtSignal(str)
    def __init__(self, file_name, stripchars=0, parent=None):
        super().__init__(parent=parent)
        self.timer = QtC.QTimer()
        self.timer.timeout.connect(self.gettext)
        self.gotLine.connect(self.update_plot)
        self.menu = None
        self.file = None
        self.tell = 0
        self.stripchars = stripchars
        self.set_file_name(file_name)
        self.timeout_msec = 50

    def open_file(self):
        return self.fpath.open()

    def set_file_name(self, file_name):
        self.fpath = Path(file_name) if file_name is not None else None
        self.on_connect()

    def on_connect(self):
        print(f"self.fpath = {self.fpath}")
        self._stop_follow()
        if self.fpath is not None:
            file = self.open_file()
            try:
                lines = file.readlines()[-100:]
            except Exception as e:
                print(e)
            else:
                self.clear()
                self.tell = file.tell()
                for txt in lines:
                    self.plot(txt[self.stripchars:],clear=0)
            finally:
                file.close()
        if self.isVisible():
            self._start_follow()

    def on_disconnect(self):
        pass

    def gettext(self):
        lines = self.file.readlines()
        txt = ""
        for _txt in lines:
            txt+=_txt[self.stripchars:]
        if txt:
            self.gotLine.emit(txt)

    def update_plot(self,msg):
        self.plot(msg,clear=0)

    def _start_follow(self):
        if self.fpath is None:
            return
        try:
            self.file = self.open_file()
        except FileNotFoundError as e:
            print(e)
        else:
            self.file.seek(self.tell)
            self.timer.start(self.timeout_msec)

    def showEvent(self, event) -> None:
        print("SHWOING")
        self._start_follow()
        return super().showEvent(event)

    def _stop_follow(self):
        self.timer.stop()
        if self.file is not None:
            self.tell = self.file.tell()
            self.file.close()
            self.file = None

    def hideEvent(self, event) -> None:
        print("HIDIING")
        self._stop_follow()
        return super().hideEvent(event)


class RemoteFileFollower(LocalFileFollower):
    def __init__(self, file_name, host="localhost", stripchars=0, parent=None):
        super().__init__(file_name,stripchars,parent)
        self.set_host(host)
        self.timeout_msec = 500

    def set_file_location(self, file_name, host=None):
        self.set_host(host)
        self.set_file_name(file_name)

    def set_host(self,host):
        self.host = host if host is not None else self.host

    def open_file(self):
        return connectDaemon(self.host).openFile(self.fpath)

class LoggerFilePrint(LocalFileFollower):
    def __init__(self, file_name, parent=None):
        fpath = Path("/var/log/lark")/f"{file_name}"
        stripchars = len(fpath.stem)+8
        super().__init__(file_name=fpath,stripchars=stripchars,parent=parent)

class FileDropDown(QtW.QWidget):
    fileSelected = QtC.pyqtSignal(str)
    def __init__(self, directory, host=None, filter=None, parent=None):
        super().__init__(parent)
        self.dir = Path(directory)
        self.host = host
        self.filter = filter
        self.dropdown = QtW.QComboBox()
        self.folder_button = QtW.QPushButton("Folder")
        self.folder_button.clicked.connect(self.folder_callback)

        self.dropdown.currentIndexChanged.connect(self.file_callback)
        self.refresh()

        self.hbox = QtW.QHBoxLayout()
        self.hbox.addWidget(self.dropdown)
        self.hbox.addWidget(self.folder_button)

        self.setLayout(self.hbox)

    def set_directory(self, directory):
        self.dir = Path(directory)
        self.refresh()

    def refresh(self):
        self.dropdown.clear()
        if self.host is not None:
            files = connectDaemon(self.host).listDir(self.dir)
            files = files["file"]
        else:
            files = [file.name for file in self.dir.iterdir()]
        for file in files:
            if self.filter is not None and self.filter not in file:
                continue
            self.dropdown.addItem(file)
        self.dropdown.setCurrentIndex(0)

    def folder_callback(self):
        if self.host is None:
            # filen = QtW.QFileDialog.getOpenFileName(self, 'Open Folder', "/",options=QtW.QFileDialog.DontUseNativeDialog)[0]
            filen = QtW.QFileDialog.getExistingDirectory(self, "Open Directory", "/",options=QtW.QFileDialog.Options())
            print(filen)
        else:
            wdg = DaemonFilePicker(self.host)#,dirs_only=True)
            if(wdg.exec()):
                if Path(wdg.fname).is_dir():
                    self.set_directory(wdg.fname)
        pass

    def file_callback(self, index):
        print(index)
        print(self.dropdown.currentText())
        self.fileSelected.emit(str(self.dir/self.dropdown.currentText()))

class LogFileTailer(QtW.QWidget):
    def __init__(self, host="localhost", dir="/var/log/lark", filter=None, parent=None):
        super().__init__(parent=parent)
        self.host = host
        self.menu = None

        self.filelist = FileDropDown(dir, host, filter=filter)

        self.vbox = QtW.QVBoxLayout()
        self.vbox.addWidget(self.filelist)

        self.logbox = RemoteFileFollower(None,self.host)
        self.vbox.addWidget(self.logbox)

        self.setLayout(self.vbox)

        self.filelist.fileSelected.connect(self.filelist_callback)
        self.filelist.file_callback(None)

    def filelist_callback(self,filename):
        print("FNAME:",filename)
        fpath = Path(filename)
        if ".log" in fpath.suffixes:
            self.logbox.set_file_location(fpath, self.host)

if __name__ == "__main__":
    from lark.display.main import widget_tester
    widget = LogFileTailer
    args = []
    kwargs = {"host":"LaserLab"}
    # kwargs = {"host":None}
    widget_tester(widget,args,kwargs)

# class ObservingBlockOpener(QtW.QWidget):
#     def __init__(self,parent=None):
#         super().__init__(parent=parent)
#         """Open an observing block"""

#         self.mode_list = QtW.QListWidget()
#         # self.mode_list.setStyleSheet("QListWidget::item { background-color: red; border-bottom: 1px solid black; }")
#         self.mode_list.setStyleSheet("QListWidget::item { background-color: lightgray;\
#     border-style: outset;\
#     border-width: 2px;\
#     border-radius: 10px;\
#     border-color: beige;\
#     font: bold 14px;\
#     min-width: 10em;  }" "QListWidget::item:selected { \
#             background-color: rgba(0, 0, 224, 50); \
#             border-style: inset; }")
#         self.modestart_button = QtW.QPushButton("Start")
#         self.modestop_button = QtW.QPushButton("Stop")
#         self.modeopen_button = QtW.QPushButton("Open")
#         self.modeinfo_textbox = QtW.QPlainTextEdit()
#         self.modeinfo_textbox.setReadOnly(True)

#         self.prefix_label = QtW.QLabel("Running DARCS:")
#         self.prefix_list = QtW.QListWidget()
#         self.prefixopen_button = QtW.QPushButton("Open")
#         self.prefixstop_button = QtW.QPushButton("Stop")
#         self.stopall_button = QtW.QPushButton("Stop All")

#         self.options_item = OptionsItem(self)
#         self.options_item.clicked.connect(self.options_callback)

#         # self.options_item = QtW.QListWidgetItem(self.mode_list)
#         # self.options_item.setSizeHint(options_widget.sizeHint())
#         # self.options_item.setBackground(QtG.QColor(100,100,100,100))

#         # self.mode_list.addItem(self.options_item)
#         # self.mode_list.setItemWidget(self.options_item, options_widget)

#         self.mode_list.itemSelectionChanged.connect(self.modelist_callback)

#         self.options_widget = OptionsWidget(self)

#         self.prefix_lay = QtW.QGridLayout()

#         self.prefix_lay.addWidget(self.prefix_label,0,0,1,2)
#         self.prefix_lay.addWidget(self.prefix_list,1,0,1,2)
#         self.prefix_lay.addWidget(self.prefixopen_button,2,0,1,1)
#         self.prefix_lay.addWidget(self.prefixstop_button,2,1,1,1)
#         self.prefix_lay.addWidget(self.stopall_button,3,0,1,2)

#         self.mode_lay = QtW.QGridLayout()

#         self.mode_lay.addWidget(self.modestart_button,0,0,1,1)
#         self.mode_lay.addWidget(self.modeopen_button,0,1,1,1)
#         self.mode_lay.addWidget(self.modestop_button,0,2,1,1)
#         self.mode_lay.addWidget(self.modeinfo_textbox,1,0,1,3)

#         self.mode_frame = QtW.QFrame()
#         self.mode_frame.setLayout(self.mode_lay)

#         self.hlay = QtW.QHBoxLayout()

#         self.vlay = QtW.QVBoxLayout()
#         self.vlay.addWidget(self.options_item)
#         self.vlay.addWidget(self.mode_list)

#         self.hlay.addLayout(self.vlay,1)
#         self.hlay.addWidget(self.mode_frame,2)
#         self.hlay.addWidget(self.options_widget,2)
#         self.hlay.addLayout(self.prefix_lay,1)

#         self.options_widget.hide()
#         self.options_widget.modeDirChanged.connect(self.setModeDir)

#         self.modestart_button.clicked.connect(self.modestart_callback)
#         self.modestop_button.clicked.connect(self.modestop_callback)
#         self.modeopen_button.clicked.connect(self.modeopen_callback)

#         self.setLayout(self.hlay)

#         self.mode_dir = None
#         self.displays = UpperDict()
#         self.modes = UpperDict()
#         self.darcs = []

#     def modelist_callback(self):
#         self.options_item.unselect()
#         self.mode_frame.show()
#         self.options_widget.hide()
#         mode = self.mode_list.itemWidget(self.mode_list.currentItem())
#         if mode is not None:
#             mode = mode.name()
#             self.modeinfo_textbox.setPlainText(self.modes[mode][0].info)

#     def options_callback(self):
#         self.mode_list.clearSelection()
#         self.mode_frame.hide()
#         self.options_widget.show()

#     def setModeDir(self, mode_dir):
#         self.mode_dir = mode_dir
#         self.options_widget.setModeDir(mode_dir)
#         self.setupModes()

#     def check_mode_dir(self):
#         self.modes = UpperDict()
#         if self.mode_dir is not None:
#             try:
#                 file_list = list(Path(self.mode_dir).iterdir())
#             except FileNotFoundError as e:
#                 print(e)
#             else:
#                 for fn in file_list:
#                     if fn.name.startswith("mode"):
#                         mode_mod = import_from(fn)
#                         self.modes[fn.stem[4:]] = [mode_mod, False]

#     def interrogate_nameserver(self):
#         reg = get_registrar()
#         serv_list: Tuple[str] = reg.list()
#         print(serv_list)
#         self.darcs = []
#         for sn in serv_list:
#             if sn.endswith("SRTC"):
#                 name = sn.split("SRTC")[0]
#                 mode = self.modes.get(name,[None,False])
#                 mode[1] = True
#                 self.modes[name] = mode
#             elif sn.endswith("CONTROL"):
#                 name = sn.split("CONTROL")[0]
#                 self.darcs.append(name)
#         self.prefix_list.clear()
#         for d in self.darcs:
#             self.prefix_list.addItem(d)

#     def setupModes(self):
#         selected = self.mode_list.currentIndex()
#         self.mode_list.clear()
#         # search dir for modes
#         self.check_mode_dir()
#         # query name server for SRTCs
#         self.interrogate_nameserver()
#         # modes = {"This":True, "That One":False, "Not this one":False,"This2":True, "That One No":False, "Not this one yet":False}
#         for mode,(mode_mod,status) in self.modes.items():
#             mode_widget = ModeItem(self.mode_list)
#             mode_widget.setName(mode)
#             mode_widget.setStatus(status,mode_mod is not None)
#             mode_item = QtW.QListWidgetItem(self.mode_list)
#             mode_item.setSizeHint(mode_widget.sizeHint())
#             mode_item.setBackground(QtG.QColor(180,180,180,255))

#             self.mode_list.addItem(mode_item)
#             self.mode_list.setItemWidget(mode_item, mode_widget)
#         self.mode_list.setCurrentIndex(selected)

#     def modestart_callback(self):
#         mode = self.mode_list.itemWidget(self.mode_list.currentItem())
#         if mode is not None:
#             mode = mode.name()
#             self.modes[mode][0].start()
#             self.setupModes()

#     def modestop_callback(self):
#         mode = self.mode_list.itemWidget(self.mode_list.currentItem())
#         if mode is not None:
#             mode = mode.name()
#             self.modes[mode][0].stop()
#             self.setupModes()

#     def modeopen_callback(self):
#         mode = self.mode_list.itemWidget(self.mode_list.currentItem())
#         if mode is not None:
#             mode = mode.name()
#             self.displays[mode] = self.modes[mode][0].open()
#             self.setupModes()

#     def prefixopen_callback(self):
#         prefix = self.prefix_list.currentItem().text()
#         self.displays[prefix] = LarkPlot(prefix)
#         self.setupModes()

        #list of darcs
        #drop down of modes
        #stop all button
        #start mode button
        #open displays button
        #info box

# class MainWidgets(QtW.QWidget):
#     def __init__(self, *widget_classes, parent=None, orient="horizontal"):
#         QtW.QWidget.__init__(self,parent=parent)
#         self.widgets = []
#         if orient == "horizontal":
#             self.lay = QtW.QHBoxLayout(self)
#         else:
#             self.lay = QtW.QVBoxLayout(self)
#         for widg in widget_classes:
#             tmp = widg(parent=self)
#             self.widgets.append(tmp)
#             self.lay.addWidget(tmp)
#         self.setLayout(self.lay)
#         self.installEventFilter(self)

#     def eventFilter(self, obj, event):
#         if obj is self and event.type() == QtC.QEvent.Close:
#             for wdg in self.widgets:
#                 wdg.close()
#         return super().eventFilter(obj, event)

# class MainWindow(QtW.QMainWindow):
#     def __init__(self,*widget_classes,orient="horizontal"):
#         super().__init__()
#         self.installEventFilter(self)
#         self.mainwidget = MainWidgets(*widget_classes,parent=self,orient=orient)
#         menuBar = self.menuBar()
#         for wdg in self.mainwidget.widgets:
#             menuBar.addMenu(wdg.menu)
#         self.setMenuBar(menuBar)
#         self.setCentralWidget(self.mainwidget)

#     def eventFilter(self, obj, event):
#         if obj is self and event.type() == QtC.QEvent.Close:
#             self.centralWidget().close()
#         return super().eventFilter(obj, event)
