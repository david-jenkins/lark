

"""This is a prototype 'Observing Block' for the CaNaPy RTC
It defines an operating mode of the RTC including which darcs to start.
It also loads the functions for the SRTC system which is launched
using this script.
"""

from pathlib import Path

# file_path is needed for relative file locations
# all paths are relative to the 2nd parent directory
# so it's easier to get darc configs and files from other modes
file_name = Path(__file__).parent.stem.replace("mode","")
file_path = Path(__file__).parent.parent.resolve()

host = "LASERLAB"

# prefix: (config_file, hostname)
darcs = {
    "LgsWF" : ("darc/configLGSWF_sim.py",host),
    "PyScoring" : ("darc/configPyScoring_sim.py",host),
}

# name: (class_name, source_file, hostname)
# services are started remotely by sending the raw text of the source file to the host daemon
# this then extracts the service class via the class_name and starts it remotely
# this is needed because it's not easy/not possible to pickle a class definition
services = {
    "LabPySimSRTC": ("CanapySrtc","modeLabPyTest/srtc.py",host),
    "LgsWFiPortSRTC": ("iPortService","modeLabPySim/srtc.py",host)
}

services_config = {
    
}

GUI = ("CanapyGUI", "modeLabPyTest/gui.py")

info = """A placeholder mode for testing purposes."""

def startlark():
    """A helper function to start the darcs and configure them with the parameters
    """
    print("Starting lark....")
    return

    from lark.utils import var_from_file
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
    
    print("Starting srtc....")
    return

    import lark
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
    
    print("Stopping lark....")
    return

    from lark.interface import connectDaemon

    for prefix,(pth,hst) in darcs.items():
        try:
            h = connectDaemon(hst)
        except Exception as e:
            print(e)
        else:
            h.stoplark(prefix)

def stopsrtc():
    
    print("Stopping srtc....")
    return
    
    import lark
    import time
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
    print("Opening GUI....")
    return
    
    from lark.utils import var_from_file
    CanapyGUI = var_from_file(GUI[0],file_path/GUI[1])
    return CanapyGUI(srtc="LabPySim")

if __name__ == "__main__":
    """If this file is executed directly, it should start and configure the observing block then exit
    """
    start()

