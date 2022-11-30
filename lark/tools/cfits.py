from astropy.io import fits
import numpy


def getdata(filename, *args, header=None, lower=None, upper=None, view=None, **kwargs):
    raw:numpy.ndarray
    raw, hdr = fits.getdata(filename, *args, header=True, lower=lower, upper=upper, view=view, **kwargs)
    if "BZERO" in hdr:
        data = (raw+hdr["BZERO"]).newbyteorder()
    else:
        data = raw.newbyteorder()
    if header:
        return data, header
    return data
    
def appendToHeader(filename, index=0, **kwargs):
    allowed_types = (str,int,float)
    with fits.open(filename, mode='update') as hdul:
        for key,value in kwargs.items():
            if not isinstance(value,allowed_types):
                raise ValueError(f"For now, header values must be one of types {allowed_types}")
            if index is None:
                for hdu in hdul:
                    hdu.header[key] = value
            else:
                hdul[index].header[key] = value
        hdul.flush()
    
if __name__ == "__main__":
    
    from matplotlib import pyplot
    
    test_files = ['/opt/lark/data/darc/2022-11-28/1213_15-lgswf/rtcCentBuf-2022-11-28T1213_36-703633-000.cfits', '/opt/lark/data/darc/2022-11-28/1213_15-lgswf/rtcCentBuf-2022-11-28T1213_36-703633-001.cfits']
    
    data = []
    ftimes = []
    fnums = []
    for file in test_files:
        data.append(getdata(file,0))
        ftimes.append(getdata(file,1))
        fnums.append(getdata(file,2))
        
    print(data)
    print(data[0].shape)
    pyplot.plot(fnums[0])
    pyplot.plot(numpy.arange(len(fnums[1]))+len(fnums[0]),fnums[1])
    pyplot.show()