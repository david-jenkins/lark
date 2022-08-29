

"""This is a prototype 'Observing Block' for the CaNaPy RTC
It defines an operating mode of the RTC including which darcs to start.
It also loads the functions for the SRTC system which is launched
using this script.
"""

# import darc configs to get configuration parameters

info = """
Name: Placeholder,
Darcs: LgsWF: configLGSWF.py, PyScoring: configPyScoring.py
Hosts: LgsWF: localhost, PyScoring: localhost
Description:
A placeholder mode for testing purposes
"""

# define darc prefixes and extract the control dictionaries
params = {
    "LgsWF": {},
    "PyScoring": {}
}

# define the machines where the darcs will be launched
hostnames = {
    "LgsWF": "localhost",
    "PyScoring": "localhost"
}

srtcname = "LabPyTestSRTC"
srtchost = "localhost"


def startlark():
    """A helper function to start the darcs and configure them with the parameters
    """
    print("starting larks")

def startsrtc():
    """A helper function to start the SRTC instance for this observng block
    """
    print("starting srtc")

def start():
    startlark()
    startsrtc()

def stoplark():
    """A helper function to stop the larks associated with this observing block
    """
    print("stopping larks")

def stopsrtc():
    print("stopping srtc")

def stop():
    stopsrtc()
    stoplark()

def open():
    """A helper function to open the displays of each running prefix/srtc
    """
    print("Opening display")

if __name__ == "__main__":
    """If this file is executed directly, it should start and configure the observing block then exit
    """
    start()
