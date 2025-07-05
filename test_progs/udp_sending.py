#!/usr/bin/python3

import argparse
import socket
import time 
import math
import sys

parser = argparse.ArgumentParser("udp_sending")
parser.add_argument("receive_ip")
parser.add_argument("--sleep", default = "NaN")
args = parser.parse_args()

port = 1337

receive_ip = args.receive_ip
loops_cnt = 10000
sleep = float(args.sleep)
pkt_size = 1024
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

data = bytearray([0x1a] * pkt_size)

print("Starting transmission...")

for i in range(0, loops_cnt):
    sock.sendto(data, (receive_ip, port))
    if not math.isnan(sleep):
        time.sleep(sleep)

sock.close()
print("Done " + str(loops_cnt) + " transmissions of " + str(pkt_size) + " bytes.")
