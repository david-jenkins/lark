

"""This is a prototype 'Observing Block' for the CaNaPy RTC
It defines an operating mode of the RTC including which darcs to start.
It also loads the functions for the SRTC system which is launched
using this script.
"""
import lark
from pathlib import Path

# file_path is needed for relative file locations
# all paths are relative to the 2nd parent directory
# so it's easier to get darc configs and files from other modes
file_name = Path(__file__).parent.stem.replace("mode","")
file_path = Path(__file__).parent.parent.resolve()

# prefix: (config_file, daemonname)
darcs = {
    "arran" : ("darc/configLGSWF_sim.py", "arran"),
    "master" : ("darc/configLGSWF_sim.py", "arran"),
    "spey" : ("darc/configLGSWF_sim.py", "spey"),
}

# name: (class_name, source_file, daemonname)
# services are started remotely by sending the raw text of the source file to the host daemon
# this then extracts the service class via the class_name and starts it remotely
# this is needed because it's not easy/not possible to pickle a class definition
services = {
    "LatteSimSRTC": ("CanapySrtc","modeLabPySim/srtc.py", "oban"),
    # "ArranSRTC": ("CanapySrtc","modeLatteSim/srtc.py", "arran"),
    # "SpeySRTC": ("CanapySrtc","modeLatteSim/srtc.py", "spey"),
}

services_config = {
    "LatteSimSRTC": {"srtcname":"LatteSim"},
    "ArranSRTC": {"srtcname":"ArranControl"},
    "SpeySRTC": {"srtcname":"SpeyControl"},
}

GUI = ("CanapyGUI", "modeLatteSim/gui.py")

info = """Used for the simulation of the LATTE RTC"""

def startlark():
    """A helper function to start the darcs and configure them with the parameters
    """
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
    return CanapyGUI(prefix="arran", srtc="LatteSim")

if __name__ == "__main__":
    """If this file is executed directly, it should start and configure the observing block then exit
    """
    # start()
    from types import SimpleNamespace

    
    md = SimpleNamespace(file_name=file_name,darcs=darcs,file_path=file_path,services=services,info=info)
    
    nlspsp = "\n  "
    info = f"""Name: {md.file_name}\n
Path: {md.file_path}\n
Darcs: {nlspsp}{nlspsp.join([f'{k} -> {", ".join(v)}' for k,v in md.darcs.items()])}\n
Services: {nlspsp}{nlspsp.join([f'{k} -> {", ".join(v)}' for k,v in md.services.items()])}\n
Description: {nlspsp}{md.info}"""

    print(info)


    stop()

    # startsrtc()

    # s = startService(CanapySrtc,"LabPyTest")

    # s = lark.startservice(CanapySrtc,"LabPyTest",srtchost)

    # s.block()

    srtcname = next(iter(services))

    s = lark.getservice(srtcname)

    print(s.getPlugin())

    print(s.save_data.run(file_name="/tmp/data"))

    print(s.getResult())

    # s.stop()
