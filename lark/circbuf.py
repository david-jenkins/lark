import datetime
import os
from typing import Dict
import rpyc
import rpyc.core.netref
from rpyc.lib import get_id_pack
import numpy
# import darc
from lark.ccirc import cCircReader, cCircSubscriber, cCircSync, cZMQContext
import code
import threading
import time
import queue
import sys
from astropy.io import fits
from lark.parallel import threadSynchroniser, processSynchroniser
from pathlib import Path
import lark.utils
from lark import LarkConfig

from logging import getLogger

'''
    Data is saved in .cfits files with little endianness....
   .cfits files need converting to .fits (big endian) if opening with 
   any standard fits library...
'''

FRAMES_PER_FILE = 100000
MAX_FILE_SIZE = 100000000

CNT = 0

from lark.configLoader import get_lark_config

def make_cfits(fname, delem, dtype, frames=None, header=None, overwrite=0):
    """ Generate a large empty cfits file on disk.
    A cfits file is similar to a fits file but the data is little endian
    and unsigned integers are stored as-is, data is copied directly from C

    Args:
        fname ([type]): [description]
        delem ([type]): [description]
        dtype ([type]): [description]
        frames ([type], optional): [description]. Defaults to None.

    Returns:
        [type]: [description]
    """
    data = numpy.zeros((2,2),dtype=dtype)
    hdu1 = fits.PrimaryHDU(data=data)
    header1 = hdu1.header

    data = numpy.zeros((2,2),dtype=numpy.double)
    hdu2 = fits.ImageHDU(data=data)
    header2 = hdu2.header

    data = numpy.zeros((2,2),dtype=numpy.uint32)
    hdu3 = fits.ImageHDU(data=data)
    header3 = hdu3.header

    if frames is None:
        frames = FRAMES_PER_FILE

    # while len(header) < (36 * 4 - 1):
    #     header.append()
    # while len(header1) < (36 * 4 - 1):
    #     header1.append()

    header1['NAXIS1'] = delem
    header1['NAXIS2'] = frames
    header2['NAXIS1'] = 1
    header2['NAXIS2'] = frames
    header3['NAXIS1'] = 1
    header3['NAXIS2'] = frames

    fname = Path(fname)
    strname = str(fname.with_suffix(".cfits"))
    
    if header is not None:
        for key,value in header:
            header1[key] = value

    header1.tofile(strname,overwrite=bool(overwrite))

    shape1 = tuple(header1[f'NAXIS{ii}'] for ii in range(1, header1['NAXIS']+1))
    shape2 = tuple(header2[f'NAXIS{ii}'] for ii in range(1, header2['NAXIS']+1))
    shape3 = tuple(header3[f'NAXIS{ii}'] for ii in range(1, header3['NAXIS']+1))

    size1 = int(((numpy.product(shape1) * numpy.abs(header1['BITPIX']//8)) + 2879)//2880 * 2880)
    size2 = int(((numpy.product(shape2) * numpy.abs(header2['BITPIX']//8)) + 2879)//2880 * 2880)
    size3 = int(((numpy.product(shape3) * numpy.abs(header3['BITPIX']//8)) + 2879)//2880 * 2880)

    with open(strname, 'rb+') as fobj:
        fobj.seek(len(header1.tostring()) + size1)
        fobj.write(header2.tostring().encode())
        fobj.seek(size2 ,1)
        fobj.write(header3.tostring().encode())
        fobj.seek(size3 - 1,1)
        fobj.write(b'\0')

    return strname, len(header1.tostring()), size1 + len(header2.tostring()), size2 + len(header3.tostring())

class CircSubscriber(cCircSubscriber):
    def __init__(self,prefix,streamName):
        super().__init__(prefix,streamName)
        self.logger = getLogger(f"{prefix}.CircSubscriber")
        self.cb_funcs = []
        self.cb_thread = None
        
    def addTelemFileCallback(self, telemcb):
        # this will eventualy allow registering a callback for when a telemetry file has been written
        # it will return information on the file, perhaps enough to be able to scp the file remotely.
        # info: start_time, start_fnum, Path, host, prefix, etc.
        pass

    def addCallback(self,cb_func):
        if self.cb_thread is None:
            self.cb_funcs.append(cb_func)
            self.cb_thread = threading.Thread(target=self.callback_thread)
            self.cbt_go = 1
            self.cb_thread.start()
        else:
            self.cb_funcs.append(cb_func)

    def removeCallback(self,cb_func):
        if cb_func in self.cb_funcs:
            if len(self.cb_funcs) == 1:
                self.cbt_go = 0
                self.cb_thread.join()
                self.cb_thread = None
            self.cb_funcs.remove(cb_func)
        else:
            raise Exception("This callback is not set")

    def callback_thread(self):
        self.cbt_data = self.set_callback()
        while self.cbt_go!=0:
            try:
                self.wait_for_cb()
            except TimeoutError as e:
                self.logger.info("Timeout....")
            else:
                for c in self.cb_funcs:
                    c(self.cbt_data)
        self.stop_callback()

class CircReader(cCircReader):
    def __init__(self,prefix,streamName):
        super().__init__(prefix,streamName)
        self.cond = threading.Condition()
        self.go_event = threading.Event()
        self.cb_event = threading.Event()
        self.interval = 0.0
        self.cbs = {}
        self.file_cbs = {}
        self.remove = None
        self._thread = None
        self.thread_started = False
        self.thread_users = 0
        self.dir = Path(get_lark_config().DATA_DIR)
        self.logger = getLogger(f"{prefix}.{streamName}")

    def start(self, started=True):
        if self.start_reader():
            self.logger.info("C thread already running")
        if self._start_cb_thread():
            self.logger.info("CB thread already running")
        self.cbt_data = self.set_callback()
        self.thread_started = started

    def _temp_start(self):
        self.thread_users += 1
        if not self._threadRunning:
            self.start(False)

    def _start_cb_thread(self):
        if self._thread is None or not self._thread.is_alive():
            self.cbs.clear()
            self._thread = threading.Thread(target=self.cb_thread)
            self.cb_event.clear()
            self.go_event.clear()
            self._thread.start()
            return 0
        return 1

    def stop(self):
        if self.thread_users == 0:
            self._stop_cb_thread()
            self._thread = None
            self.stop_reader()
        self.thread_started = False

    def _temp_stop(self):
        self.thread_users -= 1
        if not self.thread_started:
            if self.thread_users < 1:
                self.stop()
                self.thread_users = 0

    def _stop_cb_thread(self):
        print("Stopping cb thread")
        if self._thread is not None and self._thread.is_alive():
            self.cb_event.set()
            self.go_event.set()
            self._thread.join()
        print("Stopped cb thread")

    @property
    def decimation(self):
        return self.get_decimation()

    @decimation.setter
    def decimation(self, value):
        if value >= 0:
            self._decimation = int(value)
        else:
            raise TypeError("Decimation cannot be less than zero")

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self,value):
        self._host = value

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self,value):
        self._port = value

    @property
    def multicast(self):
        return self._multicast

    @multicast.setter
    def multicast(self,value):
        self._multicast = value

    @property
    def dataDir(self):
        return self._dir

    @dataDir.setter
    def dataDir(self, value):
        if type(value) is not str:
            raise TypeError("Needs a string")
        else:
            self._dir = Path(value)

    @property
    def shape(self):
        return self._shape

    @shape.setter
    def shape(self,value):
        self._shape = value
        self.cbt_data = self._cbdata

    @property
    def status(self):
        return self._status

    @property
    def info(self):
        return {
            "dec":self._decimation,
            "ip":(self._host,self._port,self._multicast),
            "arr":(self._shape,self._dtype)
        }

    def publish(self,go=1):
        print(f"Starting publisher")
        self.set_publish(go)

    def getDim(self):
        return self.ndim

    def getSize(self):
        """The number of elements"""
        shape = self._size
        return shape

    def getDataType(self):
        chartype = chr(self._dtype)
        dtype = numpy.dtype(chartype)
        return dtype

    def getDataBlock(self,ndata=1):
        self._temp_start()
        retvals = self.prepare_data(ndata)
        self.get_data()
        self._temp_stop()
        return retvals[1:]

    # def addCallback(self,cb_func):
    #     self.logger.info(f"got callback {str(cb_func)}")
    #     if self.cb_thread is None:
    #         self.cb_funcs.append(cb_func)
    #         self.logger.info("Starting callback thread")
    #         self.cb_thread = threading.Thread(target=self.callback_thread)
    #         self.cbt_go = 1
    #         self.cb_thread.daemon = True
    #         self.cb_thread.start()
    #     else:
    #         if self.cb_thread.is_alive():
    #             self.cb_funcs.append(cb_func)
    #         else:
    #             self.cb_thread = None
    #             self.addCallback(cb_func)
    #     return cb_func

    # def removeCallback(self,cb_func):
    #     self.logger.info(f"got callback {str(cb_func)}")
    #     if cb_func in self.cb_funcs:
    #         self.logger.info("Remvoing callback")
    #         if len(self.cb_funcs) == 1:
    #             if self.cb_thread is not None and self.cb_thread.is_alive():
    #                 self.cbt_go = 0
    #                 self.cb_thread.join()
    #             self.cb_thread = None
    #         self.cb_funcs.remove(cb_func)
    #     else:
    #         raise Exception("This callback is not set")
    #     return cb_func

    # def callback_thread(self):
    #     self.cbt_data = self.set_callback()
    #     to_remove = []
    #     while self.cbt_go!=0:
    #         self.logger.info("waiting for cb....")
    #         self.wait_for_cb()
    #         self.logger.info("Calling back....")
    #         for c in self.cb_funcs:
    #             try:
    #                 self.logger.info("executing callback")
    #                 c(self.cbt_data)
    #                 self.logger.info("executed callback")
    #             except EOFError:
    #                 self.logger.info("ERROR")
    #                 to_remove.append(c)
    #         for c in to_remove:
    #             self.cb_funcs.remove(c)
    #             if len(self.cb_funcs) == 0:
    #                 self.cbt_go = 0
    #     self.logger.info("Ending callback thread")
    #     # self.stop_callback()
    def addTelemFileCallback(self, telemcb):
        # this will eventualy allow registering a callback for when a telemetry file has been written
        # it will return information on the file, perhaps enough to be able to scp the file remotely.
        # info: start_time, start_fnum, Path, host, prefix, etc.
        tid = id(telemcb)
        self.file_cbs[tid] = telemcb
        return tid

    def removeTelemFileCallback(self, tid):
        # this will eventualy allow registering a callback for when a telemetry file has been written
        # it will return information on the file, perhaps enough to be able to scp the file remotely.
        # info: start_time, start_fnum, Path, host, prefix, etc.
        self.file_cbs.pop(tid, None)
        return None

    def _addCallback(self, cb, dec, interval):
        self.cond.acquire()
        tid = id(cb)
        if isinstance(cb,rpyc.core.netref.BaseNetref):
            cb = rpyc.timed(cb,0.1)
        self.cbs[tid] = cb,dec
        self.interval = interval
        self.cb_event.set()
        self.cond.release()
        return tid

    def addCallback(self, cb, dec=1, interval=0.0):
        self._temp_start()
        if self._thread.is_alive():
            return self._addCallback(cb,dec,interval)
        else:
            self._start_cb_thread()
            return self._addCallback(cb,dec,interval)

    # def removeCallback(self, cb):
    #     cb_ind = id(cb)
    #     if cb_ind not in self.cbs:
    #         raise IndexError(f"cb {str(cb)} is not registered")
    #     self.cond.acquire()
    #     # cb_ind = self.cbf.index(cb)
    #     # cb_ind = id(cb)
    #     self.logger.info(f"thread_users before = {self.thread_users}")
    #     self.remove = cb_ind
    #     if not self.cond.wait(0.5):
    #         print("Error, thread is blocked")
    #     self.cond.release()
    #     self.logger.info("Removed callback")
    #     self._temp_stop()
    #     self.logger.info(f"thread_users after = {self.thread_users}")

    def removeCallback(self, cb_id):
        if cb_id not in self.cbs:
            raise IndexError(f"cb with id {str(cb_id)} is not registered")
        self.cond.acquire()
        self.remove = cb_id
        if not self.cond.wait(0.5):
            print("Error, thread is blocked")
        self.cond.release()
        self._temp_stop()

    def cb_thread(self):
        self.cbt_data = self.set_callback()
        cnt = 0
        while not self.go_event.wait(self.interval):
        # while not self.go_event.is_set():
            try:
                # self.logger.info("waiting for cb")
                self.wait_for_cb()
                # self.logger.info("waited for cb")
            except RuntimeError:
                print(e)
                self.cb_event.clear()
                continue
            except TimeoutError as e:
                print(e)
                self.cb_event.clear()
                continue
            # for i,cb in enumerate(self.cbf):
            for i,(cb,dec) in self.cbs.items():
                if (cnt%dec) == 0:
                    try:
                        # self.logger.info("cbing")
                        res = cb(self.cbt_data)
                        # res.value
                        # self.logger.info("cbed")
                    except (RuntimeError,TimeoutError,EOFError) as e:
                        print(e)
                        self.logger.warn(e)
                        self.remove = i
            if self.remove is not None:
                self.cond.acquire()
                try:
                    # self.cbf[self.remove] = None
                    self.cbs[self.remove] = None
                # except IndexError as e:
                except KeyError as e:
                    print(e)
                    self.remove = None
                    continue
                # self.cbf.pop(self.remove)
                # self.cbd.pop(self.remove)
                del self.cbs[self.remove]
                # if len(self.cbf) == 0:
                if len(self.cbs) == 0:
                    self.cb_event.clear()
                self.cond.notify()
                self.remove = None
                self.cond.release()
            cnt = (cnt+1)%1000
            self.cb_event.wait()
        self.logger.info("Ending callback thread")


    # def callback_thread(self, cb_func):
    #     self.cbt_data = self.set_callback()
    #     to_remove = []
    #     while self.cbt_go!=0:
    #         self.logger.info("waiting for cb....")
    #         self.wait_for_cb()
    #         self.logger.info("Calling back....")
    #         try:
    #             self.logger.info("executing THIS callback")
    #             cb_func(self.cbt_data.copy())
    #             self.logger.info("executed callback")
    #         except EOFError:
    #             self.logger.info("ERROR")
    #             to_remove.append(c)
    #         for c in to_remove:
    #             self.cb_funcs.remove(c)
    #             if len(self.cb_funcs) == 0:
    #                 self.cbt_go = 0
    #     self.logger.info("Ending callback thread")
    #     # self.stop_callback()

    def call_callbacks(self,data):
        for c in self.cb_funcs:
            c(data)

    # def prepare_save(self,a,b,c,d,e):
    #     print("Doing prepare_save with ", a, b, c, d, e)
    #     return super().prepare_save(a,b,c,d,e)

    # def start_save(self):
    #     print("Doing start_save")
    #     return super().start_save()

    # def wait_for_save(self, a):
    #     print("Doing wait for save with ", a)
    #     return super().wait_for_save(a)

    def saveFrames(self, fname, frames, overwrite=0):
        self._temp_start()
        fpath = Path(fname)
        if not fpath.is_absolute():
            fpath = (self._dir / fpath).resolve()
        else:
            fpath = fpath.resolve()
        framesperfile = int(MAX_FILE_SIZE/(self.getSize()*self.getDataType().itemsize))
        print("Frames per file = ",framesperfile)
        wholefiles = frames//framesperfile
        print(f"wholefiles = {wholefiles}")
        remainder = frames%framesperfile
        print(f"remainder = {remainder}")

        def make_cfits(a,b,c,frames,overwrite):
            print("Doing make_cfits with ",a,b,c,frames,overwrite)
            global make_cfits
            return make_cfits(a,b,c,frames,overwrite=overwrite)

        fileh = [None,None]
        findex = [None,None]
        saved = 0
        for i in range(wholefiles+int(remainder>0)):
            fname = fpath.with_name(fpath.name+f"-{i:0>3}")
            if (frames-saved)//framesperfile > 0:
                _frames = framesperfile
            else:
                _frames = (frames-saved)%framesperfile
            try:
                fname , d, t, n = make_cfits(fname,self.getSize(),self.getDataType(),frames=_frames,overwrite=overwrite)
            except OSError as e:
                self.cancel_save()
                raise FileExistsError(str(e))
            fileh[i%2] = open(fname,mode="rb+")
            print(f"preparing findex[{i%2}]")
            findex[i%2] = self.prepare_save(fileh[i%2].fileno(),d,d+t,d+t+n,_frames)
            print(f"prepared findex[{i%2}] = {findex[i%2]}")
            saved += _frames
            now = datetime.datetime.now().isoformat("_")
            self.start_save()
            if i > 0:
                print(f"waiting for findex[{1-i%2}] = {findex[1-i%2]}")
                self.wait_for_save(findex[1-i%2])
                fileh[1-i%2].close()
                todel = []
                for tid,file_cb in self.file_cbs.items():
                    try:
                        file_cb({
                            "prefix": self._prefix,
                            "stream": self._streamName,
                            "timestamp": now,
                            "filepath": fname
                        })
                    except Exception as e:
                        print(e)
                        todel.append(tid)
                for tid in todel:
                    self.file_cbs.pop(tid)
        self.wait_for_save(findex[i%2])
        fileh[i%2].close()
        self._temp_stop()
        return fpath
        # if wholefiles==0:
        #     pass
        # if remainder==0:
        #     remainder=framesperfile
        #     wholefiles-=1
        # cnt = 0
        # for i in range(wholefiles):
        #     fname = fpath.with_name(fpath.name+f"-{cnt}")
        #     fname, d,t,n = make_cfits(fname, self.getSize(), self.getDataType(), frames=framesperfile)
        #     fileh = open(fname,mode="rb+")
        #     print(d,t,n)
        #     findex = self.prepare_save(fileh.fileno(),d,d+t,d+t+n,frames)
    # def saveFile(self, fname, frames=100):
    #     fpath = Path(fname)
    #     if not fpath.is_absolute():
    #         fpath = self._dir / fname
    #     fname, d,t,n = make_cfits(fpath, self.getSize(), self.getDataType(), frames=frames)
    #     fileh = open(fname,mode="rb+")
    #     print(d,t,n)
    #     findex = self.prepare_save(fileh.fileno(),d,d+t,d+t+n,frames)
    #     if findex is not None:
    #         print("waiting for file....")
    #         self.wait_for_save(findex)
    #         print("waited for file...")
    #         fileh.close()
    #     else:
    #         fileh.close()
    #         os.remove(fname)

    # def save3File(self,fname1,fname2,fname3,frames=100):
    #     fname1 = self._dir / fname1
    #     fname1 , d, t, n = make_cfits(fname1,self.getSize(),self.getDataType(),frames=frames)
    #     fileh1 = open(fname1,mode="rb+")
    #     print(d,t,n)
    #     print(type(d),type(t),type(n))
    #     print(type(fileh1.fileno()),type(frames))
    #     # fits_file1 = fits.open(fileh1,mode='update',memmap=True)
    #     try:
    #         # findex1 = self.prepare_save(1,2,3,4,5)
    #         print(int(fileh1.fileno()),int(d),int(d+t),int(d+t+n),int(frames))
    #         findex1 = self.prepare_save(int(fileh1.fileno()),int(d),int(d+t),int(d+t+n),int(frames))
    #         # findex1 = self.prepare_save(1,int(d),int(d+t),int(d+t+n),int(frames))
    #         # findex1 = self.prepare_save(int(fileh1.fileno()),1,int(d+t),int(d+t+n),int(frames))
    #         # findex1 = self.prepare_save(int(fileh1.fileno()),int(d),1,int(d+t+n),int(frames))
    #         # findex1 = self.prepare_save(int(fileh1.fileno()),int(d),int(d+t),1,int(frames))
    #         # findex1 = self.prepare_save(int(fileh1.fileno()),int(d),int(d+t),int(d+t+n),1)
    #     except Exception as e:
    #         fileh1.close()
    #         raise e
    #     print(findex1)
    #     fname2 = self._dir / fname2
    #     fname2, d,t,n = make_cfits(fname2,self.getSize(),self.getDataType(),frames=frames)
    #     fileh2 = open(fname2,mode="rb+")
    #     print(d,t,n)
    #     # fits_file2 = fits.open(fileh2,mode='update',memmap=True)
    #     findex2 = self.prepare_save(fileh2.fileno(),d,d+t,d+t+n,frames)
    #     print("waiting for first file")
    #     self.start_save()
    #     if findex1 is not None:
    #         self.wait_for_save(findex1)
    #         fileh1.close()
    #         print("got 1st file")
    #     else:
    #         fileh1.close()
    #         os.remove(fname1)
    #     fname3 = self._dir / fname3
    #     fname3, d,t,n = make_cfits(fname3,self.getSize(),self.getDataType(),frames=frames)
    #     fileh3 = open(fname3,mode="rb+")
    #     print(d,t,n)
    #     # fits_file2 = fits.open(fileh2,mode='update',memmap=True)
    #     try:
    #         findex3 = self.prepare_save(fileh3.fileno(),d,d+t,d+t+n,frames)
    #     except RuntimeError as e:
    #         print(e)
    #         time.sleep(1)
    #         findex3 = self.prepare_save(fileh3.fileno(),d,d+t,d+t+n,frames)
    #     print("waiting for second file")
    #     if findex2 is not None:
    #         self.wait_for_save(findex2)
    #         fileh2.close()
    #         print("got second file")
    #     else:
    #         fileh2.close()
    #         os.remove(fname2)

    #     if findex3 is not None:
    #         self.wait_for_save(findex3)
    #         fileh3.close()
    #         print("got third file")
    #     else:
    #         fileh3.close()
    #         os.remove(fname3)

    # def saveNFiles(self,fname,frames,files):
    #     fpath = Path(fname)
    #     if not fpath.is_absolute():
    #         fpath = (self._dir / fpath).resolve()
    #     cnt = 0
    #     fileh = [0,0]
    #     findex = [0,0]
    #     for i in range(files):
    #         fname = fpath.with_name(fpath.name+f"-{i}")
    #         fname , d, t, n = make_cfits(fname,self.getSize(),self.getDataType(),frames=frames)
    #         fileh[i%2] = open(fname,mode="rb+")
    #         findex[i%2] = self.prepare_save(fileh[i%2].fileno(),d,d+t,d+t+n,frames)




    #         fname = fpath.with_name(fpath.name+f"-{cnt}")
    #         fname , d, t, n = make_cfits(fname,self.getSize(),self.getDataType(),frames=frames)
    #         fileh2 = open(fname,mode="rb+")
    #         findex2 = self.prepare_save(fileh1.fileno(),d,d+t,d+t+n,frames)
    #         self.start_save()
    #         self.wait_for_save(findex1)
    #     fname2 = self._dir / fname2
    #     fname2, d,t,n = make_cfits(fname2,self.getSize(),self.getDataType(),frames=frames)
    #     fileh2 = open(fname2,mode="rb+")
    #     print(d,t,n)
    #     # fits_file2 = fits.open(fileh2,mode='update',memmap=True)
    #     findex2 = self.prepare_save(fileh2.fileno(),d,d+t,d+t+n,frames)
    #     print("waiting for first file")
    #     self.start_save()
    #     if findex1 is not None:
    #         self.wait_for_save(findex1)
    #         fileh1.close()
    #         print("got 1st file")
    #     else:
    #         fileh1.close()
    #         os.remove(fname1)
    #     if findex2 is not None:
    #         self.wait_for_save(findex2)
    #         fileh2.close()
    #         print("got second file")
    #     else:
    #         fileh2.close()
    #         os.remove(fname2)

class TelemetrySystem:
    coreStreamNames = ["rtcCentBuf","rtcFluxBuf","rtcMirrorBuf","rtcStatusBuf","rtcSubLocBuf","rtcTimeBuf"]
    otherStreamNames = ["rtcActuatorBuf","rtcErrorBuf"]
    pxlStreamNames = ["rtcCalPxlBuf","rtcPxlBuf"]
    def __init__(self,prefix="",connect=1):
        self.telem_logger = getLogger(f"{prefix}.TelemSys")
        self.CircReaders: dict[str,CircReader] = {}
        self.telem_initialised = 0
        if connect:
            self.telem_init(prefix)

    def telem_init(self,prefix):
        def addStream(stream):
            cnt = 5
            while cnt:
                try:
                    self.telem_logger.info(f"Opening CircReader for {stream}")
                    self.CircReaders[stream] = CircReader(prefix,stream)
                except FileNotFoundError as e:
                    print(f"{stream} not yet ready, retrying")
                    cnt-=1
                    time.sleep(0.05)
                else:
                    break
            if cnt==0:
                raise FileNotFoundError(f"{stream} not found")
        if not self.telem_initialised:
            for stream in self.coreStreamNames:
                addStream(stream)
            for stream in self.pxlStreamNames:
                addStream(stream)
            # for stream in self.otherStreamNames:
            #     addStream(stream)
            self.telem_initialised = 1

    def startTelemetry(self):
        for stream in self.coreStreamNames:
            if stream in self.CircReaders.keys():
                self.CircReaders[stream].start()

        for stream in self.pxlStreamNames:
            if stream in self.CircReaders.keys():
                self.CircReaders[stream].start()

    def startOtherStreams(self):
        for stream in self.otherStreamNames:
            if stream in self.CircReaders.keys():
                self.CircReaders[stream].start()

    def stopTelemetry(self):
        for s,cr in self.CircReaders.items():
            cr.stop()

    def startStream(self, name):
        if name in self.CircReaders.keys():
            self.CircReaders[name].start()

    def stopStream(self, name):
        self.CircReaders[name].stop()

    def streamStatus(self):
        status = {}
        for name, value in self.CircReaders.items():
            status[name] = value.status
        return status

    def streamInfo(self):
        status = {}
        for name, value in self.CircReaders.items():
            status[name] = value.info
        return status

    def getStreamBlock(self,stream,Nframes):
        if type(stream) in (list,tuple):
            if len(stream) == 1:
                return self.getStreamBlock(stream[0],Nframes)
            barrier = CircSync(len(stream))
            retvals = [self.CircReaders[name].prepare_data(Nframes) for name in stream]
            funcs = [self.CircReaders[name].get_data for name in stream]
            args = [(barrier,)]*len(funcs)
            # args = [()]*len(funcs)
            threadSynchroniser(funcs,args)
            return {name:retval[1:] for name,retval in zip(stream,retvals)}
        elif type(stream) is str:
            return self.CircReaders[stream].getDataBlock(Nframes)
            
    def addTelemFileCallback(self, stream, telemcb):
        # this will eventualy allow registering a callback for when a telemetry file has been written
        # it will return information on the file, perhaps enough to be able to scp the file remotely.
        # info: start_time, start_fnum, Path, host, prefix, etc.
        if isinstance(stream,(list,tuple)):
            pass
        elif stream in ("ALL",):
            return {name:value.addTelemFileCallback(telemcb) for name,value in self.CircReaders.items()}
        elif isinstance(stream,str):
            return self.CircReaders[stream].addTelemFileCallback(telemcb)
            
    def removeTelemFileCallback(self, stream, pid):
        # this will eventualy allow registering a callback for when a telemetry file has been written
        # it will return information on the file, perhaps enough to be able to scp the file remotely.
        # info: start_time, start_fnum, Path, host, prefix, etc.
        if type(stream) in (list,tuple):
            pass
        elif isinstance(stream,str):
            return self.CircReaders[stream].removeTelemFileCallback(pid)

    def addCallback(self, stream, cb_func, dec=1, interval=0.01):
        if type(stream) in (list,tuple):
            pass
        elif type(stream) is str:
            return self.CircReaders[stream].addCallback(cb_func,dec,interval)
            
    def removeCallback(self, stream, cb_ind):
        if type(stream) in (list,tuple):
            pass
        elif type(stream) is str:
            return self.CircReaders[stream].removeCallback(cb_ind)

    def saveContinuously(self, stream, framesPerFile=FRAMES_PER_FILE):
        if type(stream) in (list,tuple):
            pass
        elif type(stream) is str:
            return self.CircReaders[stream].saveContinuously(framesPerFile)

    def stopSaving(self,stream):
        if type(stream) in (list,tuple):
            pass
        elif type(stream) is str:
            return self.CircReaders[stream].stopSaving()

    def saveFrames(self, stream, Nframes, file_name, overwrite=0):
        if type(stream) in (list,tuple):
            pass
        elif type(stream) is str:
            return self.CircReaders[stream].saveFrames(file_name, Nframes, overwrite)

    def startStreamPublish(self,stream):
        if type(stream) in (list,tuple):
            pass
        elif type(stream) is str:
            return self.CircReaders[stream].publish(1)

    def stopStreamPublish(self,stream):
        if type(stream) in (list,tuple):
            pass
        elif type(stream) is str:
            return self.CircReaders[stream].publish(0)

    def setDecimation(self,stream,value):
        if type(stream) in (list,tuple):
            pass
        elif type(stream) is str:
            self.CircReaders[stream].decimation = value

    def setStreamHost(self,stream,value):
        if type(stream) in (list,tuple):
            pass
        elif type(stream) is str:
            self.CircReaders[stream].host = value

    def setStreamPort(self,stream,value):
        if type(stream) in (list,tuple):
            pass
        elif type(stream) is str:
            self.CircReaders[stream].port = value

    def setStreamMulticast(self,stream,value):
        if type(stream) in (list,tuple):
            pass
        elif type(stream) is str:
            self.CircReaders[stream].multicast = value

    # def setStreamShape(self,stream,shape=None):
    #     if shape is None:
    #         if stream == "rtcCentBuf":
    #             ncam = self.get("ncam")
    #             nsub = self.get("nsub")
    #             subapFlag = self.get("subapFlag")
    #             vsubs = []
    #             ncumsub = 0
    #             for k in range(ncam):
    #                 vsubs.append(subapFlag[ncumsub:ncumsub+nsub[k]].sum())
    #                 ncumsub+=nsub[k]
    #             if all(vsubs==vsubs[0]):
    #                 shape = ncam,vsubs[0]*2
    #             else:
    #                 print(f"Unable to reshape array to {ncam}{vsubs}")
    #                 return 1
    #             self.CircReaders[stream].shape = shape
    #     else:
    #         self.CircReaders[stream].shape = shape

    def setStreamShape(self,stream,shape=None):
        if shape is None:
            if stream == "rtcCentBuf":
                ncam = self.get("ncam")
                nsub = self.get("nsub")
                subapFlag = self.get("subapFlag")
                vsubs = []
                ncumsub = 0
                for k in range(ncam):
                    vsubs.append(int(subapFlag[ncumsub:ncumsub+nsub[k]].sum()))
                    ncumsub+=nsub[k]
                if ncam!=1:
                    if all(v==vsubs[0] for v in vsubs):
                        shape = ncam,vsubs[0]*2
                    else:
                        print(f"Unable to reshape array to {ncam},{vsubs}")
                        return 1
                else:
                    shape = (vsubs[0]*2,)
            elif stream in ("rtcPxlBuf","rtcCalPxlBuf"):
                ncam = self.get("ncam")
                npxlx = self.get("npxlx")
                npxly = self.get("npxly")
                if ncam!=1:
                    if all(x==npxlx[0] and y==npxly[0] for x,y in zip(npxlx,npxly)):
                        shape = (ncam,int(npxlx[0]),int(npxly[0]))
                    else:
                        print(f"Unable to reshape array to {ncam},{npxlx},{npxly}")
                        return 1
                else:
                    shape = (int(npxlx[0]),int(npxly[0]))
            elif stream=="rtcSubLocBuf":
                nsub = int(sum(self.get("nsub")))
                shape = (nsub,6)

            else:
                print("stream can't be reshaped")

            self.setStreamShape(stream, shape) # the recursion is to aid in testing using rpyc
            # self.CircReaders[stream].shape = shape
        else:
            self.CircReaders[stream].shape = shape

