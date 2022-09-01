
import sys
import atexit
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtGui as QtG
from PyQt5 import QtCore as QtC
from lark import LarkConfig, NoLarkError
from lark.display.wfs import WfsImages
from lark.display.widgets.misc import LoggerFilePrint
import pyqtgraph as pg
pg.setConfigOption('exitCleanup', False)

from lark.display.main import MainWindow, MainWidget as _MainWidget, DisplayWidget as _DisplayWidget
from lark.display.modules.wfs import CamControl, PyCircles
from lark.display.srtc import SrtcMain
from lark.display.modules.custom import CustomMain

srtc_name = "LabPyTest"

class MainWidget(_DisplayWidget):
    def __init__(self, larkconfig, parent=None):
        super().__init__(larkconfig, parent=parent)
        
        # self.widget(0).insertWidget(0,srtc,"SRTC")
        # self.widgets["DARC"]
        # self.widgets["DARC"].setCurrentIndex(0)
        # srtc.menu = QtW.QMenu("SRTC")
        # srtc.on_connect = lambda: print("Connecting SRTC")
        # srtc.on_disconnect = lambda: print("Disconnecting SRTC")
        # scoring.menu = QtW.QMenu("Scoring")
        # scoring.on_connect = lambda: print("Connecting Scoring")
        # scoring.on_disconnect = lambda: print("Disconnecting Scoring")
        
        srtc = SrtcMain(self.larkconfig, self)
        
        custom = CustomMain(self.larkconfig, self)
        diag = QtW.QWidget()
        diag.menu = QtW.QMenu("Diagnostics")
        diag.on_connect = lambda: print("Connecting Diagnostics")
        diag.on_disconnect = lambda: print("Disconnecting Diagnostics")

        self.addWidget(srtc,"SRTC")
        self.addWidget(custom,"Custom")
        self.addWidget(diag,"Diagnostics")
        
        evtconfig = LarkConfig("PyScoring")
        camcontrol = CamControl(larkconfig,evtconfig,"LgsWFiPortSRTC",self)
        self.widgets["WFS"].addWidget(camcontrol,"Cam Control")
        
        evtconfig = LarkConfig("PyScoring")
        evtdisplay = WfsImages(evtconfig)
        self.widgets["WFS"].addWidget(evtdisplay,"Scoring Cam")
        evtdisplay_raw = WfsImages(evtconfig,cal=0)
        self.widgets["WFS"].addWidget(evtdisplay_raw,"Scoring Raw")
        
        iportdaemonprint = LoggerFilePrint(f"{larkconfig.prefix}iPortSRTC.log")
        self.widgets["SRTC"].addWidget(iportdaemonprint,"iPort output")
        
        pycirc = PyCircles(larkconfig,srtc_name)
        self.widgets["SRTC"].addWidget(pycirc,"PyCirc")

        srtc.on_first_start(srtc_name)
        self.control.on_first_start()

# class DisplayWidget(_DisplayWidget):
#     def __init__(self, larkcontrol, parent=None):
#         super().__init__(larkcontrol, parent=parent)
#         self.larkcontrol = larkcontrol

#         scoring = QtW.QWidget()
#         scoring.menu = QtW.QMenu("Scoring")
#         scoring.on_connect = lambda: print("Connecting Scoring")
#         scoring.on_disconnect = lambda: print("Disconnecting Scoring")
#         custom = QtW.QWidget()
#         custom.menu = QtW.QMenu("Custom")
#         custom.on_connect = lambda: print("Connecting Custom")
#         custom.on_disconnect = lambda: print("Disconnecting Custom")

#         self.addWidget(scoring,"Scoring")
#         self.addWidget(custom,"Custom")

#         ocam = OcamControl(self.larkcontrol,self)
#         self.widgets["WFS"].addWidget(ocam,"OCAM")


def CanapyGUI(prefix="LgsWF",srtc="LabPyTest"):
    larkconfig = LarkConfig(prefix)
    global srtc_name
    srtc_name = srtc
    try:
        larkconfig.getlark()
    except NoLarkError as e:
        return None
    win = MainWindow(larkconfig, MainWidget, MainWidget)
    win.setWindowTitle("CaNaPy RTC Control")
    win.show()
    return win

def main():
    app = QtW.QApplication(sys.argv)
    win = CanapyGUI()
    sys.exit(app.exec())

if __name__ == "__main__":
    CanapyGUI()
