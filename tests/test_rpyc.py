
from lark.rpyclib.interface import connectClient, startServer
import numpy
from lark.rpyclib.interface import rpycService
import socket
import time

class MyNewService(rpycService):
    def __init__(self, name):
        super().__init__(name)

    def my_func(self, x):
        print(x)
        return type(x)

if __name__ == "__main__":
    x = {"hello":"hi","goodbye":"bye"}
    name = "this"
    obj1 = startServer(x,name)
    time.sleep(0.01)
    obj12 = startServer(x,name)
    time.sleep(0.01)
    obj13 = startServer(x,name)
    time.sleep(0.01)
    obj14 = startServer(x,name)
    time.sleep(0.01)
    obj2, conn = connectClient(name)

    print(obj1)
    print(obj2)

    print(obj1)
    try:
        print(obj2)
    except EOFError as e:
        print("Server is gone")
    try:
        obj2, conn = connectClient(name)
    except ConnectionError as e:
        print("Working as intended")

    # name = "that"
    y = MyNewService(name)

    y.new_param = None

    # can use with to startServer, closes the server when done
    with startServer(y) as obj3:
        time.sleep(0.01)

        obj4, conn = connectClient(y.rpyc_name)

        print(obj3)
        print(obj4)

        t = obj4.my_func(5)

        print(t)

        # can start "blocking" by joining the thread
        try:
            obj3.rpyc_thread.join()
        except KeyboardInterrupt:
            pass

    print(y.new_param)

    print(obj1 .rpyc_name)
    print(obj12.rpyc_name)
    print(obj13.rpyc_name)
    print(obj14.rpyc_name)

    obj1.close()
    obj12.close()
    obj13.close()
    obj14.close()