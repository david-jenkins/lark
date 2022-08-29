

"""This defines and registers functions for the SRTC systemd
"""

# import cv2
from lark import LarkConfig
from lark.services import BaseService, BasePlugin
import numpy

class CanapyDiagnostics(BaseService):
    PLUGINS = {}
    RESULTS = {}
    INITIALISED = {}
    def notify(self, *args):
        print(*args)

from lark.tests.wfs import darc_pyr_slopes

@CanapyDiagnostics.register_plugin("pyr_slopes")
class CheckPyrSlopes(BasePlugin):
    """Get images and slopes from darc, process the images and check the slopes
    """
    def __init__(self):
        self.defaults = {
            "n_img": 10,
            "prefix": "LgsWF"
        }
        self.arg_desc = {
            "n_img": "The number of images to grab"
        }
        super().__init__()

    def Configure(self,
            n_img: int = None
        ):
        kwargs = {key:value for key,value in locals().items() if key not in ["self","__class__"] and value is not None}
        super().Configure(**kwargs)

    def Setup(self):
        self.lark = LarkConfig(self["prefix"]).getlark()
        pass

    def Acquire(self):
        n_img = self["n_img"]
        prefix = self["prefix"]
        data = self.lark.getStreamBlock(["rtcPxlBuf","rtcCentBuf"],n_img)
        self.subapLocation = self.lark.get("subapLocation")
        self.subapFlag = self.lark.get("subapFlag")
        self.nsub = self.lark.get("nsub")
        self.centIndexArray = self.lark.get("centIndexArray")
        self.images = data["rtcPxlBuf"]
        self.slopes = data["rtcSlopeBuf"]

    def Execute(self):
        # subapLocation = getlark().get("subapLocation")
        print(f"self.images = {self.images}")
        print(f"self.slopes = {self.slopes}")
        print(f"self.subapLocation = {self.subapLocation}")
        print(f"self.subapFlag = {self.subapFlag}")
        print(f"self.centIndexArray = {self.centIndexArray}")
        print(f"self.nsub = {self.nsub}")
        pass

    def Check(self):
        pass

    def Finalise(self):
        pass

# @CanapyDiagnostics.register_plugin("pyr_quadcell")
# class QuadCellPyr(BasePlugin):
#     def __init__(self):
#         self.defaults = {
#             "n_img": 10,
#             "prefix": "LgsWF"
#         }
#         super().__init__()

#     def Configure(self,
#             n_img: int = None
#         ):
#         kwargs = {key:value for key,value in locals().items() if key not in ["self","__class__"] and value is not None}
#         super().Configure(**kwargs)

#     def Setup(self):
#         self.lark = LarkConfig(self["prefix"]).getlark()

#     def Acquire(self):
#         n_img = self["n_img"]
#         pxls = self.lark.getStreamBlock("rtcPxlBuf",n_img)[0]
#         print(pxls.shape)
#         npxlx = self.lark.get("npxlx")
#         npxly = self.lark.get("npxly")
#         px = npxlx[0]
#         py = npxly[0]

#         py_imgs = numpy.zeros((n_img,px*py),dtype=pxls.dtype)
#         for i in range(n_img):
#             py_imgs[i,:] = pxls[i,:px*py]

#         py_imgs.shape = n_img,py,px

#         self.im = py_imgs.mean(0)

#     def Execute(self):
#         # subapLocation = getlark().get("subapLocation")
#         self.circles = cv2.HoughCircles(self.im.astype(numpy.uint8), cv2.HOUGH_GRADIENT, 2.0, 50)

#         self.pupils = []
#         self.flux = []
#         for x,y,r in self.circles[0]:
#             x = int(x)
#             y = int(y)
#             r = int(r)
#             circ = numpy.zeros((2*r,2*r),int)
#             for i in range(2*r):
#                 for j in range(2*r):
#                     if (i-r)**2+(j-r)**2 < r**2:
#                         circ[i,j] = 1
#             pup = self.im[y-r:y+r,x-r:x+r]
#             self.pupils.append(pup)
#             self.flux.append(pup[numpy.where(circ==1)].sum())

#         self.flux = numpy.array(self.flux)
#         self.flux /= numpy.sum(self.flux)

#         pass

#     def Check(self):
#         assert len(self.circles[0])==4
#         pass

#     def Finalise(self):
#         self.result = self.pupils, self.circles, self.flux
