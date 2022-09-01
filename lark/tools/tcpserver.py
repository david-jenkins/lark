#!/usr/bin/env python3

import socket
import select
import sys
import os
import threading
import concurrent.futures
import time

# from canapyrtc.srtc.darc import Control

class clientThread(threading.Thread):
    def __init__(self, conn, addr, executor):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.exc = executor
        self.cmd_list = None
        self.commands = None
        self.r, self.w = os.pipe()

    def run(self):

        # sends a message to the client whose user object is conn
        self.conn.send(b"darc SRTC communication v0.0.0.0.1")
        self.go = 1
        while self.go:
            rs, ws, es = select.select([self.r,self.conn], [], [])
            if self.r in rs:
                print("got exit")
                break
            try:
                message = self.conn.recv(2048)
                print("Server got: ",message)
                if message == b'':
                    print("Client probably disconnected")
                    self.stop()
                    continue
            except Exception as e:
                print("Exception in client thread: ",e)
                continue
            else:
                message = message.split(b'\r')[0].split(b" ")
                cmd = message[0].decode()
                if self.commands is not None and self.cmd_list is not None:
                    if cmd in self.cmd_list:
                        print("executing command: ",self.commands[cmd])
                        try:
                            args = self.parseArgs(cmd,message[1:])
                            retval = self.commands[cmd][0](*args)
                            to_send = f"<{self.addr[0]}>: {retval}".encode()
                            self.conn.send(to_send)
                        except Exception as e:
                            print(e)
                        else:
                            self.conn.send(retval)
                        finally:
                            continue
                        #run commands
                if cmd in ('quit','exit'):
                    self.go = 0
                    self.conn.send(b"Goodbye!")
                else:
                    print(f"<{self.addr[0]}> {message} == incorrect!")
                    message_to_send = f"<{self.addr[0]}> {message}".encode()
                    self.conn.send(message_to_send)

    def stop(self):
        self.go = 0
        os.write(self.w,b' ')

    def setCommands(self,commands):
        self.cmd_list = commands.keys()
        self.commands = commands

    def parseArgs(self,cmd,args):
        retvals = []
        for i,a in enumerate(args):
            try:
                retvals.append(self.commands[cmd][1][i](a.decode()))
            except Exception as e:
                print("Exception in parseArgs: ", e)
        return retvals


class TCPServer(threading.Thread):
    def __init__(self,ip_addr,port):
        super().__init__()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # takes the first argument from command prompt as IP address
        self.ip_addr = str(ip_addr)

        # takes second argument from command prompt as port number
        self.port = int(port)

        """
        binds the server to an entered IP address and at the
        specified port number.
        The client must be aware of these parameters
        """
        self.server.bind((self.ip_addr, self.port))

        """
        listens for 100 active connections. This number can be
        increased as per convenience.
        """
        self.server.listen(10)

        self.list_of_clients = []
        self.list_of_client_threads = []

        """Using the below function, we broadcast the message to all
        clients who's object is not the same as the one sending
        the message """
        self.go = 1

        self.commands = None
        self.args = None

        self.r, self.w = os.pipe()

    def run(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            while self.go:
                rs, ws, es = select.select([self.r,self.server], [], [])
                if self.r in rs:
                    print("got exit")
                    break
                try:
                    conn, addr = self.server.accept()
                except Exception as e:
                    print("Exception in server.run: ", e)
                else:
                    if not self.go:
                        break

                    self.list_of_clients.append(conn)

                    print (addr[0] + " connected")

                    client = clientThread(conn, addr, executor)
                    client.setCommands(self.commands)
                    self.list_of_client_threads.append(client)
                    client.start()

            print("while loop ended")
            for client in self.list_of_client_threads:
                client.stop()
            print("stopped clients")
            for conn in self.list_of_clients:
                conn.close()
            print("closed clients")
            self.server.shutdown(socket.SHUT_RDWR)
            self.server.close()

    def broadcast(self, message):
        for client in self.list_of_clients:
            try:
                client.send(message)
            except Exception as e:
                print("Exception in broadcast: ",e)
                client.close()
                self.remove(client)

    def remove(self,connection):
        if connection in self.list_of_clients:
            self.list_of_clients.remove(connection)

    def stop(self):
        print("stopping")
        self.go = 0
        os.write(self.w, b'stop')

    def setCommands(self,commands):
        self.commands = commands

class darc:
    def __init__(self,*args, **kwargs):
        self.darc = None
        for dictionary in args:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def get(self, name):
        return self.params[name]

    def set(self, name, value):
        self.params[name] = value

def print1(args):
    print(args)
    return args

def execute(x,y,z):
    print(x,y,z)
    return x*y*z

def help():
    return "Type print any\n" + \
           "Type execute int int float\n"

def stop():
    server.stop()

def blocking(wait):
    time.sleep(wait)

if __name__ == "__main__":
    server = TCPServer("10.45.45.22", 18467)
    params = {'gain':0.1,'nacts':97}
    d = darc(params)
    d.params = params

    commands = {'print' : (print1,[str]),
                'execute' : (execute,[int,int,float]),
                'help' : (help,),
                'stop' : (stop,),
                'blocking' : (blocking,),
                'get' : (d.get,[str]),
                'set' : (d.set, [str,str]),
                }
    server.setCommands(commands)

    server.start()
