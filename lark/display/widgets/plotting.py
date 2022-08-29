
from time import perf_counter
from typing import Any
import PyQt5
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG
from pyqtgraph import PlotItem, PlotDataItem, ViewBox, ImageItem, ImageView, GraphicsLayoutWidget, ColorBarItem
import pyqtgraph as pg

import lark
import lark.display
from .toolbar import PlotToolbar
from ...rpyclib.interface import BgServer
from ...interface import ControlClient
import numpy

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

colours = ["b","r","k","g","o"]

FRAMERATE = 10
CB_DEC = 9
BG_INTERVAL = 0.01

class _GraphicsLayoutWidget(GraphicsLayoutWidget):
    sigMouseMove = QtC.pyqtSignal(int,int,object)
    def __init__(self,parent=None):
        super().__init__(parent=parent)

class Plot1D(_GraphicsLayoutWidget):
    def __init__(self,parent=None):
        super().__init__(parent=parent)

        self.plotitem = PlotItem()
        self.plots = []
        self.plots.append(PlotDataItem(pen=pg.mkPen(colours[len(self.plots)%2])))
        self.plotitem.addItem(self.plots[0])
        self.addItem(self.plotitem)
        self.viewbox: ViewBox = self.plots[0].getViewBox()
        self.viewbox.setMenuEnabled(False)
        self.viewbox.disableAutoRange(ViewBox.YAxis)
        self.setMouseTracking(True)
        self.installEventFilter(self)
        self.viewport().installEventFilter(self)
        self.x_data = None

    def eventFilter(self, obj:Any, event:Any) -> bool:
        if obj is self and event.type() == QtC.QEvent.MouseButtonPress:
            pos = event.pos()
            print(pos)
            mousePoint = self.viewbox.mapSceneToView(pos)
            print(mousePoint.x(),mousePoint.y())
        elif event.type() == QtC.QEvent.MouseButtonDblClick and obj is self.viewport():
            self.viewbox.autoRange()
        return super().eventFilter(obj, event)

    def plot(self,*data,autoLevels=False,levels=None):
        if len(data) != len(self.plots):
            raise ValueError("Need data for each image")
        if levels is not None:
            self.viewbox.setRange(yRange=levels)
        if self.x_data is None:
            for i,plot in enumerate(self.plots):
                plot.setData(data[i])#,autoLevels=autoscale,levels=scale)
        else:
            for i,plot in enumerate(self.plots):
                plot.setData(self.x_data[i],data[i])#,autoLevels=autoscale,levels=scale)

    def makeNPlots(self,N=1):
        Nplot = len(self.plots)
        if N==Nplot:
            return
        elif N<Nplot:
            for i in range(Nplot-N):
                self.viewbox.removeItem(self.plots.pop())
        elif N>Nplot:
            for i in range(N-Nplot):
                self.plots.append(PlotDataItem(pen=pg.mkPen(colours[len(self.plots)%2])))
                self.viewbox.addItem(self.plots[-1])
        self.x_data = None

    def placePlots(self,spacing=10):
        self.x_data = []
        l1 = len(self.plots[0].getData()[1])
        self.x_data.append(numpy.arange(0,l1,1))
        cuml = l1+spacing
        for i in range(1,len(self.plots)):
            # l1 = len(self.plots[i-1].getData()[1])
            l2 = len(self.plots[i].getData()[1])
            self.x_data.append(numpy.arange(cuml,cuml+l2,1))
            cuml+=(l2+spacing)

    def _addItem(self, item):
        self.viewbox.addItem(item)

    def _removeItem(self, item):
        self.viewbox.removeItem(item)

    def reset(self):
        self.x_data = None

class Plot2D(_GraphicsLayoutWidget):
    def __init__(self,parent=None):
        super().__init__(parent=parent)

        self.viewbox = ViewBox()
        self.viewbox.setAspectLocked(True)
        self.addItem(self.viewbox)
        self.viewbox.setMenuEnabled(False)
        # self.colorbar = ColorBarItem(
        #     values = (0, 30_000),
        #     colorMap='CET-L4',
        #     label='horizontal color bar',
        #     limits = (0, None),
        #     rounding=1000,
        #     orientation = 'h',
        #     pen='#8888FF', hoverPen='#EEEEFF', hoverBrush='#EEEEFF80'
        # )
        cmap = pg.colormap.get("CET-L1")
        self.colorbar = ColorBarItem(
            values = (0, 1000),
            limits = (-5000, 5000), # start with full range...
            rounding= 1,
            width = 10,
            colorMap=cmap )
        self.addItem(self.colorbar)
        
        self.images = []
        self._addImage()
        
        self.setMouseTracking(True)
        self.installEventFilter(self)
        self.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self and event.type() == QtC.QEvent.MouseButtonPress:
            pos = event.pos()
            print(pos)
            mousePoint = self.viewbox.mapSceneToView(pos)
            print(mousePoint.x(),mousePoint.y())
        elif event.type() == QtC.QEvent.MouseButtonDblClick and obj is self.viewport():
            self.viewbox.autoRange()
        elif event.type() == QtC.QEvent.MouseMove and obj is self.viewport():
            self.mousemove(event)
        elif event.type() == QtC.QEvent.Leave and obj is self.viewport():
            self.sigMouseMove.emit(0,0,None)
        return super().eventFilter(obj, event)

    def mousemove(self,event):
        pos = event.pos()
        for image,data in self.images:
            if image.sceneBoundingRect().contains(pos):
                mousePoint = self.viewbox.mapSceneToView(pos)
                px = int(mousePoint.x())
                py = int(mousePoint.y())
                ipos = image.pos()
                px = int(px-ipos[0])
                py = int(py-ipos[1])
                if data is not None:
                    self.sigMouseMove.emit(px,py,data[px,py])

    def mousefocusout(self, event):
        print("mouse focus out")

    def plot(self, *data, autoLevels=1, levels=None):
        if len(data) != len(self.images):
            raise ValueError("Need data for each image")
        for i,image in enumerate(self.images):
            if levels is None:
                levels = self.colorbar.levels()
            else:
                self.colorbar.setLevels(levels)
            image[1] = data[i]
            image[0].setImage(data[i],autoLevels=False,levels=levels)

    def makeNPlots(self,N=1):
        Nimg = len(self.images)
        if N==Nimg:
            return
        elif N<Nimg:
            for i in range(Nimg-N):
                # self.viewbox.removeItem(self.images.pop()[0])
                self._removeImage()
        elif N>Nimg:
            for i in range(N-Nimg):
                # self.images.append([ImageItem(),None])
                # self.viewbox.addItem(self.images[-1][0])
                self._addImage()
            # self.images[-1].setPos(10,10)
            # print(self.images[-1].width(),self.images[-1].height())

    def placePlots(self,spacing=10):
        for i in range(1,len(self.images)):
            self.images[i][0].setPos(self.images[i-1][0].pos()[0]+self.images[i-1][0].width()+spacing,0)

    def _addItem(self, item):
        self.viewbox.addItem(item)

    def _removeItem(self, item):
        self.viewbox.removeItem(item)
        
    def _addImage(self):
        im = ImageItem()
        self.images.append([im,None])
        self.viewbox.addItem(im)
        self.colorbar.setImageItem([im[0] for im in self.images])
        
    def _removeImage(self):
        self.viewbox.removeItem(self.images.pop()[0])

    def reset(self):
        pass

class PlotText(QtW.QTextEdit):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.setReadOnly(True)
        self.viewbox = None
        self.installEventFilter(self)
        self.document().setMaximumBlockCount(1000)

    def eventFilter(self, obj, event):
        if obj is self and event.type() == QtC.QEvent.MouseButtonPress:
            pos = event.pos()
            print(pos)
            mousePoint = self.viewbox.mapSceneToView(pos)
            print(mousePoint.x(),mousePoint.y())
        return super().eventFilter(obj, event)

    def plot(self, data:str, clear=1):
        if clear:
            self.setPlainText(data)
        else:
            self.moveCursor(QtG.QTextCursor.End)
            self.insertPlainText(data)
            self.moveCursor(QtG.QTextCursor.End)

    def reset(self):
        pass

class PlotImage(ImageView):
    sigMouseMove = QtC.pyqtSignal(int,int,object)
    def __init__(self,parent=None):
        super().__init__(parent=parent)

        self.viewbox = self.getView()
        self.images = []
        self.images.append([self.getImageItem(),None])
        self.viewbox.setAspectLocked(True)
        self.viewbox.setMenuEnabled(False)
        self.setMouseTracking(True)
        self.installEventFilter(self)
        self.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self and event.type() == QtC.QEvent.MouseButtonPress:
            pos = event.pos()
            print(pos)
            mousePoint = self.viewbox.mapSceneToView(pos)
            print(mousePoint.x(),mousePoint.y())
        elif event.type() == QtC.QEvent.MouseButtonDblClick and obj is self.viewport():
            self.viewbox.autoRange()
        elif event.type() == QtC.QEvent.MouseMove and obj is self.viewport():
            self.mousemove(event)
        elif event.type() == QtC.QEvent.Leave and obj is self.viewport():
            self.sigMouseMove.emit(0,0,None)
        return super().eventFilter(obj, event)

    def viewport(self):
        return self.ui.graphicsView.viewport()

    def mousemove(self,event):
        pos = event.pos()
        for image,data in self.images:
            if image.sceneBoundingRect().contains(pos):
                mousePoint = self.viewbox.mapSceneToView(pos)
                px = int(mousePoint.x())
                py = int(mousePoint.y())
                ipos = image.pos()
                px = int(px-ipos[0])
                py = int(py-ipos[1])
                if data is not None:
                    self.sigMouseMove.emit(px,py,data[px,py])

    def mousefocusout(self, event):
        print("mouse focus out")

    def plot(self, *data, autoLevels=1, levels=None):
        if len(data) != len(self.images):
            raise ValueError("Need data for each image")
        for i,image in enumerate(self.images):
            image[1] = data[i]
            image[0].setImage(data[i],autoLevels=autoLevels,levels=levels)

    def makeNPlots(self,N=1):
        Nimg = len(self.images)
        if N==Nimg:
            return
        elif N<Nimg:
            for i in range(Nimg-N):
                self.viewbox.removeItem(self.images.pop()[0])
        elif N>Nimg:
            for i in range(N-Nimg):
                self.images.append([ImageItem(),None])
                self.viewbox.addItem(self.images[-1][0])
            # self.images[-1].setPos(10,10)
            # print(self.images[-1].width(),self.images[-1].height())

    def placePlots(self,spacing=10):
        for i in range(1,len(self.images)):
            self.images[i][0].setPos(self.images[i-1][0].pos()[0]+self.images[i-1][0].width()+spacing,0)

    def _addItem(self, item):
        self.viewbox.addItem(item)

    def _removeItem(self, item):
        self.viewbox.removeItem(item)

    def reset(self):
        pass

PlotTypes = {
    "1D": Plot1D,
    "2D": Plot2D,
    "text": PlotText,
    "image": PlotImage
}

class Plotter(QtW.QWidget):
    def __init__(self,larkconfig:lark.LarkConfig,parent=None,plottype="2D",streams=None):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig

        self.menu = None

        if plottype not in PlotTypes:
            raise ValueError("plottype is invalid")

        # define layout
        self.mainlayout = QtW.QHBoxLayout()
        self.vlay = QtW.QVBoxLayout()

        self.update_timer = QtC.QTimer()
        self.update_timer.timeout.connect(self.try_update_plot)

        self.framerate = FRAMERATE
        self.bg_interval = BG_INTERVAL
        self.dec = CB_DEC
        
        self.streams = streams[0] if streams is not None else None
        self.lark = None
        self.bgsrv = None
        self.ncam = 1
        self.reshape = 1
        self._data = None
        self.data = None
        self.scale_lim = (0,0)
        self.cb_id = None

        # define other widgets
        self.plotter = PlotTypes[plottype](parent=self)
        if plottype in ["1D","2D","image"]:
            self.toolbar = PlotToolbar(self.plotter,self.vlay,parent=self)
            
        self.plotscale_button = None
        self.autoscale_button = None
        if plottype in ["1D","2D"]:
            custom_layout = QtW.QHBoxLayout()
            self.plotscale_button = QtW.QPushButton("Use Plot Scaling")
            self.plotscale_button.setCheckable(True)
            self.autoscale_button = QtW.QPushButton("Use Auto Scaling")
            self.autoscale_button.setCheckable(True)
            custom_layout.addWidget(self.plotscale_button)
            custom_layout.addWidget(self.autoscale_button)
            self.toolbar.addCustomLayout(custom_layout)

        # populate layout
        self.vlay.addWidget(self.plotter)
        if plottype in ["1D","2D","image"]:
            self.vlay.addWidget(self.toolbar)
        self.mainlayout.addLayout(self.vlay)

        # set layout
        self.setLayout(self.mainlayout)

    def on_connect(self):
        self._data = None
        self.lark = self.larkconfig.getlark(unique=True)

    def update_plot(self):
        pass
    
    def try_update_plot(self):
        try:
            self.update_plot()
        except:
            self.on_connect()

    def on_disconnect(self):
        if self.lark is not None:
            self.lark.conn.close()
            self.lark = None

    def plot_callback(self, data):
        self._data = data

    def makeNPlots(self,N=1):
        self.plotter.makeNPlots(N)

    def placePlots(self,spacing=10):
        self.plotter.placePlots(spacing)

    def plot(self,*args,**kwargs):
        if self.toolbar.freeze:
            return
        this_min = 1000000
        this_max = -1000000
        if self.autoscale_button is not None and self.autoscale_button.isChecked():
            for d in args:
                this_min = min(this_min,numpy.nanmin(d))
                this_max = max(this_max,numpy.nanmax(d))
            self.plotter.plot(*args,**kwargs,autoLevels=False,levels=(this_min,this_max))
            return
        if self.plotscale_button is None or not self.plotscale_button.isChecked():
            if self.toolbar.autoscale:
                for d in args:
                    this_min = min(this_min,numpy.nanmin(d))
                    this_max = max(this_max,numpy.nanmax(d))
                self.scale_lim = min(this_min,self.scale_lim[0]),max(this_max,self.scale_lim[1])
                scale = self.scale_lim
                self.toolbar.setScaleRange(self.scale_lim)
            else:
                self.scale_lim = (0,0)
                scale = self.toolbar.scale
            if scale==(0,0): scale=(-1.,1.)
            self.plotter.plot(*args,**kwargs,autoLevels=False,levels=scale)
        else:
            self.plotter.plot(*args,**kwargs,autoLevels=False)
        

    def reset(self):
        self.plotter.reset()
        self.toolbar.reset()

    def showEvent(self, event):
        print("showing Plotter")
        if self.toolbar.isStuck():
            self.toolbar.show()
        if self.lark is not None:
            self._startUpdates()
            self.update_timer.start(1000//self.framerate)
        super().showEvent(event)

    def _startUpdates(self):
        if self.lark is not None and self.streams is not None:
            print("starting callbacks")
            self.bgsrv = BgServer(self.lark.conn,self.bg_interval)
            self.cb_id = self.lark.addCallback(self.streams,self.plot_callback,self.dec,0.)

    def hideEvent(self, event):
        print("hiding Plotter")
        if self.toolbar.isStuck():
            self.toolbar.hide()
        self._stopUpdates()
        self.update_timer.stop()
        super().hideEvent(event)

    def _stopUpdates(self):
        if self.lark is not None and self.streams is not None:
            if self.cb_id is not None:
                self.lark.removeCallback(self.streams,self.cb_id)
                self.bgsrv.stop()
        self.cb_id = None

    def closeEvent(self, event):
        self._data = None
        if self.bgsrv is not None:
            self.bgsrv.stop()
        if self.lark is not None:
            self.on_disconnect()
        super().closeEvent(event)
        
        
class ScrollingPlot(Plotter):
    def __init__(self, larkconfig: lark.LarkConfig, parent=None, streams=None):
        self.chunkSize = 1000
        self.maxChunks = 100
        self.curves = []
        self.scale = (1000000,-1000000)
        self.plot_data = numpy.empty((self.chunkSize+1,2))
        super().__init__(larkconfig, parent, plottype="1D", streams=streams)
        self.plotter.plotitem.setXRange(-10, 0)
        self.startTime = None
        self.cnt = 0
        
    def plot(self,*args,**kwargs):
        if self.toolbar.freeze:
            return
        this_min = 1000000
        this_max = -1000000
        if self.plotscale_button is None or not self.plotscale_button.isChecked():
            if self.toolbar.autoscale:
                for d in args:
                    this_min = min(this_min,numpy.nanmin(d))
                    this_max = max(this_max,numpy.nanmax(d))
                self.scale_lim = min(this_min,self.scale_lim[0]),max(this_max,self.scale_lim[1])
                scale = self.scale_lim
                self.toolbar.setScaleRange(self.scale_lim)
            else:
                self.scale_lim = (0,0)
                scale = self.toolbar.scale
            print(scale)
            if scale==(0,0): scale=(-1.,1.)
            self.plotter.plot(*args,**kwargs,autoLevels=False,levels=scale)
        else:
            self.plotter.plot(*args,**kwargs)
        
    def plot(self,new_value,*args,**kwargs):
        now = perf_counter()
        for c in self.curves:
            c.setPos(-(now-self.startTime), 0)
        if self.plotscale_button is None or not self.plotscale_button.isChecked():
            if self.toolbar.autoscale:
                self.scale = (min(self.scale[0],new_value),max(self.scale[1],new_value))
                spread = abs((self.scale[1]-self.scale[0]))/2
                scale = self.scale[0]-spread,self.scale[1]+spread
                self.plotter.plotitem.setYRange(*scale)
                self.toolbar.setScaleRange(scale)
            else:
                self.scale = (1000000,-1000000)
                scale = self.toolbar.scale
                self.plotter.plotitem.setYRange(*scale)
        i = self.cnt % self.chunkSize
        if i == 0:
            curve = self.plotter.plotitem.plot(pen=pg.mkPen("red", width=2))
            self.curves.append(curve)
            self.plot_data = numpy.empty((self.chunkSize+1,2))        
            self.plot_data[0] = now - self.startTime, new_value
            while len(self.curves) > self.maxChunks:
                c = self.curves.pop(0)
                self.plotter.plotitem.removeItem(c)
        else:
            curve = self.curves[-1]
            self.plot_data[i,0] = now - self.startTime
            self.plot_data[i,1] = new_value
        curve.setData(x=self.plot_data[:i+1, 0], y=self.plot_data[:i+1, 1])
        self.cnt += 1
            
    def showEvent(self, event):
        if self.startTime is None:
            self.startTime = perf_counter()
        # self.cnt = 0
        # while len(self.curves) > 0:
        #     c = self.curves.pop()
        #     self.plotter.plotitem.removeItem(c)
        # self.plotter.plotitem.clear()
        self.cnt = 0
        # self.scale = (1000000,-1000000)
        return super().showEvent(event)
        
    def hideEvent(self, event):
        # while len(self.curves) > 0:
        #     c = self.curves.pop()
        #     self.plotter.plotitem.removeItem(c)
        # self.plotter.plotitem.clear()
        return super().hideEvent(event)

if __name__ == "__main__":
    import sys
    from .main_base import TabWidget

    class PlottingMain(TabWidget):
        def __init__(self,parent=None):
            super().__init__(parent=parent)
            self.menu = QtW.QMenu("Plotting",self)
            self.plot1D = Plotter(self, "1D")
            self.plot2D = Plotter(self, "2D")
            self.plotImage = Plotter(self, "image")
            self.plotText = Plotter(self, "text")

            self.addTab(self.plot1D, "1D")
            self.addTab(self.plot2D, "2D")
            self.addTab(self.plotImage, "Image")
            self.addTab(self.plotText, "Text")


    class PlottingWindow(QtW.QMainWindow):
        def __init__(self):
            super().__init__()
            menu = self.menuBar()
            self.filemenu = QtW.QMenu("&File")
            self.quitAction = QtW.QAction('&Quit')
            self.filemenu.addAction(self.quitAction)
            self.quitAction.triggered.connect(self.close)

            self.main = PlottingMain(self)
            menu.addMenu(self.filemenu)
            menu.addMenu(self.main.menu)
            self.setMenuBar(menu)
            self.setCentralWidget(self.main)
            self.displays = []

    def main():
        app = QtW.QApplication(sys.argv)
        win = PlottingWindow()
        win.show()
        sys.exit(app.exec_())

    main()
