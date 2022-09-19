import sys
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG
import pyqtgraph as pg
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
import numpy

PHOTONS_PER_S_PER_M2_PER_WATT = PSM2W = 600000.0
DUTY33_INT_TIME_MUS = 57.0

c_m = 299705000
l = 1000
t = 0.000001
c = c_m*t/l

km_per_step = 2
time_per_step = km_per_step/c
sanity = 0

def calc_dist(alt, angle):
    rad_m = 6375783.316
    rad = rad_m/l
    elev = 2.39
    hyp = 1000
    
    angle = 90-angle
    
    r = alt+rad-elev
    
    x1 = 0
    y1 = rad
    x2 = numpy.cos(angle*numpy.pi/180.)*hyp
    y2 = y1+numpy.sin(angle*numpy.pi/180.)*hyp
    
    dx = x2-x1
    dy = y2-y1
    
    D = x1*y2-x2*y1
    dr = numpy.sqrt(dx**2+dy**2)
    
    xi1 = (D*dy+dx*numpy.sqrt((r**2)*(dr**2)-D**2))/dr**2
    xi2 = (D*dy-dx*numpy.sqrt((r**2)*(dr**2)-D**2))/dr**2
    yi1 = (-D*dx+dy*numpy.sqrt((r**2)*(dr**2)-D**2))/dr**2
    yi2 = (-D*dx-dy*numpy.sqrt((r**2)*(dr**2)-D**2))/dr**2
    
    return numpy.sqrt(xi1**2+(yi1-y1)**2)
    
def gaussian(x, mu, sig):
    return numpy.exp(-numpy.power(x - mu, 2.) / (2 * numpy.power(sig, 2.)))/numpy.sqrt(2*numpy.pi*numpy.power(sig, 2.))


def rayleigh(alt, offset=0, stretch=1):
    x = 1000*(alt-offset)/stretch # convert from km and transform
    return (2.551555e-13*numpy.power(x,3)-1.688837e-8*numpy.power(x,2)+3.567613e-4*x-2.406285)*10 # *10 for 60W

class Sim():
    def __init__(self):
        self._pulse = 50
        self._exposure = 500
        self._pulse_per_exposure = 4
        self._angle = 30
        self._duty = 33.333333

        self._na_alt = 91
        self._na_thick = 15
        self._ra_alt = 25
        self._overlap = 0
        
        self.calc_pulse = True
        self.calc_exposure = True
        
        self.cbs = []
        
        self.update()
        
    @property
    def pulse(self):
        return self._pulse
        
    @pulse.setter
    def pulse(self,value):
        self._pulse = value
        self.update()
        
    @property
    def angle(self):
        return self._angle
        
    @angle.setter
    def angle(self,value):
        self._angle = value
        self.update()
        
    @property
    def duty(self):
        return self._duty
        
    @duty.setter
    def duty(self,value):
        self._duty = value
        self.update()
        
    @property
    def na_alt(self):
        return self._na_alt
        
    @na_alt.setter
    def na_alt(self,value):
        self._na_alt = value
        self.update()
        
    @property
    def na_thick(self):
        return self._na_thick
        
    @na_thick.setter
    def na_thick(self,value):
        self._na_thick = value
        self.update()
        
    @property
    def ra_alt(self):
        return self._ra_alt
        
    @ra_alt.setter
    def ra_alt(self,value):
        self._ra_alt = value
        self.update()
        
    @property
    def overlap(self):
        return self._overlap
        
    @overlap.setter
    def overlap(self,value):
        self._overlap = value
        self.update()
        
    @property
    def exposure(self):
        return self._exposure
        
    @exposure.setter
    def exposure(self, value):
        self._exposure = value
        self.update()
        
    @property
    def pulse_per_exposure(self):
        return self._pulse_per_exposure
        
    @pulse_per_exposure.setter
    def pulse_per_exposure(self, value):
        self._pulse_per_exposure = value
        self.update()
        
    def autoPulse(self, onoff:bool):
        print("Auto pulse = ",onoff)
        self.calc_pulse = onoff
        self.update()

    def autoExposure(self, onoff:bool):
        print("Auto pulse = ",onoff)
        self.calc_exposure = onoff
        self.update()

    def update(self):
        na_alt_1 = self.na_alt-self.na_thick/2.
        na_alt_2 = self.na_alt+self.na_thick/2.
    
        self.na_dist_1 = calc_dist(na_alt_1,self.angle)
        self.na_dist_2 = calc_dist(na_alt_2,self.angle)
        
        self.x_values = numpy.linspace(self.na_dist_1, self.na_dist_2, 100)
                
        duty_1 = 100/self.duty
        
        self.ratio = duty_1-1
        
        if self.calc_pulse:
            self._pulse = (2/((self.ratio+self.overlap)*c))*(self.na_dist_2-self.na_dist_1)
            
        if self.calc_exposure:
            self._exposure = max(500,self.pulse_per_exposure*duty_1*self._pulse)

        self.ra_dist = calc_dist(self.ra_alt,self.angle)
        
        self.calc_flux()
        
    def calc_flux(self):
        # from matplotlib import pyplot
        pt1 = 2*self.na_dist_1/c
        pt2 = 2*self.na_dist_2/c
        
        extra_step = (pt2-pt1)/time_per_step
        
        time_values = numpy.arange(0,pt2+extra_step*time_per_step,time_per_step)
        height_values = time_values*c/2
        
        profile = numpy.zeros_like(time_values)
        
        photons = 60*(self.duty/100.)*6e5*0.71*t*180

        profile += (3*photons/4)*gaussian(time_values,(pt1+pt2)/2-(pt2-pt1)/4,(pt1+pt2)/70)
        profile += (photons/4)*gaussian(time_values,(pt1+pt2)/2+(pt2-pt1)/4,(pt1+pt2)/70)

        print(f"Photons from Na = {photons}")
        
        print(f"Area = {numpy.trapz(profile,x=time_values)}")
        
        pulse_fn = numpy.ones(int(self.pulse/time_per_step))*0.25
        
        self.naflux = numpy.convolve(pulse_fn,profile,"full")
        
        airmass = 1/numpy.cos(self.angle*numpy.pi/180.)
        
        ra1 = 14.75
        ra2 = 21
        rd1 = airmass*ra1
        rd2 = airmass*ra2
        
        # ra_start = 2*2/(c*numpy.cos((self.angle)*numpy.pi/180.))
        # ra_end = 2*60/(c*numpy.cos((self.angle)*numpy.pi/180.))
        # ra_eq_na = 2*2/(c*numpy.cos((self.angle)*numpy.pi/180.))
        # ra_scale = 2*30/c
        # ra_scale = ra_end
        # # profile += 2*gaussian(time_values,0,1.5*self.na_dist_1)
        # ra_profile = 0.8*numpy.amax(profile)*(numpy.exp(-5.5*time_values/ra_scale)/numpy.exp(-5.5*ra_eq_na/ra_scale))
        
        ind = numpy.where((height_values>rd1) & (height_values<rd2))
        ra_height = height_values[ind]
        ra_time = ra_height/c
        ra_profile = rayleigh(ra_height,stretch=airmass)*2*(self.duty/100.)*10
        print(f"Photons from Ra = {numpy.trapz(ra_profile,x=ra_time)}")
        profile[ind] += ra_profile
        # profile[numpy.where(time_values<ra_start)] = 0
        # profile[numpy.where((time_values<pt1) & (time_values>ra_end))] = 0
        
        if sanity:
            ra1 = 2*ra1/(c*numpy.cos((self.angle)*numpy.pi/180.))
            ra2 = 2*ra2/(c*numpy.cos((self.angle)*numpy.pi/180.))
            profile = numpy.zeros_like(time_values)
            profile[int(pt1/time_per_step):int(pt2/time_per_step)] = 20
            self.naflux = numpy.convolve(pulse_fn,profile,"full")
            profile[int(ra1/time_per_step):int(ra2/time_per_step)] = 40
        
        self.retflux = numpy.convolve(pulse_fn,profile,"full")
        self.time_values = numpy.arange(0,pt2+extra_step*time_per_step+self.pulse+0.00001,time_per_step)
        if len(self.time_values)==len(self.retflux)+2:
            self.time_values = self.time_values[1:-1]
        else:
            self.time_values = self.time_values[1:]
        self.profile = profile
        self.height_values = height_values
        
        # pyplot.plot(self.height_values,profile)
        # pyplot.plot(self.time_values[:len(pulse_fn)],pulse_fn)
        # pyplot.plot(self.time_values,self.retflux)
        # pyplot.show()


class LaserItem(pg.GraphicsObject):
    def __init__(self, sim:Sim, index):
        pg.GraphicsObject.__init__(self)
        self.sim = sim  ## data must have fields: time, open, close, min, max
        self.index = index
        self.generatePicture()
    
    def generatePicture(self):
        ## pre-computing a QPicture object allows paint() to run much more quickly, 
        ## rather than re-drawing the shapes every time.
        self.picture = QtG.QPicture()
        p = QtG.QPainter(self.picture)
        p.setPen(pg.mkPen('w'))
        offset = (self.sim.ratio+1)*self.index*self.sim.pulse
        x1 = [0,self.sim.na_dist_1/c,self.sim.na_dist_1/c+self.sim.pulse,self.sim.pulse]
        points = QtG.QPolygonF([
            QtC.QPointF(offset+x1[0],0),
            QtC.QPointF(offset+x1[1],self.sim.na_dist_1),
            QtC.QPointF(offset+x1[2],self.sim.na_dist_1),
            QtC.QPointF(offset+x1[3],0),
            ])
        x2 = [x1[1],self.sim.na_dist_2/c,self.sim.na_dist_2/c+self.sim.pulse,2*self.sim.na_dist_2/c+self.sim.pulse,2*x1[1]]
        points2 = QtG.QPolygonF([
            QtC.QPointF(offset+x2[0],self.sim.na_dist_1),
            QtC.QPointF(offset+x2[1],self.sim.na_dist_2),
            QtC.QPointF(offset+x2[2],self.sim.na_dist_2),
            QtC.QPointF(offset+x2[3],0),
            QtC.QPointF(offset+x2[4],0),
            ])
        p.setBrush(pg.mkBrush([240,135,5,128]))
        p.drawPolygon(points)
        p.setBrush(pg.mkBrush([240,135,5,255]))
        p.drawPolygon(points2)
        p.end()
        
    def update(self):
        self.generatePicture()
        self.informViewBoundsChanged()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtC.QRectF(self.picture.boundingRect())
        
        
class PulseItem(pg.GraphicsObject):
    def __init__(self, sim, index):
        pg.GraphicsObject.__init__(self)
        self.sim = sim  ## data must have fields: time, open, close, min, max
        self.index = index
        self.generatePicture()
    
    def generatePicture(self):
        ## pre-computing a QPicture object allows paint() to run much more quickly, 
        ## rather than re-drawing the shapes every time.
        self.picture = QtG.QPicture()
        p = QtG.QPainter(self.picture)
        p.setPen(pg.mkPen('w'))
        p.setBrush(pg.mkBrush([240,135,5,128],alpha=0.5))
        offset = (self.sim.ratio+1)*self.index*self.sim.pulse
        x1 = [0,0,self.sim.pulse,self.sim.pulse]
        points = QtG.QPolygonF([
            QtC.QPointF(offset+x1[0],0),
            QtC.QPointF(offset+x1[1],-5),
            QtC.QPointF(offset+x1[2],-5),
            QtC.QPointF(offset+x1[3],0),
            ])
        p.drawPolygon(points)
        x2 = [self.sim.pulse,self.sim.pulse,(self.sim.ratio+1)*self.sim.pulse,(self.sim.ratio+1)*self.sim.pulse]
        p.setBrush(pg.mkBrush([0,0,255,128],alpha=0.5))
        points2 = QtG.QPolygonF([
            QtC.QPointF(offset+x2[0],0),
            QtC.QPointF(offset+x2[1],-5),
            QtC.QPointF(offset+x2[2],-5),
            QtC.QPointF(offset+x2[3],0),
            ])
        p.drawPolygon(points2)
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
        
    def update(self):
        self.generatePicture()
        self.informViewBoundsChanged()
    
    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtC.QRectF(self.picture.boundingRect())
        
class ExposureItem(pg.GraphicsObject):
    def __init__(self, sim, index):
        pg.GraphicsObject.__init__(self)
        self.sim = sim  ## data must have fields: time, open, close, min, max
        self.index = index
        self.generatePicture()
    
    def generatePicture(self):
        ## pre-computing a QPicture object allows paint() to run much more quickly, 
        ## rather than re-drawing the shapes every time.
        self.picture = QtG.QPicture()
        p = QtG.QPainter(self.picture)
        p.setPen(pg.mkPen('w'))
        p.setBrush(pg.mkBrush([104,151,84,128],alpha=0.75))
        offset = self.index*self.sim.exposure
        x1 = [0,0,self.sim.exposure,self.sim.exposure]
        points = QtG.QPolygonF([
            QtC.QPointF(offset+x1[0],-5),
            QtC.QPointF(offset+x1[1],-10),
            QtC.QPointF(offset+x1[2],-10),
            QtC.QPointF(offset+x1[3],-5),
            ])
        p.drawPolygon(points)
        x2 = [0,0,500,500]
        p.setBrush(pg.mkBrush([149,210,242,128],alpha=0.75))
        points2 = QtG.QPolygonF([
            QtC.QPointF(offset+x2[0],-10),
            QtC.QPointF(offset+x2[1],-15),
            QtC.QPointF(offset+x2[2],-15),
            QtC.QPointF(offset+x2[3],-10),
            ])
        p.drawPolygon(points2)
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
        
    def update(self):
        self.generatePicture()
        self.informViewBoundsChanged()
    
    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtC.QRectF(self.picture.boundingRect())
        
        
class AtmosItem(pg.GraphicsObject):
    def __init__(self,sim):
        pg.GraphicsObject.__init__(self)
        self.sim = sim
        self.generatePicture()
    
    def generatePicture(self):
        ## pre-computing a QPicture object allows paint() to run much more quickly, 
        ## rather than re-drawing the shapes every time.
        self.picture = QtG.QPicture()
        p = QtG.QPainter(self.picture)
        p.setPen(pg.mkPen('k'))
        p.setBrush(pg.mkBrush([0,135,5,128],alpha=0.5))
        x1 = [0,0,2000,2000]
        points = QtG.QPolygonF([
            QtC.QPointF(x1[0],self.sim.na_dist_1),
            QtC.QPointF(x1[1],self.sim.na_dist_2),
            QtC.QPointF(x1[2],self.sim.na_dist_2),
            QtC.QPointF(x1[3],self.sim.na_dist_1),
            ])
        p.drawPolygon(points)
        p.drawLine(QtC.QPointF(0,self.sim.ra_dist),QtC.QPointF(2000,self.sim.ra_dist))
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
        
    def update(self):
        self.generatePicture()
        self.informViewBoundsChanged()
    
    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtC.QRectF(self.picture.boundingRect())
        
class Window(QtW.QWidget):
    def __init__(self,sim:Sim):
        super().__init__()
        self.sim = sim
        self.app = QtW.QApplication.instance()
        gbox = QtW.QGridLayout()
        self.anglelabel = QtW.QLabel("Angle from zenith (deg)")
        self.anglebox = QtW.QDoubleSpinBox()
        self.anglebox.setRange(0,90)
        self.anglebox.setValue(sim.angle)
        self.anglebox.valueChanged.connect(self.anglebox_callback)
        self.na_alt_label = QtW.QLabel("Na Alt from sea (km)")
        self.na_alt_box = QtW.QDoubleSpinBox()
        self.na_alt_box.setRange(80,120)
        self.na_alt_box.setValue(sim.na_alt)
        self.na_alt_box.valueChanged.connect(self.na_alt_callback)
        self.na_thick_label = QtW.QLabel("Na thickness (km)")
        self.na_thick_box = QtW.QDoubleSpinBox()
        self.na_thick_box.setRange(5,30)
        self.na_thick_box.setValue(sim.na_thick)
        self.na_thick_box.valueChanged.connect(self.na_thick_callback)
        self.duty_label = QtW.QLabel("Duty Cycle (%)")
        self.duty_box = QtW.QDoubleSpinBox()
        self.duty_box.setRange(2,95)
        self.duty_box.setValue(sim.duty)
        self.duty_box.valueChanged.connect(self.duty_callback)
        self.pulse_check_label = QtW.QLabel("Auto Pulse length")
        self.pulse_check = QtW.QCheckBox()
        self.pulse_check.setChecked(sim.calc_pulse)
        self.pulse_check.toggled.connect(self.pulse_check_callback)
        self.pulse_box_label = QtW.QLabel("Pulse Length (us)")
        self.pulse_box = QtW.QDoubleSpinBox()
        self.pulse_box.setRange(30,1500)
        self.pulse_box.setValue(sim.pulse)
        self.pulse_box.valueChanged.connect(self.pulse_callback)
        self.period_label = QtW.QLabel("Total Period (us)")
        self.period_box = QtW.QLabel()
        self.overlap_label = QtW.QLabel("Overlap in Pulse Length")
        self.overlap_box = QtW.QDoubleSpinBox()
        self.overlap_box.setRange(-5,5)
        self.overlap_box.setValue(sim.overlap)
        self.overlap_box.setSingleStep(0.05)
        self.overlap_box.valueChanged.connect(self.overlap_callback)
        self.exposure_check_label = QtW.QLabel("Auto Exposure length")
        self.exposure_check = QtW.QCheckBox()
        self.exposure_check.setChecked(sim.calc_exposure)
        self.exposure_check.toggled.connect(self.exposure_check_callback)
        self.ppe_box_label = QtW.QLabel("Pulse per exposure")
        self.ppe_box =  QtW.QSpinBox()
        self.ppe_box.setRange(1,20)
        self.ppe_box.setValue(sim.pulse_per_exposure)
        self.ppe_box.valueChanged.connect(self.ppe_callback)
        self.exposure_box_label = QtW.QLabel("Exposure Length (us)")
        self.exposure_box = QtW.QDoubleSpinBox()
        self.exposure_box.setRange(500,2000)
        self.exposure_box.setValue(sim.exposure)
        self.exposure_box.valueChanged.connect(self.exposure_callback)
        self.framerate_label = QtW.QLabel("Frame rate (Hz)")
        self.framerate_box = QtW.QLabel()
        row = 0
        gbox.addWidget(self.anglelabel,row:=row+1,0)
        gbox.addWidget(self.anglebox,row,1)
        gbox.addWidget(self.na_alt_label,row:=row+1,0)
        gbox.addWidget(self.na_alt_box,row,1)
        gbox.addWidget(self.na_thick_label,row:=row+1,0)
        gbox.addWidget(self.na_thick_box,row,1)
        gbox.addWidget(self.duty_label,row:=row+1,0)
        gbox.addWidget(self.duty_box,row,1)
        gbox.addWidget(self.pulse_check_label,row:=row+1,0)
        gbox.addWidget(self.pulse_check,row,1)
        gbox.addWidget(self.pulse_box_label,row:=row+1,0)
        gbox.addWidget(self.pulse_box,row,1)
        gbox.addWidget(self.period_label,row:=row+1,0)
        gbox.addWidget(self.period_box,row,1)
        gbox.addWidget(self.overlap_label,row:=row+1,0)
        gbox.addWidget(self.overlap_box,row,1)
        gbox.addWidget(self.exposure_check_label,row:=row+1,0)
        gbox.addWidget(self.exposure_check,row,1)
        gbox.addWidget(self.ppe_box_label,row:=row+1,0)
        gbox.addWidget(self.ppe_box,row,1)
        gbox.addWidget(self.exposure_box_label,row:=row+1,0)
        gbox.addWidget(self.exposure_box,row,1)
        gbox.addWidget(self.framerate_label,row:=row+1,0)
        gbox.addWidget(self.framerate_box,row,1)
        gbox.setRowStretch(row:=row+1,1)
        vbox = QtW.QHBoxLayout()
        
        plt = pg.plot()
        plt.getPlotItem().getAxis("left").setLabel("Distance (km)")
        plt.getPlotItem().getAxis("bottom").setLabel("Time (us)")
        self.items = []
        self.plots = []
        item = AtmosItem(sim)
        plt.addItem(item)
        self.items.append(item)
        for i in range(10):
            item = LaserItem(sim,i)
            plt.addItem(item)
            self.items.append(item)
        for i in range(12):
            item = PulseItem(sim,i)
            plt.addItem(item)
            self.items.append(item)
        for i in range(3):
            item = ExposureItem(sim,i)
            plt.addItem(item)
            self.items.append(item)
        for i in range(10):
            self.plots.append(plt.getPlotItem().plot(x=i*(self.sim.ratio+1)*self.sim.pulse+self.sim.time_values,y=self.sim.retflux,pen=pg.mkPen("g",width=2)))
            self.plots.append(plt.getPlotItem().plot(x=i*(self.sim.ratio+1)*self.sim.pulse+self.sim.time_values,y=self.sim.naflux,pen=pg.mkPen("r",width=2)))
        plt.setWindowTitle('pyqtgraph example: customGraphicsItem')
        
        exp_text = pg.TextItem("Exposure time",color="k")
        plt.addItem(exp_text)
        exp_text.setPos(0,-5)
        ro_text = pg.TextItem("Read-out",color="k")
        plt.addItem(ro_text)
        ro_text.setPos(0,-10)
        
        # ti = pg.TextItem(e,color=getPyQtColour(e3))
        # fi = QtG.QFont()
        # fi.setPointSize(int(e4))
        # ti.setFont(fi)
        # self.plotter._addItem(ti)
        # ti.setPos(e2[0],e2[1])
        
        pbox = QtW.QVBoxLayout()
        pbox.addWidget(plt,3)
        
        # self.plt = pg.plot(x=sim.x_values,y=sim.profile)
        self.plt = pg.plot(x=sim.height_values,y=sim.profile,pen=pg.mkPen("b",width=2))
        
        self.plt.getPlotItem().getAxis("left").setLabel("Photons per us")
        self.plt.getPlotItem().getAxis("bottom").setLabel("Distance (km)")
        
        pbox.addWidget(self.plt,1)
        
        vbox.addLayout(pbox)
        vbox.addLayout(gbox)
        self.setLayout(vbox)
        
        
    def anglebox_callback(self):
        self.sim.angle = self.anglebox.value()
        self.update()
        
    def na_alt_callback(self):
        self.sim.na_alt = self.na_alt_box.value()
        self.update()
        
    def na_thick_callback(self):
        self.sim.na_thick = self.na_thick_box.value()
        self.update()
        
    def duty_callback(self):
        self.sim.duty = self.duty_box.value()
        self.update()
        
    def pulse_check_callback(self,value):
        self.sim.autoPulse(value)
        self.update()
        
    def pulse_callback(self):
        self.sim.pulse = self.pulse_box.value()
        self.update()
        
    def exposure_check_callback(self,value):
        self.sim.autoExposure(value)
        self.update()
        
    def exposure_callback(self):
        self.sim.exposure = self.exposure_box.value()
        self.update()

    def overlap_callback(self):
        self.sim.overlap = self.overlap_box.value()
        self.update()
        
    def ppe_callback(self):
        self.sim.pulse_per_exposure = self.ppe_box.value()
        self.update()
        
    def update(self):
        # self.plt.getPlotItem().listDataItems()[0].setData(x=self.sim.x_values,y=self.sim.profile)
        # for i,plot in enumerate(self.plots):
        for item in self.items:
            item.update()
        for i in range(10):
            plot = self.plots[i*2]
            plot.setData(x=i*(self.sim.ratio+1)*self.sim.pulse+self.sim.time_values,y=self.sim.retflux)
            plot = self.plots[i*2+1]
            plot.setData(x=i*(self.sim.ratio+1)*self.sim.pulse+self.sim.time_values,y=self.sim.naflux)
        try:
            self.plt.getPlotItem().listDataItems()[0].setData(x=self.sim.height_values,y=self.sim.profile)
        except Exception as e:
            print(e)
        self.pulse_box.setValue(self.sim.pulse)
        self.exposure_box.setValue(self.sim.exposure)
        self.period_box.setText(f"{self.sim.pulse*(100/self.sim.duty):.2f}")
        self.app.processEvents()
        self.framerate_box.setText(f"{1000000/self.sim.exposure:.2f}")


def main():
    sim = Sim()
    sim.angle = 30
    app = QtW.QApplication(sys.argv)
    win = Window(sim)
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    
    main()
    
    # from matplotlib import pyplot
    
    # airmass = 1/numpy.cos(30*numpy.pi/180.)
    
    # ra1 = 14.75
    # ra2 = 21
    
    # x = numpy.linspace(airmass*ra1,airmass*ra2,100)
    
    # y = rayleigh(x,stretch=airmass)
    
    # pyplot.plot(x,y)
    # pyplot.xlim(14,26)
    # pyplot.figure()
    
    # x = numpy.linspace(ra1,ra2,100)
    
    # y = rayleigh(x)
    
    # pyplot.plot(x,y)
    
    # pyplot.xlim(14,26)
    
    # pyplot.show()
    # sys.exit()
    
    # from matplotlib import pyplot
    
    # km_per_step = 0.5
    # time_per_step = km_per_step/c
    
    # extra_step = 0
    
    # sanity = 0
    
    # alt1 = 80
    # pt1 = alt1/c
    # alt2 = 105
    # pt2 = alt2/c
    
    # extra_step = (pt2-pt1)/time_per_step
    
    # print(pt1,pt2)
    
    # steps = pt2/time_per_step+extra_step
    
    # print(steps)
    
    # time_values = numpy.arange(0,pt2+extra_step*time_per_step,time_per_step)
    
    # print(time_values)
    
    # profile = numpy.zeros_like(time_values)
        
    # profile += 3*gaussian(time_values,(pt1+pt2)/2-(pt2-pt1)/4,(pt1+pt2)/70)
    # profile += gaussian(time_values,(pt1+pt2)/2+(pt2-pt1)/4,(pt1+pt2)/70)
    
    
    # if sanity:
    #     profile = numpy.zeros_like(time_values)
    #     profile[int(pt1/time_per_step):int(pt2/time_per_step)] = 1
    
    # pulse = 50
    
    # pulse_fn = numpy.ones(int(pulse/time_per_step))
        
    # retflux = numpy.convolve(pulse_fn,profile,"self")
    
    # pyplot.plot(time_values,profile)
    # pyplot.plot(time_values[:len(pulse_fn)],pulse_fn)
    # pyplot.plot(time_values,retflux)
    # pyplot.show()
    
    # sys.exit()
    
    