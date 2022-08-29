#darc, the Durham Adaptive optics Real-time Controller.
#Copyright (C) 2013 Alastair Basden.

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU Affero General Public License as
#published by the Free Software Foundation, either version 3 of the
#License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU Affero General Public License for more details.

#You should have received a copy of the GNU Affero General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.
#This is a configuration file for CANARY.
#Aim to fill up the control dictionary with values to be used in the RTCS.

#A basic config file for getting pixels out of the OCAM.

from pathlib import Path
from lark.utils import import_from
import numpy

file_path = Path(__file__).parent.resolve()
parent = file_path/"configLGSWF.py"
control = import_from(parent).control
delay = 10000
camfile = 1

if camfile:
    camerasOpen = 0
    try:
        # use darc/test/make_fake_images.py to make this file...
        # fname=b"ncam2-240x240-264x170-10.fits"
        # fname=b"/home/canapyrtc/git/canapy-rtc/ncam2-264x242-264x170-200.fits"
        # fname=b"/home/canapyrtc/git/canapy-rtc/data/pyr_test-0.fits"
        # fname = "/home/canapyrtc/git/data/pyr_test-35.fits"
        # fname = "/home/canapyrtc/git/data/py_images-0.fits"
        # fname = "/home/canapyrtc/git/data/pyff_images-0.fits"
        fname = Path("~/temp/DATA_DIR/images/pyff_images-0.fits").expanduser()
        if not fname.exists():
            raise Exception("File does not exist!")
        fname = str(fname)
        while len(fname)%4!=0:#zero pad to it fits into 32bit int array
            fname += "\0"
        cameraParams = numpy.frombuffer(fname.encode(),dtype="i")
        camerasOpen = 1
    except Exception as e:
        print(e)
        print("No camfile found, not using one")
        cameraParams = None

    cameraName = "libcamfile.so"
else:
    cameraName = "libcamzmqsub.so"
    camerasOpen = 1
    address = "tcp://localhost:18998"
    l = len(address)
    while(len(address)%4!=0):
        address+="\0"
    intaddr = numpy.frombuffer(address.encode(),dtype="i")
    cameraParams = numpy.array((0,l,*intaddr),dtype="i")

control["cameraName"] = cameraName
control["cameraParams"] = cameraParams
control["camerasOpen"] = camerasOpen
control["delay"] = delay
