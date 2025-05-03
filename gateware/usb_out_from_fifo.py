#!/usr/bin/env python3
#
# Copyright (c) 2022 Konrad Gotfryd <gotfrydkonrad@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0

from amaranth import *
from amlib.stream  import StreamInterface

__all__ = ["USBOutFromFifo"]

class USBOutFromFifo(Elaboratable):
    def __init__(self, simulation):
        self.simulation = simulation
        self.usb_stream_out = StreamInterface(name = "usb_stream_out")
        self.fifo_r_rdy = Signal(reset = 0)
        self.fifo_r_en = Signal(reset = 0)
        self.fifo_count_r_rdy = Signal(reset = 0)
        self.fifo_count_r_en = Signal(reset = 0)
        self.fifo_r_data = Signal(32, reset = 0)
        self.fifo_count_r_data = Signal(11, reset = 0)
        self.end = Signal(reset = 0)
        self.leds = Signal(8, reset = 0)

    def elaborate(self, platform):
        m = Module()

        usb_valid = Signal()
        usb_first = Signal()
        usb_last = Signal()
        usb_payload = Signal(8)
        packet_size = Signal(11)
        counter = Signal(11)
        tmp = Signal(32)

        m.d.comb += self.usb_stream_out.valid.eq(0)
        m.d.comb += self.usb_stream_out.last.eq(0)

        with m.FSM(reset="RESET"):
            with m.State("RESET"):
                m.next = "GET_PACKET_SIZE"
            with m.State("GET_PACKET_SIZE"):
                m.d.sync += self.leds.eq(0b10000000)
                with m.If(self.fifo_count_r_rdy):
                    m.d.sync += packet_size.eq(self.fifo_count_r_data)
                    m.d.sync += self.fifo_count_r_en.eq(1)
                    m.d.sync += counter.eq(0)
                    m.next = "GET_DATA"

            with m.State("GET_DATA"):
                m.d.sync += self.leds.eq(0b01000000)
                m.d.sync += self.fifo_count_r_en.eq(0)
                with m.If(self.fifo_r_rdy):
                    m.d.sync += self.fifo_r_en.eq(1)
                    m.d.sync += tmp.eq(self.fifo_r_data)
                    m.next = "SEND_DATA"

            with m.State("SEND_DATA"):
                m.d.sync += self.leds.eq(0b00100000)
                m.d.sync += self.fifo_r_en.eq(0)
                with m.If(self.usb_stream_out.ready):
                    m.d.comb += self.usb_stream_out.valid.eq(1)
                    m.d.comb += self.usb_stream_out.payload.eq(tmp >> 
                            (((3 - (counter % 4)) * 8).as_unsigned()))
                    with m.If(counter == 0):
                        m.d.comb += self.usb_stream_out.first.eq(1)
                    with m.Else():
                        m.d.comb += self.usb_stream_out.first.eq(0)
    
                    with m.If(counter == (packet_size - 1)):
                        m.d.comb += self.usb_stream_out.last.eq(1)
                        m.next = "GET_PACKET_SIZE"
                    with m.Else():
                        m.d.comb += self.usb_stream_out.last.eq(0)
                        m.d.sync += counter.eq(counter + 1)
                        with m.If((counter + 1) % 4 == 0):
                            m.next = "GET_DATA"

        return m
