
import lark
from .interface import ControlClient
from lark import getlark, NoLarkError

if __name__ == "__main__":
    print(lark.PREFIX)
    this_lark = ControlClient("canapy")
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
