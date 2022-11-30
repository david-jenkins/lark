from pathlib import Path
import numpy 
import struct
import ast
import warnings
import pickle
import sys

def make_array_header_from_dtype_shape(dtype,shape,fortran_order=False):
    d = {'shape': shape,'fortran_order': fortran_order}
    d['descr'] = numpy.lib.format.dtype_to_descr(dtype)
    header = ["{"]
    for key, value in sorted(d.items()):
        # Need to use repr here, since we eval these when reading
        header.append("'%s': %s, " % (key, repr(value)))
    header.append("}")
    header = "".join(header)
    header = numpy.lib.format._wrap_header(header, (1, 0))
    return header

def make_npy(fname,size,dtype,frames=None,overwrite=False):
    fname = Path(fname).with_suffix(".npy")
    if not overwrite:
        if fname.exists():
            raise FileExistsError(f"{fname} already exists")
    cbuf_header = numpy.dtype("i4, i4, f8, (1,16)b")
    cbuf_type = numpy.dtype([("hdr",cbuf_header),("data",dtype,(size,))])
    header = make_array_header_from_dtype_shape(cbuf_type,(frames,))
    with fname.open("wb+") as fp:
        fp.write(header)
        fp.seek(cbuf_type.itemsize*frames-1,1)
        fp.write(b'\0')
    print(len(header))
    print(cbuf_type.itemsize*frames)
    
    return str(fname), len(header)

ddd = sys.exit

_print = print
def print(*args,**kwargs):
    _print(*args,**kwargs)
    _print()

cbuf_header = numpy.dtype("i4, i4, f8, (1,16)b")

cbuf_type = numpy.dtype([("header",cbuf_header),("data",numpy.float32,(5,5))])

# print(str(cbuf_type))


make_npy("temp0.npy",100,numpy.float32,10,True)

with open("temp0.npy","rb") as f:
    buf = f.read()

print(type(buf))
print(buf)

x = numpy.load("temp0.npy",allow_pickle=True)

print(x.dtype)
print(x)
print(x["hdr"])
print(x["data"])

ddd()
# print(cbuf_type.fields.items())

x = numpy.zeros(5,dtype=cbuf_type)

x[0]["header"] = 1,2,3,(4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19)
x[1]["header"] = x[0]["header"]

x[0]["data"] = numpy.arange(20,20+25).reshape(5,5)

numpy.save("temp.npy",x)

x = numpy.load("temp.npy")

with open("temp.npy","rb") as f:
    buf = f.read()

print(type(buf))
print(buf)

ddd()

npy_hdr = numpy.frombuffer(buf[:10],dtype=[('f0','<B',(1,6)),('f1','<B'),('f2','<B'),('f3','<H')])[0]
data_index = di = npy_hdr[3]+10
info_str = (buf[10:di-1]).decode()
info = ast.literal_eval(info_str)

print(npy_hdr)
print(info)

array = numpy.frombuffer(buf[di:],dtype=info["descr"])
data = array["data"]
print(array)
print(array["header"])
print(data)
print(data.shape)

ddd()
hdr_type = numpy.dtype(info["descr"][0][1])
data_type = numpy.dtype(info["descr"][1][1])
hdr_size = hs = hdr_type.itemsize
data_size = ds = data_type.itemsize*numpy.product(info["descr"][1][2])
print(numpy.frombuffer(buf[di:di+hs],dtype=hdr_type))
print(numpy.frombuffer(buf[di+hs:di+hs+data_size],dtype=data_type).reshape(info["descr"][1][2]))