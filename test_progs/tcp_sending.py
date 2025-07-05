#!/usr/bin/python3

import argparse
import socket
import time 
import math
import sys

parser = argparse.ArgumentParser("tcp_sending")
parser.add_argument("pkt_size")
parser.add_argument("receive_ip")
parser.add_argument("loops_cnt")
parser.add_argument("--sleep", default = "NaN")
args = parser.parse_args()

port = 1337

pkt_size = int(args.pkt_size)
receive_ip = args.receive_ip
loops_cnt = int(args.loops_cnt)
sleep = float(args.sleep)

socket_type = socket.SOCK_STREAM

sock = socket.socket(socket.AF_INET, socket_type)

total_packets = bytearray(loops_cnt.to_bytes(4, sys.byteorder))
buffer_size = bytearray(pkt_size.to_bytes(4, sys.byteorder))

data = bytearray([0x1a] * pkt_size)

print("Starting transmission...")

sock.connect((receive_ip, port))
sock.send(total_packets)
sock.send(buffer_size)

for i in range(0, loops_cnt):
    sock.send(data)
    if not math.isnan(sleep):
        time.sleep(sleep)

sock.close()
print("Done " + str(loops_cnt) + " transmissions of " + str(pkt_size) + " bytes.")
