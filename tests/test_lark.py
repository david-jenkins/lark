
import lark
from lark.interface import ControlClient
from lark import LarkConfig, NoLarkError, startservice, getservice, stopservice
from lark.configLoader import get_lark_config
from lark.interface import get_registry_parameters

from lark.services import BaseService, BasePlugin

class TestService(BaseService):
    PLUGINS = {}
    RESULTS = {}
    INITIALISED = {}

@TestService.register_plugin("TestPlugin")
class TestFunc(BasePlugin):
    def Execute(self):
        self.result = "Run success"

def test_service():
    handle1 = startservice(TestService, "Tester", get_registry_parameters().RPYC_HOSTNAME)
    
    handle2 = getservice("Tester")
    
    handle1.getPlugin("TestPlugin").run()
    
    print(handle2.getResult("TestPlugin"))
    
    stopservice("Tester")

if __name__ == "__main__":
    print(lark.PREFIX)
    larkconfig = LarkConfig("canapy")
    this_lark = larkconfig.getlark()
    print(this_lark)
    # lark.INSTANCES["canapy"] = this_lark
    print(getlark("canapy"))
    lark.INSTANCES.pop("canapy")
    print(getlark("canapy"))
    lark.PREFIX = "canapy1"
    try:
        print(getlark())
    except NoLarkError:
        print("ERRORORROOORRRR")
    print(lark.PREFIX)