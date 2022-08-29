
# from ..client import rpycClient
# from ..daemon import rpycControlClient

# prefix = None
# lark = None
# CONFIG_DIR = "/home/canapyrtc/git/canapy-rtc/config"
# DEFAULT_PREFIX = "canapy"

# def startlark(hostname,params):
#     if prefix is None:
#         raise RuntimeError("No prefix specified")
#     global lark
#     lark = rpycControlClient(prefix,hostname=hostname,params=params)

# def getlark():
#     global lark
#     if lark is not None:
#         try:
#             lark.conn.ping()
#         except EOFError as e:
#             print(e)
#             print("Lark not connected, retrying")
#         else:
#             return lark
#     lark = rpycClient(prefix)
#     return lark

# def closelark():
#     global lark
#     try:
#         lark.conn.close()
#     except Exception:
#         pass
#     lark = None

# from ..config import DATA_DIR

# if __name__ == "__main__":
#     lark = rpycClient("canapy")
#     print(lark)
#     prefix = "canapy"
#     lark = None
#     getlark()
