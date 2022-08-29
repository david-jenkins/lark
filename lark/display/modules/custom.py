import lark
from PyQt5 import QtWidgets as QtW
from lark.display.wfs import WfsImages
from lark.display.widgets.main_base import MainTabWidget
from lark.display.widgets.plotting import Plotter, ScrollingPlot
import numpy


class CalibratedFullFrame(WfsImages):
    def __init__(self, larkconfig, parent=None, cal=0):
        super().__init__(larkconfig, parent, cal)
        
    def update_plot(self):
        if self._data is not None:
            data = self._data[0].astype(numpy.float32)
            if self.calmult is not None:
                data*=self.calmult
            if self.calsub is not None:
                data-=self.calsub
            if self.calthr is not None:
                data[numpy.where(data<self.calthr)] = 0
            self._data = (data,*self._data[1:])
        return super().update_plot()
    
    def showEvent(self, event):
        self.calsub = self.lark.get("calsub")
        self.calmult = self.lark.get("calmult")
        self.calthr = self.lark.get("calthr")
        return super().showEvent(event)
        
class ScrollingMedianFlux(ScrollingPlot):
    def __init__(self, larkconfig: lark.LarkConfig, parent=None):
        super().__init__(larkconfig, parent, streams=["rtcFluxBuf"])
        
    def update_plot(self):
        if self._data is not None:
            self.plot(numpy.median(self._data[0]))

class CustomMain(MainTabWidget):
    def __init__(self,larkconfig,parent=None):
        super().__init__(parent=parent)
        self.larkconfig = larkconfig

        self.menu = QtW.QMenu("Custom",self)
        self.cal_ff = CalibratedFullFrame(larkconfig)
        self.flux_scroll = ScrollingMedianFlux(larkconfig)

        self.addWidget(self.cal_ff,"Calibrated")
        self.addWidget(self.flux_scroll,"FLux")
