# DECA USB Ethernet Interface

DECA MAX 10 based USB 2.0 High Speed Ethernet interface, fully supporting 100Mbps duplex speed.

## Hardware
This project is written for [DECA MAX 10 FPGA board](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=English&CategoryNo=&No=944&PartNo=1#), which contains all needed interfaces and ICs, like FPGA (MAX10 10M50DAF484C6G), high-speed (480-Mbps) USB transceiver (TUSB1210) and Ethernet 10/100Mbps PHY transceiver (DP83620).

## Gateware
This project bases heavily on [deca-usb2-audio-interface](https://github.com/amaranth-community-unofficial/deca-usb2-audio-interface) and written in Verilog [ethmac](https://opencores.org/projects/ethmac).
Connection of both things is implemented in [Amaranth, a Python FPGA framework](https://github.com/amaranth-lang/amaranth) and is a relatively simple thing to do, as some kind of bridge between one interface and another is needed.

### How to build gateware
1. Prerequisite: Install quartus (intel prime) and assure that it is visible by shell (path to binaries is in PATH env variable),
2. Call `make -C gateware`, after that `gateware/build/top.sof` should be built.

## Firmware
To use it with PC Linux kernel driver was written, which is located under `driver` directory.

### How to build firmware
1. Prerequisite: assure that you can build out-of-tree Linux kernel driver,
2. Call `make -C driver`, after that `driver/deca_eth_interface.ko` should be built
