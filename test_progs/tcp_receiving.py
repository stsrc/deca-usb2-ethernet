#!/usr/bin/python3

import argparse
import socket
import time
import sys 

parser = argparse.ArgumentParser("tcp_receiving")
parser.add_argument("ip")
args = parser.parse_args()

ip = args.ip

port = 1337

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((ip, port))
sock.listen(1)

time_nanosec = time.time_ns()
received = 0
packets = 0
loop_cnt = 0

client, addr = sock.accept()
data = client.recv(4)
buf = client.recv(4)

total_packets = int.from_bytes(data, byteorder=sys.byteorder, signed=False)
buffer_size = int.from_bytes(buf, byteorder = sys.byteorder, signed=False)

while packets < total_packets:
    data = client.recv(buffer_size)

    received = received + len(data)
    packets = packets + 1
    loop_cnt = (loop_cnt + 1) % 1000
    if not loop_cnt % 100:
        print("received {} packets".format(packets))
    if not loop_cnt:
        now = time.time_ns()
        print("received: " + str(received) + "; time: " + str((now - time_nanosec) / 1000) + " [us]")
        time_nanosec = now
        received = 0

client.close()
sock.close()
