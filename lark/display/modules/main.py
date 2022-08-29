
from pathlib import Path
import sys
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtGui as QtG
from PyQt5 import QtCore as QtC
from lark import LarkConfig, configLoader
from lark.rpyclib.interface import get_registry_parameters
import pyqtgraph as pg
# pyqtgraph does some cleanup that is MAYBE not necessary anymore
# it raises an exception on exit when using RPyC, this disables the
# cleanup routine
pg.setConfigOption('exitCleanup', False)
# from .control import ControlMain
# from .telemetry import TelemetryMain
# from .dm import DmMain
# from .wfs import WfsMain
# from .stats import StatsMain
# from .srtc import SrtcMain
# from .diagnostics import DiagnosticsMain
# from . import config

from lark.display.main import MainWindow, MainWidget as _MainWidget, DisplayWidget as _DisplayWidget
from .wfs import CamControl
from .srtc import SrtcMain

from lark.display.modes import ObservingBlockOpener


class MainWidget(_MainWidget):
    def __init__(self, larkconfig, parent=None):
        super().__init__(larkconfig, parent=parent)

        srtc = SrtcMain(self.larkconfig, self)
        # srtc.menu = QtW.QMenu("SRTC")
        # srtc.on_connect = lambda: print("Connecting SRTC")
        # srtc.on_disconnect = lambda: print("Disconnecting SRTC")
        custom = QtW.QWidget()
        custom.menu = QtW.QMenu("Custom")
        custom.on_connect = lambda: print("Connecting Custom")
        custom.on_disconnect = lambda: print("Disconnecting Custom")
        diag = QtW.QWidget()
        diag.menu = QtW.QMenu("Diagnostics")
        diag.on_connect = lambda: print("Connecting Diagnostics")
        diag.on_disconnect = lambda: print("Disconnecting Diagnostics")
        self.addWidget(srtc,"SRTC")
        self.addWidget(custom,"Custom")
        self.addWidget(diag,"Diagnostics")

        ocam = CamControl(self.larkconfig, self)
        self.widgets["WFS"].addWidget(ocam,"OCAM")

class DisplayWidget(_DisplayWidget):
    def __init__(self, larkcontrol, parent=None):
        super().__init__(parent=parent)
        self.larkcontrol = larkcontrol

        custom = QtW.QWidget()
        custom.menu = QtW.QMenu("Custom")
        custom.on_connect = lambda: print("Connecting Custom")
        custom.on_disconnect = lambda: print("Disconnecting Custom")

        self.addWidget(custom,"Custom")

        ocam = CamControl(self.larkcontrol,self)
        self.widgets["WFS"].addWidget(ocam,"OCAM")


def modeselector():
    app = QtW.QApplication(sys.argv)
    win = ObservingBlockOpener()
    config_dir = Path(configLoader.CONFIG_DIR).expanduser()
    # win.setModeDir("/home/laserlab/djenkins/git/canapy-rtc/canapyconfig")
    win.setModeDir(config_dir)
    # win.setModeDir("/home/canapyrtc/git/canapy-rtc/canapyconfig")
    host = get_registry_parameters()["hostname"]
    win.setDaemonHost(host)
    win.show()
    sys.exit(app.exec())

def main():
    larkconfig = LarkConfig()
    app = QtW.QApplication(sys.argv)
    win = MainWindow(larkconfig, MainWidget, DisplayWidget)
    win.setWindowTitle("CaNaPy RTC Control")
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
