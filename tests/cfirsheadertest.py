
from lark.tools.cfits import getdata, appendToHeader
from astropy.io import fits




file = '/opt/lark/data/darc/2022-11-28/1236_28-lgswf/rtcCentBuf-2022-11-28T1236_34-917161-000.cfits'

header = fits.getheader(file,0)
print(header)
header = fits.getheader(file,1)
print(header)
header = fits.getheader(file,2)
print(header)

appendToHeader(file,None,david=49)