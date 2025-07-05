#!/usr/bin/env python3
#
# Copyright (c) 2022 Konrad Gotfryd <gotfrydkonrad@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0

from amaranth import *
from amlib.stream  import StreamInterface

__all__ = ["USBInToFifo"]

class USBInToFifo(Elaboratable):
    def __init__(self, simulation):
        self.simulation = simulation
        self.usb_stream_in = StreamInterface(name = "usb_stream_in")
        self.fifo_w_rdy = Signal(reset = 0)
        self.fifo_w_en = Signal(reset = 0)
        self.fifo_count_w_rdy = Signal(reset = 0)
        self.fifo_count_w_en = Signal(reset = 0)
        self.fifo_w_data = Signal(32, reset = 0)
        self.fifo_count_w_data = Signal(11, reset = 0)
        self.end = Signal(reset = 0)
        self.leds = Signal(8, reset = 0)
        self.debug_received = Signal(8, reset = 0)

    def elaborate(self, platform):
        m = Module()

        usb_valid = Signal()
        usb_first = Signal()
        usb_last = Signal()
        usb_payload = Signal(8)

        debug_counter = Signal(16, reset = 0)

        m.d.comb += [
            usb_first.eq(self.usb_stream_in.first),
            usb_last.eq(self.usb_stream_in.last),
            usb_valid.eq(self.usb_stream_in.valid),
            usb_payload.eq(self.usb_stream_in.payload)
        ]

        with m.FSM(reset="RESET"):
            with m.State("RESET"):
                m.next = "GET_DATA"

            with m.State("GET_DATA"):
                m.d.sync += self.fifo_w_en.eq(0)
                m.d.sync += self.fifo_count_w_en.eq(0)
                m.d.comb += self.usb_stream_in.ready.eq(0)
 
                m.d.sync += self.leds.eq(self.fifo_w_rdy << 2 | self.fifo_count_w_rdy << 1 | usb_valid)

                with m.If(self.fifo_w_data == 0x1a1a1a1a):
                    with m.If(debug_counter == 16):
                        m.d.sync += self.debug_received.eq(self.debug_received + 1)
                        m.d.sync += debug_counter.eq(debug_counter + 1)
                    with m.Elif(debug_counter != 17):
                        m.d.sync += debug_counter.eq(debug_counter + 1)

                with m.If(self.end):
                    m.d.sync += self.fifo_count_w_data.eq(0)
                    m.d.sync += self.end.eq(0)
                    m.d.sync += debug_counter.eq(0)
                with m.Elif(usb_valid & self.fifo_w_rdy & self.fifo_count_w_rdy):
                    m.d.comb += self.usb_stream_in.ready.eq(1)
                    m.d.sync += self.fifo_count_w_data.eq(self.fifo_count_w_data + 1)
                    with m.If(self.fifo_count_w_data % 4 == 0):
                        m.d.sync += self.fifo_w_data.eq(usb_payload << 24)
                    with m.Else():
                        m.d.sync += self.fifo_w_data.eq((usb_payload << 
                            (((3 - (self.fifo_count_w_data % 4)) * 8).as_unsigned())) 
                            | self.fifo_w_data)
                    with m.If(usb_last):
                        m.d.sync += self.fifo_w_en.eq(1)
                        m.d.sync += self.fifo_count_w_en.eq(1)
                        m.d.sync += self.end.eq(1)
                    with m.Elif((self.fifo_count_w_data + 1) % 4 == 0):
                        m.d.sync += self.fifo_w_en.eq(1)

        return m

