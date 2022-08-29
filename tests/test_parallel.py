import time
from lark.parallel import threadSynchroniser, processSynchroniser

def printlist(args,delay,ret):
    for i in args:
        print(i)
        time.sleep(delay)
    return args[ret]

def test_synchroniser():
    lista = ['a1','a2','a3','a4','a5']
    listb = ['b1','b2','b3','b4','b5']
    listc = ['c1','c2','c3','c4','c5']
    listd = ['d1','d2','d3','d4','d5']

    retvals1 =  threadSynchroniser([printlist,printlist,printlist,printlist],[(lista,0.1,2),(listb,0.15,3),(listc,0.2,1),(listd,0.05,4)],0.01)
    print(retvals1)
    retvals2 = processSynchroniser([printlist,printlist,printlist,printlist],[(lista,0.1,2),(listb,0.15,3),(listc,0.2,1),(listd,0.05,4)],0.01)
    print(retvals2)

    assert retvals2==retvals1

if __name__ == "__main__":
    test_synchroniser()