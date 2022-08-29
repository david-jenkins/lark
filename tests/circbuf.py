import os

from lark.ccirc import _CircReader, _CircSubscriber, CircSync, ZMQContext
import code
import time
import sys
from astropy.io import fits
import lark.utils
from lark import LarkConfig

from lark.configLoader import DATA_DIR

from lark.circbuf import CircReader, TelemetrySystem

def my_callback1(args):
    print(args[2])
    print(args[0][:5])
    print(args[0].shape)
    print("Calledback A!")
    # print(args)

def my_callback2(args):
    print(args[2])
    print(args[0][:5])
    print(args[0].shape)
    print("Calledback B!")
    # print(args)

if __name__ == "__main__":
    # from .interface import ControlClient


    # d = darc.Control("canapy")
    # d = ControlClient("canapy")

    # refs = d.set("refCentroids",numpy.arange(2528))

    l = LarkConfig("LgsWF").getlark()

    npxlx = l.get("npxlx")
    npxly = l.get("npxly")

    print(npxly,npxlx)

    # sys.exit()

    print("init")
    s = CircReader("LgsWF","rtcPxlBuf")

    # print("start")
    # s.start()
    # print("go")
    
    print(s.info)
    print(s._cbdata)
    print(s.status)
    
    s.stop()
    sys.exit()

    print(s._prefix)

    # s._prefix = "hello"
    print(s._status)

    s.addCallback(my_callback1)

    time.sleep(0.2)

    s.removeCallback(my_callback1)

    this_dir = "/home/canapyrtc/tmp"

    # for i in range(20):
    #     if os.path.exists(this_dir+f'/saving-{i:0>3}.cfits'):
    #         os.remove(this_dir+f'/saving-{i:0>3}.cfits')

    s.dataDir = this_dir
    try:
        s.saveFrames('saving',5000,overwrite=1)
    except FileExistsError as e:
        print(e)
        s.stop()
        del s
        sys.exit()
    # s.save3File('saving-0',"saving-1","saving-2",500)


    fnums = []
    for i in range(20):
        if os.path.exists(this_dir+f'/saving-{i:0>3}.cfits'):
            fnums.append(fits.getdata(this_dir+f'/saving-{i:0>3}.cfits',2))

    fh = fits.getheader(this_dir+'/saving-0.cfits',2)

    print((fnums[0]+fh['BZERO']).newbyteorder()[-5:])
    print()

    for i in range(len(fnums)-1):
        print((fnums[i]+fh['BZERO']).newbyteorder()[-5:])
        print((fnums[i+1]+fh['BZERO']).newbyteorder()[:5])
        print()

    s.stop()
    del s
    sys.exit()

    data1 = fits.getdata(this_dir+'/saving-0.cfits',0)
    data2 = fits.getdata(this_dir+'/saving-1.cfits',0)
    ftim1 = fits.getdata(this_dir+'/saving-0.cfits',1)
    ftim2 = fits.getdata(this_dir+'/saving-1.cfits',1)
    fnum1 = fits.getdata(this_dir+'/saving-0.cfits',2)
    fnum2 = fits.getdata(this_dir+'/saving-1.cfits',2)
    fnum3 = fits.getdata(this_dir+'/saving-2.cfits',2)
    fh = fits.getheader(this_dir+'/saving-0.cfits',2)
    # print(fh)

    t0 = ftim1.newbyteorder()[0]

    print(data1.shape)
    print(npxlx[0]*npxly[0])
    print(data1.dtype)
    print(data1[0])
    print(data1.newbyteorder()[:3,:6])
    print(ftim1.newbyteorder()[:5])
    print((fnum1+fh['BZERO']).newbyteorder()[:5])
    print(fnum1.shape)
    print(fnum1.dtype)
    print((fnum1+fh['BZERO']).newbyteorder()[-5:])
    print((fnum2+fh['BZERO']).newbyteorder()[:5])
    print()
    print((fnum2+fh['BZERO']).newbyteorder()[-5:])
    print((fnum3+fh['BZERO']).newbyteorder()[:5])

    data = data1.newbyteorder()
    n=39
    im1 = data[n,:npxlx[0]*npxly[0]]
    # im2 = data[n,npxlx[0]*npxly[0]:]
    im1.shape = npxly[0],npxlx[0]
    # im2.shape = npxly[1],npxlx[1]
    from matplotlib import pyplot
    pyplot.imshow(im1)
    # pyplot.figure()
    # pyplot.imshow(im2)
    pyplot.show()

    s.stop()
    del s

    sys.exit()

    sys.exit()

    # readers = {}
    # for key in TelemetrySystem.pxlStreamNames:
    #     print("Starting ", key)
    #     try:
    #         readers[key] = CircReader("canapy",key)
    #     except TypeError as e:
    #         print(e)
    #         print("Can't start ",key)
    # s = CircSubscriber("canapy","rtcCentBuf")
    t = TelemetrySystem("canapy")

    t.start()

    vals = t.getStreamBlock("rtcStatusBuf",1)
    print(vals)
    print(lark.utils.statusBuf_tostring(vals[0][0]))

    for i in range(10):
        x = t.getStreamBlock(["rtcCentBuf","rtcMirrorBuf"],10)
        # for k,v in x.items():
        #     print(k)
        #     print(v[2])
        print(int(x["rtcCentBuf"][2][0])-int(x["rtcMirrorBuf"][2][0]))

    # print(t)

    # t.start()

    # time.sleep(2)

    sys.exit()

    print(c)

    c.start_reader()

    print("params:")
    print(c._prefix)
    print(c._host)
    c._port = 18547
    c._port = 5001
    # c._port = 1854
    c._host = "enp0s17"
    c._multicast = "224.0.0.18"
    c._port = 18547
    c._host = "10.0.2.15"
    print(c._host)
    z = ZMQContext()
    c.use_tcp()
    # c.use_ipc()
    # c.use_epgm()
    # s.use_ipc()
    c.set_publish(1)
    # s.start_subscriber()

    # cb_ind1 = s.addCallback(my_callback2)
    cb_ind2 = c.addCallback(my_callback1)

    time.sleep(2)
    # s.removeCallback(cb_ind1)
    c.removeCallback(cb_ind2)
    c.set_publish(0)
    # s.stop_subscriber()

    # x = c.getDataBlock(100)
    # print(x[0][:,:5])
    sys.exit()
    print(c._port)
    c._port = 18547
    print(c._port)
    print(c._threadRunning)
    print(c._ndim)
    print(c._dtype)
    print(c._size)
    print(c._decimation)
    c._decimation = 10
    print(c._decimation)
    c._decimation = 1
    print(c._decimation)
    print(c._shape)
    print()
    print("arr size = ",c._size)
    print("dtype = ",chr(c._dtype))

    # print(c._shape)
    # c._shape = [2,2528//2]
    # print(c._shape)

    for i in range(10):
        x = c.getDataBlock(10)
        print(x[2])

    cb_ind1 = c.addCallback(my_callback1)
    cb_ind2 = c.addCallback(my_callback2)
    time.sleep(0.1)
    c.shape = [2,2528//2]
    time.sleep(0.1)
    c.removeCallback(cb_ind1)
    time.sleep(0.1)
    c.removeCallback(cb_ind2)

    print("Sleeping...")
    time.sleep(0.1)

    print(c._cbdata)
    print(c._latest)

    z = ZMQContext()

    c.set_publish(1,z)

    time.sleep(2)

    c.set_publish(0)
    c.stop_reader()

    sys.exit()


    # time.sleep(0.1)
    # for i in range(100):
    #     time.sleep(0.1)
    #     y = t.getStreamBlock(('rtcCentBuf','rtcMirrorBuf'),1)
        # print(x)
        # for k,v in y.items():
        #     print(v[2])

        # print(y['rtcCentBuf'][2][0],y['rtcMirrorBuf'][2][0])
        # print(y['rtcCentBuf'][2].astype(int)[0]-y['rtcMirrorBuf'][2].astype(int)[0])
        # print()

    # y = d.GetStreamBlock("rtcCentBuf",10)
    # y = y['rtcCentBuf']
    # print(y)

    # print(x[0].shape,y[0].shape)

    # assert((x[0]==y[0]).all())
    if os.path.exists('data/saving1.cfits'):
        os.remove('data/saving1.cfits')
    if os.path.exists('data/saving2.cfits'):
        os.remove('data/saving2.cfits')
    c.dataDir = "data"
    c.save2File('saving1','saving2',10000)

    c.stop_reader()
    del c

    sys.exit()

    data = fits.getdata('data/saving1.cfits',0)
    ftim = fits.getdata('data/saving1.cfits',1)
    fnum = fits.getdata('data/saving1.cfits',2)
    fnum1 = fits.getdata('data/saving1.cfits',2)
    fnum2 = fits.getdata('data/saving2.cfits',2)
    fh = fits.getheader('data/saving1.cfits',2)
    # print(fh)

    print(data.shape)
    print(data.dtype)
    print(data[0])
    print(data.newbyteorder()[:3,:6])
    print(ftim.newbyteorder()[:5])
    print((fnum+fh['BZERO']).newbyteorder()[:5])
    print(fnum.shape)
    print(fnum.dtype)
    print((fnum1+fh['BZERO']).newbyteorder()[-5:])
    print((fnum2+fh['BZERO']).newbyteorder()[:5])

    sys.exit()


    cb_ind1 = c.addCallback(my_callback1)
    cb_ind2 = c.addCallback(my_callback2)
    time.sleep(0.1)
    c.removeCallback(cb_ind1)
    time.sleep(0.1)
    c.removeCallback(cb_ind2)

    print("Sleeping...")
    time.sleep(0.1)

    cb_ind = c.addCallback(my_callback1)
    time.sleep(0.1)
    c.removeCallback(cb_ind)

    if os.path.exists('saving.fits'):
        os.remove('saving.fits')
    if os.path.exists('saving1.fits'):
        os.remove('saving1.fits')
    if os.path.exists('data/saving2.fits'):
        os.remove('data/saving2.fits')

    c.saveFile('saving.fits',500)
    time.sleep(0.5)
    c.save2File('saving1.fits','saving2.fits',500)

    data = fits.getdata('saving.fits',0)
    ftim = fits.getdata('saving.fits',1)
    fnum = fits.getdata('saving.fits',2)
    fnum1 = fits.getdata('saving1.fits',2)
    fnum2 = fits.getdata('data/saving2.fits',2)
    fh = fits.getheader('saving.fits',2)
    # print(fh)

    print(data.shape)
    print(data.dtype)
    print(data[0])
    print(data.newbyteorder()[:3,:6])
    print(ftim.newbyteorder()[:5])
    print((fnum+fh['BZERO']).newbyteorder()[:5])
    print(fnum.shape)
    print(fnum.dtype)
    print((fnum1+fh['BZERO']).newbyteorder()[-5:])
    print((fnum2+fh['BZERO']).newbyteorder()[:5])
    # print(fnum)
    # with open('saving.fits') as f:
    #     print(f.read().encode())
    # print(data.newbyteorder().tobytes()[:10])
    # print(data.tobytes()[:10])
    # print(numpy.frombuffer(data.tobytes(),dtype=numpy.float32))
    # print(fits.getdata('saving.fits',1).shape)
    # print(fits.getdata('saving.fits',2).shape)

    print(c.getDataType())

    code.interact(local=globals())


