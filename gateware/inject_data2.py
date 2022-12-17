#!/usr/bin/env python3
#
# Copyright (c) 2022 Konrad Gotfryd <gotfrydkonrad@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0

import os

from amaranth import *
from simple_ports_to_wb import SimplePortsToWb
from amlib.stream  import StreamInterface

__all__ = ["InjectData2"]

class InjectData2(Elaboratable):
    def __init__(self, simulation):
        self.simple_ports_to_wb = SimplePortsToWb()

        self.leds = Signal(8)
        self.wait_counter = Signal(26)
        self.phy_resetn = Signal()
        self.simulation = simulation

        self.head = Signal(6)
        self.tail = Signal(6)
        self.end = Signal()

        self.usb_stream_in = StreamInterface(name="usb_stream")

    def get_bus(self):
        return self.simple_ports_to_wb.bus

    def elaborate(self, platform):
        m = Module()
        m.submodules.simple_ports_to_wb = self.simple_ports_to_wb

        usb_valid = Signal()
        usb_first = Signal()
        usb_last = Signal()
        usb_payload = Signal(8)
        payload = Signal(32)
        counter = Signal(11)
        counter2 = Signal(11)
        m.d.comb += [
            usb_first.eq(self.usb_stream_in.first),
            usb_last.eq(self.usb_stream_in.last),
            usb_valid.eq(self.usb_stream_in.valid),
            usb_payload.eq(self.usb_stream_in.payload)
        ]

        with m.FSM(reset="RESET"):
            with m.State("RESET"):
                m.d.sync += self.leds.eq(1)
                m.d.sync += self.wait_counter.eq(0)
                m.d.sync += self.phy_resetn.eq(0)
                m.next = "WAIT_BEFORE_START"

            with m.State("WAIT_BEFORE_START"):
                m.d.sync += self.leds.eq(2)

                m.d.sync += self.wait_counter.eq(self.wait_counter + 1)

                if self.simulation:
                    m.d.sync += self.wait_counter.eq(30000000)

                with m.If (self.wait_counter == 30000000):
                    m.next = "WRITE_ETHMAC_INT_MASK"
                    m.d.sync += self.wait_counter.eq(0)

            with m.State("WRITE_ETHMAC_INT_MASK"):
                m.d.sync += self.leds.eq(3)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000007f)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x08 >> 2)
                m.next = "WRITE_ETHMAC_INT_MASK_WAIT"

            with m.State("WRITE_ETHMAC_INT_MASK_WAIT"):
                m.d.sync += self.leds.eq(4)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_MAC_ADDR0"

            with m.State("WRITE_ETHMAC_MAC_ADDR0"):
                m.d.sync += self.leds.eq(5)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0a0a_0a0a)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x40 >> 2)
                m.next = "WRITE_ETHMAC_MAC_ADDR0_WAIT"

            with m.State("WRITE_ETHMAC_MAC_ADDR0_WAIT"):
                m.d.sync += self.leds.eq(6)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_MAC_ADDR1"

            with m.State("WRITE_ETHMAC_MAC_ADDR1"):
                m.d.sync += self.leds.eq(7)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000_0a0a)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x44 >> 2)
                m.next = "WRITE_ETHMAC_MAC_ADDR1_WAIT"

            with m.State("WRITE_ETHMAC_MAC_ADDR1_WAIT"):
                m.d.sync += self.leds.eq(8)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_MODER"
                    m.d.sync += self.phy_resetn.eq(1)

            with m.State("WRITE_ETHMAC_MODER"):
                m.d.sync += self.leds.eq(9)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000a002) # crc add enabled
#                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x00008002) # crc add disabled
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x00 >> 2)
                m.next = "WRITE_ETHMAC_MODER_WAIT"

            with m.State("WRITE_ETHMAC_MODER_WAIT"):
                m.d.sync += self.leds.eq(10)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "IDLE"

            with m.State("IDLE"):
                m.d.sync += self.leds.eq(11)
                with m.If(usb_valid & ((self.head + 1) % 32 != self.tail)):
                    m.next = "WRITE_DATA_PREPARE"

            with m.State("WRITE_DATA_PREPARE"):
                m.d.sync += self.leds.eq(12)
                with m.If(usb_valid):
                    m.d.comb += self.usb_stream_in.ready.eq(1)
                    m.d.sync += counter.eq(counter + 1)
                    m.d.sync += payload.eq((usb_payload << ( (3 - (counter % 4)) * 8)) | payload)
                    with m.If(usb_last):
                        m.d.sync += self.end.eq(1)
                        m.next = "WRITE_DATA"
                    with m.Elif((counter + 1) % 4 == 0):
                        m.next = "WRITE_DATA"

            #TODO: check what happens if we have to wait for wb to end transaction...
            with m.State("WRITE_DATA"):
                m.d.sync += self.leds.eq(13)
                m.d.comb += self.usb_stream_in.ready.eq(0)

                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(payload)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)

                if self.simulation:
                    m.d.sync += self.simple_ports_to_wb.address_in.eq(0x0400_0000 + 16 * self.head + counter2)
                else:
                    m.d.sync += self.simple_ports_to_wb.address_in.eq(0x0400_0000 + 2048 * self.head + counter2)
                m.d.sync += counter2.eq(counter)
                m.next = "WRITE_DATA_WAIT"

            with m.State("WRITE_DATA_WAIT"):
                m.d.sync += self.leds.eq(14)
                m.d.sync += payload.eq(0)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out & (~self.end)):
                    m.next = "WRITE_DATA_PREPARE"
                with m.Elif(self.simple_ports_to_wb.op_rdy_out & self.end):
                    m.d.sync += self.end.eq(0)
                    m.next = "WRITE_ETHMAC_TX_BUF_DESC_0"

            with m.State("WRITE_ETHMAC_TX_BUF_DESC_0"):
                m.d.sync += self.leds.eq(15)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)

                if self.simulation:
                    m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0400_0000 + 16 * self.head)

                else:
                    m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0400_0000 + 2048 * self.head)

                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq((0x400 + self.head * 8 + 4) >> 2)
                m.next = "WRITE_ETHMAC_TX_BUF_DESC_0_WAIT"

            with m.State("WRITE_ETHMAC_TX_BUF_DESC_0_WAIT"):
                m.d.sync += self.leds.eq(16)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_TX_BUF_DESC_1"

            with m.State("WRITE_ETHMAC_TX_BUF_DESC_1"):
                m.d.sync += self.leds.eq(17)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                with m.If(self.head != 31):
                    m.d.sync += self.simple_ports_to_wb.data_in.eq((counter << 16) | 0xc000)
                with m.Else():
                    m.d.sync += self.simple_ports_to_wb.data_in.eq((counter << 16) | 0xe000)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq((0x400 + self.head * 8) >> 2)
                m.next = "WRITE_ETHMAC_TX_BUF_DESC_1_WAIT"

            with m.State("WRITE_ETHMAC_TX_BUF_DESC_1_WAIT"):
                m.d.sync += self.leds.eq(18)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.d.sync += counter2.eq(0)
                    m.d.sync += counter.eq(0)
                    m.d.sync += self.head.eq((self.head + 1) % 32)
                    m.next = "IDLE"

        return m
