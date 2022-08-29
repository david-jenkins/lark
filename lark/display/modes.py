from pathlib import Path
from typing import Dict, List, Tuple
from lark import LarkConfig, NoLarkError
from lark.display.main import LarkPlot
from lark.display.widgets.main_base import ObservingBlockOpener_base
from lark.interface import connectDaemon
from lark.rpyclib.interface import connectClient, get_registrar, get_registry_parameters
from lark.utils import UpperDict, import_from

from PyQt5 import QtCore as QtC
from PyQt5 import QtWidgets as QtW


class ObservingBlockOpener(ObservingBlockOpener_base):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        """Open an observing block"""

        self.options_item.clicked.connect(self.options_callback)

        # self.options_item = QtW.QListWidgetItem(self.mode_list)
        # self.options_item.setSizeHint(options_widget.sizeHint())
        # self.options_item.setBackground(QtG.QColor(100,100,100,100))

        # self.mode_list.addItem(self.options_item)
        # self.mode_list.setItemWidget(self.options_item, options_widget)

        self.mode_list.itemSelectionChanged.connect(self.modelist_callback)

        self.options_widget.hide()
        self.options_widget.modeDirChanged.connect(self.setModeDir)
        hostname = get_registry_parameters()["hostname"]
        self.options_widget.setDaemonHost(hostname)
        self.options_widget.resetDaemonClicked.connect(self.reset_daemon)

        self.modestart_button.clicked.connect(self.modestart_callback)
        self.modestop_button.clicked.connect(self.modestop_callback)
        self.modeopen_button.clicked.connect(self.modeopen_callback)

        self.prefixopen_button.clicked.connect(self.prefixopen_callback)
        self.prefixstop_button.clicked.connect(self.prefixstop_callback)

        self.mode_dir = None
        self.displays = UpperDict()
        self.modes = UpperDict()
        self.darcs = []
        
        self.first_start()

        self.timer = QtC.QTimer()
        self.update_timer = QtC.QTimer()
        self.timer.timeout.connect(self.setupModes)
        self.timer.start(1000)
        
    def first_start(self):
        self.setupModes()
        self.mode_list.setCurrentRow(0)
        self.modelist_callback()
        
    def setupModes(self):
        # selected = self.mode_list.currentIndex()
        # self.mode_list.clear()
        # search dir for modes
        self.check_mode_dir()
        # query name server for SRTCs
        self.interrogate_nameserver()
        # modes = {"This":True, "That One":False, "Not this one":False,"This2":True, "That One No":False, "Not this one yet":False}
        self.update_lists()

    def modelist_callback(self):
        self.options_item.unselect()
        self.mode_frame.show()
        self.options_widget.hide()
        mode = self.mode_list.itemWidget(self.mode_list.currentItem())
        if mode is not None:
            mode = mode.name()
            if self.modes[mode][0] is not None:
                md = self.modes[mode][0]
                nlspsp = "\n  "
                info = f"""Name: {md.file_name.replace("mode","")}\n
Path: {md.file_path}\n
Darcs: {nlspsp}{nlspsp.join([f'{k} -> {v[0]} on {v[1]}' for k,v in md.darcs.items()])}\n
Services: {nlspsp}{nlspsp.join([f'{k} -> {v[0]} from {v[1]} on {v[2]}' for k,v in md.services.items()])}\n
Description: {nlspsp}{md.info}"""
                self.modeinfo_textbox.setPlainText(info)
            else:
                self.modeinfo_textbox.setPlainText("No Info Available")

    def options_callback(self):
        self.mode_list.clearSelection()
        self.mode_frame.hide()
        self.options_widget.show()

    def setModeDir(self, mode_dir):
        self.options_widget.setModeDir(mode_dir)
        self.mode_dir = Path(mode_dir)
        self.setupModes()
        
    def setDaemonHost(self, hostname):
        self.options_widget.setDaemonHost(hostname)

    def check_mode_dir(self):
        self.modes = UpperDict()
        if self.mode_dir is not None:
            try:
                file_list = list(self.mode_dir.iterdir())
            except FileNotFoundError as e:
                print(e)
                self.mode_dir = None
            else:
                for fn in file_list:
                    # if fn.name.startswith("mode"):
                    #     mode_mod = import_from(fn)
                    #     self.modes[fn.stem[4:]] = [mode_mod, False]
                    if fn.name.startswith("mode") and fn.is_dir():
                        mode_mod = import_from(fn/"mode.py")
                        self.modes[fn.stem[4:]] = [mode_mod, False]

    def interrogate_nameserver(self):
        reg = get_registrar()
        serv_list: Tuple[str] = reg.list()
        self.darcs = []
        for sn in serv_list:
            try:
                lark = connectClient(sn)
            except ConnectionError as e:
                print(e)
            except ConnectionRefusedError as e:
                print("Can't connect to ",sn)
            else:
                if sn.endswith("SRTC"):
                    name = sn.split("SRTC")[0]
                    mode = self.modes.get(name,[None,False])
                    mode[1] = True
                    self.modes[name] = mode
                elif sn.endswith("CONTROL"):
                    self.darcs.append(lark.prefix)
                    lark.conn.close()

    def update_lists(self):
        selected = self.prefix_list.currentItem()
        count = self.prefix_list.count()
        for i in range(count):
            dd = self.prefix_list.item(i)
            if dd is not None:
                if dd.text() not in self.darcs:
                    self.prefix_list.takeItem(self.prefix_list.row(dd))
                else:
                    self.darcs.remove(dd.text())
        for d in self.darcs:
            self.prefix_list.addItem(d)
        try:
            self.prefix_list.setCurrentItem(selected)
        except:
            pass

        count = self.mode_list.count()
        to_add = {mode:(status,mode_mod is not None) for mode,(mode_mod,status) in self.modes.items()}
        for i in range(count):
            mm = self.mode_list.item(i)
            m = self.mode_list.itemWidget(mm)
            if m is not None:
                if m.name() not in to_add:
                    self.mode_list.takeItem(self.mode_list.row(mm))
                else:
                    m.setStatus(*to_add.pop(m.name()))
        for mode,(status1,status2) in to_add.items():
            self.addModeWidget(mode,status1,status2)

    def modestart_callback(self):
        mode = self.mode_list.itemWidget(self.mode_list.currentItem())
        if mode is not None:
            mode = mode.name()
            if self.modes[mode][0] is not None:
                # self.modes[mode][0].setup()
                self.modes[mode][0].start()
                self.setupModes()
                try:
                    disp = self.modes[mode][0].open()
                except Exception as e:
                    print(e)
                else:
                    if disp:
                        self.displays[mode] = disp

    def modestop_callback(self):
        mode = self.mode_list.itemWidget(self.mode_list.currentItem())
        if mode is not None:
            mode = mode.name()
            if self.modes[mode][0] is not None:
                qm = QtW.QMessageBox()
                ans = qm.question(self,'', "Are you sure you want to stop?", qm.Yes | qm.No)
                if ans == qm.Yes:
                    self.modes[mode][0].stop()
                    self.setupModes()

    def modeopen_callback(self):
        mode = self.mode_list.itemWidget(self.mode_list.currentItem())
        if mode is not None:
            mode = mode.name()
            if self.modes[mode][0] is not None:
                try:
                    disp = self.modes[mode][0].open()
                except Exception as e:
                    print(e)
                else:
                    if disp:
                        self.displays[mode] = disp
                        self.setupModes()

    def prefixopen_callback(self):
        prefix = None
        item = self.prefix_list.currentItem()
        if item is not None:
            prefix = item.text()
        try:
            disp = LarkPlot(prefix)
        except Exception as e:
            print(e)
        else:
            if disp:
                self.displays[prefix] = disp
                self.setupModes()

    def prefixstop_callback(self):
        prefix = self.prefix_list.currentItem().text()
        larkconfig = LarkConfig(prefix)
        ans = self.messagebox.question(self,'', "Are you sure you want to stop DARC?", self.messagebox.Yes | self.messagebox.No)
        if ans == self.messagebox.Yes:
            try:
                larkconfig.getlark()
            except NoLarkError:
                print("No lark available")
            else:
                err = ""
                try:
                    larkconfig.getlark().stop()
                except EOFError as e:
                    err = e
                larkconfig.closelark()
                print(f"Stopped: {prefix}",err)
            self.setupModes()

    def reset_daemon(self, hostname):
        ans = self.messagebox.question(self,'', "Are you sure you want to reset the Daemon+Nameserver?", self.messagebox.Yes | self.messagebox.No)
        if ans == self.messagebox.Yes:
            h = connectDaemon(hostname=hostname)
            h.shutdown()
            
    def closeEvent(self, event) -> None:
        for key,value in self.displays.items():
            if isinstance(value, (tuple,list)):
                for val in value:
                    val.close()
            else:
                value.close()
        return super().closeEvent(event)
