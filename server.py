import threading
import socket
from datetime import datetime


# Server configuration
HOST = '127.0.0.1'  # localhost
PORT = 12345        # port number

# Store connected clients
clients:list[socket.socket] = []
nicknames = []


def broadcast(message):
    """Send message to all connected clients"""
    for client in clients:
        try:
            client.send(message)
        except Exception:
            # Remove client if sending fails
            remove_client(client)


def remove_client(client):
    """Remove a client from the server"""
    if client in clients:
        index = clients.index(client)
        clients.remove(client)
        nickname = nicknames[index]
        nicknames.remove(nickname)
        broadcast(f"{nickname} left the chat!".encode('utf-8'))
        print(f"{nickname} left the chat!".encode('utf-8'))
        client.close()


def handle_client(client):
    """Handle messages from a client"""
    while True:
        try:
            message = client.recv(1024)
            if message:
                index = clients.index(client)
                nickname = nicknames[index]
                message=("["+nickname+"]: "+message.decode("utf-8")).encode("utf-8")
                broadcast(message)
                print(str(client.fileno())+" "+message.decode("utf-8"))
            else:
                remove_client(client)
                break
        except Exception:
            remove_client(client)
            break


def find_by_fn(fn):
    return [c.fileno() for c in clients].index(int(fn))

def admin():
    start=datetime.now()
    while True:
        try:
            inp=input()
            command=inp.split(" ")
            if(command[0]=="kick"):
                fileno=command[1]
                ix = find_by_fn(fileno)
                to_remove=clients[ix]
                remove_client(to_remove)
            if(command[0]=="list"):
                cli_list=zip(clients,nicknames)
                print('\n'.join(f"{client.fileno()}:{nickname}" for client, nickname in cli_list))
            if(command[0]=="rename"):
                fileno=command[1]
                ix=find_by_fn(fileno)
                name=command[2]
                nicknames[ix]=name
            if(command[0]=="send"):
                message = (("<SERVER>: " + command[1]).encode("utf-8"))
                try:
                    broadcast(message)
                except Exception:
                    print("not sent")
            if(command[0]=="time"):
                d=datetime.now()-start
                print(d)
            if(command[0]=="exec"):
                exec(command[1])
            if(command[0]=="help"):
                print("help\nlist\ntime\nkick -fn\nrename -fn -name\nsend -msg\nexec -code")
        except Exception:
            print("ERROR")


def start_server():
    """Start the chat server"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    server.bind((HOST, PORT))
    server.listen()
    admin_thread=threading.Thread(target=admin)
    admin_thread.start()

    print(f"Chat server is listening on {HOST}:{PORT}")

    while True:
        client, address = server.accept()
        print(f"Connected with {str(address)}")

        # Request nickname
        client.send("NICK".encode('utf-8'))
        try:
            nickname = client.recv(1024).decode('utf-8')
            nicknames.append(nickname)
            print(f"Nickname of {client.fileno()} is {nickname}")
            broadcast(f"{nickname} joined the chat!".encode('utf-8'))
        except Exception:
            remove_client(client)
            continue

        clients.append(client)
        # Start handling thread for client
        thread = threading.Thread(target=handle_client, args=(client,))
        thread.start()


if __name__ == "__main__":
    start_server()
