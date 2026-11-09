import socket
from datetime import datetime as dt
import os

# TCP_IP should be the IP address of the Raspberry Pi
TCP_IP = "0.0.0.0"  # Replace with your Raspberry Pi's IP
TCP_PORT = 60001
BUFFER_SIZE = 40960

# Path to the directory containing images to send

# Create a socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(5)

print("Server is listening on {}:{}".format(TCP_IP, TCP_PORT))

# while True:
# Accept connections from clients
client_socket, addr = s.accept()
print("Connection from", addr)

# List image files in the directory
image_files = ["mandala.jpg"]

for file in image_files:
    # Send each image file to the client
    with open(file, "rb") as f:
        data = f.read()
        while data:
            client_socket.send(data)
            data = f.read()

client_socket.close()
now = dt.now().time().strftime("%H:%M:%S")
print(f"\n-----------Images sent at {now}----------------\n")
s.close()
