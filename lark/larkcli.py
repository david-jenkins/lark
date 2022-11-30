#!/usr/bin/env python3

import argparse
from .interface import ControlClient
from .utils import statusBuf_tostring
from ast import literal_eval

def main():
    from lark.control import Control
    parser = argparse.ArgumentParser(description='Some helpful lark commands')
    parser.add_argument("cmd",metavar='cmd',type=str,nargs='+')
    parser.add_argument("--prefix",default="",dest='prefix',type=str)
    parser.add_argument("-s",dest='stdev',action='store_true')
    parser.add_argument("--string",dest='string',type=str)
    parser.add_argument("--name",dest="name",type=str)

    args = parser.parse_args()

    try:
        c:Control = ControlClient(args.prefix)
    except ConnectionError as e:
        print(e)
        return

    if args.cmd[0] == "status":
        value = c.getStreamBlock("rtcStatusBuf",1)
        print(statusBuf_tostring(value[0][0]))

    elif args.cmd[0] == "set":
        if len(args.cmd) != 3:
            raise ValueError("wrong number of args for set")
        try:
            value = literal_eval(args.cmd[2])
        except ValueError:
            value = args.cmd[2]
        c.set(args.cmd[1],value,switch=1,check=1)
        
    elif args.cmd[0] == "set_noswitch":
        if len(args.cmd) != 3:
            raise ValueError("wrong number of args for set")
        try:
            value = literal_eval(args.cmd[2])
        except ValueError:
            value = args.cmd[2]
        c.set(args.cmd[1],value,switch=0,check=1)
        
    elif args.cmd[0] == "switchbuf":
        print(c.switchBuffer())

    elif args.cmd[0] == "stop":
        c.stop()

    elif args.cmd[0] == "get":
        value = c.getMany(args.cmd[1:])
        for key,val in value.items():
            print(f"{key} = ",val)
            print(f"type({key}) = ",type(val))
            
    elif args.cmd[0] == "get1":
        val = c.get(args.cmd[1])
        key = args.cmd[1]
        print(f"{key} = ",val)
        print(f"type({key}) = ",type(val))

    elif args.cmd[0] == "labels":
        value = c.getLabels()
        print(value)

    elif args.cmd[0] == "print":
        values = c.getAll()
        for key,val in values.items():
            print(f"{key} = {val}")
            
    elif args.cmd[0] == "print2":
        names = c.getAll()
        for key,value in names.items():
            print(f"{key} = {value}")

    elif args.cmd[0] == "time":
        nframes = 1000
        if len(args.cmd) == 2:
            nframes = int(args.cmd[1])
        values = c.getStreamBlock("rtcTimeBuf",nframes)
        mean = values[0].mean()
        min = values[0].min()
        max = values[0].max()
        if not args.stdev:
            std = values[0].std(ddof=1)
            print(f"{mean:.5} +- {std:.5} s (range {max:.5} - {min:.5} = {max-min:.5})")
            print(f"{1/mean:.5} +- {std/mean/mean:.5} Hz")
        else:
            print(f"{mean:.5} s (range {max:.5} - {min:.5} = {max-min:.5})")
            print(f"{1/mean:.5} Hz")

    c.conn.close()

if __name__ == "__main__":
    main()
