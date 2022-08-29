
import sys
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from .widgets.telemetry_base import TelemetryControl_base, TelemetryDisplay_base
from lark.display.main import TabWidget
import lark

class TelemetryControl(TelemetryControl_base):
    def __init__(self,parent=None):
        TelemetryControl_base.__init__(self,parent=parent)
        # self.stream_tree.addStream("rtcCentBuf")
        # self.stream_tree.addStream("rtcMirrorBuf")
        self.timer = QtC.QTimer(self)
        self.timer.timeout.connect(self.on_refresh)

    def on_connect(self):
        self.stream_tree.reset()
        status = config.lark.streamStatus()
        info = config.lark.streamInfo()
        self.stream_tree.setStreams(status.keys())
        for stream,value in status.items():
            self.stream_tree.connectStream(stream,value,info[stream])

    def on_refresh(self):
        if config.lark is not None:
            status = config.lark.streamStatus()
            info = config.lark.streamInfo()
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
    def __init__(self,parent=None):
        TelemetryDisplay_base.__init__(self,parent=parent)

    def on_connect(self):
        print("telemetry display connecting")

class TelemetryMain(TabWidget):
    def __init__(self,parent=None):
        TabWidget.__init__(self,parent=parent)
        self.menu = QtW.QMenu("Telemetry",self)
        self.control = TelemetryControl(self)
        self.display = TelemetryDisplay(self)

        self.menu.addMenu(self.control.menu)
        self.menu.addMenu(self.display.menu)

        self.addTab(self.control, "Control")
        self.addTab(self.display, "Display")

    def on_connect(self):
        self.control.on_connect()
        self.display.on_connect()

    def on_disconnect(self):
        self.control.on_disconnect()

def main():
    from .misc import MainWindow
    app = QtW.QApplication(sys.argv)
    win = MainWindow(TelemetryControl)
    # win = DaemonQt()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()