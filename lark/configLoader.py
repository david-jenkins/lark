
from copy import copy
from dataclasses import dataclass
from pathlib import Path
import toml

HERE = Path(__file__).parent.parent.resolve()

# print(HERE)
# print(Path.home())

@dataclass
class Config:
    """The basic lark config dataclass.
    """
    LARK_DIR:str = "/opt/lark"
    # PARAM_DIR:str = "/opt/lark/params"
    DATA_DIR:str = "/opt/lark/data"
    CONFIG_DIR:str = "/opt/lark/config"
    LOG_DIR:str = "/opt/lark/log"
    # CONFIG_DIR:Path = HERE/"conf"
    TELEMETRY_IP:str = "localhost"
    TELEMETRY_PORT:int = 18761
    DEFAULT_PREFIX:str = "lark"
    
    def __post_init__(self):
        self.LARK_DIR = Path(self.LARK_DIR)
        self.DATA_DIR = Path(self.DATA_DIR)
        self.CONFIG_DIR = Path(self.CONFIG_DIR)
        self.LOG_DIR = Path(self.LOG_DIR)
        # if not self.PARAM_DIR.is_absolute():
        #     self.PARAM_DIR = self.LARK_DIR/self.PARAM_DIR
        if not self.DATA_DIR.is_absolute():
            self.DATA_DIR = self.LARK_DIR/self.DATA_DIR
        if not self.CONFIG_DIR.is_absolute():
            self.CONFIG_DIR = self.LARK_DIR/self.CONFIG_DIR
        if not self.LOG_DIR.is_absolute():
            self.LOG_DIR = self.LARK_DIR/self.LOG_DIR


# read config at /etc/lark.cfg
def get_lark_config(reload:bool = False) -> Config:
    """Returns a Config with options loaded from file pointed to by /etc/lark.cfg

    Args:
        reload (bool, optional): Whether to reload the cfg file. Defaults to False and a cached version is returned.

    Returns:
        Config: The lark config, dataclass defined above
    """
    try:
        LARK_DIR =  Path(toml.load("/etc/lark.cfg")["LARK_DIR"])
        cfile = LARK_DIR()/"lark.cfg"
    except FileNotFoundError:
        print("No file at /etc/lark.cfg found, using /tmp/lark as main dir and conf/lark.cfg")
        LARK_DIR = "/tmp/lark"
        cfile = HERE/"conf"/"lark.cfg"
    if get_lark_config.config is None or reload:
        from_file = {"LARK_DIR":LARK_DIR}
        if cfile.exists():
            from_file.update(toml.load(cfile)["general"])
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

if __name__ == "__main__":
    c = get_lark_config()
    
    print(c)