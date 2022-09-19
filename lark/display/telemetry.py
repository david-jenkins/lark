
import sys
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC

from lark import LarkConfig, NoLarkError
import lark.display
from lark.display.widgets.plotting import Plotter
from .widgets.telemetry_base import TelemetryControl_base, TelemetryDisplay_base
from .widgets.main_base import TabWidget
from ..utils import statusBuf_tostring

from .widgets.main_base import SubTabWidget

class TelemetryControl(TelemetryControl_base):
    def __init__(self, larkconfig:LarkConfig, parent=None):
        TelemetryControl_base.__init__(self,parent=parent)
        self.larkconfig = larkconfig
        self.stream_tree.setLarkConfig(larkconfig)
        # self.stream_tree.addStream("rtcCentBuf")
        # self.stream_tree.addStream("rtcMirrorBuf")
        self.timer = QtC.QTimer(self)
        self.timer.timeout.connect(self.on_refresh)

    def on_connect(self):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            self.stream_tree.reset()
            status = lrk.streamStatus()
            info = lrk.streamInfo()
            self.stream_tree.setStreams(status.keys())
            for stream,value in status.items():
                self.stream_tree.connectStream(stream,value,info[stream])

    def on_refresh(self):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError:
            print("No lark available")
        else:
            status = lrk.streamStatus()
            info = lrk.streamInfo()
            for stream,value in status.items():
                self.stream_tree.updateStream(stream,value,info[stream])

    def on_disconnect(self):
        self.stream_tree.reset()

    def showEvent(self, event):
        self.timer.start(1000)
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)


class TelemetryDisplay(TelemetryDisplay_base):
    def __init__(self,larkconfig,parent=None):
        TelemetryDisplay_base.__init__(self,parent=parent)
        self.larkconfig = larkconfig

    def on_connect(self):
        print("telemetry display connecting")

    def on_disconnect(self):
        print("telemetry display disconnecting")


class StatusDisplay(Plotter):
    def __init__(self,larkconfig,parent=None):
        super().__init__(larkconfig,parent=parent,plottype="text",streams = ["rtcStatusBuf"])
        self.menu = QtW.QMenu("&Status")

    def on_connect(self):
        super().on_connect()
        self.data = self.lark.getStreamBlock("rtcStatusBuf",1)[0][0]
        self.update_plot()

    def update_plot(self):
        if self._data is not None:
            # self.data = self.encoder.decode(self._data)[0]
            self.data = self._data[0]
        if self.data is not None:
            self.plotter.plot(statusBuf_tostring(self.data))
        QtC.QCoreApplication.processEvents()

    def showEvent(self, event):
        self._startUpdates()
        self.update_timer.start(1000//self.framerate)
        super(Plotter, self).showEvent(event)

    def hideEvent(self, event):
        self._stopUpdates()
        self.update_timer.stop()
        super(Plotter, self).hideEvent(event)

class TelemetryMain(SubTabWidget):
    def __init__(self,larkconfig,parent=None,**kwargs):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig

        self.menu.setTitle("Telemetry")

        control = TelemetryControl(self.larkconfig, self)
        display = TelemetryDisplay(self.larkconfig, self)
        status = StatusDisplay(self.larkconfig, self)

        self.addWidget(control, "Control")
        self.addWidget(display, "Display")
        self.addWidget(status, "Status")
class TelemetryWindow(QtW.QMainWindow):
    def __init__(self, larkconfig):
        super().__init__()
        self.larkconfig = larkconfig
        menu = self.menuBar()
        self.filemenu = QtW.QMenu("&File")
        self.quitAction = QtW.QAction('&Quit')
        self.filemenu.addAction(self.quitAction)
        self.quitAction.triggered.connect(self.close)

        self.main = TelemetryMain(self.larkconfig,self)
        menu.addMenu(self.filemenu)
        menu.addMenu(self.main.menu)
        self.setMenuBar(menu)
        self.setCentralWidget(self.main)
        self.displays = []

def main():
    larkconfig = LarkConfig()
    if len(sys.argv) > 1:
        larkconfig.prefix = sys.argv[1]
    else:
        print("Need a prefix")
        sys.exit()
    try:
        larkconfig.getlark()
    except NoLarkError as e:
        print(e)
        sys.exit()
    from .main import MainLarkWindow
    app = QtW.QApplication(sys.argv)
    win = MainLarkWindow(larkconfig, TelemetryMain)
    win.setWindowTitle("Telemetry")
    win.on_connect()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()