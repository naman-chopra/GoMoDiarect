import socket
import os

print(os.getcwd())


TCP_IP = "192.168.170.153"  # Listen on all available network interfaces
TCP_PORT = 60001

BUFFER_SIZE = 40960

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)  # Listen for one incoming connection

print(f"Server listening on {TCP_IP}:{TCP_PORT}")

conn, addr = s.accept()
print(f"Connection address: {addr}")

# Define the path to the file you want to send
file_path = "GeeksForGeeks.png"

with open(file_path, "rb") as f:
    print("File opened")
    while True:
        data = f.read(BUFFER_SIZE)
        if not data:
            break
        conn.send(data)

print("File sent successfully")
conn.close()
print("Connection closed")
