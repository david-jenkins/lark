
import pickle
import sys
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG

from lark.display.widgets.main_base import MainTabWidget

from lark.interface import startServiceClient, connectDaemon, connectClient

from .widgets.srtc_base import SrtcFunctionList_base, SrtcControl_base

import lark

class SrtcFunctionList(SrtcFunctionList_base):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        
        self.period_input.setValue(1.0)

        # self.func_list.itemChanged.connect(self.get_params)
        self.func_list.currentItemChanged.connect(self.get_params)
        self.execute_button.clicked.connect(self.execute_callback)
        self.begin_button.clicked.connect(self.begin_callback)
        self.stop_button.clicked.connect(self.stop_callback)
        self.setvalues_button.clicked.connect(self.setvalues_callback)
        self.name:str = None

    def execute_callback(self):
        name = self.func_list.currentItem().text()
        print(name)
        apply = self.apply_check.isChecked()
        lark.getservice(self.name).getPlugin(name).run(_apply=apply,**self.param_tree.get_values())

    def begin_callback(self):
        name = self.func_list.currentItem().text()
        period = self.period_input.value()
        print(name)
        lark.getservice(self.name).getPlugin(name).start(**self.param_tree.get_values(),_period=period)

    def stop_callback(self):
        name = self.func_list.currentItem().text()
        print(name)
        lark.getservice(self.name).getPlugin(name).stop()

    def setvalues_callback(self):
        name = self.func_list.currentItem().text()
        print("SETTING")
        print(name)
        print(self.param_tree.get_values())
        lark.getservice(self.name).getPlugin(name).Configure(**self.param_tree.get_values())

    def get_params(self):
        name = self.func_list.currentItem().text()
        print(name)
        function = lark.getservice(self.name).getPlugin(name)
        print(function)
        values = function.values
        self.param_tree.setData(values)

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def srtc_connect(self, name):
        self.name = name
        self.func_list.clear()
        self.param_tree.clear()
        functions = lark.getservice(self.name).getPlugin()
        for k,v in functions.items():
            item = QtW.QListWidgetItem(k)
            self.func_list.addItem(item)
            self.param_tree.setData(v.values)



class SrtcControl(SrtcControl_base):
    def __init__(self,parent=None):
        super().__init__(parent=parent)

        self.control = parent

        # self.startsrtc_button.clicked.connect(self.startsrtc_callback)
        # self.stopsrtc_button.clicked.connect(self.stopsrtc_callback)
        self.statussrtc_button.clicked.connect(self.statussrtc_callback)
        self.srtcname_chooser.valueSet.connect(self.srtcname_callback)
        self.srtcname_finder.serviceChosen.connect(self.on_first_start)

    def srtcname_callback(self, name):
        self.name = name+"SRTC"
        try:
            self.srtc = lark.getservice(self.name)
        except ConnectionError as e:
            print(e)
            self.status_label.setPlainText("No SRTC found")
            self.setButtons(True,False,False)
        else:
            self.control.srtc_connect(self.name)
            self.print("Connected to SRTC")
            self.setButtons(False,True,True)
            self.statussrtc_callback()


    # def startsrtc_callback(self):
    #     startservice("LGSWF")
    #     self.control.srtc_connect()
    #     status = getservice("LGSWF").status()
    #     self.status_label.setPlainText(status)
    #     self.setButtons(False,True,True)

    # def stopsrtc_callback(self):
    #     try:
    #         srtc = lark.getservice(self.name)
    #     except Exception as e:
    #         status = repr(e)
    #     else:
    #         srtc.unblock()
    #         status = "Stopped SRTC"
    #     self.setButtons(True,False,False)
    #     self.print(status)

    def resetsrtc_callback(self):
        pass

    def statussrtc_callback(self):
        try:
            srtc = lark.getservice(self.name)
        except Exception as e:
            self.print(repr(e))
        else:
            self.print(srtc.status())
            self.print("Functions : Values: Results",1)
            self.print("===========================",1)
            functions = srtc.getPlugin()
            results = srtc.getResult()
            for k,v in functions.items():
                # vals = {k:v for k,v in v.Values().items()}
                self.print(f"{k} : {v.Values()} : {results.get(k,None)}",1)

    def on_connect(self):
        pass
        # try:
        #     srtc = lark.getservice("LGSWF")
        # except Exception as e:
        #     print(e)
        #     self.status_label.setPlainText("No SRTC found")
        #     self.setButtons(True,False,False)
        # else:
        #     self.control.srtc_connect()
        #     self.print("Connected to SRTC")
        #     self.startsrtc_button.setEnabled(False)
        #     self.setButtons(False,True,True)

    def on_first_start(self, name):
        self.srtcname_chooser.set_value(name,True)

    def on_disconnect(self):
        pass

    def setButtons(self,start,stop,status):
        self.startsrtc_button.setEnabled(start)
        self.stopsrtc_button.setEnabled(stop)
        self.statussrtc_button.setEnabled(status)

    def print(self,message,append=0):
        if not append:
            self.status_label.setPlainText(message)
        else:
            self.status_label.append(message)

class SrtcMain(MainTabWidget):
    def __init__(self,larkconfig,parent=None):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig

        self.menu = QtW.QMenu("SRTC",self)
        self.control = SrtcControl(self)
        self.functions = SrtcFunctionList(self)

        self.addWidget(self.control,"Control")
        self.addWidget(self.functions,"Functions")

    def srtc_connect(self, name):
        self.functions.srtc_connect(name)

    def on_first_start(self, name):
        self.control.on_first_start(name)

# def main():
#     app = QtW.QApplication(sys.argv)
#     sys.exit(app.exec_())

# if __name__ == "__main__":
#     main()



