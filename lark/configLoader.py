
from copy import copy
from dataclasses import dataclass
from distutils.dir_util import remove_tree
from pathlib import Path
import toml

HERE = Path(__file__).parent.parent.resolve()

cfile = Path("/etc/lark.cfg")

# print(HERE)
# print(Path.home())

@dataclass
class Config:
    DATA_DIR:Path = Path("/tmp/larkdata")
    CONFIG_DIR:Path = Path.home()/"lark/config"
    # CONFIG_DIR:Path = HERE/"conf"
    TELEMETRY_IP:str = "localhost"
    TELEMETRY_PORT:int = 18761
    DEFAULT_PREFIX:str = "lark"

# read config at /etc/lark.cfg
def get_lark_config(reload:bool = False) -> Config:
    if get_lark_config.config is None or reload:
        from_file = {}
        if cfile.exists():
            from_file = toml.load(cfile)["general"]
        get_lark_config.config = Config(**from_file)
    return get_lark_config.config

get_lark_config.config = None
# this is a bad idea as processes will be started by root and so this will be inconsistent
# config at /etc/lark.cfg will be consistent for all users
# cfile = Path.home()/"lark.cfg"
# if cfile.exists():
#     cf = toml.load(cfile)["general"]
#     config.update(cf)
#     del cf

# for key, value in config.items():
#     globals()[key] = value
    
    
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