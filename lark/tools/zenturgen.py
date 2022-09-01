import numpy
import itertools
import scipy.io
import sys
from canapyrtc import HOME

# independent module helper functions
'''Get the variance for each zernike coefficient based on the remaining residual wavefront error'''
def getDeltaJ(J,D,r_0):
    deltaJcoeff = [1.0299,0.582,0.134,0.111,0.088,0.0648,0.0587,0.0525,0.0463,0.0401,0.0377,0.0352,0.0328,0.0304,0.0279,0.0267,0.0255,0.0243,0.0232,0.0220,0.0208]
    if J<22:
        return deltaJcoeff[J-1]*numpy.power(D/r_0,5./3.)
    else:
        return 0.2944*numpy.power(J,-numpy.sqrt(3.)/2.)*numpy.power(D/r_0,5./3.)

def getVarZcoef(J,D,r_0):
    '''This uses the numbers from Noll to calculate the varinace for each zernike, J=1 is Piston'''
    if J==0:
        print("Error, J can't be zero")
    elif J==1:
        return getDeltaJ(J,D,r_0)
    else:
        return getDeltaJ(J-1,D,r_0)-getDeltaJ(J,D,r_0)

'''define the Noll Zernike polynomials'''
    
def getR(n,m,r):
    '''get the radial component as a function of n,m,r'''
    R=0.
    for s in range((n-m)//2+1):
        t=numpy.power(-1,s)*numpy.math.factorial(n-s)
        b=numpy.math.factorial(s)*numpy.math.factorial((n+m)/2-s)*numpy.math.factorial((n-m)/2-s)
        R+=(t/b)*numpy.power(r,n-(2*s))
    return R

#class for generating and storing corresponding J, N, M values
class JNM:
    def __init__(self,Zn):
        self._jnm = numpy.zeros((Zn+1,2),dtype=int)
        n = 0
        jmax = 0
        while jmax<(Zn+1):
            for m in range(-n,n+1,2):
                j = (n*(n+1))//2+numpy.abs(m)
                if m>=0 and ((n%4)==2 or (n%4)==3):
                    j+=1
                elif m<=0 and ((n%4)==0 or (n%4)==1):
                    j+=1
                if j<=(Zn+1):
                    self._jnm[j-1]=(n,m)
                    jmax+=1
            n+=1

    def __getitem__(self,key):
        if type(key) is slice:
            if key.start<=0:
                raise Exception("Cannot get index 0 with slice")
            key = slice(key.start-1,key.stop-1,key.step)
        elif type(key) is tuple:
            if key[0].start<=0:
                raise Exception("Cannot get index 0 with slice")
            key = (slice(key[0].start-1,key[0].stop-1,key[0].step),key[1])
        elif type(key) is int:
            if key<=0:
                raise Exception("Cannot get index 0 with index")
            key -= 1
        return self._jnm[key]

    def __setitem__(self,key,value):
        raise Exception("Cannot set")

    def __repr__(self):
        return repr(self._jnm)

    def __str__(self):
        return str(self._jnm)

    def __iter__(self):
        for i in range(self._Zn):
            yield self._jnm[i]

# class for producing zernike images
class ZernikeMaps:
    def __init__(self, Zn, size):
        self.current_values = (0,0)
        self.Zn = Zn
        self.size = size

    @property
    def Zn(self):
        return self._Zn

    @Zn.setter
    def Zn(self,value):
        if value <= 0:
            raise Exception("Gimme some zernikes!")
        self._Zn = int(value)
        self._jnm = JNM(self._Zn)

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self,value):
        if value<=0:
            raise Exception("Size can't be zero or less")
        self._size = int(value)
        self.regen()

    def makeZernikeMaps(self):
        '''return phase maps of the zernike modes, across a unit circle with pupsize values across'''
        self.current_values = (self._Zn,self._size)
        pupsize = self._size
        self._phase = numpy.zeros((self._Zn,self._size,self._size),dtype=float)
        x = (numpy.arange(pupsize,dtype=numpy.float)-(pupsize-1)/2.)/((pupsize)/2.)
        thetas=numpy.arctan2(-x[:,numpy.newaxis],x[numpy.newaxis,:,])
        rs=numpy.sqrt(x[:,numpy.newaxis]**2 + x[numpy.newaxis,:,]**2)
        for j in range(self._Zn):
            J=j+1
            n,M = self._jnm[J]
            m = numpy.abs(M)
            if m==0:
                self._phase[j] = numpy.sqrt(n+1)*getR(n,m,rs)
            elif (J%2)==0:
                self._phase[j] = numpy.sqrt(n+1)*getR(n,m,rs)*numpy.sqrt(2.)*numpy.cos(m*thetas)
            elif (J%2)!=0:
                self._phase[j] = numpy.sqrt(n+1)*getR(n,m,rs)*numpy.sqrt(2.)*numpy.sin(m*thetas)
            self._phase[j][numpy.where(rs>1.)] = 0.
    
    def regen(self):
        if (self._Zn,self._size) != self.current_values:
            self.makeZernikeMaps()

    def __call__(self,zcoeffs):
        return self.getPhase(zcoeffs)

    def __iter__(self):
        self.regen()
        for i in range(self._Zn):
            yield self._phase[i]
    
    def __getitem__(self,key):
        if type(key) is slice:
            if key.start<=0:
                raise Exception("Cannot get index 0")
            key = slice(key.start-1,key.stop-1)
        elif type(key) is int:
            if key<=0:
                raise Exception("Cannot get index 0")
            key -= 1
        self.regen()
        return self._phase[key]

    def __setitem__(self,key,value):
        raise Exception("__setitem__ not implemented")

    def getPhase(self,zcoeffs):
        '''get the sum of the phase with a given array of coefficients and the unit phase maps given by getZernikeMaps'''
        self.regen()
        phase = numpy.zeros((self._size,self._size))
        n = min(zcoeffs.shape[0],self._Zn)
        for i in range(n):
            phase+=zcoeffs[i]*self._phase[i+1]
        return phase

    def Z2DM(self,Z2C):
        nacts = Z2C.shape[1]
        Zn = min(self._Zn,Z2C.shape[0])
        DMcube = numpy.zeros((Zn,nacts))
        dmZsign = numpy.ones(Zn,dtype=int)
        dmZsign[numpy.where(self._jnm[2:Zn+2,0]%2==0)]=-1
        unity = numpy.diag(numpy.ones(Zn))
        for i in range(Zn):
            DMmodes = dmZsign*unity[:,i]
            DMcube[i] = numpy.dot(DMmodes,Z2C[:Zn,:])
        return DMcube

# class for generating zernike coeffecients based on atmospheric parameters
class AtmosphereGenerator():
    AG_property_defaults = {"Zn":30,"N":1000,"f":100,"D":1,"r_0":0.137,"V":5,"wl":0.589}
    def __init__(self,*args,**kwargs):
        self.readConfig(*args,**kwargs)
        self._Z_coeffs = None
        self._Z_coeffs_params = []

    def __getitem__(self,key):
        return self._Z_coeffs[key]

    def __setitem__(self,key,value):
        raise Exception("__setitem__ not implemented")

    def readConfig(self,*args,**kwargs):
        for config in args:
            for key in config:
                setattr(self,key,config.get(key,self.AG_property_defaults[key]))
        for key in kwargs:
            setattr(self, key, kwargs.get(key,self.AG_property_defaults[key]))

    def generateTurbulence(self):
        self._Z_coeffs, noise, ffts = self.getZcoeffs()
        return self._Z_coeffs

    @property
    def D(self):
        return self._D

    @D.setter
    def D(self, value):
        if value <= 0:
            print("Error, D can't be zero or less")
        else:
            self._D = float(value)

    @property
    def Zn(self):
        return self._Zn

    @Zn.setter
    def Zn(self, value):
        if value <= 0:
            raise Exception("Error, Zn can't be zero or less")
        self._Zn = int(value)
        print("Generating JNM values...")
        self._jnm = JNM(self._Zn)

    @property
    def wl(self):
        return self._wl

    @wl.setter
    def wl(self, value):
        if value <= 0:
            print("Error, wl can't be zero or less")
        else:
            self._wl = float(value)

    @property
    def V(self):
        return self._V

    @V.setter
    def V(self, value):
        if value <= 0:
            print("Error, V can't be zero or less")
        else:
            self._V = float(value)

    @property
    def N(self):
        return self._N

    @N.setter
    def N(self, value):
        if value <= 0:
            print("Error, N can't zero or less")
        else:
            self._N = int(value)

    @property
    def r_0(self):
        return self._r_0

    @r_0.setter
    def r_0(self, value):
        if value <= 0:
            print("Error, r_0 can't zero or less")
        else:
            self._r_0 = float(value)

    @property
    def f(self):
        return self._f

    @f.setter
    def f(self, value):
        if value <= 0:
            print("Error, f can't zero or less")
        else:
            self._f = float(value)

    @property
    def Z_coeffs(self):
        if [self._Zn,self._N,self._f,self._D,self._r_0,self._V,self._wl] == self._Z_coeffs_params:
            return self._Z_coeffs
        else:
            print("Generating turbulence")
            self.generateTurbulence()
            return self._Z_coeffs

    @Z_coeffs.setter
    def Z_coeffs(self, value):
        print("Error, cannot set Z_coeffs")

    def regen(self):
        if [self._Zn,self._N,self._f,self._D,self._r_0,self._V,self._wl] != self._Z_coeffs_params:
            self.getZcoeffs()
    
    def getZcoeffs(self):
        '''to store results'''
        self._Z_coeffs_params = [self._Zn,self._N,self._f,self._D,self._r_0,self._V,self._wl]
        self._noise = numpy.zeros((self._Zn,self._N))                            #initial white noise
        self._Z_coeffs = numpy.zeros((self._Zn,self._N))                          #zernike coefficients
        self._zffts = numpy.zeros((self._Zn,self._N//2+1),dtype=complex)   #ffts of zernike coefficients
        freq = numpy.fft.rfftfreq(self._N,d=1./self._f)                      #the frequency of each element in the fft

        '''Main loop'''
        for i in range(self._Zn):
            #the Noll index of the mode
            J = i+2
            zstd = numpy.sqrt(getVarZcoef(J,self._D,self._r_0))   #get the standard deviation for each mode
            zcoeff = numpy.random.normal(0.,zstd,self._N)   #white noise, zero mean
            self._noise[i] = zcoeff                         #store the initial distribution
            zfft = numpy.fft.rfft(zcoeff)             #take the fft
            zero_f = zfft[0]                          #store the zero frequency component for later

            '''below cutoff'''
            if J<4:
                '''tip and tilt'''
                vc = 0.3*self._V/self._D
                power = -2./3.
                idx = numpy.where(freq<vc)
                shape = numpy.power(freq[idx],power)
                zfft[idx] *= (shape/numpy.amin(shape))
            else:
                '''higher order modes'''
                vc = 0.3*(self._jnm[J][0]+1)*self._V/self._D
                #the higher order modes are treated as having a gradient of 1 for below v_c

            '''above cutoff'''
            power = -17./3.
            idx = numpy.where(freq>vc)
            shape = numpy.power(freq[idx],power)       #the shape of the distribution
            zfft[idx] *= (shape/numpy.amax(shape))     #multiple the fourier distribution by the shape
            zfft[numpy.isinf(zfft)] = 0.               #just incase an inf gets in...
            zfft[0] = 0.+0j #zero_f                    #use the old zero freq component or 0, as it should be the mean...
            powerfactor = numpy.sqrt(self._N)*zstd/numpy.std(zfft)
            zfft *= powerfactor #scale the fft distribution by the ratio of stds to compensate for loss of power
            self._zffts[i] = zfft                            #store the fourier representation
            self._Z_coeffs[i,:] = numpy.fft.irfft(zfft)*(self._wl/(2*numpy.pi))         #inverse fourier transform and store the result
        return self._Z_coeffs, self._noise, self._zffts

    def Z2DM(self,Z2C):
        nacts = Z2C.shape[1]
        Zn = min(self._Zn,Z2C.shape[0])
        DMcube = numpy.zeros((self._N,nacts))
        dmZsign = numpy.ones(Zn,dtype=int)
        dmZsign[numpy.where(self._jnm[2:Zn+2,0]%2==0)]=-1
        for i in range(self._N):
            DMmodes = dmZsign*self.Z_coeffs[:,i]
            DMcube[i] = numpy.dot(DMmodes,Z2C[:Zn,:])
        return DMcube

# animation function.  This is called sequentially
def animate(i):
    # a = im.get_array()
    # a[:] = getPhase(zcoeffs[i])    # exponential decay of the values
    # im.set_array(a)
    data = getPhase(animate.zcoeffs[i])
    # data = getPhase.zerns[i]
    animate.im.set_data(data)
    animate.im.set_clim(numpy.amin(data),numpy.amax(data))
    return [animate.im]

def old():
    
    '''constants'''
    D = 1.                  #telescope diameter
    N = 1000                #number of frames
    nacts = 97              #number of actuators
    wl = 0.589              #wavelength
    '''variables'''
    Zn = [60,36,96]                #number of zernike modes, does NOT include piston, Zernike modes 2->(Zn+1)
    r_0 = [0.137,0.137,0.5]             #fried parameter
    V = [5.,10.,15.]                  #wind speed
    f = [200.,300.,500.]               #frequency
    
    # mat = scipy.io.loadmat('/home/djenkins/Canapy/canapy-rtc/config/AlpaoConfig/BAX224-Z2C-noll.mat')
    mat = scipy.io.loadmat('/home/canapyrtc/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C-noll.mat')
    alpao_zmat = mat['Z2C'][:,:]

    atmos = AtmosphereGenerator(D=1,wl=0.589,N=1000)

    '''mapping of all variables'''
    vals = itertools.product(Zn,f,r_0,V)
    '''loop through all and save DM commands'''
    for val in vals:
        Zn,f,r_0,V = val
        try:
            atmos.readConfig(Zn=Zn,f=f,r_0=r_0,V=V)
            # zcoeffs,noise,zffts = atmos.getZcoeffs()
            DMcube = atmos.Z2DM(alpao_zmat)
            filen = "alpaoDMZernike-D{}wl{}Zn{}r{}V{}f{}.npy".format(int(D),int(wl*1000),Zn,int(r_0*100),int(V),int(f))
            print("saving: ",filen)
#             numpy.save(filen,DMcube)
        except Exception as e:
            print(e)

def plotPower():
    '''plotting of a single zernike time series for verification'''
    N=1000
    f=100
    atmos = AtmosphereGenerator(D=1,wl=0.589,N=N,Zn=30,f=f,r_0=0.137,V=5)
    zcoeffs,noise,zfft = atmos.getZcoeffs()
    freq = numpy.fft.rfftfreq(N,d=1./f)
    time = numpy.arange(0.,N*1./f,1./f)
    J=2 # here it starts at 2, 1 is piston and therefore not used
    pyplot.figure()
    pyplot.plot(time,noise[J-2],alpha=0.5)
    pyplot.plot(time,zcoeffs[J-2])
    # pyplot.show()
    # ddd

    pyplot.figure()
    pyplot.plot(freq,numpy.fft.rfft(noise[J-2]),alpha=0.5)
    pyplot.plot(freq,numpy.fft.rfft(zcoeffs[J-2]))
    pyplot.figure()
    pyplot.psd(noise[J-2],N,f,alpha=0.5)
    pyplot.psd(zcoeffs[J-2],N,f)
    pyplot.figure()
    pyplot.loglog(freq,((1./(f*N)) * numpy.abs(numpy.fft.rfft(noise[J-2]))**2),alpha=.5)
    pyplot.loglog(freq,((1./(f*N)) * numpy.abs(numpy.fft.rfft(zcoeffs[J-2]))**2))

    pyplot.show()

    # '''Plottting of some of the time series for verification'''
    # pyplot.figure()
    # for mode in range(2,100):
    #     mode*=5
    #     pyplot.plot(zcoeffs[:,mode-1])
    # pyplot.show()

if __name__ == "__main__":
    from matplotlib import pyplot
    from matplotlib import animation
    plotPower()
    # old()
    # sys.exit()
    ''' Intial parameters and array generation '''
    Vs = [5.,15.]                  #wind speed
    D = 1.                  #telescope diameter
    N = 1000               #number of frames
    nacts = 97              #number of actuators
    Zns = [15]                #number of zernike modes, does NOT include piston, Zernike modes 2->(Zn+1)
    r_0s = [0.05,0.137]             #fried parameter
    wl = 0.589              #wavelength
    fs = [200]               #frequency

    pupsize = 11
    zerns = ZernikeMaps(max(Zns)+1,pupsize)

    PHs = {}
    DMs = {}

    # mat = scipy.io.loadmat('/home/canapyrtc/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C-noll.mat')
    mat = scipy.io.loadmat(HOME+'/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C-noll.mat')
    # mat = scipy.io.loadmat(HOME+'/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C.mat')
    # mat = scipy.io.loadmat('/Users/djenkins/OneDrive - ESO/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C-noll.mat')
    alpao_zmat = mat['Z2C'][:,:]


    plot_atmos = 1
    if plot_atmos:

        atmos = AtmosphereGenerator(D=D,wl=wl,N=N)
        vals = itertools.product(Zns,fs,r_0s,Vs)
        '''loop through all and save DM commands'''
        for val in vals:
            Zn,f,r_0,V = val
            try:
                # zcoeffs,noise,zffts = getZcoeffs(Zn,N,f,D,r_0,V)
                print("generating atmos")
                atmos.readConfig(Zn=Zn,f=f,r_0=r_0,V=V)
                DMcube = atmos.Z2DM(alpao_zmat)
                # DMcube = ZcoeffsToDM(N,nacts,zcoeffs,wl,alpao_zmat)
                filen = "alpaoDMZernike-D{}wl{}Zn{}r{}V{}f{}.npy".format(int(D),int(wl*1000),Zn,int(r_0*100),int(V),int(f))
                print("saving: ",filen)
                # numpy.save(filen,DMcube)
                phscube = numpy.zeros((N,pupsize,pupsize))
                mode_from = 1
                mode_to = Zn
                for i in range(N):
                    phscube[i] = zerns(atmos[:,i])
                PHs[f"D{int(D)}wl{int(wl*1000)}Zn{Zn}r{int(r_0*100)}V{int(V)}f{int(f)}.npy"] = phscube
                DMs[f"D{int(D)}wl{int(wl*1000)}Zn{Zn}r{int(r_0*100)}V{int(V)}f{int(f)}.npy"] = DMcube
            except Exception as e:
                print(e)
                raise e
            

    dmsurf1 = numpy.zeros((11,11))
    dmsurf2 = numpy.zeros((11,11))
    dmmap = numpy.array([
        [0,0,0,1,1,1,1,1,0,0,0],
        [0,0,1,1,1,1,1,1,1,0,0],
        [0,1,1,1,1,1,1,1,1,1,0],
        [1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1],
        [0,1,1,1,1,1,1,1,1,1,0],
        [0,0,1,1,1,1,1,1,1,0,0],
        [0,0,0,1,1,1,1,1,0,0,0],
    ])
    dmnoedge = numpy.array([
        [0,0,0,0,0,0,0,0,0,0,0],
        [0,0,0,1,1,1,1,1,0,0,0],
        [0,0,1,1,1,1,1,1,1,0,0],
        [0,1,1,1,1,1,1,1,1,1,0],
        [0,1,1,1,1,1,1,1,1,1,0],
        [0,1,1,1,1,1,1,1,1,1,0],
        [0,1,1,1,1,1,1,1,1,1,0],
        [0,1,1,1,1,1,1,1,1,1,0],
        [0,0,1,1,1,1,1,1,1,0,0],
        [0,0,0,1,1,1,1,1,0,0,0],
        [0,0,0,0,0,0,0,0,0,0,0],
    ])

    print(PHs.keys())
    dmcube1 = DMs[f"D{int(D)}wl{int(wl*1000)}Zn{Zns[0]}r{int(r_0s[0]*100)}V{int(Vs[0])}f{int(fs[0])}.npy"]
    dmcube2 = DMs[f"D{int(D)}wl{int(wl*1000)}Zn{Zns[0]}r{int(r_0s[0]*100)}V{int(Vs[1])}f{int(fs[0])}.npy"]

    phscube1 = PHs[f"D{int(D)}wl{int(wl*1000)}Zn{Zns[0]}r{int(r_0s[0]*100)}V{int(Vs[0])}f{int(fs[0])}.npy"]
    phscube2 = PHs[f"D{int(D)}wl{int(wl*1000)}Zn{Zns[0]}r{int(r_0s[0]*100)}V{int(Vs[1])}f{int(fs[0])}.npy"]

    j = 0
    dmsurf1[numpy.where(dmmap==1)] = dmcube1[j]
    dmsurf1[numpy.where(dmmap==1)] = dmcube2[j]
    fig, ((ax1,ax2),(ax3,ax4)) = pyplot.subplots(2,2)
    ax1.set_title("phase map, zernike sum (rad)")
    ax2.set_title("DM command")
    im1 = ax1.imshow(phscube1[j],animated=True)
    im2 = ax2.imshow(phscube2[j],animated=True)
    im1.set_clim(numpy.amin(phscube1),numpy.amax(phscube1))
    im2.set_clim(numpy.amin(phscube2),numpy.amax(phscube2))
    im3 = ax3.imshow(dmsurf1,animated=True)
    im4 = ax4.imshow(dmsurf2,animated=True)
    im3.set_clim(numpy.amin(dmcube1),numpy.amax(dmcube1))
    im4.set_clim(numpy.amin(dmcube2),numpy.amax(dmcube2))
    cbar2 = pyplot.colorbar(im3)
    def updateFig(*args):
        global j,dmsurf1,dmsurf2,im1,im2,im3,im4,dmcube1,dmcube2,phscube1,phscube2
        j+=1
        dmsurf1[numpy.where(dmmap==1)] = dmcube1[j]
        dmsurf2[numpy.where(dmmap==1)] = dmcube2[j]
        dmsurf1 = numpy.rot90(dmsurf1)
        dmsurf2 = numpy.rot90(dmsurf2)
        # dmsurf1*=dmnoedge
        # dmsurf2*=dmnoedge
        im1.set_data(phscube1[j])
        im2.set_data(phscube2[j])
        # dmsurf2*=dmnoedge
        # dmsurf1*=dmnoedge
        im3.set_data(dmsurf1)
        im4.set_data(dmsurf2)
        pyplot.draw()
        return im1,im2,im3,im4,
    anim = animation.FuncAnimation(fig,updateFig,interval=5., blit=True)
    pyplot.show()




    # sys.exit()
    

    time = numpy.arange(0.,N*1./f,1./f)
    pi = numpy.pi
    pupsize = 11            #pupil size of zernike phase reconstruction
    # zcoeffs,noise,zffts = getZcoeffs(Zn,N,f,D,r_0,V)
    atmos = AtmosphereGenerator(D=D,wl=wl,N=N,Zn=Zn,f=f,r_0=r_0,V=V)

    # rad_rms_sum = 0.
    # for i in range(N):
    #     rad_rms_sum += numpy.sqrt(numpy.sum(zcoeffs[:,i]**2))
    # rad_rms_mean = rad_rms_sum/N

    # Jzn_1 = getDeltaJ(1,D,r_0)
    # print("{:.4}".format(rad_rms_mean*((wl/(2*pi)))*1000.))
    # print(rad_rms_mean)
    # print(numpy.sqrt(Jzn_1))
    # print()

    # plotPower()


    mat = scipy.io.loadmat(HOME+'/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C-noll.mat')
    noll_zmat = mat['Z2C'][:,:]
    mat = scipy.io.loadmat(HOME+"/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C.mat")
    # mat = scipy.io.loadmat('/Users/djenkins/OneDrive - ESO/git/canapy-rtc/config/AlpaoConfig/BAX224-Z2C-noll.mat')
    alpao_zmat = mat['z2C'][:,:]
    # dmZsign = numpy.ones(Zn,dtype=int)
    # dmZsign[numpy.where(getNMforJ.jnm[1:Zn+1,0]%2==0)]=-1

    dmsurf = numpy.zeros((11,11))
    dmmap = numpy.array([
        [0,0,0,1,1,1,1,1,0,0,0],
        [0,0,1,1,1,1,1,1,1,0,0],
        [0,1,1,1,1,1,1,1,1,1,0],
        [1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1],
        [0,1,1,1,1,1,1,1,1,1,0],
        [0,0,1,1,1,1,1,1,1,0,0],
        [0,0,0,1,1,1,1,1,0,0,0],
    ])

    zmat2noll_i = [1,0,2,4, 3,5,6, 8, 9,7,10,11,15,16,13,12,18,17,21,19,14,20,22,23,24,25,26,27,28,29]
    zmat2noll_s = [1,1,1,1,-1,1,1,-1,-1,1,-1, 1, 1,-1, 1, 1,-1,-1, 1, 1,-1, 1,1,1,1,1,1,1,1,1]

    zmat2noll = numpy.zeros((30,30),dtype=float)

    for i in range(30):
        zmat2noll[i,zmat2noll_i[i]] = zmat2noll_s[i]

    alpao_zmat = numpy.dot(zmat2noll,alpao_zmat)

    Zn = 30

    # zerns = getZernikeMapsNoPiston(pupsize,Zn)
    zerns = ZernikeMaps(Zn+1,pupsize)

    zcoeffs_index = numpy.diag(numpy.ones(Zn))
    print(zcoeffs_index.shape)
    # DMcube = ZcoeffsToDM(Zn,nacts,zcoeffs_index,wl,alpao_zmat)
    print("getting DM cube")
    DMcube1 = zerns.Z2DM(noll_zmat)
    DMcube2 = zerns.Z2DM(alpao_zmat)

    this_n = 0,5
    for i in range(*this_n):
        # modes = numpy.zeros(Zn)
        # modes[i] = 1
        J = i+2 #start from tip, J=1 is piston
        phase = zerns[J]
        # dmsurf*=dmnoedge
        fig, (ax1,ax2,ax3,ax4,ax5) = pyplot.subplots(1,5)
        pyplot.title(f"Z[{i}] == {i+2} ({zmat2noll_i[i]})")
        im1 = ax1.imshow(phase)
        dmsurf[numpy.where(dmmap==1)] = DMcube1[i]#numpy.dot(dmZsign*modes, alpao_zmat)
        print(dmsurf.shape)
        dmsurf = numpy.rot90(dmsurf)
        im2 = ax2.imshow((dmsurf/numpy.abs(dmsurf))*numpy.power(numpy.abs(dmsurf),0.75))
        dmsurf*=dmnoedge
        im3 = ax3.imshow((dmsurf/numpy.abs(dmsurf))*numpy.power(numpy.abs(dmsurf),0.75))
        
        dmsurf[numpy.where(dmmap==1)] = DMcube2[i]#numpy.dot(dmZsign*modes, alpao_zmat)
        print(dmsurf.shape)
        dmsurf = numpy.rot90(dmsurf)
        im4 = ax4.imshow((dmsurf/numpy.abs(dmsurf))*numpy.power(numpy.abs(dmsurf),0.75))
        dmsurf*=dmnoedge
        im5 = ax5.imshow((dmsurf/numpy.abs(dmsurf))*numpy.power(numpy.abs(dmsurf),0.75))
# im2 = ax2.imshow((dmsurf/numpy.abs(dmsurf))*numpy.power(numpy.abs(dmsurf),0.75))
    pyplot.show()
    sys.exit(0)


    phscube = numpy.zeros((N,pupsize,pupsize))

    mode_from = 0
    mode_to = Zn
    for i in range(N):
        phscube[i] = getPhase(zcoeffs[mode_from:mode_to,i],zerns[mode_from:mode_to])

    DMcube = ZcoeffsToDM(N,nacts,zcoeffs,wl,alpao_zmat)

    j = 0    
    dmsurf[numpy.where(dmmap==1)] = DMcube[j]
    fig, (ax1,ax2) = pyplot.subplots(1,2)
    ax1.set_title("phase map, zernike sum (rad)")
    ax2.set_title("DM command")
    im1 = ax1.imshow(phscube[j],animated=True)
    im1.set_clim(numpy.amin(phscube),numpy.amax(phscube))
    im2 = ax2.imshow(dmsurf,animated=True)
    im2.set_clim(numpy.amin(DMcube),numpy.amax(DMcube))
    cbar2 = pyplot.colorbar(im2)
    def updateFig(*args):
        global j,dmsurf,im1,im2,DMcube,phscube
        j+=1
        dmsurf[numpy.where(dmmap==1)] = DMcube[j]
        dmsurf = numpy.rot90(dmsurf)
        dmsurf*=dmnoedge
        im1.set_data(phscube[j])
        im2.set_data(dmsurf)
        pyplot.draw()
        return im1,im2,
    anim = animation.FuncAnimation(fig,updateFig,interval=100., blit=True)
    pyplot.show()