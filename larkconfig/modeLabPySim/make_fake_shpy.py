
from pathlib import Path
import sys
from lark.darc import FITS
import numpy
from matplotlib import pyplot
from PIL import Image

DATA_DIR = Path("~/temp/DATA_DIR").expanduser()
IM_DIR = DATA_DIR/"images"

if not IM_DIR.exists():
    IM_DIR.mkdir(parents=True)

n_img = 200
dtype = numpy.int16

py_npxly = 264
py_npxlx = 170

sh_npxly = 264
sh_npxlx = 242

sc_npxly = 512
sc_npxlx = 512

py_images = numpy.zeros((n_img,py_npxlx*py_npxly),dtype=dtype)
pyff_images = numpy.zeros((n_img,sh_npxlx*sh_npxly),dtype=dtype)
sh_images = numpy.zeros((n_img,sh_npxlx*sh_npxly),dtype=dtype)
sc_images = numpy.zeros((n_img,sc_npxlx*sc_npxly),dtype=dtype)

pyff = numpy.random.normal(100,30,n_img*sh_npxlx*sh_npxly)
pyff += numpy.random.poisson(100.0, n_img*sh_npxlx*sh_npxly)
pyff = pyff.astype(dtype)
pyff.shape = n_img,sh_npxlx*sh_npxly

pyff[numpy.where(pyff<0)] = 0
### make py windowed

pyff_images = pyff

rotation1 = 0.05
rotation2 = -0.02

from_edge = 35
cenpy = 170//2,264//2
pos0 = numpy.array([[from_edge,from_edge],[from_edge,264-from_edge],[170-from_edge,from_edge],[170-from_edge,264-from_edge]],float)
pos1 = pos0 + numpy.array((5,8))
pos2 = numpy.zeros_like(pos0)
for i in range(4):
    lx = pos0[i,0]-cenpy[0]
    ly = pos0[i,1]-cenpy[1]
    r = numpy.sqrt(lx**2+ly**2)
    a = numpy.arctan2(lx,ly)
    pos2[i,0] = r*numpy.sin(a+rotation1)+cenpy[0]
    pos2[i,1] = r*numpy.cos(a+rotation1)+cenpy[1]
pos3 = numpy.zeros_like(pos0)
for i in range(4):
    lx = pos0[i,0]-cenpy[0]
    ly = pos0[i,1]-cenpy[1]
    r = numpy.sqrt(lx**2+ly**2)
    a = numpy.arctan2(lx,ly)
    pos3[i,0] = r*numpy.sin(a+rotation2)+cenpy[0]
    pos3[i,1] = r*numpy.cos(a+rotation2)+cenpy[1]
pos3 -= numpy.array((5,8))

# positions = [pos0,pos1,pos2,pos3]
positions = [pos2]

radius0 = 20
radius1 = 16
radius2 = 23

# radii = [radius0,radius1,radius2]
radii = [radius0]

flux0 = [100,100,100,100]
flux1 = [60,115,80,95]
flux2 = [80,85,105,130]

# fluxes = [flux0,flux1,flux2]
fluxes = [flux1]

scale = 10

import itertools

vals = itertools.product(positions,radii,fluxes)

for number,v in enumerate(vals):
    pos,radius,flux = v
    pos = pos.astype(int)
    print(f"pos = {pos}")
    print(f"radius = {radius}")
    print(f"flux = {flux}")
    print(f"i = {number}")

    circ_kern = numpy.zeros((2*radius*scale,2*radius*scale),int)
    for i in range(2*radius*scale):
        for j in range(2*radius*scale):
            if (i-radius*scale)**2+(j-radius*scale)**2 < (radius*scale)**2:
                circ_kern[i,j] = 1

    indx,indy = numpy.where(circ_kern==1)

    image = numpy.zeros((py_npxlx*scale,py_npxly*scale),dtype=dtype)

    for i in range(n_img):
        image[:,:] = 0
        for j,p in enumerate(pos):
            p0 = p[0]
            p1 = p[1]
            rando = numpy.random.randint(0,flux[j],indx.shape[0])
            image[indx+scale*(p0-radius),indy+scale*(p1-radius)] = rando
        im = Image.fromarray(image)
        im = im.resize((py_npxly,py_npxlx))
        im = numpy.asarray(im)
        im = im-numpy.amin(im)
        py_images[i] = im.flatten()
    
    FITS.Write(py_images,IM_DIR/f"py_images-{number}.fits")


# make py full frame

from_edge = 35
cenpy = sh_npxlx//2,264//2
pos0 = numpy.array([[from_edge,from_edge],[from_edge,264-from_edge],[sh_npxlx-from_edge,from_edge],[sh_npxlx-from_edge,264-from_edge]],float)
pos1 = pos0 + numpy.array((5,8))
pos2 = numpy.zeros_like(pos0)
for i in range(4):
    lx = pos0[i,0]-cenpy[0]
    ly = pos0[i,1]-cenpy[1]
    r = numpy.sqrt(lx**2+ly**2)
    a = numpy.arctan2(lx,ly)
    pos2[i,0] = r*numpy.sin(a+rotation1)+cenpy[0]
    pos2[i,1] = r*numpy.cos(a+rotation1)+cenpy[1]
pos3 = numpy.zeros_like(pos0)
for i in range(4):
    lx = pos0[i,0]-cenpy[0]
    ly = pos0[i,1]-cenpy[1]
    r = numpy.sqrt(lx**2+ly**2)
    a = numpy.arctan2(lx,ly)
    pos3[i,0] = r*numpy.sin(a+rotation2)+cenpy[0]
    pos3[i,1] = r*numpy.cos(a+rotation2)+cenpy[1]
pos3 -= numpy.array((5,8))

# positions = [pos0,pos1,pos2,pos3]
positions = [pos2]

vals = itertools.product(positions,radii,fluxes)

for number,v in enumerate(vals):
    pos,radius,flux = v
    pos = pos.astype(int)
    print(f"pos = {pos}")
    print(f"radius = {radius}")
    print(f"flux = {flux}")
    print(f"i = {number}")

    circ_kern = numpy.zeros((2*radius*scale,2*radius*scale),int)
    for i in range(2*radius*scale):
        for j in range(2*radius*scale):
            if (i-radius*scale)**2+(j-radius*scale)**2 < (radius*scale)**2:
                circ_kern[i,j] = 1

    indx,indy = numpy.where(circ_kern==1)

    image = numpy.zeros((sh_npxlx*scale,sh_npxly*scale),dtype=dtype)

    for i in range(n_img):
        image[:,:] = 0
        for j,p in enumerate(pos):
            p0 = p[0]
            p1 = p[1]
            rando = numpy.random.randint(0,flux[j],indx.shape[0])
            image[indx+scale*(p0-radius),indy+scale*(p1-radius)] = rando
        im = Image.fromarray(image)
        im = im.resize((sh_npxly,sh_npxlx))
        im = numpy.asarray(im)
        im = im-numpy.amin(im)
        pyff_images[i] += im.flatten()
    
    FITS.Write(pyff_images,IM_DIR/f"pyff_images-{number}.fits")
    
number = 0
im = FITS.Read(IM_DIR/f"pyff_images-{number}.fits")[1]
im.shape = n_img,sh_npxlx,sh_npxly

# pyplot.imshow(im[0])
# pyplot.show()

# sys.exit()
    
# sh images
image = numpy.zeros((sh_npxlx,sh_npxly),dtype=dtype)
for i in range(n_img):
    k = i*3
    l1 = numpy.arange(0,k,1)[max(0,k-sh_npxly):min(k,sh_npxlx)]
    l2 = numpy.arange(k-1,-1,-1)[max(0,k-sh_npxly):min(k,sh_npxlx)]
    image[l1,l2] = 100
    sh_images[i] = image.flatten()

FITS.Write(sh_images,IM_DIR/f"sh_images.fits")
    
# sc images
image = numpy.zeros((sc_npxlx,sc_npxly),dtype=dtype)
for i in range(n_img):
    k = i*3
    l1 = numpy.arange(0,k,1)[max(0,k-sc_npxly):min(k,sc_npxlx)]
    l2 = numpy.arange(k-1,-1,-1)[max(0,k-sc_npxly):min(k,sc_npxlx)]
    image[l1,l2] = 100
    sc_images[i] = image.flatten()

FITS.Write(sc_images,IM_DIR/f"sc_images.fits")