
import time
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import Manager


def sync_wrap(func, args, lock):
    """Wrapper function for the Synchroniser functions"""
    lock.wait()
    return func(*args)

def threadSynchroniser(funcs:list, args:list=None, delay=0) -> list:
    """Synchronise the parallel execution of functions in funcs.
    Does funcs[i](args[i]) after delay for each element in funcs.
    """
    barrier = threading.Barrier(len(funcs)+1)
    futures = []
    if args is None:
        args = [()]*len(funcs)
    with ThreadPoolExecutor(max_workers=len(funcs)) as executor:
        for func,arg in zip(funcs,args):
            futures.append(executor.submit(sync_wrap,func,arg,barrier))
        time.sleep(delay)
        barrier.wait()
    return [future.result() for future in futures]

def processSynchroniser(funcs:list, args:list, delay=0) -> list:
    """Synchronise the parallel execution of functions in funcs.
    Uses seperate Python processes to sidestep the GIL, not everything
    can use this! Functions need pickling.
    Does funcs[i](args[i]) after delay for each element in funcs.
    """
    m = Manager()
    barrier = m.Barrier(len(funcs)+1)
    futures = []
    with ProcessPoolExecutor(max_workers=len(funcs)) as executor:
        for i,func in enumerate(funcs):
            futures.append(executor.submit(sync_wrap,func,args[i],barrier))
        time.sleep(delay)
        barrier.wait()
    return [future.result() for future in futures]