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
        self.fifo_w_rdy = Signal()
        self.fifo_w_en = Signal(reset = 0)
        self.fifo_count_w_rdy = Signal()
        self.fifo_count_w_en = Signal(reset = 0)
        self.fifo_w_data = Signal(32, reset = 0)
        self.fifo_count_w_data = Signal(11, reset = 0)
        self.leds = Signal(8, reset = 1)
        self.debug_received = Signal(8, reset = 0)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.fifo_w_en.eq(0)
        m.d.comb += self.fifo_count_w_en.eq(0)

        m.d.comb += self.usb_stream_in.ready.eq(0)

        usb_valid = Signal()
        usb_first = Signal()
        usb_last = Signal()
        ready = Signal(reset = 0)
        usb_payload = Signal(8)
        counterr = Signal(11, reset = 0)
        tmp = Signal(1, reset = 0)
        tx_pkt_len = Signal(32, reset = 0)
        tx_pkt_len_comb = Signal(32, reset = 0)
        payload = Signal(32, reset = 0)
        payload_comb = Signal(32, reset = 0)

        m.d.comb += [
            usb_first.eq(self.usb_stream_in.first),
            usb_last.eq(self.usb_stream_in.last),
            usb_valid.eq(self.usb_stream_in.valid),
            usb_payload.eq(self.usb_stream_in.payload),

            payload_comb.eq(0),
            tx_pkt_len_comb.eq(0)
        ]

        with m.FSM(reset="IDLE"):
            with m.State("IDLE"):
                with m.If(self.fifo_w_rdy & self.fifo_count_w_rdy):
                    m.d.sync += counterr.eq(0)
                    m.d.sync += payload.eq(0)
                    m.next = "GET_COUNT_0"
            with m.State("GET_COUNT_0"):
                m.d.comb += self.usb_stream_in.ready.eq(self.fifo_w_rdy & self.fifo_count_w_rdy)
                with m.If(usb_valid & self.fifo_w_rdy):
                        m.d.sync += tx_pkt_len.eq(usb_payload << 8)
                        m.next = "GET_COUNT_1"
            with m.State("GET_COUNT_1"):
                m.d.comb += self.usb_stream_in.ready.eq(self.fifo_w_rdy & self.fifo_count_w_rdy)
                with m.If(usb_valid & self.fifo_w_rdy):
                        m.d.comb += tx_pkt_len_comb.eq(usb_payload | tx_pkt_len)
                        m.d.sync += tx_pkt_len.eq(tx_pkt_len_comb)
                        m.d.comb += self.fifo_w_data.eq(tx_pkt_len_comb)
                        m.d.comb += self.fifo_w_en.eq(1)
                        m.next = "GET_DATA"
            with m.State("GET_DATA"): 
                m.d.comb += self.usb_stream_in.ready.eq(self.fifo_w_rdy & self.fifo_count_w_rdy)
                with m.If(usb_valid & self.usb_stream_in.ready):
                    m.d.comb += payload_comb.eq((usb_payload <<
                        (((3 - (counterr % 4)) * 8).as_unsigned())) | payload)
                    m.d.sync += counterr.eq(counterr + 1)
                    m.d.sync += payload.eq(payload_comb)
                    m.d.comb += self.fifo_w_data.eq(payload_comb)
                    with m.If(usb_last | ((counterr + 1) == tx_pkt_len)):
                        m.d.comb += self.fifo_w_en.eq(1)
                        m.d.comb += self.fifo_count_w_en.eq(1)
                        m.d.comb += self.fifo_count_w_data.eq(counterr + 1)
                        m.next = "IDLE"
                    with m.Elif(((counterr + 1) % 4) == 0):
                        m.d.comb += self.fifo_w_en.eq(1)
                        m.d.sync += payload.eq(0)
                    with m.If(((counterr + 1) != tx_pkt_len) & usb_last):
                        m.d.sync += self.leds.eq(0b01010101)

        return m

