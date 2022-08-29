


from pathlib import Path
from typing import Dict
from astropy.io import fits
import sys

from matplotlib import pyplot
import numpy

def convert_cfits(fname):
    fpath = Path(fname)
    new_path = fpath.with_suffix(".fits")
    with fits.open(fname) as hdul:
        for hdu in hdul:
            if "nd" in hdu.header:
                shape = [hdu.header[f"nd{i+1}"] for i in range(hdu.header["nd"])]
                try:
                    hdu.data.shape = shape
                except ValueError as e:
                    print(e)
            hdu.data = (hdu.data + hdu.header.get("BZERO",0)).newbyteorder()
        hdul.writeto(new_path,overwrite=True)
    return str(new_path)

def add_to_header(fname,header:Dict[str,object],index=0):
    with fits.open(fname, mode="update") as hdul:
        hdu: fits.PrimaryHDU = hdul[index]
        for key, value in header.items():
            if value is None:
                hdu.header.pop(key, None)
            else:
                hdu.header[key] = value
                
def reshape_fits(fname,shape,index=0):
    with fits.open(fname, mode="update") as hdul:
        hdu = hdul[index]
        hdu.data.shape = shape

if __name__ == "__main__":

    fname = sys.argv[1]

    # fname = convert_cfits(fname)
    
    newhead = {"nd":3,"nd1":782,"nd2":241,"nd3":264}
    newhead = {"nd":None,"nd0":None,"nd1":None,"nd2":None,"nd3":None}
    
    add_to_header(fname,newhead)
    
    # reshape_fits(fname,(782,242,264),0)

    with fits.open(fname) as hdul:
        print(repr(hdul[0].header))
        hdu = hdul[0]
        pyplot.imshow(hdu.data[0])
        pyplot.show()
        for hdu in hdul:
            print(hdu.data[:5])
