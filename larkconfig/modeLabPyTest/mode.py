

"""This is a prototype 'Observing Block' for the CaNaPy RTC
It defines an operating mode of the RTC including which darcs to start.
It also loads the functions for the SRTC system which is launched
using this script.
"""
import numpy
import toml
import lark
from lark.utils import var_from_file
from lark.utils import get_datetime_stamp
from lark.interface import get_registry_parameters
from pathlib import Path

# file_path is needed for relative file locations
# all paths are relative to the 2nd parent directory
# so it's easier to get darc configs and files from other modes
file_name = Path(__file__).parent.stem.replace("mode","")
mode_path = Path(__file__).parent.resolve()
file_path = Path(__file__).parent.parent.resolve()

# host = "laserlab"
host = get_registry_parameters().RPYC_HOSTNAME

# prefix: (config_file, hostname)
darcs = {
    "LgsWF" : ("darc/configLGSWF.py",host),
    "PyScoring" : ("darc/configPyScoring.py",host),
}

# name: (class_name, source_file, hostname)
# services are started remotely by sending the raw text of the source file to the host daemon
# this then extracts the service class via the class_name and starts it remotely
# this is needed because it's not easy/not possible to pickle a class definition
services = {
    "LabPyTestSRTC": ("CanapySrtc","modeLabPyTest/srtc.py",host),
    "LgsWFiPortSRTC": ("iPortService","modeLabPyTest/iport.py",host),
    "LabPyTestDiagSRTC": ("CanapyDiagnostics","modeLabPyTest/tests.py",host)
}

# try:
#     srtc_config = toml.load(mode_path/"config.toml")
# except FileNotFoundError:
#     var_from_file("save_toml",mode_path/'config.py')()
#     srtc_config = toml.load(mode_path/"config.toml")

# def replace_filenames(srtc_config):
#     for key,value in srtc_config.items():
#         if isinstance(value,str) and ".npy" in value:
#             try:
#                 srtc_config[key] = numpy.load(mode_path/value)
#             except:
#                 var_from_file("save_file",mode_path/'config.py')(value)
#                 srtc_config[key] = numpy.load(mode_path/value)
#         elif isinstance(value,dict):
#             srtc_config[key] = replace_filenames(value)
#     return srtc_config

# srtc_config = replace_filenames(srtc_config)


services_config = {
    "LgsWFiPortSRTC": {
        "prefix":"LgsWf", "localip":"169.254.24.100", "iportip":"169.254.24.101"
    },
    "LabPyTestSRTC": {
        "srtcName":"LabPyTest",
        "modeName": "modeLabPyTest",
        "prefixes": ["LgsWF", "PyScoring"],
        "dateNow":get_datetime_stamp(split=True)[0]}
}

GUI = ("CanapyGUI", "modeLabPyTest/gui.py")

info = """Used for the calibration and testing of the OCAM PyWFS in the OAR Lab.
Also uses the EVT scoring camera."""

def startlark():
    """A helper function to start the darcs and configure them with the parameters
    """
    from lark.interface import startControlClient

    print("starting larks")
    for prefix, (pth,hst) in darcs.items():
        this_path = file_path/Path(pth)
        param = var_from_file("control",this_path)
        param["configfile"] = str(this_path.resolve().absolute())
        startControlClient(prefix,hostname=hst,params=param)
    pass

def startsrtc():
    """A helper function to start the SRTC instance for this observng block
    """
    for name, (cls,pth,hst) in services.items():
        text = (cls,(file_path/pth).read_text())
        srv = lark.startservice(text, name, hst)
        if name in services_config:
            srv.Configure(**services_config[name])
        srv.start()
    # CanapySrtc_text = ("CanapySrtc",(file_path/"../modeLabPyTest/srtc.py").read_text())
    # iPortService_text = ("iPortService",(file_path/"srtc.py").read_text())
    # CanapyDiagnostics_text = ("CanapyDiagnostics",(file_path/"tests.py").read_text())
    
    # lark.startservice(CanapySrtc_text,srtcname,srtchost)
    # iserv = lark.startservice(iPortService_text,iportname,hostnames["LgsWF"])
    # iserv.start()

def start():
    startlark()
    startsrtc()

def stoplark():
    """A helper function to stop the larks associated with this observing block
    """
    from lark.interface import connectDaemon

    for prefix,(pth,hst) in darcs.items():
        try:
            h = connectDaemon(hst)
        except Exception as e:
            print(e)
        else:
            h.stoplark(prefix)

def stopsrtc():
    for name, (cls,pth,hst) in services.items():
        try:
            s = lark.getservice(name)
        except Exception as e:
            print(e)
        else:
            s.stop()

def stop():
    try:
        stopsrtc()
    except ConnectionError as e:
        print(e)
    try:
        stoplark()
    except ConnectionError as e:
        print(e)

def open():
    """A helper function to open the displays of each running prefix/srtc
    """
    from lark.utils import var_from_file
    CanapyGUI = var_from_file(GUI[0],file_path/GUI[1])
    return CanapyGUI(srtc="LabPyTest")

if __name__ == "__main__":
    """If this file is executed directly, it should start and configure the observing block then exit
    """
    start()

