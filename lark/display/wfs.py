import sys
import time
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG

import pyqtgraph as pg

from lark import LarkConfig, NoLarkError
from .widgets.main_base import SubTabWidget
from .widgets.plotting import Plotter
import numpy

class WfsSlopes1D(Plotter):
    def __init__(self,larkconfig, parent=None):
        super().__init__(larkconfig,parent=parent,plottype="1D",streams=["rtcCentBuf"])

    def on_connect(self):
        super().on_connect()
        data = self.lark.getStreamBlock("rtcCentBuf",1)
        self.data = data[0][0]
        self._data = None
        self.ncam = self.lark.get("ncam")
        self.makeNPlots(self.ncam*2)
        if len(self.data.shape)==1:
            self.reshape = 1
            nsub = self.lark.get("nsub")
            subapFlag = self.lark.get("subapFlag")
            self.vsubs = []
            for k in range(self.ncam):
                start = 0 if k==0 else sum(nsub[:k])
                self.vsubs.append(int(subapFlag[start:start+nsub[k]].sum()))
        else:
            self.reshape = 0
        self.plotter.reset()
        self.update_plot()
        self.placePlots()
        print("Connected on wfs 1d")

    def update_plot(self):
        if self._data is not None:
            # self.data = self.encoder.decode(self._data)[0]
            self.data = self._data[0]
            self._data = None
        if self.data is not None:
            if self.reshape:
                camdata = []
                for i in range(self.ncam):
                    start = 0 if i==0 else 2*sum(self.vsubs[:i])
                    data = self.data[start:start+2*self.vsubs[i]:2]
                    camdata.append(data)
                    data = self.data[start+1:start+2*self.vsubs[i]:2]
                    camdata.append(data)
                self.plot(*camdata)
            else:
                self.plot(*self.data)
        QtC.QCoreApplication.processEvents()
        # self.plotter.autoRange()

class WfsFlux1D(Plotter):
    def __init__(self,larkconfig,parent=None):
        super().__init__(larkconfig,parent=parent,plottype="1D",streams=["rtcFluxBuf"])

    def on_connect(self):
        super().on_connect()
        data = self.lark.getStreamBlock("rtcFluxBuf",1)
        self.data = data[0][0]
        self._data = None
        self.ncam = self.lark.get("ncam")
        self.makeNPlots(self.ncam)
        if len(self.data.shape)==1:
            self.reshape = 1
            nsub = self.lark.get("nsub")
            subapFlag = self.lark.get("subapFlag")
            self.vsubs = []
            for k in range(self.ncam):
                start = 0 if k==0 else sum(nsub[:k])
                self.vsubs.append(int(subapFlag[start:start+nsub[k]].sum()))
        else:
            self.reshape = 0
        self.plotter.reset()
        self.update_plot()
        self.placePlots()
        print("Connected on flux")

    def update_plot(self):
        if self._data is not None:
            # self.data = self.encoder.decode(self._data)[0]
            self.data = self._data[0]
            self._data = None
        if self.data is not None:
            if self.reshape:
                camdata = []
                for i in range(self.ncam):
                    start = 0 if i==0 else sum(self.vsubs[:i])
                    data = self.data[start:start+self.vsubs[i]]
                    camdata.append(data)
                self.plot(*camdata)
            else:
                self.plot(*self.data)
        QtC.QCoreApplication.processEvents()
        # self.plotter.autoRange()

class WfsFlux2D(Plotter):
    def __init__(self,larkconfig,parent=None):
        super().__init__(larkconfig,parent=parent,plottype="2D",streams=["rtcFluxBuf"])

    def on_connect(self):
        super().on_connect()
        data = self.lark.getStreamBlock("rtcFluxBuf",1)
        self.data = data[0][0]
        self._data = None
        self.ncam = self.lark.get("ncam")
        self.makeNPlots(self.ncam)
        self.imdata = []
        self.vmaps = []
        try:
            self.nsubx = self.lark.get("nsubx")
            self.nsuby = self.lark.get("nsuby")
        except Exception as e:
            self.lark = None
        else:
            if len(self.data.shape)==1:
                self.reshape = 1
                self.nsub = self.lark.get("nsub")
                self.subapFlag = self.lark.get("subapFlag")
                self.vsubs = []
                for k in range(self.ncam):
                    start = 0 if k==0 else sum(self.nsub[:k])
                    v = self.subapFlag[start:start+self.nsub[k]]==1
                    v.shape = self.nsubx[k],self.nsuby[k]
                    self.vmaps.append(v)
                    x = numpy.zeros_like(self.subapFlag[start:start+self.nsub[k]],float)
                    x.shape = self.nsubx[k],self.nsuby[k]
                    x[~v] = numpy.nan
                    self.imdata.append(x)
                    self.vsubs.append(int(self.subapFlag[start:start+self.nsub[k]].sum()))
            else:
                self.reshape = 0
        self.plotter.reset()
        self.update_plot()
        self.placePlots()
        print("Connected on flux")

    def update_plot(self):
        if self._data is not None:
            # self.data = self.encoder.decode(self._data)[0]
            self.data = self._data[0]
            self._data = None
        if self.data is not None:
            if self.reshape:
                camdata = []
                for i in range(self.ncam):
                    start = 0 if i==0 else sum(self.vsubs[:i])
                    data = self.data[start:start+self.vsubs[i]]
                    
                    imdata = self.imdata[i]
                    # imdata[:,:] = 0
                    imdata[self.vmaps[i]] = data
                    camdata.append(imdata)
                self.plot(*camdata)
            else:
                self.plot(*self.data)
        QtC.QCoreApplication.processEvents()
        # self.plotter.autoRange()

class WfsSlopes2D(Plotter):
    def __init__(self,larkconfig,parent=None):
        super().__init__(larkconfig,parent=parent,plottype="2D",streams=["rtcCentBuf"])

    def on_connect(self):
        super().on_connect()
        data = self.lark.getStreamBlock("rtcCentBuf",1)
        self.data = data[0][0]
        self._data = None
        self.ncam = self.lark.get("ncam")
        self.makeNPlots(self.ncam*2)
        self.imdatax = []
        self.imdatay = []
        self.vmaps = []
        self.data_shape = self.data.shape
        print("WFS2D initial shape ", self.data_shape)
        try:
            self.nsubx = self.lark.get("nsubx")
            self.nsuby = self.lark.get("nsuby")
        except Exception as e:
            self.lark = None
        else:
            if len(self.data.shape)==1:
                self.reshape = 1
                self.nsub = self.lark.get("nsub")
                self.subapFlag = self.lark.get("subapFlag")
                self.vsubs = []
                for k in range(self.ncam):
                    start = 0 if k==0 else sum(self.nsub[:k])
                    v = self.subapFlag[start:start+self.nsub[k]]==1
                    v.shape = self.nsubx[k],self.nsuby[k]
                    self.vmaps.append(v)
                    x = numpy.zeros_like(self.subapFlag[start:start+self.nsub[k]],float)
                    x.shape = self.nsubx[k],self.nsuby[k]
                    x[~v] = numpy.nan
                    self.imdatax.append(x)
                    y = numpy.zeros_like(self.subapFlag[start:start+self.nsub[k]],float)
                    y.shape = self.nsubx[k],self.nsuby[k]
                    y[~v] = numpy.nan
                    self.imdatay.append(y)
                    self.vsubs.append(int(self.subapFlag[start:start+self.nsub[k]].sum()))
            else:
                self.reshape = 0
            self.update_plot()
            self.placePlots(4)
            print("Connected on wfs 2d")

    def update_plot(self):
        if self._data is not None:
            # self.data = self.encoder.decode(self._data)[0]
            self.data = self._data[0]
        if self.data is not None:
            print(f"self.data.shape = {self.data.shape}")
            if self.data.shape != self.data_shape:
                self.on_connect()
                return
            if self.reshape:
                camdata = []
                for i in range(self.ncam):
                    start = 0 if i==0 else 2*sum(self.vsubs[:i])
                    data = self.data[start:start+2*self.vsubs[i]:2]

                    start = 0 if i==0 else self.nsub[i-1]
                    imdatax = self.imdatax[i]
                    # imdatax[:,:] = 0
                    imdatax[self.vmaps[i]] = data
                    # imdatax -= numpy.amin(self.data).astype(imdatax.dtype)
                    camdata.append(imdatax)

                    start = 0 if i==0 else 2*sum(self.vsubs[:i])
                    data = self.data[start+1:start+2*self.vsubs[i]:2]

                    start = 0 if i==0 else self.nsub[i-1]
                    imdatay = self.imdatay[i]
                    # imdatay[:,:] = 0

                    imdatay[self.vmaps[i]] = data
                    # imdatay -= numpy.amin(self.data).astype(imdatay.dtype)
                    camdata.append(imdatay)
                self.plot(*camdata)
            else:
                self.plot(*self.data)

        QtC.QCoreApplication.processEvents()
        # self.plotter.autoRange()

class WfsImages(Plotter):
    def __init__(self,larkconfig,parent=None,cal=1):
        self._stream = "rtcCalPxlBuf" if cal else "rtcPxlBuf"
        super().__init__(larkconfig,parent=parent,plottype="2D",streams=[self._stream])

    def on_connect(self):
        super().on_connect()
        data = self.lark.getStreamBlock(self._stream,1)
        self.data = data[0][0]
        self._data = None
        self.ncam = int(self.lark.get("ncam"))
        self.makeNPlots(self.ncam)
        if len(self.data.shape)==1:
            self.reshape = 1
            self.npxlx = [int(n) for n in self.lark.get("npxlx")]
            self.npxly = [int(n) for n in self.lark.get("npxly")]
        else:
            self.reshape = 0
        self.update_plot()
        self.placePlots()

    def update_plot(self):
        if self._data is not None:
            # self.data = self.encoder.decode(self._data)[0]
            self.data = self._data[0]
            self._data = None
        if self.data is not None:
            if self.reshape:
                camdata = []
                for i in range(self.ncam):
                    start = 0 if i==0 else self.npxlx[i-1]*self.npxly[i-1]
                    data = self.data[start:start+self.npxlx[i]*self.npxly[i]].T
                    data.shape = self.npxly[i],self.npxlx[i]
                    camdata.append(data.T)
                self.plot(*camdata)
            else:
                self.plot(self.data)
        QtC.QCoreApplication.processEvents()

class WfsMain(SubTabWidget):
    def __init__(self,larkconfig,parent=None,**kwargs):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig
        self.menu.setTitle("WFS")

        slopes1d = WfsSlopes1D(self.larkconfig, self)
        slopes2d = WfsSlopes2D(self.larkconfig, self)
        raw = WfsImages(self.larkconfig, self, cal=0)
        cal = WfsImages(self.larkconfig, self, cal=1)
        flux1d = WfsFlux1D(self.larkconfig, self)
        flux2d = WfsFlux2D(self.larkconfig, self)

        self.addWidget(slopes1d, "1D Slopes")
        self.addWidget(slopes2d, "2D Slopes")
        self.addWidget(raw, "Raw Images")
        self.addWidget(cal, "Calibrated")
        self.addWidget(flux1d, "1D Flux")
        self.addWidget(flux2d, "2D Flux")

def main():
    larkconfig = LarkConfig
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
    win = MainLarkWindow(larkconfig, WfsMain)
    win.setWindowTitle("WFS")
    win.on_connect()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
