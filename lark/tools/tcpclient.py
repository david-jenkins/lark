# Python program to implement client side of chat room.
import socket
import select
import sys

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ip = "10.45.45.22"
    # ip = "10.45.45.21"
    port = 18467
    # port = 21
    print(f"Connecting to {ip}:{port}  ...")
    server.connect((ip, port))
    print("Connected!")
    go = 1

    while go:

        # maintains a list of possible input streams
        sockets_list = [sys.stdin, server]

        """ There are two possible input situations. Either the
        user wants to give manual input to send to other people,
        or the server is sending a message to be printed on the
        screen. Select returns from sockets_list, the stream that
        is reader for input. So for example, if the server wants
        to send a message, then the if condition will hold true
        below.If the user wants to send a message, the else
        condition will evaluate as true"""
        read_sockets, write_socket, error_socket = select.select(sockets_list,[],[])

        for socks in read_sockets:
            if socks == server:
                message = socks.recv(2048)
                if message == b"":
                    print("server probably disconnected")
                    go = 0
                print(message.decode())
            else:
                message = input("--> ")
                # message = message.split("\n")[0]
                server.send(message.encode())
                print("<You>: ", message)
                cmd = message.split(" ")[0]
                print(cmd)
                if cmd in ('quit','exit'):
                    go = 0
                # sys.stdout.write("<You>: ")
                # sys.stdout.write(message)
                # sys.stdout.flush()
    server.close()


if __name__ == "__main__":
    main()