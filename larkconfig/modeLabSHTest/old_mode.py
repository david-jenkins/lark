

"""This is a prototype 'Observing Block' for the CaNaPy RTC
It defines an operating mode of the RTC including which darcs to start.
It also loads the functions for the SRTC system which is launched
using this script.
"""

# import darc configs to get configuration parameters
from pathlib import Path
from lark.utils import var_from_file

file_path = Path(__file__).parent.resolve()

configs = {
    "LGSWF" : "configLGSWF.py",
    "PyScoring" : "configPyScoring.py",
}

# configs = {
#     "LGSWF" : "configNGSWF.py",
#     "PyScoring" : "configPyScoring.py",
# }

for prefix in configs:
    this_path = file_path/Path(f"../darc/{configs[prefix]}")
    configs[prefix] =  var_from_file("control",this_path)
    configs[prefix]["configfile"] = str(this_path.resolve().absolute())
    
# CanapySrtc = import_from(file_path/"srtc.py").CanapySrtc
# iPortService = import_from(file_path/"srtc.py").iPortService
# CanapyDiagnostics = import_from(file_path/"tests.py").CanapyDiagnostics
# CanapyGUI = import_from(file_path/"gui.py").CanapyGUI

# CanapySrtc = import_from(file_path/"../modeLabPyTest/srtc.py").CanapySrtc
CanapySrtc_text = ("CanapySrtc",(file_path/"srtc.py").read_text())
# iPortService = import_from(file_path/"srtc.py").iPortService
iPortService_text = ("iPortService",(file_path/"srtc.py").read_text())
# CanapyDiagnostics = import_from(file_path/"tests.py").CanapyDiagnostics
CanapyDiagnostics_text = ("CanapyDiagnostics",(file_path/"tests.py").read_text())
CanapyGUI = var_from_file("CanapyGUI",file_path/"gui.py")
# CanapyGUI  = import_from(file_path/"../modeLabPyTest/gui.py")

# these just need importing and the decorators inside do the rest
# from canapylark.config.modeLabPyTest.srtc import CanapySrtc, iPortService
# from canapylark.config.modeLabPyTest.tests import CanapyDiagnostics
# from canapylark.config.modeLabPyTest.gui import CanapyGUI
import lark
from lark.daemon import LarkDaemon
from lark.interface import ControlClient, connectDaemon, startControlClient, startService, startServiceClient
from lark.rpyclib.interface import connectClient

info = """
Name: LabPyTest,
Darcs: LgsWF: configLGSWF.py, PyScoring: configPyScoring.py
Hosts: LgsWF: localhost, PyScoring: localhost
Description:
Used for the calibration and testing of the OCAM PyWFS in the OAR Lab.
Also uses the EVT scoring camera.
"""
print(configs["LGSWF"]["configfile"])


# configLGSWF.control["configfile"] = configLGSWF.__file__
# configLGSWF.control["configfile"] = configPyScoring.__file__

# define darc prefixes and extract the control dictionaries
params = {
    "LgsWF": configs["LGSWF"],
    "PyScoring": configs["PyScoring"]
}

host = "LASERLAB"

# define the machines where the darcs will be launched
hostnames = {
    "LgsWF": host,
    "PyScoring": host
}

srtcname = "LabPyTestSRTC"
srtchost = host

iportname = "LgsWFiPortSRTC"

def startlark():
    """A helper function to start the darcs and configure them with the parameters
    """
    print("starting larks")
    print(params)
    for prefix, param in params.items():
        hostname = hostnames.get(prefix, "localhost")
        startControlClient(prefix,hostname=hostname,params=param)
    pass

def startsrtc():
    """A helper function to start the SRTC instance for this observng block
    """
    lark.startservice(CanapySrtc_text,srtcname,srtchost)
    iportservice = lark.startservice(iPortService_text,iportname,hostnames["LgsWF"])
    iportservice.getPlugin("iPortDaemon").Configure(prefix="LgsWf", localip="169.254.24.100", iportip="169.254.24.101")
    iportservice.getPlugin("iPortSerial").Configure(prefix="LgsWf")
    iportservice.start()

def start():
    # start larks first
    startlark()
    # now start srtc
    startsrtc()

def stoplark():
    """A helper function to stop the larks associated with this observing block
    """
    for prefix, param in params.items():
        hostname = hostnames.get(prefix, "localhost")
        try:
            h = connectDaemon(hostname)
            h.stoplark(prefix)
        except Exception as e:
            print(e)
    pass

def stopsrtc():
    import lark

    try:
        s = lark.getservice(srtcname)
    except Exception as e:
        print(e)
    else:
        s.stop()
    try:    
        i = lark.getservice(iportname)
    except Exception as e:
        print(e)
    else:
        i.stop()

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
    print("Opening display")
    return CanapyGUI()

if __name__ == "__main__":
    """If this file is executed directly, it should start and configure the observing block then exit
    """
    # start()

    stop()

    # startsrtc()

    # s = startService(CanapySrtc,"LabPyTest")

    # s = lark.startservice(CanapySrtc,"LabPyTest",srtchost)

    # s.block()

    s = lark.getservice(srtcname)

    print(s.getPlugin())

    print(s.save_data.run(file_name="/tmp/data"))

    print(s.getResult())

    # s.stop()
