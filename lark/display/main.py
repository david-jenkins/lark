
import atexit
import sys
import PyQt5
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC

from lark import LarkConfig, NoLarkError

from .control import ControlPlot, ControlGui
from .telemetry import TelemetryMain
from .dm import DmMain
from .wfs import WfsMain
import pyqtgraph as pg
pg.setConfigOption('exitCleanup', False)

from .widgets.main_base import MainTabWidget, MainWindow as _MainWindow, ObservingBlockOpener_base

class DisplayWidget(MainTabWidget):
    def __init__(self, larkconfig:LarkConfig, parent=None, **kwargs):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig

        self.control = ControlPlot(self.larkconfig,self)
        self.control.widgets["Control"].larkConnected.connect(self.on_connect)
        self.control.widgets["Control"].larkDisconnected.connect(self.on_disconnect)
        telemetry = TelemetryMain(self.larkconfig,self)
        wfs = WfsMain(self.larkconfig,self)
        dm = DmMain(self.larkconfig,self)

        self.addWidget(self.control, "DARC")
        self.addWidget(telemetry, "Telemetry")
        self.addWidget(wfs, "WFS")
        self.addWidget(dm, "DM")
        self.control.on_first_start()

class MainWidget(MainTabWidget):
    def __init__(self, larkconfig:LarkConfig, parent=None, **kwargs):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig

        control = ControlGui(self.larkconfig,self)
        control.widgets["Control"].larkConnected.connect(self.on_connect)
        control.widgets["Control"].larkDisconnected.connect(self.on_disconnect)
        telemetry = TelemetryMain(self.larkconfig,self)
        wfs = WfsMain(self.larkconfig,self)
        dm = DmMain(self.larkconfig,self)

        self.addWidget(control, "DARC")
        self.addWidget(telemetry, "Telemetry")
        self.addWidget(wfs, "WFS")
        self.addWidget(dm, "DM")
        control.on_first_start()

class MainWindow(_MainWindow):
    def __init__(self, larkconfig: LarkConfig, main_class=MainWidget, display_class=DisplayWidget, parent=None, **kwargs):
        super().__init__(parent=parent)

        self.larkconfig = larkconfig
        self.main_class = main_class
        self.display_class = display_class
        self.kwargs = kwargs

        menu = self.menuBar()
        self.main = main_class(self.larkconfig,parent=self,**kwargs)
        self.main.addMenus(menu)
        self.setMenuBar(menu)
        self.setCentralWidget(self.main)

        self.openDisplayAction = QtW.QAction('Open Display')
        self.openDisplayAction.triggered.connect(self.openDisplay)
        self.filemenu.insertAction(self.quitAction,self.openDisplayAction)

        self.setWindowTitle("Lark Control")

        self.displays = []

    def closeEvent(self, event):
        self.main.close()
        return super().closeEvent(event)

    def openDisplay(self):
        display = MainWindow(self.larkconfig, main_class=self.display_class, parent=self.main, **self.kwargs)
        display.setWindowTitle("Lark Display")
        display.on_connect()
        display.installEventFilter(self)
        self.displays.append(display)
        self.main.add_display(display)
        display.resize(self.size())
        display.show()

    def eventFilter(self, obj, event):
        if obj in self.displays and event.type() == QtC.QEvent.Close:
            self.main.remove_display(obj)
            self.displays.remove(obj)
        return super().eventFilter(obj,event)


def larkplot():

    if len(sys.argv)>1:
        prefix = sys.argv[1]
    else:
        print("Needs a prefix")
        sys.exit()

    app = QtW.QApplication(sys.argv)
    win = LarkPlot(prefix)
    if win is None:
        sys.exit()
    # pyqtgraph does some cleanup that is MAYBE not necessary anymore
    # it raises an exception on exit when using RPyC, this disables the
    # cleanup routine
    sys.exit(app.exec())

def LarkPlot(prefix=None):
    larkconfig = LarkConfig(prefix=prefix)
    try:
        larkconfig.getlark()
    except NoLarkError as e:
        print("No lark available with this prefix")
        return None
    win = MainWindow(larkconfig,DisplayWidget,DisplayWidget)
    win.setWindowTitle("Lark Plot")
    win.show()
    return win

def LarkGUI(prefix=None):
    larkconfig = LarkConfig(prefix=prefix)
    win = MainWindow(larkconfig)
    win.setWindowTitle("Lark GUI")
    win.show()
    return win
    
def widget_tester(widget,args,kwargs):
    app = QtW.QApplication(sys.argv)
    win = QtW.QMainWindow()
    widget = widget(*args,**kwargs)
    win.setCentralWidget(widget)
    win.show()
    sys.exit(app.exec_())

def main():
    app = QtW.QApplication(sys.argv)
    win = LarkGUI()
    ret = app.exec()
    sys.exit(ret)

if __name__ == "__main__":
    main()