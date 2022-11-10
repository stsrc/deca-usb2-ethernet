#!/usr/bin/env python3
#
# Copyright (c) 2022 Konrad Gotfryd <gotfrydkonrad@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0

import os

from amaranth import *
from simple_ports_to_wb import SimplePortsToWb

__all__ = ["InjectData"]

class InjectData(Elaboratable):
    def __init__(self):
        self.simple_ports_to_wb = SimplePortsToWb()
        self.arp_packet = [0xffffffff, 0xffff0a0a,
                           0x0a0a0a0a, 0x08060001,
                           0x08000604, 0x00010a0a,
                           0x0a0a0a0a, 0xc0a80042,
                           0x00000000, 0x0000c0a8,
                           0x00870000, 0x00000000,
                           0x00000000, 0x00000000,
                           0x00000000, 0x9e597bf9]
        self.counter = Signal(4)
        self.leds = Signal(8)

    def get_bus(self):
        return self.simple_ports_to_wb.bus

    def elaborate(self, platform):
        m = Module()
        m.submodules.simple_ports_to_wb = self.simple_ports_to_wb

        rom = Memory(width=32, depth=16, init=self.arp_packet)
        m.submodules.rom_read_port = rom_read_port = rom.read_port(transparent=False)

        # TODO: check if clock is properly assigned, should be usb_clk something
        with m.FSM(reset="RESET"):
            with m.State("RESET"):
                m.d.sync += self.counter.eq(0)
                m.d.sync += self.leds.eq(1)
                m.next = "WRITE_ARP_PACKET"
            with m.State("WRITE_ARP_PACKET"):
                m.d.sync += self.leds.eq(2)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(rom_read_port.data)
                m.d.sync += rom_read_port.addr.eq(self.counter + 1)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x0001_0000 + self.counter * 4)
                m.d.sync += self.counter.eq(self.counter + 1)

                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.d.sync += self.leds.eq(0b11110000)

                m.next = "WRITE_ARP_PACKET_WAIT"
            with m.State("WRITE_ARP_PACKET_WAIT"):
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.d.sync += self.leds.eq(0b1010101)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out & (self.counter != 0)):
                    m.next = "WRITE_ARP_PACKET"
                with m.Elif(self.simple_ports_to_wb.op_rdy_out & (self.counter == 0)):
                    m.next = "WRITE_ETHMAC_MAC_ADDR0"
            with m.State("WRITE_ETHMAC_MAC_ADDR0"):
                m.d.sync += self.leds.eq(4)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0a0a_0a0a)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x40)
                m.next = "WRITE_ETHMAC_MAC_ADDR0_WAIT"
            with m.State("WRITE_ETHMAC_MAC_ADDR0_WAIT"):
                m.d.sync += self.leds.eq(5)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_MAC_ADDR1"
            with m.State("WRITE_ETHMAC_MAC_ADDR1"):
                m.d.sync += self.leds.eq(6)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000_0a0a)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x44)
                m.next = "WRITE_ETHMAC_MAC_ADDR1_WAIT"
            with m.State("WRITE_ETHMAC_MAC_ADDR1_WAIT"):
                m.d.sync += self.leds.eq(7)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_TX_BUF_DESC_0"
            with m.State("WRITE_ETHMAC_TX_BUF_DESC_0"):
                m.d.sync += self.leds.eq(8)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0001_0000)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x404)
                m.next = "WRITE_ETHMAC_TX_BUF_DESC_0_WAIT"
            with m.State("WRITE_ETHMAC_TX_BUF_DESC_0_WAIT"):
                m.d.sync += self.leds.eq(9)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_TX_BUF_DESC_1"
            with m.State("WRITE_ETHMAC_TX_BUF_DESC_1"):
                m.d.sync += self.leds.eq(10)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0040_a000)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x400)
                m.next = "WRITE_ETHMAC_TX_BUF_DESC_1_WAIT"
            with m.State("WRITE_ETHMAC_TX_BUF_DESC_1_WAIT"):
                m.d.sync += self.leds.eq(11)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "JUST_WAIT"
            with m.State("JUST_WAIT"):
                m.d.sync += self.leds.eq(12)
                m.next = "JUST_WAIT"

        return m
