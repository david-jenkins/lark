

import sys
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC

from lark import LarkConfig, NoLarkError

from .control import ControlGui
from .telemetry import TelemetryMain
from .dm import DmMain
from .wfs import WfsMain
import pyqtgraph as pg
pg.setConfigOption('exitCleanup', False)

from .widgets.main_base import MainTabWidget, MainWindow

class MainDisplay(MainTabWidget):
    """A widget for displaying Lark GUI widgets but without Lark controls.
    Can be opened from a MainWidget as a secondary viewer
    """
    def __init__(self, larkconfig:LarkConfig, parent=None, daemon_controls=True, **kwargs):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig

        self.control = ControlGui(self.larkconfig, self, daemon_controls=daemon_controls)
        self.control.widgets["Control"].larkConnected.connect(self.on_connect)
        self.control.widgets["Control"].larkDisconnected.connect(self.on_disconnect)
        if daemon_controls:
            self.control.widgets["Daemon"].larkConnected.connect(self.on_connect)
            self.control.widgets["Daemon"].larkDisconnected.connect(self.on_disconnect)
        telemetry = TelemetryMain(self.larkconfig,self)
        wfs = WfsMain(self.larkconfig,self)
        dm = DmMain(self.larkconfig,self)

        self.addWidget(self.control, "DARC")
        self.addWidget(telemetry, "Telemetry")
        self.addWidget(wfs, "WFS")
        self.addWidget(dm, "DM")
        self.control.on_first_start()

class MainLarkWindow(MainWindow):
    def __init__(self, larkconfig: LarkConfig, display_class=MainDisplay, parent=None, daemon_controls=True, **kwargs):
        
        super().__init__(parent=parent)
        main = display_class(larkconfig, parent=self, daemon_controls=daemon_controls, **kwargs)
        self.setCentralWidget(main)

        self.larkconfig = larkconfig
        self.kwargs = kwargs
        self.display_class = display_class
        
        menu = self.menuBar()
        main.addMenus(menu)
        self.setMenuBar(menu)

        self.openDisplayAction = QtW.QAction('Open Display')
        self.openDisplayAction.triggered.connect(self.openDisplay)
        self.filemenu.insertAction(self.quitAction,self.openDisplayAction)

        self.setWindowTitle("Lark Control")

        self.displays = []

    def closeEvent(self, event):
        self.centralWidget().close()
        return super().closeEvent(event)

    def openDisplay(self):
        display = MainLarkWindow(self.larkconfig, main_class=self.display_class, parent=self.centralWidget(), daemon_controls=False, **self.kwargs)
        display.setWindowTitle("Lark Display")
        display.on_connect()
        display.installEventFilter(self)
        self.displays.append(display)
        self.centralWidget().add_display(display)
        display.resize(self.size())
        display.show()

    def eventFilter(self, obj, event):
        if obj in self.displays and event.type() == QtC.QEvent.Close:
            self.centralWidget().remove_display(obj)
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
    win.show()
    sys.exit(app.exec())

def LarkPlot(prefix=None):
    larkconfig = LarkConfig(prefix=prefix)
    try:
        larkconfig.getlark()
    except NoLarkError as e:
        print(e)
    win = MainLarkWindow(larkconfig, MainDisplay, daemon_controls=False)
    win.setWindowTitle("Lark Plot")
    return win

def LarkGUI(prefix=None):
    larkconfig = LarkConfig(prefix=prefix)
    win = MainLarkWindow(larkconfig)
    win.setWindowTitle("Lark GUI")
    return win
    
def widget_tester(widget, args, kwargs):
    app = QtW.QApplication(sys.argv)
    win = QtW.QMainWindow()
    widget = widget(*args,**kwargs)
    win.setCentralWidget(widget)
    win.show()
    sys.exit(app.exec())

def main():
    app = QtW.QApplication(sys.argv)
    win = LarkGUI()
    # win = LarkPlot()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()