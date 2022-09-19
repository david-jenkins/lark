

from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from pyqtgraph.parametertree import Parameter, ParameterTree

import lark
from lark import NoLarkError
from .remote_files import RemoteFilePicker

class StreamWidget(ParameterTree):
    streamStart = QtC.pyqtSignal(str)
    def __init__(self,parent=None):
        ParameterTree.__init__(self,parent=parent)
        self.parameters = []
        self.streams = []
        self.paramgroup = None
        self.larkconfig = lark.LarkConfig()

    def setLarkConfig(self, larkconfig):
        self.larkconfig = larkconfig

    def setStreams(self,names):
        for name in names:
            self.streams.append(name)
            self.parameters.append({
                "name":name,
                "type":"group",
                "children":[
                    {
                        "name":"reader_thread",
                        "type":"bool",
                        "children":[
                            {
                                "name":"decimation",
                                "type":"int",
                                "value":1
                            }
                        ]
                    },
                    {
                        "name":"publisher",
                        "type":"bool",
                        "children":[
                            {
                                "name":"hostname",
                                "type":"str",
                                "value":"localhost"
                            },
                            {
                                "name":"port",
                                "type":"int",
                                "value":47
                            },
                            {
                                "name":"multicast",
                                "type":"str",
                            }
                        ]
                    },
                    {
                        "name":"saver",
                        "type":"bool",
                        "children":[
                            {
                                "name":"continuous",
                                "type":"bool",
                            },
                            {
                                "name":"Choose Directory",
                                "type":"action",
                            },
                            {
                                "name":"Filename",
                                "type":"str",
                            },
                            {
                                "name":"frames per file",
                                "type":"int",
                                "value":60000,
                            }
                        ]
                    }
                ]
            })
        self.paramgroup = Parameter.create(name="streams", type='group', children=self.parameters)
        self.setParameters(self.paramgroup)

    def chooseDir(self,event):
        stream = event.parent().parent().name()
        print(stream)
        print("running chooseDir")
        d = RemoteFilePicker(self.larkconfig,self,True)
        if d.exec():
            print(d.fname)
        event.parent().param("Filename").setValue(d.fname+"/")

    def connectStream(self, name, status, info):
        if name in self.streams:
            streamitem = self.paramgroup.param(name)
            dirp = streamitem.param("saver").param("Choose Directory")
            dirp.sigActivated.connect(self.chooseDir)
            filp = streamitem.param("saver").param("Filename")
            filp.setValue("Please choose directory")
            streamitem.param("reader_thread").setValue(bool(status[0]))
            streamitem.param("publisher").setValue(bool(status[1]))
            streamitem.param("saver").setValue(bool(status[4]))
            streamitem.param("reader_thread").param("decimation").setValue(info["dec"])
            streamitem.param("publisher").param("hostname").setValue(info["ip"][0])
            streamitem.param("publisher").param("port").setValue(info["ip"][1])
            streamitem.param("publisher").param("multicast").setValue(info["ip"][2])

            streamitem.param("reader_thread").sigValueChanged.connect(self.reader_callback)
            streamitem.param("reader_thread").param("decimation").sigValueChanged.connect(self.decimation_callback)
            streamitem.param("publisher").sigValueChanged.connect(self.publisher_callback)
            streamitem.param("publisher").param("hostname").sigValueChanged.connect(self.host_callback)
            streamitem.param("publisher").param("port").sigValueChanged.connect(self.port_callback)
            streamitem.param("publisher").param("multicast").sigValueChanged.connect(self.multicast_callback)
            streamitem.param("saver").sigValueChanged.connect(self.saver_callback)
            streamitem.param("saver").param("Filename").sigValueChanged.connect(self.filename_callback)
            streamitem.param("saver").param("frames per file").sigValueChanged.connect(self.frameper_callback)

    def updateStream(self, name, status, info):
        if name in self.streams:
            streamitem = self.paramgroup.param(name)
            
            # disconnect relevant signals
            streamitem.param("reader_thread").sigValueChanged.disconnect(self.reader_callback)
            streamitem.param("reader_thread").param("decimation").sigValueChanged.disconnect(self.decimation_callback)
            streamitem.param("publisher").sigValueChanged.disconnect(self.publisher_callback)
            streamitem.param("publisher").param("hostname").sigValueChanged.disconnect(self.host_callback)
            streamitem.param("publisher").param("port").sigValueChanged.disconnect(self.port_callback)
            streamitem.param("publisher").param("multicast").sigValueChanged.disconnect(self.multicast_callback)
            streamitem.param("saver").sigValueChanged.disconnect(self.saver_callback)
            
            # update relevant values
            streamitem.param("reader_thread").setValue(bool(status[0]))
            streamitem.param("reader_thread").param("decimation").setValue(info["dec"])
            streamitem.param("publisher").setValue(bool(status[1]))
            streamitem.param("publisher").param("hostname").setValue(info["ip"][0])
            streamitem.param("publisher").param("port").setValue(info["ip"][1])
            streamitem.param("publisher").param("multicast").setValue(info["ip"][2])
            streamitem.param("saver").setValue(bool(status[4]))
            
            # reconnect relevant signals
            streamitem.param("reader_thread").sigValueChanged.connect(self.reader_callback)
            streamitem.param("reader_thread").param("decimation").sigValueChanged.connect(self.decimation_callback)
            streamitem.param("publisher").sigValueChanged.connect(self.publisher_callback)
            streamitem.param("publisher").param("hostname").sigValueChanged.connect(self.host_callback)
            streamitem.param("publisher").param("port").sigValueChanged.connect(self.port_callback)
            streamitem.param("publisher").param("multicast").sigValueChanged.connect(self.multicast_callback)
            streamitem.param("saver").sigValueChanged.connect(self.saver_callback)

    def reader_callback(self, event):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            stream = event.parent().name()
            value = event.value()
            if value:
                lrk.startStream(stream)
            else:
                lrk.stopStream(stream)

    def decimation_callback(self, event):
        stream = event.parent().parent().name()
        value = event.value()
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            lrk.setDecimation(stream,value)

    def publisher_callback(self, event):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            stream = event.parent().name()
            value = event.value()
            if value:
                lrk.startStreamPublish(stream)
            else:
                lrk.stopStreamPublish(stream)

    def host_callback(self, event):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            stream = event.parent().parent().name()
            value = event.value()
            lrk.setStreamHost(stream, value)

    def port_callback(self, event):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            stream = event.parent().parent().name()
            value = event.value()
            lrk.setStreamPort(stream, value)

    def multicast_callback(self, event):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            stream = event.parent().parent().name()
            value = event.value()
            lrk.setStreamMulticast(stream, value)

    def saver_callback(self, event):
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            stream = event.parent().name()
            value = event.value()
            name  = event.param("Filename").value()
            frames  = event.param("frames per file").value()
            print(stream,value,name,frames)
            if value:
                lrk.saveFrames(stream,frames,name)

    def filename_callback(self, event):
        stream = event.parent().parent().name()
        print(stream,event.value())

    def frameper_callback(self, event):
        stream = event.parent().parent().name()
        print(stream,event.value())

    def reset(self):
        self.parameters = []
        self.paramgroup = None
        self.clear()

class TelemetryControl_base(QtW.QWidget):
    def __init__(self,parent=None):
        QtW.QWidget.__init__(self,parent=parent)

        # define menu
        self.menu = QtW.QMenu("&Control")

        # define widgets
        self.stream_tree = StreamWidget(self)

        # define layout
        self.vlay = QtW.QVBoxLayout()

        # populate layout
        self.vlay.addWidget(self.stream_tree)

        self.setLayout(self.vlay)

class TelemetryDisplay_base(QtW.QWidget):
    def __init__(self,parent=None):
        QtW.QWidget.__init__(self,parent=parent)

        # define menu
        self.menu = QtW.QMenu("&Display")