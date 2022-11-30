"""
larkcontrol is the equilavne of darccontrol to start darc/lark at the terminal

"""


import subprocess
import time


def test_launch_lark_testpy3k():
    subprocess.run(["larkcontrol","--prefix=testpy3k", "../lark/conf/configTestPy3k.py"])
    
def new_lark_testpy3k():
    return subprocess.Popen(["larkcontrol","--prefix=testpy3k", "../lark/conf/configTestPy3k.py"])
    
def test_larkmagic():
    
    lark = new_lark_testpy3k()
    time.sleep(1)
    subprocess.run(["larkmagic", "--prefix=testpy3k", "status"])
    time.sleep(1)
    subprocess.run(["larkmagic", "--prefix=testpy3k", "labels"])
    time.sleep(1)
    subprocess.run(["larkmagic", "--prefix=testpy3k", "print"])
    time.sleep(1)
    subprocess.run(["larkmagic", "--prefix=testpy3k", "stop"])
    
    lark.communicate()

if __name__ == "__main__":
    # test_launch_lark_testpy3k()
    test_larkmagic()