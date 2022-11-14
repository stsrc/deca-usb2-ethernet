#!/usr/bin/env python3
#
# Copyright (c) 2022 Konrad Gotfryd <gotfrydkonrad@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0

import os

from amaranth import *
from simple_ports_to_wb import SimplePortsToWb

__all__ = ["InjectData"]

class InjectData(Elaboratable):
    def __init__(self, simulation):
        self.simple_ports_to_wb = SimplePortsToWb()
        self.arp_packet = [0xffffffff, 0xffff0a0a,
                           0x0a0a0a0a, 0x08060001,
                           0x08000604, 0x00010a0a,
                           0x0a0a0a0a, 0xc0a80042,
                           0x00000000, 0x0000c0a8,
                           0x00870000, 0x00000000,
                           0x00000000, 0x00000000,
                           0x00000000]
        self.counter = Signal(4)
        self.leds = Signal(8)
        self.wait_counter = Signal(26)
        self.phy_resetn = Signal()
        self.simulation = simulation
    def get_bus(self):
        return self.simple_ports_to_wb.bus

    def elaborate(self, platform):
        m = Module()
        m.submodules.simple_ports_to_wb = self.simple_ports_to_wb

        rom = Memory(width=32, depth=16, init=self.arp_packet)
        m.submodules.rom_read_port = rom_read_port = rom.read_port(transparent=False)

        # TODO: use RAM initializing with arp_packet, it would make inject_data.py better
        with m.FSM(reset="RESET"):
            with m.State("RESET"):
                m.d.sync += self.counter.eq(0)
                m.d.sync += self.leds.eq(1)
                m.d.sync += self.wait_counter.eq(0)
                m.d.sync += self.phy_resetn.eq(0)
                m.next = "WAIT_BEFORE_START"

            with m.State("WAIT_BEFORE_START"):
                m.d.sync += self.wait_counter.eq(self.wait_counter + 1)

                if self.simulation:
                    m.d.sync += self.wait_counter.eq(30000000)

                with m.If (self.wait_counter == 30000000):
                    m.next = "WRITE_ARP_PACKET"
                    m.d.sync += self.wait_counter.eq(0)
            
            with m.State("WRITE_ARP_PACKET"):
                m.d.sync += self.leds.eq(2)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(rom_read_port.data)
                m.d.sync += rom_read_port.addr.eq(self.counter + 1)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x0400_0000 + 4 * self.counter) #TODO wtf 0x04000000?
                m.d.sync += self.counter.eq(self.counter + 1)
                m.next = "WRITE_ARP_PACKET_WAIT"
            with m.State("WRITE_ARP_PACKET_WAIT"):
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out & (self.counter != 15)):
                    m.next = "WRITE_ARP_PACKET"
                with m.Elif(self.simple_ports_to_wb.op_rdy_out & (self.counter == 15)):
                    m.next = "WRITE_ETHMAC_INT_MASK"
            with m.State("WRITE_ETHMAC_INT_MASK"):
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000007f)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x08 >> 2)
                m.next = "WRITE_ETHMAC_INT_MASK_WAIT"
            with m.State("WRITE_ETHMAC_INT_MASK_WAIT"):
                m.d.sync += self.leds.eq(5)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_MAC_ADDR0"
            with m.State("WRITE_ETHMAC_MAC_ADDR0"):
                m.d.sync += self.leds.eq(4)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0a0a_0a0a)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x40 >> 2)
                m.next = "WRITE_ETHMAC_MAC_ADDR0_WAIT"
            with m.State("WRITE_ETHMAC_MAC_ADDR0_WAIT"):
                m.d.sync += self.leds.eq(5)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_MAC_ADDR1"
            with m.State("WRITE_ETHMAC_MAC_ADDR1"):
                m.d.sync += self.leds.eq(6)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000_0a0a)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x44 >> 2)
                m.next = "WRITE_ETHMAC_MAC_ADDR1_WAIT"
            with m.State("WRITE_ETHMAC_MAC_ADDR1_WAIT"):
                m.d.sync += self.leds.eq(7)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_MODER"
                    m.d.sync += self.phy_resetn.eq(1)
            with m.State("WRITE_ETHMAC_TX_BD_NUM"):
                m.d.sync += self.leds.eq(6)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000_0001)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x20 >> 2)
                m.next = "WRITE_ETHMAC_TX_BD_NUM_WAIT"
            with m.State("WRITE_ETHMAC_TX_BD_NUM_WAIT"):
                m.d.sync += self.leds.eq(7)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_MODER"
            with m.State("WRITE_ETHMAC_MODER"):
                m.d.sync += self.leds.eq(8)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000a002) # think about enabling crc
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x00 >> 2)
                m.next = "WRITE_ETHMAC_MODER_WAIT"
            with m.State("WRITE_ETHMAC_MODER_WAIT"):
                m.d.sync += self.leds.eq(9)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_TX_BUF_DESC_0"
            with m.State("WRITE_ETHMAC_TX_BUF_DESC_0"):
                m.d.sync += self.leds.eq(10)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0400_0000)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x404 >> 2)
                m.next = "WRITE_ETHMAC_TX_BUF_DESC_0_WAIT"
            with m.State("WRITE_ETHMAC_TX_BUF_DESC_0_WAIT"):
                m.d.sync += self.leds.eq(11)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_TX_BUF_DESC_1"

            with m.State("WRITE_ETHMAC_TX_BUF_DESC_1"):
                m.d.sync += self.leds.eq(12)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x003c_e000)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x400 >> 2)
                m.next = "WRITE_ETHMAC_TX_BUF_DESC_1_WAIT"
            with m.State("WRITE_ETHMAC_TX_BUF_DESC_1_WAIT"):
                m.d.sync += self.leds.eq(13)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "JUST_WAIT"
            with m.State("JUST_WAIT"):
                m.d.sync += self.leds.eq(self.wait_counter[18:25])
                m.d.sync += self.wait_counter.eq(self.wait_counter + 1)
                with m.If (self.wait_counter == 60000000):
                    m.next = "WRITE_ETHMAC_TX_BUF_DESC_0"
                    m.d.sync += self.wait_counter.eq(0)

        return m
