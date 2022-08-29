
from errno import E2BIG
from matplotlib.pyplot import draw
import numpy
import PyQt5
import pyqtgraph as pg

from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG

def getPyQtColour(colour):
    valid_col_words = {'white':(255,255,255),'w':(255,255,255),'black':(0,0,0),'k':(0,0,0),'red':(255,0,0),'r':(255,0,0),'blue':(0,0,255),'b':(0,0,255),'green':(0,255,0),'g':(0,255,0)}#,'yellow','purple','orange'}
    if type(colour) is str:
        return QtG.QColor(*valid_col_words.get(colour,(255,255,255)))
    elif type(colour) is tuple:
        return QtG.QColor(*colour)

class GridItem(pg.GraphicsObject):
    def __init__(self, start, pitch, end, colour):
        super().__init__()
        ## pre-computing a QPicture object allows paint() to run much more quickly,
        ## rather than re-drawing the shapes every time.
        self.picture = QtG.QPicture()
        p = QtG.QPainter(self.picture)
        x_points = numpy.arange(start[0],end[0],pitch[0])
        y_points = numpy.arange(start[1],end[1],pitch[1])
        colour = getPyQtColour(colour)
        p.setPen(pg.mkPen(colour))
        for x in x_points[1:]:
            p.drawLine(QtC.QPointF(x,start[1]), QtC.QPointF(x,end[1]))
        for y in y_points[1:]:
            p.drawLine(QtC.QPointF(start[0],y), QtC.QPointF(end[0],y))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtC.QRectF(self.picture.boundingRect())

class LineItem(pg.GraphicsObject):
    def __init__(self, start, end, colour, size):
        super().__init__()
        self.update(start, end, colour, size)
        
    def update(self, start, end, colour, size):
        self.picture = QtG.QPicture()
        p = QtG.QPainter(self.picture)
        colour = getPyQtColour(colour)
        p.setPen(pg.mkPen(colour,width=size))
        p.drawLine(QtC.QPointF(start[0],start[1]), QtC.QPointF(end[0],end[1]))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtC.QRectF(self.picture.boundingRect())
        
class CircleItem(pg.GraphicsObject):
    def __init__(self, centre, radius, colour, size, draw_centre=0):
        super().__init__()
        self.update(centre, radius, colour, size, draw_centre)
    
    def update(self, centre, radius, colour, size, draw_centre=0):
        self.picture = QtG.QPicture()
        p = QtG.QPainter(self.picture)
        colour = getPyQtColour(colour)
        p.setPen(pg.mkPen(colour,width=size))
        if not isinstance(radius,(list,tuple)):
            radius = (radius,radius)
        p.drawEllipse(QtC.QPointF(centre[0],centre[1]), radius[0], radius[1])
        width = radius[0]/10.
        if draw_centre:
            p.drawLine(QtC.QPointF(centre[0]-width/2,centre[1]), QtC.QPointF(centre[0]+width/2,centre[1]))
            p.drawLine(QtC.QPointF(centre[0],centre[1]-width/2), QtC.QPointF(centre[0],centre[1]+width/2))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtC.QRectF(self.picture.boundingRect())

class CrossItem(pg.GraphicsObject):
    def __init__(self, start, width, colour, size):
        super().__init__()
        self.picture = QtG.QPicture()
        p = QtG.QPainter(self.picture)
        colour = getPyQtColour(colour)
        p.setPen(pg.mkPen(colour,width=size))
        p.drawLine(QtC.QPointF(start[0]-width/2,start[1]), QtC.QPointF(start[0]+width/2,start[1]))
        p.drawLine(QtC.QPointF(start[0],start[1]-width/2), QtC.QPointF(start[0],start[1]+width/2))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtC.QRectF(self.picture.boundingRect())

class ArrowItem(pg.GraphicsObject):
    def __init__(self, start, end, colour, width, size, filled=0):
        super().__init__()
        ## pre-computing a QPicture object allows paint() to run much more quickly,
        ## rather than re-drawing the shapes every time.
        self.picture = QtG.QPicture()
        p = QtG.QPainter(self.picture)
        colour = getPyQtColour(colour)
        p.setPen(pg.mkPen(colour,width=size))
        p.drawLine(QtC.QPointF(start[0],start[1]), QtC.QPointF(end[0],end[1]))
        size = width
        hl = size
        hw = size/2.
        linetheta = numpy.arctan2(end[1]-start[1], end[0]-start[0])
        theta = numpy.arctan2(hw, hl)
        length = numpy.sqrt(hl**2 + hw**2)
        angle = linetheta - theta# - numpy.pi
        x1 = end[0] - length*numpy.cos(angle)
        y1 = end[1] - length*numpy.sin(angle)
        angle = linetheta + theta# - numpy.pi
        x2 = end[0] - length*numpy.cos(angle)
        y2 = end[1] - length*numpy.sin(angle)
        # col=args.get("headColour",args.get("ec",col))
        #gc.set_foreground(col)
        if filled:
            points = QtG.QPolygonF([
                QtC.QPointF(end[0],end[1]),
                QtC.QPointF(x1,y1),
                QtC.QPointF(x2,y2),
            ])
            p.setBrush(pg.mkBrush(colour))
            p.drawPolygon(points)
        else:
            p.setPen(pg.mkPen(colour))
            p.drawLine(QtC.QPointF(end[0],end[1]), QtC.QPointF(x1,y1))
            p.drawLine(QtC.QPointF(end[0],end[1]), QtC.QPointF(x2,y2))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtC.QRectF(self.picture.boundingRect())

class OverlayWin(QtW.QWidget):
    def __init__(self, plotter, parent=None):
        super().__init__(parent=parent)

        # set window properties
        self.setWindowFlags(QtC.Qt.Window)
        self.setWindowTitle("larkplot overlays")
        self.move(QtG.QCursor().pos())  # put the window at the cursor

        # set parameters
        self.plotter = plotter # the plotter must have a viewbox attribute
        self.func_coords = {
            "hvlinepos":None,
            "crosspos":None,
            "linestart":None,
            "linestop":None,
            "gridstart":None,
            "gridstop":None,
            "gridpitch":None,
            "textpos":None,
            "arrowstart":None,
            "arrowstop":None,
        }

        self.coord_name = None
        self.clickback = None
        self.clickpoints = []

        # define layout
        self.vbox = QtW.QVBoxLayout()
        self.hbox1 = QtW.QHBoxLayout()
        self.hbox2 = QtW.QHBoxLayout()
        self.hbox3 = QtW.QHBoxLayout()
        self.hbox4 = QtW.QHBoxLayout()
        self.hbox5 = QtW.QHBoxLayout()
        self.hbox6 = QtW.QHBoxLayout()
        self.vboxOverlay = QtW.QVBoxLayout()

        # define buttons
        self.hvlinebutton = QtW.QPushButton("Add H/V line")
        self.crossbutton = QtW.QPushButton("Add cross")
        self.linebutton = QtW.QPushButton("Add line")
        self.gridbutton = QtW.QPushButton("Add grid")
        self.textButton = QtW.QPushButton("Add text")
        self.arrowButton = QtW.QPushButton("Add arrow")

        # define checkboxes
        self.horCheck = QtW.QCheckBox("Horizontal")
        self.arrowsolidCheck=QtW.QCheckBox("Solid")
        self.arrowsolidCheck.setToolTip("Solid head?")

        # define lineedits
        self.hvlinecoordEdit = QtW.QLineEdit()
        self.hvlinecoordEdit.setMinimumWidth(64)
        self.hvlinecoordEdit.setToolTip("Coordinate for the line - if empty, can be specified with a click")
        self.hvlinecolourEdit = QtW.QLineEdit()
        self.hvlinecolourEdit.setMinimumWidth(64)
        self.hvlinecolourEdit.setToolTip("Line colour")
        self.hvlinecolourEdit.setText("white")
        self.crosscoordEdit=QtW.QLineEdit()
        self.crosscoordEdit.setMinimumWidth(64)
        self.crosscoordEdit.setToolTip("Coordinates of centre, x,y (blank to select with mouse)")
        self.crosscolourEdit=QtW.QLineEdit()
        self.crosscolourEdit.setMinimumWidth(64)
        self.crosscolourEdit.setToolTip("Line colour")
        self.crosscolourEdit.setText("white")
        self.linecoord1Edit=QtW.QLineEdit()
        self.linecoord1Edit.setMinimumWidth(64)
        self.linecoord1Edit.setToolTip("Coordinates of line start, x,y (blank to select with mouse)")
        self.linecoord2Edit=QtW.QLineEdit()
        self.linecoord2Edit.setMinimumWidth(64)
        self.linecoord2Edit.setToolTip("Coordinates of line end, x,y (blank to select with mouse)")
        self.linecolourEdit=QtW.QLineEdit()
        self.linecolourEdit.setMinimumWidth(64)
        self.linecolourEdit.setToolTip("Line colour")
        self.linecolourEdit.setText("white")
        self.gridcoord1Edit=QtW.QLineEdit()
        self.gridcoord1Edit.setMinimumWidth(64)
        self.gridcoord1Edit.setToolTip("Coordinates of grid start, x,y (blank to select with mouse - first click)")
        self.gridcoord2Edit=QtW.QLineEdit()
        self.gridcoord2Edit.setMinimumWidth(64)
        self.gridcoord2Edit.setToolTip("Coordinates of grid end, x,y (blank to select with mouse - second click)")
        self.gridpitchEdit=QtW.QLineEdit()
        self.gridpitchEdit.setMinimumWidth(64)
        self.gridpitchEdit.setToolTip("Grid pitch, x,y (blank to select with mouse - third click)")
        self.gridcolourEdit=QtW.QLineEdit()
        self.gridcolourEdit.setMinimumWidth(64)
        self.gridcolourEdit.setToolTip("Line colour")
        self.gridcolourEdit.setText("white")
        self.textEdit=QtW.QLineEdit()
        self.textEdit.setToolTip("Text to be added")
        self.textcoordEdit=QtW.QLineEdit()
        self.textcoordEdit.setMinimumWidth(64)
        self.textcoordEdit.setToolTip("Coordinates of text, x,y (blank to select with mouse)")
        self.textcoordEdit.setText("")
        self.textcolourEdit=QtW.QLineEdit()
        self.textcolourEdit.setMinimumWidth(64)
        self.textcolourEdit.setToolTip("Text colour")
        self.textcolourEdit.setText("white")
        self.textfontEdit=QtW.QLineEdit()
        self.textfontEdit.setMinimumWidth(64)
        self.textfontEdit.setToolTip("Font description")
        self.textfontEdit.setText("10")
        self.arrowcoord1Edit=QtW.QLineEdit()
        self.arrowcoord1Edit.setMinimumWidth(64)
        self.arrowcoord1Edit.setToolTip("Coordinates of line start, x,y (blank to select with mouse)")
        self.arrowcoord2Edit=QtW.QLineEdit()
        self.arrowcoord2Edit.setMinimumWidth(64)
        self.arrowcoord2Edit.setToolTip("Coordinates of line end (arrow head), x,y (blank to select with mouse)")
        self.arrowcolourEdit=QtW.QLineEdit()
        self.arrowcolourEdit.setMinimumWidth(64)
        self.arrowcolourEdit.setToolTip("Line colour")
        self.arrowcolourEdit.setText("white")

        # define spinboxes
        self.hvlinewidthSpin=QtW.QSpinBox()
        self.hvlinewidthSpin.setValue(2)
        self.hvlinewidthSpin.setMinimumWidth(64)
        self.hvlinewidthSpin.setToolTip("Line width")
        self.hvlinewidthSpin.setMaximum(1000000)
        self.hvlinewidthSpin.setMinimum(0)
        self.hvlinewidthSpin.setSingleStep(1)
        self.crosswidthSpin=QtW.QSpinBox()
        self.crosswidthSpin.setValue(0)
        self.crosswidthSpin.setMinimumWidth(64)
        self.crosswidthSpin.setToolTip("Cross width")
        self.crosswidthSpin.setMaximum(1000000)
        self.crosswidthSpin.setMinimum(0)
        self.crosswidthSpin.setSingleStep(1)
        self.crosswidthSpin=QtW.QSpinBox()
        self.crosswidthSpin.setValue(1)
        self.crosswidthSpin.setMinimumWidth(64)
        self.crosswidthSpin.setToolTip("Line width")
        self.crosswidthSpin.setValue(0)
        self.crosswidthSpin.setMaximum(1000000)
        self.crosswidthSpin.setMinimum(0)
        self.crosswidthSpin.setSingleStep(1)
        self.linewidthSpin=QtW.QSpinBox()
        self.linewidthSpin.setValue(0)
        self.linewidthSpin.setMinimumWidth(64)
        self.linewidthSpin.setToolTip("Line width")
        self.linewidthSpin.setValue(0)
        self.linewidthSpin.setMaximum(1000000)
        self.linewidthSpin.setMinimum(0)
        self.linewidthSpin.setSingleStep(1)
        self.arrowwidthSpin=QtW.QSpinBox()
        self.arrowwidthSpin.setValue(0)
        self.arrowwidthSpin.setMinimumWidth(64)
        self.arrowwidthSpin.setToolTip("Line width")
        self.arrowwidthSpin.setValue(0)
        self.arrowwidthSpin.setMaximum(1000000)
        self.arrowwidthSpin.setMinimum(0)
        self.arrowwidthSpin.setSingleStep(1)
        self.arrowheadSpin=QtW.QSpinBox()
        self.arrowheadSpin.setValue(3)
        self.arrowheadSpin.setMinimumWidth(64)
        self.arrowheadSpin.setToolTip("Head width")
        self.arrowheadSpin.setValue(3)
        self.arrowheadSpin.setMaximum(1000000)
        self.arrowheadSpin.setMinimum(0)
        self.arrowheadSpin.setSingleStep(1)

        #define other widgets
        self.groupbox = QtW.QWidget()
        self.groupbox.setLayout(self.vboxOverlay)
        self.scrollarea = QtW.QScrollArea()
        self.scrollarea.resize(100,100)
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setWidget(self.groupbox)

        # build layout
        self.vbox.addLayout(self.hbox1)
        self.hbox1.addWidget(self.hvlinebutton)
        self.hbox1.addWidget(self.horCheck)
        self.hbox1.addWidget(self.hvlinecoordEdit)
        self.hbox1.addWidget(self.hvlinecolourEdit)
        self.hbox1.addWidget(self.hvlinewidthSpin)

        self.vbox.addLayout(self.hbox2)
        self.hbox2.addWidget(self.crossbutton)
        self.hbox2.addWidget(self.crosscoordEdit)
        self.hbox2.addWidget(self.crosswidthSpin)
        self.hbox2.addWidget(self.crosscolourEdit)
        self.hbox2.addWidget(self.crosswidthSpin)

        self.vbox.addLayout(self.hbox3)
        self.hbox3.addWidget(self.linebutton)
        self.hbox3.addWidget(self.linecoord1Edit)
        self.hbox3.addWidget(self.linecoord2Edit)
        self.hbox3.addWidget(self.linecolourEdit)
        self.hbox3.addWidget(self.linewidthSpin)

        self.vbox.addLayout(self.hbox4)
        self.hbox4.addWidget(self.gridbutton)
        self.hbox4.addWidget(self.gridcoord1Edit)
        self.hbox4.addWidget(self.gridcoord2Edit)
        self.hbox4.addWidget(self.gridpitchEdit)
        self.hbox4.addWidget(self.gridcolourEdit)

        self.vbox.addLayout(self.hbox5)
        self.hbox5.addWidget(self.textButton)
        self.hbox5.addWidget(self.textEdit)
        self.hbox5.addWidget(self.textcoordEdit)
        self.hbox5.addWidget(self.textcolourEdit)
        self.hbox5.addWidget(self.textfontEdit)

        self.vbox.addLayout(self.hbox6)
        self.hbox6.addWidget(self.arrowButton)
        self.hbox6.addWidget(self.arrowcoord1Edit)
        self.hbox6.addWidget(self.arrowcoord2Edit)
        self.hbox6.addWidget(self.arrowcolourEdit)
        self.hbox6.addWidget(self.arrowwidthSpin)
        self.hbox6.addWidget(self.arrowheadSpin)
        self.hbox6.addWidget(self.arrowsolidCheck)

        self.vbox.addWidget(self.scrollarea)

        self.setLayout(self.vbox)

        # connect signals
        self.hvlinebutton.clicked.connect(self.addHVLine)
        self.crossbutton.clicked.connect(self.addCross)
        self.linebutton.clicked.connect(self.addLine)
        self.gridbutton.clicked.connect(self.addGrid)
        self.textButton.clicked.connect(self.addText)
        self.arrowButton.clicked.connect(self.addArrow)

    def eventFilter(self, obj, event):
        if obj is self.plotter:
            if event.type() == QtC.QEvent.MouseButtonPress:
                if event.buttons() == QtC.Qt.LeftButton:
                    self.plotter.removeEventFilter(self)
                    self.popup.close()
                    pos = event.pos()
                    mousePoint = self.plotter.viewbox.mapSceneToView(pos)
                    pos = mousePoint.x(), mousePoint.y()
                    self.func_coords[self.coord_name] = pos
                    self.clickback()
                    return True
        return super().eventFilter(obj, event)

    def getCoord(self,coord_name,clickback,clickbox,message="Click to select position"):
        if self.func_coords[coord_name] is None:
            retval = clickbox.text()
            if retval == "":
                self.coord_name = coord_name
                self.clickback = clickback
                self.popup = QtW.QMessageBox(self)
                self.popup.setText(message)
                self.popup.setStandardButtons(QtW.QMessageBox.Cancel)
                self.popup.setModal(False)
                self.popup.show()
                self.plotter.installEventFilter(self)
                return
            coord = eval(retval)
            return float(coord[0]),float(coord[1])
        else:
            return self.func_coords[coord_name]

    def showClick(self,pos):
        c = CrossItem(pos,1,'r',1)
        self.clickpoints.append(c)
        self.plotter._addItem(c)

    def removeClicks(self):
        while len(self.clickpoints) != 0:
            c = self.clickpoints.pop()
            self.plotter._removeItem(c)

    def addHVLine(self):
        c = self.horCheck.isChecked()

        e = self.getCoord("hvlinepos",self.addHVLine,self.hvlinecoordEdit)
        if e is None:
            return
        self.func_coords["hvlinepos"] = None

        e2 = self.hvlinecolourEdit.text()
        s = self.hvlinewidthSpin.value()
        print("hvline",(c,e,e2,s))
        p = pg.mkPen(color=e2,width=s)
        l = pg.InfiniteLine(pos=e,angle=0 if c else 90,pen=p)
        self.plotter._addItem(l)

        b=QtW.QPushButton(f"{'H' if c else 'V'}Line at {int(e[0])},{int(e[1])}")
        b.clicked.connect(self.removeOverlay)
        b.item = l
        b.setToolTip("Click to remove this overlay")
        self.vboxOverlay.addWidget(b)
        b.show()
        # self.parent.addOverlay("hvline",(c,e,e2,s))

    def addCross(self):

        e = self.getCoord("crosspos",self.addCross,self.crosscoordEdit)
        if e is None:
            return
        self.func_coords["crosspos"] = None

        s = self.crosswidthSpin.value()
        e2 = self.crosscolourEdit.text()
        s2 = self.crosswidthSpin.value()

        print("cross",(e,s,e2,s2))
        c = CrossItem(e,s,e2,1)
        self.plotter._addItem(c)

        b=QtW.QPushButton(f"Cross at {int(e[0])},{int(e[1])} width {s}")
        b.clicked.connect(self.removeOverlay)
        b.item = c
        b.setToolTip("Click to remove this overlay")
        self.vboxOverlay.addWidget(b)
        b.show()
        # self.parent.addOverlay("cross",(e,s,e2,s2))

    def addLine(self):

        e1 = self.getCoord("linestart",self.addLine,self.linecoord1Edit)
        if e1 is None:
            return

        self.showClick(e1)

        e2 = self.getCoord("linestop",self.addLine,self.linecoord2Edit)
        if e2 is None:
            return

        self.removeClicks()

        self.func_coords["linestart"] = None
        self.func_coords["linestop"] = None

        e3 = self.linecolourEdit.text()
        s2 = self.linewidthSpin.value()
        print("line",(e1,e2,e3,s2))
        l = LineItem(e1,e2,e3,s2)
        self.plotter._addItem(l)

        b=QtW.QPushButton(f"Line from {int(e1[0])},{int(e1[1])} to {int(e2[0])},{int(e2[1])}")
        b.clicked.connect(self.removeOverlay)
        b.item = l
        b.setToolTip("Click to remove this overlay")
        self.vboxOverlay.addWidget(b)
        b.show()
        # self.parent.addOverlay("line",(e1,e2,e3,s2))

    def addGrid(self):
        e1 = self.getCoord("gridstart",self.addGrid,self.gridcoord1Edit,"Click to select bottom left corner")
        if e1 is None:
            return
        self.showClick(e1)
        e2 = self.getCoord("gridstop",self.addGrid,self.gridcoord2Edit,"Click to select upper right corner")
        if e2 is None:
            return
        self.showClick(e2)
        e3 = self.getCoord("gridpitch",self.addGrid,self.gridpitchEdit,"Click to choose pitch, relative to start")
        if e3 is None:
            return

        self.removeClicks()

        self.func_coords["gridstart"] = None
        self.func_coords["gridstop"] = None
        self.func_coords["gridpitch"] = None

        e4 = self.gridcolourEdit.text()
        print("grid",(e1,e2,e3,e4))
        p = e3[0]-e1[0],e3[1]-e1[1]
        g = GridItem(e1,p,e2,e4)
        self.plotter._addItem(g)

        b=QtW.QPushButton(f"Grid from {int(e1[0])},{int(e1[1])} to {int(e2[0])},{int(e2[1])} spacing {int(p[0])},{int(p[1])}")
        b.clicked.connect(self.removeOverlay)
        b.item = g
        b.setToolTip("Click to remove this overlay")
        self.vboxOverlay.addWidget(b)
        b.show()
        # self.parent.addOverlay("grid",(e1,e2,e3,e4))

    def addText(self):
        e = self.textEdit.text()
        if e == "":
            return

        e2 = self.getCoord("textpos",self.addText,self.textcoordEdit)
        if e2 is None: return
        self.func_coords["textpos"] = None

        e3 = self.textcolourEdit.text()
        e4 = self.textfontEdit.text()

        print("text",(e,e2,e3,e4))
        ti = pg.TextItem(e,color=getPyQtColour(e3))
        fi = QtG.QFont()
        fi.setPointSize(int(e4))
        ti.setFont(fi)
        self.plotter._addItem(ti)
        ti.setPos(e2[0],e2[1])

        b = QtW.QPushButton(f"Text {e} at {int(e2[0])},{int(e2[1])}")
        b.clicked.connect(self.removeOverlay)
        b.item = ti
        b.setToolTip("Click to remove this overlay")
        self.vboxOverlay.addWidget(b)
        b.show()
        # self.parent.addOverlay("text",(e,e2,e3,e4,c))

    def addArrow(self):
        e = self.getCoord("arrowstart",self.addArrow,self.arrowcoord1Edit)
        if e is None: return
        e2 = self.getCoord("arrowstop",self.addArrow,self.arrowcoord2Edit)
        if e2 is None: return
        self.func_coords["arrowstart"] = None
        self.func_coords["arrowstop"] = None
        e3 = self.arrowcolourEdit.text()
        s2 = self.arrowwidthSpin.value()
        s3 = self.arrowheadSpin.value()
        c = self.arrowsolidCheck.isChecked()
        print("arrow",(e,e2,e3,s2,s3,c))

        a = ArrowItem(e,e2,e3,s2,s3,c)
        self.plotter._addItem(a)

        b=QtW.QPushButton(f"Arrow from {int(e[0])},{int(e[1])} to {int(e2[0])},{int(e2[1])}")
        b.clicked.connect(self.removeOverlay)
        b.item = a
        b.setToolTip("Click to remove this overlay")
        self.vboxOverlay.addWidget(b)
        b.show()
        # self.parent.addOverlay("arrow",(e,e2,e3,s2,s3,c))

    def removeOverlay(self,event):
        b = self.sender()
        self.plotter._removeItem(b.item)
        self.vboxOverlay.removeWidget(b)

class DoubleSpinBox(QtW.QDoubleSpinBox):
    def stepBy(self, step):
        value = self.value()
        super(DoubleSpinBox, self).stepBy(step)
        if self.value() != value:
            self.editingFinished.emit()

class PlotToolbar(QtW.QWidget):
    # def __init__(self,plotfn=None,label="",loadFunc=None,streamName="",parentLayout=None):
    def __init__(self, plotter, parentLayout, parent=None):
        super().__init__(parent=parent)
        parent.installEventFilter(self)

        # set parameters
        self.plotter = plotter # the plotter must have a viewbox attribute and a viewport() method
        self.plotter.sigMouseMove.connect(self.mousemove)
        self.overlayWin = None
        self.parentLayout = parentLayout
        self.unstick = 0
        self.autoscale = True
        self.scale = [0,0]
        self.freeze = 0
        self.logx = 0

        # define layout
        self.mainlayout = QtW.QVBoxLayout()
        self.topsplitlayout = QtW.QVBoxLayout()
        self.bottomsplitlayout = QtW.QFrame()
        self.hbox = QtW.QHBoxLayout()
        self.hboxB = QtW.QHBoxLayout()
        self.hbox2 = QtW.QHBoxLayout()

        # configure layout
        # self.topsplitlayout.setContentsMargins(0,0,0,0)
        # self.bottomsplitlayout.setContentsMargins(0,0,0,0)
        # self.hbox.setContentsMargins(0,0,0,0)
        # self.hboxB.setContentsMargins(0,0,0,0)
        # self.hbox2.setContentsMargins(0,0,0,0)

        # define buttons
        self.reprbutton=QtW.QPushButton("Repr")
        self.reprbutton.setToolTip("Textual representation")

        self.stickbutton=QtW.QPushButton("<")
        self.stickbutton.setCheckable(True)
        self.stickbutton.setToolTip("Move to separate window, or reparent")

        self.overlaybutton=QtW.QPushButton("Overlay")
        self.overlaybutton.setCheckable(True)
        self.overlaybutton.setToolTip("Opens the overlay window")

        # define checkboxes
        self.freezebutton=QtW.QCheckBox("Freeze")
        self.freezebutton.setToolTip("freeze display")

        self.autobutton=QtW.QCheckBox("Scaling")
        self.autobutton.setToolTip("autoscale data")
        self.autobutton=QtW.QCheckBox("Scaling")
        self.autobutton.setToolTip("autoscale data")

        self.logxbutton=QtW.QCheckBox("Logx")
        self.logxbutton.setToolTip("Logaritm of x axis for 1d plots")

        # define spinboxes
        self.scaleMinEntry=DoubleSpinBox()
        # self.scaleMinEntry.setFixedWidth(64)
        self.scaleMinEntry.setToolTip("Minimum value to clip when not autoscaling")
        self.scaleMinEntry.setEnabled(False)
        self.scaleMinEntry.setRange(-100000,100000)
        self.scaleMinEntry.setDecimals(3)

        self.scaleMaxEntry=DoubleSpinBox()
        # self.scaleMaxEntry.setFixedWidth(64)
        self.scaleMaxEntry.setToolTip("Maximum value to clip when not autoscaling")
        self.scaleMaxEntry.setEnabled(False)
        self.scaleMaxEntry.setRange(-100000,100000)
        self.scaleMaxEntry.setDecimals(3)

        self.dec_spin = QtW.QSpinBox()
        self.dec_spin.setToolTip("Change the stream decimation")

        # define labels
        self.frameWidget = QtW.QLabel()
        self.frameWidget.setAlignment(QtC.Qt.AlignLeft | QtC.Qt.AlignVCenter)

        self.frameWidget.setText("Here's the fnumber and ftime")

        self.dec_label = QtW.QLabel("Dec")

        # connect signals
        self.reprbutton.clicked.connect(self.repr)
        self.stickbutton.toggled.connect(self.toggleStick)
        self.freezebutton.toggled.connect(self.togglefreeze)
        self.autobutton.toggled.connect(self.toggleAuto)
        self.autobutton.toggle()
        self.scaleMaxEntry.editingFinished.connect(self.rescaleMax)
        self.scaleMinEntry.editingFinished.connect(self.rescaleMin)
        self.logxbutton.toggled.connect(self.togglelogx)
        self.overlaybutton.toggled.connect(self.toggleOverlay)


        # build layout
        self.hbox.addWidget(self.stickbutton)
        self.hbox.addWidget(self.freezebutton)
        # self.hbox.addStretch()
        self.hbox.addWidget(self.reprbutton)
        # self.hbox.addStretch()
        self.hbox.addWidget(self.dec_label)
        self.hbox.addWidget(self.dec_spin)
        self.hbox.addStretch()
        self.hboxB.addWidget(self.autobutton)
        self.hboxB.addWidget(self.scaleMinEntry)
        self.hboxB.addWidget(self.scaleMaxEntry)
        self.hboxB.addWidget(self.logxbutton)
        self.hboxB.addWidget(self.overlaybutton)
        self.hboxB.addStretch()
        self.topsplitlayout.addLayout(self.hbox)#,False,False)
        self.topsplitlayout.addLayout(self.hboxB)#,False,False)
        self.topsplitlayout.addWidget(self.frameWidget)#,expand=False,fill=True)

        self.mainlayout.addLayout(self.topsplitlayout)
        self.mainlayout.addWidget(self.bottomsplitlayout)
        self.setLayout(self.mainlayout)

        if self.plotter.viewbox is None:
            self.overlaybutton.hide()

        self.initialised=0

    def eventFilter(self, obj, event):
        if obj is self.overlayWin and event.type() == QtC.QEvent.Close:
            self.overlaybutton.toggle()
            return True
        elif obj is self.parent() and event.type() == QtC.QEvent.MouseButtonPress:
            if event.buttons() == QtC.Qt.RightButton:
                self.toggleHidden()
        return super().eventFilter(obj, event)
        
    def addCustomLayout(self, layout):
        self.bottomsplitlayout.setLayout(layout)
        
    def removeCustomLayout(self):
        self.bottomsplitlayout.setLayout(None)

    def mousemove(self, x, y, z):
        self.frameWidget.setText(f"({x},{y}) = {z}")

    def mousefocusout(self, event):
        print(event)

    def showEvent(self, event):
        if self.overlaybutton.isChecked():
            self.overlayWin.show()
        return super().showEvent(event)

    def hideEvent(self, event):
        if self.overlaybutton.isChecked():
            self.overlayWin.hide()
        return super().hideEvent(event)

    def toggleOverlay(self,response):
        if response:
            if self.overlayWin is None:
                self.overlayWin = OverlayWin(self.plotter, self)
                self.overlayWin.installEventFilter(self)
            self.overlayWin.show()
        else:
            self.overlayWin.hide()

    def toggleStick(self):
        if self.stickbutton.isChecked():
            self.unstick=1
            self.parentLayout.removeWidget(self)
            self.setWindowFlags(QtC.Qt.Window)
            pos = QtG.QCursor().pos()
            self.move(pos)
            self.show()
        else:
            self.unstick=0
            self.setWindowFlags(QtC.Qt.Widget)
            self.parentLayout.addWidget(self)
            self.show()

    def isStuck(self):
        return bool(self.unstick)

    def toggleHidden(self):
        if self.isHidden():
            self.show()
        else:
            self.hide()

    def setScaleRange(self,scale):
        self.scaleMinEntry.setValue(scale[0])
        self.scaleMaxEntry.setValue(scale[1])
        self.scale = list(scale)

    def toggleAuto(self):
        self.autoscale = self.autobutton.isChecked()
        self.scaleMinEntry.setEnabled(not self.autoscale)
        self.scaleMaxEntry.setEnabled(not self.autoscale)

    def rescaleMin(self):
        try:
            self.scale[0] = float(self.scaleMinEntry.value())
        except Exception as e:
            print(e)

    def rescaleMax(self):
        try:
            self.scale[1] = float(self.scaleMaxEntry.value())
        except Exception as e:
            print(e)

    def togglefreeze(self):
        self.freeze = self.freezebutton.isChecked()

    def togglelogx(self):
        self.logx = self.logxbutton.isChecked()




    def dataMangle(self,event,e=None,data=None):
        #txt=w.get_text().strip()
        txt=self.dataMangleEntry.toPlainText()
        if self.mangleTxt!=txt:
            self.mangleTxt=txt
            self.replot()

    def makeArr(self,arr,shape,dtype):
        """This is used if you want to plot a history.
        eg in mangle you would put something like:
        store=makeArr(store,(1000,),"f");store[:999]=store[1:];store[999]=data[1];data=store
        """
        if arr is None or arr.shape!=shape or arr.dtype.char!=dtype:
            arr = numpy.zeros(shape,dtype)
        return arr

    def setUserButtons(self,tbVal,tbNames):
        pass

    def redraw(self,w=None,a=None):
        self.redrawFunc()

    def redrawFunc(self):
        """Redraw, if something has changed in the user widgets.  Anything the user adds to hbox can call this function when e.g. a button is clicked."""
        pass

    def prepare(self,data,dim=2,overlay=None,arrows=None,axis=None,plottype=None):
        self.origData=data
        title=self.streamName+self.hostnametxt
        streamTimeTxt=self.streamTimeTxt
        freeze=self.freeze
        colour=None
        text=None
        fount=None
        self.grid=None
        fast=0
        if self.freeze==0:
            if type(data)!=numpy.ndarray:
                data=numpy.array([data])
            if self.data is None or type(self.data)==type("") or self.data.shape!=data.shape or self.data.dtype.char!=data.dtype.char:
                self.data=data.copy()
            else:
                self.data[:]=data
            data=self.data
            if len(self.mangleTxt)>0:
                mangleTxt=self.mangleTxt
            else:
                mangleTxt=self.mangleTxtDefault
            if len(mangleTxt)>0:
                d={"parent":self,"data":data,"numpy":numpy,"overlay":overlay,"store":self.store,"makeArr":self.makeArr,"title":self.streamName,"stream":self.stream,"streamTime":self.streamTime,"streamTimeTxt":self.streamTimeTxt,"subapLocation":self.subapLocation,"freeze":0,"tbVal":self.tbVal[:],"debug":0,"dim":dim,"arrows":arrows,"npxlx":self.npxlx,"npxly":self.npxly,"nsub":self.nsub,"subapFlag":self.subapFlag,"quit":0,"colour":colour,"text":None,"axis":axis,"plottype":plottype,"fount":None,"prefix":self.prefix,"darc":self.darc,"hbox":self.tbHbox,"redraw":self.redraw}
                try:
                    # print(self.stream.keys())
                    exec(mangleTxt, d)
                    data=d["data"]#the new data... after mangling.
                    overlay=d["overlay"]#the new overlay
                    self.store=d["store"]
                    title=d["title"]
                    if title==self.streamName:#unchanged
                        title+=self.hostnametxt
                    streamTimeTxt=d["streamTimeTxt"]
                    freeze=d["freeze"]
                    tbNames=d.get("tbNames")#could be None
                    tbVal=d.get("tbVal")
                    fount=d.get("fount")
                    fast=d.get("fast",0)
                    self.grid=d.get("grid",None)#x,y,xstep,ystep,xend,yend,colour
                    self.setUserButtons(tbVal,tbNames)
                    #if d.has_key("tbNames") and type(d["tbNames"])==type([]):
                    #    for i in range(min(len(self.tbList),len(d["tbNames"])):
                    #        self.tbList[i].set_label(d["tbNames"][i])
                    dim=d["dim"]
                    if dim is None:
                        dim=2
                    elif dim>2:
                        dim=2
                    if type(data)==numpy.ndarray:
                        dim=min(dim,len(data.shape))
                    arrows=d["arrows"]
                    colour=d["colour"]
                    text=d["text"]
                    if type(text)==type(""):
                        text=[[text,0,0]]
                    elif type(text) in [type([]),type(())]:
                        if len(text)>0:
                            if type(text[0])==type(""):
                                text=[text]
                    #if title is None:
                    #    title=self.stream
                    axis=d["axis"]
                    plottype=d["plottype"]
                except SyntaxError as msg:
                    print(sys.exc_info())
                    traceback.print_exc()
                except:
                    if d["debug"]:
                        print(sys.exc_info())
                        traceback.print_exc()
                if d["quit"]:
                    sys.exit(0)

            if type(data)==type(""):
                pass
            else:
                if freeze==0:
                    if dim==2:#see if dimensions have changed...
                        dim=min(2,len(data.shape))
                    if self.logx==1 and dim==2:
                        #take log of the data...
                        data = data.astype(float)
                        m=numpy.min(data.ravel())
                        if m<0:
                            data += 0.1-m#now ranges from 0 upwards
                        elif m==0.:#get rid of any zeros...
                            data += 0.1
                        data=numpy.log(data)
                    if self.autoscale:
                        tmp=data.flat
                        #if data.flags.contiguous:
                        #    tmp=data.flat
                        #else:
                        #    tmp=numpy.array(data).flat
                        self.scale[0]=numpy.min(tmp)
                        self.scale[1]=numpy.max(tmp)
                        self.scaleMinEntry.setText("%.4g"%(self.scale[0]))
                        self.scaleMaxEntry.setText("%.4g"%(self.scale[1]))
                    #if dim==1:
                    #    data[:]=numpy.where(data<self.scale[0],self.scale[0],data)
                    #    data[:]=numpy.where(data>self.scale[1],self.scale[1],data)


            if freeze==0 and type(overlay)==numpy.ndarray and len(overlay.shape)==3 and overlay.shape[2]==4 and len(data.shape)==2:
                # an overlay has been used...
                pass
            else:
                overlay=None
        self.data=data
        return freeze,self.logx,data,self.scale,overlay,title,streamTimeTxt,dim,arrows,colour,text,axis,plottype,fount,fast,self.autoscale,self.grid,self.overlayList

    def repr(self,w=None,a=None):
        Repr(self.data,self.label,parent=self)

    def fileaddtimestamp(self):
        curpos = self.filesavebox.cursorPosition()
        text = self.filesavebox.text()
        self.filesavebox.setText(text[:curpos]+time.strftime("%y%m%d-%H%M%S")+text[curpos:])

    def savePlot(self,w=None,a=None):
        fileName, _ = QtW.QFileDialog.getSaveFileName(self.savebutton,"Save as FITS or xml","","All Files (*);;Text Files (*.txt)","",QtW.QFileDialog.DontConfirmOverwrite)

        if fileName != "":
            self.savedialog = QtW.QDialog(self.savebutton)
            message = QtW.QLabel("Save As:")
            self.filesavebox = QtW.QLineEdit(fileName)

            QBtn = QtW.QDialogButtonBox.Ok | QtW.QDialogButtonBox.Cancel

            buttonBox = QtW.QDialogButtonBox(QBtn)
            buttonBox.accepted.connect(self.filesave)
            buttonBox.rejected.connect(self.savedialog.close)

            button1 = QtW.QPushButton("Insert timestamp")
            button1.clicked.connect(self.fileaddtimestamp)
            buttonBox.addButton(button1,QtW.QDialogButtonBox.ActionRole)

            button2 = QtW.QPushButton("Save unformatted")
            button2.clicked.connect(self.filesaveorig)
            buttonBox.addButton(button2,QtW.QDialogButtonBox.ActionRole)

            layout = QtW.QVBoxLayout()
            layout.addWidget(message)
            layout.addWidget(self.filesavebox)
            layout.addWidget(buttonBox)
            self.savedialog.setLayout(layout)
            self.savedialog.exec_()

    def loadPlot(self,w=None,a=None):
        fileName, _ = QtW.QFileDialog.getOpenFileName(self.loadbutton,"Load FITS file/xml file", "","All Files (*);;Python Files (*.py)")

        if fileName != "":
            self.fileload(fileName)

    def filesaveorig(self):
        fname = self.filesavebox.text()
        self.savedialog.close()
        print("Saving shape %s, dtype %s"%(str(self.origData.shape),str(self.origData.dtype.char)))
        FITS.Write(self.origData,fname)

    def filesave(self):
        fname=self.filesavebox.text()
        self.savedialog.close()
        if fname[-5:]==".fits":
            print("Saving shape %s, dtype %s"%(str(self.data.shape),str(self.data.dtype.char)))
            FITS.Write(self.data,fname)
        elif fname[-4:]==".xml":
            print("Saving config")
            pos=self.savebutton.window.frameGeometry().x(),self.savebutton.window.frameGeometry().y()
            size=self.savebutton.window.frameGeometry().width(),self.savebutton.window.frameGeometry().height()
            vis=0
            tbVal=self.tbVal
            mangleTxt=self.mangleTxt
            subscribeList=[]
            for key in list(self.subscribeDict.keys()):
                subscribeList.append((key,self.subscribeDict[key][0],self.subscribeDict[key][1]))
            if os.path.exists(fname):
                with open(fname,'r') as xf:
                    plotList=plotxml.parseXml(xf.read()).getPlots()
            else:
                plotList=[]
            plotList.append([pos,size,vis,mangleTxt,subscribeList,tbVal,None])
            txt='<displayset date="%s">\n'%time.strftime("%y/%m/%d %H:%M:%D")
            for data in plotList:
                txt+='<plot pos="%s" size="%s" show="%d" tbVal="%s">\n<mangle>%s</mangle>\n<sub>%s</sub>\n</plot>\n'%(str(data[0]),str(data[1]),data[2],str(tuple(data[5])),data[3].replace("<","&lt;").replace(">","&gt;"),str(data[4]))
            txt+="</displayset>\n"
            with open(fname,'w') as xf:
                xf.write(txt)
        else:
            print("Nothing saved")


    def fileload(self,filename):
        if self.loadFunc is not None:
            try:
                self.loadFunc(filename,reposition=0)
            except Exception as e:
                traceback.print_exc()

    def sendToDS9(self):
        if self.data is not None:
            FITS.Write(self.data,"/tmp/tmp.fits")
            try:
                subprocess.Popen(["/opt/ds9/ds9","/tmp/tmp.fits"])
            except Exception as e:
                print(e)
                print("Might need to install ds9 to /opt/ds9/")


#### remaining functions from plottoolbar
    def initialise(self,subscribeAction,configdir=None):
        """execute is a method called to execute the command"""
        self.initialised=1
        self.resubButton=QtW.QPushButton("Re")
        self.hbox.addWidget(self.resubButton)
        self.resubButton.setToolTip("Resubscribe to existing telemetry streams")
        self.resubButton.clicked.connect(lambda:subscribeAction("resubscribe"))
        self.resubButton.show()
        self.showStreams=QtW.QPushButton("Sub")
        self.showStreams.setToolTip("Show list of telemetry streams")
        self.hbox.addWidget(self.showStreams)
        self.showStreams.show()
        self.showStreams.clicked.connect(subscribeAction)
        self.configdir=configdir
        if self.configdir is not None:
            if len(self.configdir)==0:
                self.configdir="./"
            if self.configdir[-1]!='/':
                self.configdir+='/'
            sys.path.append(self.configdir)
            self.confighbox.addWidget(self.combobox)
            self.combobox.show()
            self.wm=WatchDir(self.configdir,"plot",".xml",self.comboUpdate,self.comboRemove)
            self.wm.start()
            self.comboPopped()

    def spawn(self,w=None,a=None):
        if sys.argv[0][-3:] == ".py":
            subprocess.Popen(["python3"]+sys.argv+["-i0"])#add index of zero so that we don't spawn lots of plots if the current one is a multiplot.
        else:
            subprocess.Popen(sys.argv+["-i0"])#add index of zero so that we don't spawn lots of plots if the current one is a multiplot.

    def userButtonToggled(self,w,a=None):
        a = self.sender().id
        self.tbVal[a]=int(w)

    def displayFileList(self,parentWin=None):
        print("showing file list")
        self.displayFileWidget=QtW.QWidget(parent=self)
        self.displayFileWidget.setWindowFlags(QtC.Qt.Window | QtC.Qt.WindowStaysOnTopHint)
        self.displayFileWidget.setWindowTitle("Choose plot configuration")
        v=QtW.QVBoxLayout()
        self.displayFileWidget.setLayout(v)
        self.filebuttonlist=[]
        print(self.filelist)
        for i,f in enumerate(self.filelist):
            if f is not None:
                b=QtW.QPushButton(f)
                b.clicked.connect(self.comboChosen)
                self.filebuttonlist.append(b)
                v.addWidget(b)
        self.displayFileWidget.show()

    def comboChosen(self,response):
        fname=self.configdir+self.sender().text()
        print("loading",fname)
        while len(self.tbVal)>0:
            self.removeUserButton()
        if self.loadFunc(fname,reposition=0)==0:
            self.displayFileWidget.close()

    def comboChanged(self,w,a=None):
        print(w)
        indx=w
        if indx>=0:
            if self.filelist[indx] is None:
                while len(self.tbVal)>0:
                    self.removeUserButton()
                self.loadFunc(None)
            else:
                fname=self.configdir+self.filelist[indx]
                print("loading",fname)
                while len(self.tbVal)>0:
                    self.removeUserButton()
                self.loadFunc(fname,reposition=0)

    def comboUpdate(self,fname):
        if fname not in self.filelist:
            self.filelist.append(fname)
            self.combobox.addItem(fname)

    def comboRemove(self,fname):
        if fname in self.filelist:
            indx=self.filelist.index(fname)
            self.combobox.removeItem(indx)
            self.filelist.pop(indx)

    def comboPopped(self,w=None):
        files=os.listdir(self.configdir)
        files.sort()
        self.filelist=[None]
        self.combobox.addItem("None")
        for fname in files:
            if fname[:4]=="plot" and fname[-4:]==".xml":
                self.filelist.append(fname)
                self.combobox.addItem(fname)

    def addUserButton(self,name=None,active=0):
        pos=len(self.tbList)
        if name is None:
            name="%d"%pos
        but=QtW.QPushButton(name)
        but.setCheckable(True)
        but.setChecked(active)
        but.id = pos
        but.toggled.connect(self.userButtonToggled)
        self.tbList.append(but)
        self.tbVal.append(active)
        self.tbNames.append(name)
        self.tbHbox.addWidget(but)
        but.show()

    def removeUserButton(self):
        self.tbVal.pop()
        self.tbNames.pop()
        but=self.tbList.pop()
        self.tbHbox.removeWidget(but)

    def setUserButtons(self,tbVal,names=None):
        if tbVal==self.tbVal and names==self.tbNames:
            return
        if tbVal is None:
            tbVal=[]
        if names is not None:
            l=len(names)
            ll=len(tbVal)
            if ll<l:
                tbVal=tbVal+[0]*(l-ll)
            else:
                tbVal=tbVal[:l]
        else:
            names=list(map(str,list(range(len(tbVal)))))
            names[:len(self.tbNames)]=self.tbNames[:len(tbVal)]
        while len(self.tbVal)>len(tbVal):
            self.removeUserButton()
        l=len(self.tbList)
        for i in range(l):#for existing buttons
            self.tbList[i].setChecked(tbVal[i])
            if names[i]!=self.tbNames[i]:
                self.tbList[i].setText(names[i])
                self.tbNames[i]=names[i]
        for i in range(l,len(tbVal)):#and add new if required.
            self.addUserButton(names[i],tbVal[i])