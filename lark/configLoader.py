
from copy import copy
from distutils.dir_util import remove_tree
from pathlib import Path
import toml

HERE = Path(__file__).parent.parent.resolve()

# print(HERE)
# print(Path.home())

# default config
defaults = {
    "DATA_DIR": "/tmp/larkdata",
    "CONFIG_DIR": Path.home()/"lark/config", # this means that for each user that opens the GUI, they will see a different default config, this can be changes in /etc/lark.cfg
    # "CONFIG_DIR": HERE/"conf",
    "TELEMETRY_IP": "localhost",
    "TELEMETRY_PORT": 18761,
    "DEFAULT_PREFIX": "lark",
}

config = copy(defaults)

# read config at /etc/lark.cfg
cfile = Path("/etc/lark.cfg")
if cfile.exists():
    config.update(toml.load(cfile)["general"])


# this is a bad idea as processes will be started by root and so this will be inconsistent
# config at /etc/lark.cfg will be consistent for all users
# cfile = Path.home()/"lark.cfg"
# if cfile.exists():
#     cf = toml.load(cfile)["general"]
#     config.update(cf)
#     del cf

for key, value in config.items():
    globals()[key] = value
    
    
darcmain_format = {
    "darcaffinity"      : "-I{0:#f}",
    "nhdr"              : "-e{0:d}",
    "bufsize"           : "-b{0:d}",
    "circBufMaxMemSize" : "-m{0:d}",
    "redirectdarc"      : "-r",
    "shmPrefix"         : "-s{0:s}",
    "numaSize"          : "-N{0:d}",
    "nstoreDict"        : "-c",
}
    
####### - NO LONGER USED - #########
# remote_fns is a list of functions available over RPyC, thse are defined in lark/control.py:Control
# they get called from lark/client.py:Client

# # remote functions
# remote_fns = ["remote_close"]

# # parambuf functions
# remote_fns += ["set", "get", "setMany", "getMany", "switchBuffer", "getLabels", "stop"]

# # general commands
# remote_fns += ["configure_from_dict", "is_running", "getDataDir"]

# # telemetry functions
# remote_fns += ["streamStatus", "getStreamBlock", "streamInfo", "startStream", "stopStream"]
# remote_fns += ["setDecimation", "startStreamPublish", "stopStreamPublish","setStreamHost","setStreamMulticast"]
# remote_fns += ["setStreamPort","addCallback", "removeCallback", "startTelemetry", "stopTelemetry","setStreamShape"]
# remote_fns += ["saveFrames","addParamCallback","removeParamCallback","addTelemFileCallback","removeTelemFileCallback"]