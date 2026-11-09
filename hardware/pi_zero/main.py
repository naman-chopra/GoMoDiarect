import socket
from datetime import datetime as dt
import os
from clickutil import capture


TCP_IP = "0.0.0.0"
TCP_PORT = 60001
BUFFER_SIZE = 40960
username = "Naman_chopra"

# Create a socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(5)

print("Server is listening on {}:{}".format(TCP_IP, TCP_PORT))


def upload(file):
    with open(file, "rb") as f:
        data = f.read()
        while data:
            client_socket.send(data)
            data = f.read()
    now = dt.now().time().strftime("%H:%M:%S")
    print(f"\n-----------Images sent at {now}----------------\n")


while True:
    # Accept connections from clients
    client_socket, addr = s.accept()
    print("Connection from", addr)
    ### Handle push button
    # response = "HTTP/1.1 200 OK\r\n\r\nMessage received"

    # client_socket.send(response.encode())
    now = dt.now().time().strftime("%H%M%S")
    save = username + now + ".jpg"
    capture(f"{save}")
    upload(save)
    os.remove(save)

    client_socket.close()
