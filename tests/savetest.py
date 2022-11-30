import sys
from copy import copy
from lark import LarkConfig
from lark.tools.cfits import getdata
from matplotlib import pyplot
import numpy

def fits_test(l):
    # files = l.getlark().saveFrames(("rtcCentBuf","rtcMirrorBuf"),10000)
    # files = l.getlark().saveFrames(("rtcCentBuf","rtcMirrorBuf","rtcPxlBuf"),1000)
    # files = l.getlark().saveFrames("rtcCentBuf",100)
    files = [['/opt/lark/data/darc/2022-11-28/1236_28-lgswf/rtcCentBuf-2022-11-28T1236_34-917161-000.cfits', '/opt/lark/data/darc/2022-11-28/1236_28-lgswf/rtcCentBuf-2022-11-28T1236_34-917161-001.cfits', '/opt/lark/data/darc/2022-11-28/1236_28-lgswf/rtcCentBuf-2022-11-28T1236_34-917161-002.cfits'], ['/opt/lark/data/darc/2022-11-28/1236_28-lgswf/rtcMirrorBuf-2022-11-28T1236_34-917161-000.cfits']]
    fnums = copy(files)
    def iter_list(list1,list2):
        for i,item in enumerate(list1):
            if isinstance(item,list):
                iter_list(item,list2[i])
            else:
                list2[i] = getdata(item,2)

    iter_list(files,fnums)

    def plot_list(list1):
        plotted = False
        c=0
        for i,item in enumerate(list1):
            if isinstance(item,list):
                plot_list(item)
            else:
                if not plotted:
                    pyplot.figure()
                    plotted=True
                pyplot.plot(numpy.arange(len(item))+c,item)
                c+=len(item)
                
    plot_list(fnums)

    pyplot.show()
# print(files)


def npy_test(l):
    
    l.getlark().saveParamBuf()
    
    files = l.getlark().saveNpyFrames(("rtcCentBuf","rtcMirrorBuf","rtcPxlBuf","rtcStatusBuf"),10000)

    # files = [['/opt/lark/data/darc/2022-11-30/1402_35-lgswf/rtcCentBuf-2022-11-30T1402_41-285405-000.npy'], ['/opt/lark/data/darc/2022-11-30/1402_35-lgswf/rtcMirrorBuf-2022-11-30T1402_41-285405-000.npy'], ['/opt/lark/data/darc/2022-11-30/1402_35-lgswf/rtcPxlBuf-2022-11-30T1402_41-285405-000.npy', '/opt/lark/data/darc/2022-11-30/1402_35-lgswf/rtcPxlBuf-2022-11-30T1402_41-285405-001.npy', '/opt/lark/data/darc/2022-11-30/1402_35-lgswf/rtcPxlBuf-2022-11-30T1402_41-285405-002.npy']]

    # files = [['/opt/lark/data/darc/2022-11-30/1556_58-lgswf/rtcCentBuf-2022-11-30T1557_01-202320-000.npy'], ['/opt/lark/data/darc/2022-11-30/1556_58-lgswf/rtcMirrorBuf-2022-11-30T1557_01-202320-000.npy'], ['/opt/lark/data/darc/2022-11-30/1556_58-lgswf/rtcPxlBuf-2022-11-30T1557_01-202320-000.npy', '/opt/lark/data/darc/2022-11-30/1556_58-lgswf/rtcPxlBuf-2022-11-30T1557_01-202320-001.npy', '/opt/lark/data/darc/2022-11-30/1556_58-lgswf/rtcPxlBuf-2022-11-30T1557_01-202320-002.npy']]

    # files = [['/opt/lark/data/darc/2022-11-30/1604_33-lgswf/rtcCentBuf-2022-11-30T1604_51-096143-000.npy'], ['/opt/lark/data/darc/2022-11-30/1604_33-lgswf/rtcMirrorBuf-2022-11-30T1604_51-096143-000.npy'], ['/opt/lark/data/darc/2022-11-30/1604_33-lgswf/rtcPxlBuf-2022-11-30T1604_51-096143-000.npy', '/opt/lark/data/darc/2022-11-30/1604_33-lgswf/rtcPxlBuf-2022-11-30T1604_51-096143-001.npy', '/opt/lark/data/darc/2022-11-30/1604_33-lgswf/rtcPxlBuf-2022-11-30T1604_51-096143-002.npy']]

    print(files)

    arrs = copy(files)
    
    def iter_list(list1,list2):
        for i,item in enumerate(list1):
            if isinstance(item,list):
                iter_list(item,list2[i])
            else:
                arr = numpy.load(item)
                list2[i] = arr

    iter_list(files,arrs)
    
    print(arrs[1][0].shape)
    print(arrs[1][0].dtype)
    print(arrs[0][0]["hdr"])
    for i in range(20):
        print(arrs[1][0]["hdr"][i])

    def plot_list(list1):
        plotted = False
        c=0
        for i,item in enumerate(list1):
            if isinstance(item,list):
                plot_list(item)
            else:
                if not plotted:
                    pyplot.figure()
                    plotted=True
                fnums = item["hdr"][:]["f1"]
                pyplot.plot(numpy.arange(len(fnums))+c,fnums)
                c+=len(fnums)
                
    plot_list(arrs)

    pyplot.show()


if __name__ == "__main__":
    l = LarkConfig("lgswf")
    npy_test(l)
