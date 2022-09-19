import sys
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG
from lark import LarkConfig
import numpy
from .widgets.plotting import Plotter

from .widgets.main_base import SubTabWidget

from lark import NoLarkError

class DmCommands1D(Plotter):
    def __init__(self,larkconfig,parent=None):
        super().__init__(larkconfig,parent=parent,plottype="1D",streams=["rtcMirrorBuf"])

    def on_connect(self):
        super().on_connect()
        print("Connected dm commands")

    def update_plot(self):
        if self._data is not None:
            # self.data = self.encoder.decode(self._data)[0]
            self.data = self._data[0]
            self._data = None
        if self.data is not None:
            self.plot(self.data)
        QtC.QCoreApplication.processEvents()
        # self.plotter.autoRange()

    def on_disconnect(self):
        super().on_disconnect()

class DmCommands2D(Plotter):
    def __init__(self,larkconfig,parent=None):
        self.stopped = False
        super().__init__(larkconfig,parent=parent,plottype="2D",streams=["rtcMirrorBuf"])

    def on_connect(self):
        super().on_connect()
        data = self.lark.getStreamBlock("rtcMirrorBuf",1)
        self.data = data[0][0]
        self.actFlag = self.lark.get("actFlag")
        if self.actFlag is not None:
            self.imdata = numpy.zeros_like(self.actFlag,float)
            self.imdata[numpy.where(self.actFlag!=1)] = numpy.nan
            self.imdata[numpy.where(self.actFlag==1)] = self.data
            self.update_plot()
        else:
            self.stopped = True
        print("Connected dm commands")

    def update_plot(self):
        if self.stopped:
            return
        if self._data is not None:
            # self.data = self.encoder.decode(self._data)[0]
            self.data = self._data[0]
            self._data = None
        if self.data is not None:
            self.imdata[numpy.where(self.actFlag==1)] = self.data
            self.plot(self.imdata)
        QtC.QCoreApplication.processEvents()
        # self.plotter.autoRange()

    def on_disconnect(self):
        super().on_disconnect()

class DmMain(SubTabWidget):
    def __init__(self,larkconfig,parent=None,**kwargs):
        super().__init__(parent=parent)
        self.menu.setTitle("DM")
        self.larkconfig = larkconfig

        commands1d = DmCommands1D(self.larkconfig, self)
        commands2d = DmCommands2D(self.larkconfig, self)

        self.addWidget(commands1d,"Commands 1D")
        self.addWidget(commands2d,"Commands 2D")

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
    app = QtW.QApplication(sys.argv)
    from .main import MainLarkWindow
    win = MainLarkWindow(larkconfig, DmMain)
    win.on_connect()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
