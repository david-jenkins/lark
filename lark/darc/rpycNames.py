#!/usr/bin/env python3
"""

By default the registry server listens with the parameters defined in 4 ways with
increasing priority:
    written in this file
    written in the config file at /etc/rpyc.cfg (darc/conf/rpyc.cfg)
    written in environment variables - RPYC_IP, RPYC_PORT, RPYC_MODE
    supplied as command line parameters when running this script (darcNames)

The broadcast mode (UDP, ip=255.255.255.255) *SHOULD* allow darc instances on the local network to find
the registry server automatically. If this does not work then a fixed IP should be used.
The Broadcasting mode DOES NOT work with the Linux firewall. Disable the firewall or use a fixed IP.

This script is added to the PATH as darcNames, use -o option to print logs to command line
without -o the log is appended to /dev/shm/darcNames.log. Run darcNames & to put into background.
use "nohup darcNames &" to keep it running even when the terminal is closed, use "pkill -f darcNames" to stop
if nohup is not available, use screen or tmux

if darcNames is killed when darc is running, darc will reconnect to a restarted nameserver with the
same starting arguments after at most 60 seconds

use darcNames ip:port to change the arguments at run time
use the -mode=MODE flag to change the mode
e.g.
darcNames 192.168.1.11:2456 -mode=UDP
darcNames 10.0.1.2:4573 -mode=TCP

alternatively, the ip, port and mode can be set with environment variables,
which can be set persistently if needed, i.e in .bashrc
BUT be careful that the same environment variables are set locally for darc
e.g.
export RPYC_IP=192.168.1.11
export RPYC_PORT=35677
export RPYC_MODE=TCP

EVEN ALTERNATIVELY, and the recomended option,
the paramters are loaded from the file at /etc/rpyc.cfg which is installed from darc/conf/rpyc.cfg
to use this mode do not set any environment variables and do not use command line parameters.
"""

import os
import sys
import time
import argparse
import toml
import logging
import datetime
from rpyc.utils.registry import UDPRegistryServer, TCPRegistryServer
from rpyc.lib import setup_logger
from collections import ChainMap

DEFAULT_IP = "255.255.255.255"
DEFAULT_PORT = "18811"
DEFAULT_MODE = "UDP"

DEFAULT_PARAMS = {"RPYC_IP":DEFAULT_IP,"RPYC_PORT":DEFAULT_PORT,"RPYC_MODE":DEFAULT_MODE}

def get_default_registry_parameters():

    if os.path.exists("/etc/rpyc.cfg"):
        try:
            with open("/etc/rpyc.cfg",'r') as yf:
                cfg_args = toml.load(yf)
        except Exception as e:
            print(e)
            print("Can't open /etc/rpyc.cfg file")

    env_args = {}
    for k in DEFAULT_PARAMS.keys():
        value = os.environ.get(k)
        if value is not None:
            env_args[k] = value

    these_args = ChainMap(env_args,cfg_args,DEFAULT_PARAMS)

    return these_args["RPYC_IP"], these_args["RPYC_PORT"], these_args["RPYC_MODE"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start the RPyC registry server')

    this_ip, this_port, this_mode = get_default_registry_parameters()

    default_ip_port = f"{this_ip}:{this_port}"
    parser.add_argument("ip_port",default=default_ip_port,nargs='?',type=str,help="format = ip:port")
    parser.add_argument("-mode",dest="mode",default=this_mode,type=str, help="UDP or TCP")
    parser.add_argument("-o",dest="output",action="store_true",help="Use to print output to command line, else prints to /dev/shm/darcNames.log")

    args = parser.parse_args()

    ip = args.ip_port.split(':')[0]

    if len(ip.split('.')) != 4:
        if ip != 'localhost':
            print("ip is not valid")
            parser.print_help()
            exit(0)

    try:
        port = int(args.ip_port.split(':')[1])
    except ValueError as e:
        print("error with port, using default port")
        port = DEFAULT_PORT
    except IndexError as e:
        print("using default port")
        port = DEFAULT_PORT

    if args.mode != "UDP" and args.mode != "TCP":
        print("mode is not valid")
        parser.print_help()
        exit(0)

    try:
        if args.mode == "UDP":
            server = UDPRegistryServer(host=ip, port=port)
        elif args.mode == "TCP":
            server = TCPRegistryServer(host=ip, port=port)
    except OSError as e:
        if e.errno == 98:
            print("Address already in use. Is darcNames already running?")
            sys.exit(0)
        else:
            raise e

    if not args.output:
        setup_logger(False,"/dev/shm/darcNames.log")
    else:
        setup_logger(False, None)
    now = datetime.datetime.now()
    logging.info(f"Starting new darcNames at {now.hour:0>2}:{now.minute:0>2} on {now.day:0>2}/{now.month:0>2}/{now.year} :-")
    server.start()
