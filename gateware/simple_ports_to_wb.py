#!/usr/bin/env python3
#
# Copyright (c) 2022 Konrad Gotfryd <gotfrydkonrad@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0

import os

from amaranth import *
from amaranth_soc.wishbone.bus import Interface

__all__ = ["SimplePortsToWb"]

class SimplePortsToWb(Elaboratable):
    def __init__(self, *, addr_width=32, data_width=32, granularity=8):
        self.bus_addr_width = addr_width
        self.bus_data_width = data_width
        self.bus_granularity = granularity
        self.bus = Interface(addr_width=self.bus_addr_width, 
                             data_width=self.bus_data_width, 
                             granularity=self.bus_granularity, 
                             features = { "err" })

        self.address_in = Signal(addr_width)
        self.data_in = Signal(data_width)
        self.data_out = Signal(data_width)
        self.sel_in = Signal(data_width // granularity)
        self.rd_strb_in = Signal()
        self.wr_strb_in = Signal()
        self.op_rdy_out = Signal()
        self.leds = Signal(8)

    def elaborate(self, platform):
        m = Module()

        with m.FSM(reset="IDLE"):
            with m.State("IDLE"):
                m.d.sync += self.op_rdy_out.eq(0)
                m.d.sync += self.data_out.eq(0)
                m.d.sync += self.leds.eq(1)
                with m.If(self.rd_strb_in):
                    m.d.sync += self.bus.adr.eq(self.address_in)
                    m.d.sync += self.bus.we.eq(0)
                    m.d.sync += self.bus.sel.eq(self.sel_in)
                    m.d.sync += self.bus.cyc.eq(1)
                    m.d.sync += self.bus.stb.eq(1)
                    m.next = "READ"
                with m.Elif(self.wr_strb_in):
                    m.d.sync += self.bus.adr.eq(self.address_in)
                    m.d.sync += self.bus.dat_w.eq(self.data_in)
                    m.d.sync += self.bus.we.eq(1)
                    m.d.sync += self.bus.sel.eq(self.sel_in)
                    m.d.sync += self.bus.cyc.eq(1)
                    m.d.sync += self.bus.stb.eq(1)
                    m.next = "WRITE"
            with m.State("READ"):
                m.d.sync += self.leds.eq(2)
                with m.If(self.bus.ack):
                    m.d.sync += self.data_out.eq(self.bus.dat_r)
                    m.d.sync += self.op_rdy_out.eq(1)
                    m.d.sync += self.bus.adr.eq(0)
                    m.d.sync += self.bus.we.eq(0)
                    m.d.sync += self.bus.sel.eq(0)
                    m.d.sync += self.bus.cyc.eq(0)
                    m.d.sync += self.bus.stb.eq(0)
                    m.next = "IDLE"
            with m.State("WRITE"):
                m.d.sync += self.leds.eq(3)
                with m.If(self.bus.ack):
                    m.d.sync += self.op_rdy_out.eq(1)
                    m.d.sync += self.bus.adr.eq(0)
                    m.d.sync += self.bus.we.eq(0)
                    m.d.sync += self.bus.sel.eq(0)
                    m.d.sync += self.bus.cyc.eq(0)
                    m.d.sync += self.bus.stb.eq(0)
                    m.d.sync += self.bus.dat_w.eq(0)
                    m.next = "IDLE"
        return m
