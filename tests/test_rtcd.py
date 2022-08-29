
from sqlite3 import paramstyle
import sys
from lark import daemon
from lark import control

def test_startdarcmain():
    pass

if __name__ == "__main__":
    prefix = "canapy"
    if len(sys.argv)>1:
        prefix = sys.argv[1]
    config_file = "/home/canapyrtc/git/canapy-rtc/config/configOcamTest.py"

    params = control.processConfigFile(prefix,config_file)

    print(params["nsub"])
    print(type(params["nsub"]))

    c = daemon.rpycControlClient(prefix,hostname="localhost",params=params)

    print(c)

    h, c = daemon.connectHost()

    print(h.status())
