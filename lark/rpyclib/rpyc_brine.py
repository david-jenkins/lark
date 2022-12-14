import copy
from pathlib import Path, PosixPath, PurePath, PurePosixPath
import pickle
import numpy
import rpyc.core.brine
from rpyc.core.brine import register, _dump_registry, _dump, _load, I1, I4, _load_registry, dump, load, IMM_INTS, dumpable as _dumpable


"""
Trying different behaviour for moving lists and dicts between RPyC connections

Current default: all list and dicts are copied, to ensure netrefs for remote objects use RemoteDict and RemoteList wrapper

Other option: all list and dicts are netrefed, to copy use CopyDict and CopyList

I can't decide which option is best... perhaps the default and use CopyDict and CopyList
I think copy.deepcopy works to make local copies of lists and dicts but can be slow.

"""

"""
The following code implements rpyc boxing for dictionaries and lists.
It goes through the dict and boxes each key,value pair.
Shouldn't really have any performance penalty versus CopyDict but will
be slower than netrefing entire dicts, same as CopyDict.
For very large dictionaries it might be better to use a different type that doesn't get
boxed up like this.
"""

from rpyc.core import consts
from rpyc.core import protocol
consts.LABEL_DICT = 5
consts.LABEL_LIST = 6

_old_box = protocol.Connection._box
_old_unbox = protocol.Connection._unbox

def _box(self, obj):
    if type(obj) is dict:
        return consts.LABEL_DICT, tuple((self._box(_name),self._box(_value)) for _name,_value in obj.items())
    elif type(obj) is list:
        return consts.LABEL_LIST, tuple(self._box(_value) for _value in obj)
    return _old_box(self, obj)

def _unbox(self, package):
    label,value = package
    if label == consts.LABEL_DICT:
        return {self._unbox(_name):self._unbox(_value) for _name,_value in value}
    elif label == consts.LABEL_LIST:
        return [self._unbox(_value) for _value in value]
    return _old_unbox(self, package)

protocol.Connection._box = _box
protocol.Connection._unbox = _unbox

class CopyDict(dict):
    """A CopyDict behaves EXACTLY like a dict
    except it is an instance of CopyDict and 
    therefore can be distinguished from normal dicts,
    this is used to copy a dict by values through rpyc.
    A normal dict will be passed as a netref.
    Now handles nested dicts at init.
    """
    def __init__(self, indict={}):
        for key,value in indict.items():
            if isinstance(value, dict):
                indict[key] = CopyDict(value)
            elif isinstance(value, list):
                indict[key] = CopyList(value)
        super().__init__(indict)

class CopyList(list):
    """A CopyList behaves EXACTLY like a list
    except it is an instance of copylist and 
    therefore can be distinguished from normal lists,
    this is used to copy a list by values through rpyc.
    A normal list will be passed as a netref.
    Now handles nested lists at init.
    """
    def __init__(self, inlist=[]):
        for index,value in enumerate(inlist):
            if isinstance(value,list):
                inlist[index] = CopyList(value)
            elif isinstance(value, dict):
                inlist[index] = CopyDict(value)
        super().__init__(inlist)

def retrieve(object):
    return copy.deepcopy(object)

class RemoteDict(dict):
    """A dict wrapper to force netref behaviour
    """
    def __init__(self, indict={}):
        for key,value in indict.items():
            if isinstance(value, dict):
                indict[key] = RemoteDict(value)
            elif isinstance(value, list):
                indict[key] = RemoteList(value)
        super().__init__(indict)

class RemoteList(list):
    """A list wrapper to force netref behaviour
    """
    def __init__(self, inlist=[]):
        for index,value in enumerate(inlist):
            if isinstance(value,list):
                inlist[index] = RemoteList(value)
            elif isinstance(value, dict):
                inlist[index] = RemoteDict(value)
        super().__init__(inlist)

my_types = [numpy.ndarray, CopyDict, CopyList, numpy.int32, numpy.int64, numpy.float32, numpy.float64, Path, PurePath, PurePosixPath, PosixPath]

def dumpable(obj):
    if type(obj) in my_types:
        return True
    return _dumpable(obj)

rpyc.core.brine.dumpable = dumpable

TAG_DICT = b"\x1c"

TAG_EMPTY_LIST = b"\xf0"
TAG_LIST1 = b"\xf1"
TAG_LIST2 = b"\xf2"
TAG_LIST3 = b"\xf3"
TAG_LIST4 = b"\xf4"
TAG_LIST_L1 = b"\xf5"
TAG_LIST_L4 = b"\xf6"

TAG_NINT32 = b"\xf7"
TAG_NINT64 = b"\xf8"
TAG_NFLOAT32 = b"\xf9"
TAG_NFLOAT64 = b"\xfa"
TAG_NDARRAY = b"\xfb"

TAG_PATH = b"\xfc"
TAG_PUREPATH = b"\xfd"
TAG_PUREPOSIXPATH = b"\xfe"
TAG_POSIXPATH = b"\xff"

@register(_dump_registry, CopyList)
def _dump_list(obj, stream):
    lenobj = len(obj)
    if lenobj == 0:
        stream.append(TAG_EMPTY_LIST)
    elif lenobj == 1:
        stream.append(TAG_LIST1)
    elif lenobj == 2:
        stream.append(TAG_LIST2)
    elif lenobj == 3:
        stream.append(TAG_LIST3)
    elif lenobj == 4:
        stream.append(TAG_LIST4)
    elif lenobj < 256:
        stream.append(TAG_LIST_L1 + I1.pack(lenobj))
    else:
        stream.append(TAG_LIST_L4 + I4.pack(lenobj))
    for item in obj:
        _dump(item, stream)
        
@register(_load_registry, TAG_EMPTY_LIST)
def _load_empty_list(stream):
    return []

@register(_load_registry, TAG_LIST1)
def _load_list1(stream):
    return [_load(stream),]


@register(_load_registry, TAG_LIST2)
def _load_list2(stream):
    return [_load(stream), _load(stream)]

@register(_load_registry, TAG_LIST3)
def _load_list3(stream):
    return [_load(stream), _load(stream), _load(stream)]

@register(_load_registry, TAG_LIST4)
def _load_list4(stream):
    return [_load(stream), _load(stream), _load(stream), _load(stream)]

@register(_load_registry, TAG_LIST_L1)
def _load_list_l1(stream):
    l, = I1.unpack(stream.read(1))
    return list(_load(stream) for i in range(l))


@register(_load_registry, TAG_LIST_L4)
def _load_list_l4(stream):
    l, = I4.unpack(stream.read(4))
    return list(_load(stream) for i in range(l))


@register(_dump_registry, numpy.ndarray)
def _dump_ndarray(obj, stream):
    # stream.append(TAG_NDARRAY)
    # data = (obj.shape,str(obj.dtype),obj.tobytes())
    # _dump(data,stream)
    data = pickle.dumps(obj)
    lenobj = len(data)
    stream.append(TAG_NDARRAY + I4.pack(lenobj) + data)

@register(_load_registry, TAG_NDARRAY)
def _load_ndarray(stream):
    # data = _load(stream)
    # arr = numpy.frombuffer(data[2],dtype=numpy.dtype(data[1]))
    # arr.shape = data[0]
    # return arr
    l, = I4.unpack(stream.read(4))
    data = stream.read(l)
    return pickle.loads(data)

@register(_dump_registry, numpy.int32)
def _dump_nint32(obj, stream):
    # stream.append(TAG_NINT32)
    # data = obj.tobytes()
    # _dump(data,stream)
    stream.append(TAG_NINT32+obj.tobytes())

@register(_load_registry, TAG_NINT32)
def _load_nint32(stream):
    # data = _load(stream)
    # return numpy.frombuffer(data,dtype=numpy.int32)[0]
    return numpy.frombuffer(stream.read(4),dtype=numpy.int32)[0]


@register(_dump_registry, numpy.int64)
def _dump_nint64(obj, stream):
    # stream.append(TAG_NINT64)
    # data = obj.tobytes()
    # _dump(data,stream)
    stream.append(TAG_NINT64+obj.tobytes())

@register(_load_registry, TAG_NINT64)
def _load_nint64(stream):
    # data = _load(stream)
    # return numpy.frombuffer(data,dtype=numpy.int64)[0]
    return numpy.frombuffer(stream.read(8),dtype=numpy.int64)[0]

@register(_dump_registry, numpy.float32)
def _dump_nfloat32(obj, stream):
    # stream.append(TAG_NFLOAT32)
    # data = obj.tobytes()
    # _dump(data,stream)
    stream.append(TAG_NFLOAT32+obj.tobytes())

@register(_load_registry, TAG_NFLOAT32)
def _load_nfloat32(stream):
    # data = _load(stream)
    # return numpy.frombuffer(data,dtype=numpy.float32)[0]
    return numpy.frombuffer(stream.read(4),dtype=numpy.float32)[0]

@register(_dump_registry, numpy.float64)
def _dump_nfloat64(obj, stream):
    # stream.append(TAG_NFLOAT64)
    # data = obj.tobytes()
    # _dump(data,stream)
    stream.append(TAG_NFLOAT64+obj.tobytes())

@register(_load_registry, TAG_NFLOAT64)
def _load_nfloat64(stream):
    # data = _load(stream)
    # return numpy.frombuffer(data,dtype=numpy.float64)[0]
    return numpy.frombuffer(stream.read(8),dtype=numpy.float64)[0]


@register(_dump_registry, CopyDict)
def _dump_dict(obj, stream):
    stream.append(TAG_DICT+I4.pack(len(obj)))
    for key,value in obj.items():
        _dump(key,stream)
        _dump(value,stream)

@register(_load_registry, TAG_DICT)
def _load_dict(stream):
    l, = I4.unpack(stream.read(4))
    return {_load(stream):_load(stream) for i in range(l)}

@register(_dump_registry, Path)
def _dump_path(obj, stream):
    stream.append(TAG_PATH)
    _dump(str(obj),stream)

@register(_load_registry, TAG_PATH)
def _load_path(stream):
    data = _load(stream)
    return Path(data)

@register(_dump_registry, PurePath)
def _dump_purepath(obj, stream):
    stream.append(TAG_PUREPATH)
    _dump(str(obj),stream)

@register(_load_registry, TAG_PUREPATH)
def _load_purepath(stream):
    data = _load(stream)
    return PurePath(data)

@register(_dump_registry, PurePosixPath)
def _dump_pureposixpath(obj, stream):
    stream.append(TAG_PUREPOSIXPATH)
    _dump(str(obj),stream)

@register(_load_registry, TAG_PUREPOSIXPATH)
def _load_pureposixpath(stream):
    data = _load(stream)
    return PurePosixPath(data)

@register(_dump_registry, PosixPath)
def _dump_posixpath(obj, stream):
    stream.append(TAG_POSIXPATH)
    _dump(str(obj),stream)

@register(_load_registry, TAG_POSIXPATH)
def _load_posixpath(stream):
    data = _load(stream)
    return PosixPath(data)

if __name__ == "__main__":
    vars = [
        [1,2,3,4],
        numpy.array([[1,2,3],[4,5,6]],dtype=numpy.int32),
        CopyDict({"a":numpy.array([[1,2,3,9,2,5],[7,5,34,5,6,3]],dtype=numpy.int64),"b":numpy.arange(5)}),
        Path.home(),
        PurePath("/tmp/"),
        numpy.int32(6),
        numpy.int64(8),
        numpy.float32(9.4),
        numpy.float64(10.3),
        ]

    for var in vars:
        print(f"type(var) = {type(var)}")
        d = dump(var)
        print(f"d = {d}")
        l = load(d)
        print(f"l = {l}")
        print(f"type(l) = {type(l)}")


    obj = numpy.zeros(1)

    y = (str(obj.shape),str(obj.dtype),obj.tobytes())
    p = pickle.dumps(obj)

    print(len(y[0])+len(y[1])+len(y[2]),len(p))