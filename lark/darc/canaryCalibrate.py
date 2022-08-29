#darc, the Durham Adaptive optics Real-time Controller.
#Copyright (C) 2010 Alastair Basden.

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
"""A script to calibrate CANARY."""
import sys
import numpy

import FITS
import controlCorba


def computeThreshold(img,n,subloc,ncam,npxlx,npxly,nsub):
    pxlcum=0
    pos=0
    thr=numpy.zeros((nsub.sum(),),numpy.float32)
    for i in range(ncam):
        data=img[pxlcum:pxlcum+npxlx[i]*npxly[i]]
        data.shape=npxly[i],npxlx[i]
        pxlcum+=npxly[i]*npxlx[i]
        for j in range(nsub[i]):
            sl=subloc[pos]
            if sl[2]!=0:
                subimg=list(data[sl[0]:sl[1]:sl[2],sl[3]:sl[4]:sl[5]].ravel())
                subimg.sort()
                thr[pos]=(subimg[-n]+subimg[-n-1])/2.
            pos+=1
    return thr
        



if __name__=="__main__":
    if len(sys.argv)>1:
        prefix=sys.argv[1]
    else:
        prefix=""
    ctrl=controlCorba.controlClient(controlName=prefix+"Control",debug=0)
    y=input("Do you want to do pixel calibration? y/n")
    if y=="y":
        y=input("Do you want to do dark map calibration?  If so, please turn of light sources. y/n")
        if y=="y":
            n=input("Number of frames to average?")
            n=int(n)
            ctrl.set("bgImage",None)
            ctrl.set("flatField",None)
            ctrl.set("darkNoise",None)
            ctrl.set("thresholdType",0)
            dark=ctrl.AverageImage(n,whole=1)
            ctrl.set("darkNoise",dark)
            FITS.Write(dark,"darkNoise.fits")
        y=input("Do you want to do flat field calibration?  If so, please illuminate with a flat field.  y/n")
        if y=="y":
            n=input("Number of frames to average?")
            n=int(n)
            ctrl.set("bgImage",None)
            ctrl.set("flatField",None)
            ctrl.set("thresholdType",0)
            ff=ctrl.AverageImage(n,whole=1)
            ctrl.set("flatField",ff)
            FITS.Write(ff,"flatField.fits")
        y=input("Do you want to do a background image calibration?  If so, please turn off light sources and get your background ready. y/n")
        if y=="y":
            n=input("Number of frames to average?")
            n=int(n)
            ctrl.set("bgImage",None)
            ctrl.set("thresholdType",0)
            bg=ctrl.AverageImage(n,whole=1)
            ctrl.set("bgImage",bg)
            FITS.Write(bg,"bgImage.fits")
    y=input("Do you want to do threshold calibration? y/n")
    if y=="y":
        n=input("Please make sure your sub-apertures have spots.  How many pixels to you want to allow per subaperture?")
        n=int(n)
        ctrl.set("thresholdType",0)
        thr=ctrl.AverageImage(n,whole=1)
        subloc=ctrl.Get("subapLocation")
        ncam=ctrl.Get("ncam")
        npxlx=ctrl.Get("npxlx")
        npxly=ctrl.Get("npxly")
        nsub=ctrl.Get("nsub")
        #nsuby=ctrl.Get("nsuby")
        val=computeThreshold(thr,n,subloc,ncam,npxlx,npxly,nsub)
        mode=input("What thresholding mode do you want? 1/2")
        mode=int(mode)
        ctrl.set("thresholdType",mode)
        ctrl.set("thresholdValue",val)
        FITS.Write(val,"thresholdValue.fits")
    else:
        n=input("Should I use brightest N pixels thresholding mode?  If so enter the number of pixels to be used in each sub-aperture (20?) - enter 0 if you don't with to use this feature")
        if n=="n":
            n=0
        n=int(n)
        ctrl.set("useBrightest",n)
        mode=input("Do you want to implement any thresholding?  What mode?  0/1/2 (Note - if you have chosen to implement using the brightest N pixels, this operation is carried out after the thresholding defined here).")
        mode=int(mode)
        val=0
        if mode==1 or mode==2:
            val=input("What threshold value should be used?")
            val=float(val)
        ctrl.set("thresholdType",mode)
        ctrl.set("thresholdValue",val)

    y=input("Do you want to calibrate reference slopes? y/n")
    if y=="y":
        n=input("Please make sure your sub-apertures have spots.  How many frames to average?")
        n=int(n)
        ctrl.set("refCentroids",None)
        ref=ctrl.AverageCentroids(n)
        ctrl.set("refCentroids",ref)
        FITS.Write(ref,"refCentroids.fits")
    y=input("Do you want to create an interaction matrix? y/n")
    if y=="y":
        v=input("How many dac values should I change for each poke? 1000? 2000?")
        v=int(v)
        n=input("How many frames should I average for each poke?")
        n=int(n)
        ig=input("How many frames should I allow for mirror settling?")
        ig=int(ig)
        pmx=ctrl.AutoPoke(ig,n,v)
        FITS.Write(pmx,"pmx.fits")
        y=input("Should I compute the least-squares control matrix? y/n")
        if y=="y":
            rcond=input("What conditioning value should I use? 0.1? 0.01?")
            rcond=float(rcond)
            u,e,vt=numpy.linalg.svd(pmx)
            mask=e/e[0]>rcond
            ie=numpy.where(mask,1/e,0)
            neig=e.shape[0]
            for i in range(neig):
                u.T[i]*=ie[i]
            rmx=-numpy.dot(vt.T[:,:neig],u.T[:neig,:neig]).T
            FITS.Write(rmx,"rmx.fits")
            ctrl.set("rmx",rmx)
    print("Calibration done")
