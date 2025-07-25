#!/usr/bin/env python3
#
# Copyright (c) 2022 Konrad Gotfryd <gotfrydkonrad@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0

import os

from amaranth import *
from amaranth_soc.wishbone.bus import Interface

__all__ = ["SimplePortsToWb"]

class SimplePortsToWb(Elaboratable):
    def __init__(self, *, addr_width=32, data_width=32, granularity=8, simulation=False):
        self.bus_addr_width = addr_width
        self.bus_data_width = data_width
        self.bus_granularity = granularity
        self.bus = Interface(addr_width=self.bus_addr_width, 
                             data_width=self.bus_data_width, 
                             granularity=self.bus_granularity, 
                             features = { "err" })

        self.address_in = Signal(addr_width)
        self.data_in = Signal(data_width)

        self.rd_strb_in = Signal()
        self.wr_strb_in = Signal()
        self.op_rdy_out = Signal()
        self.rd_data_out = Signal(data_width)
        if simulation:
            self.test = Signal(2)
        self.simulation = simulation

    def elaborate(self, platform):
        m = Module()

        if self.simulation:
            m.d.sync += self.test.eq(self.test + 1)

        m.d.comb += self.op_rdy_out.eq(0)

        m.d.comb += self.rd_data_out.eq(0)

        m.d.comb += self.bus.we.eq(0)
        m.d.comb += self.bus.sel.eq(0)
        m.d.comb += self.bus.cyc.eq(0)
        m.d.comb += self.bus.stb.eq(0)
        m.d.comb += self.bus.dat_w.eq(0)

        m.d.comb += self.bus.adr.eq(self.address_in)

        m.d.comb += self.op_rdy_out.eq(self.bus.ack)
        m.d.comb += self.rd_data_out.eq(self.bus.dat_r)
        m.d.comb += self.bus.dat_w.eq(self.data_in)

        with m.If(self.rd_strb_in):
            m.d.comb += self.bus.sel.eq(0b1111)
            m.d.comb += self.bus.we.eq(0)
            m.d.comb += self.bus.cyc.eq(1)
            m.d.comb += self.bus.stb.eq(1)
        with m.Elif(self.wr_strb_in):
            m.d.comb += self.bus.sel.eq(0b1111)
            m.d.comb += self.bus.we.eq(1)
            m.d.comb += self.bus.cyc.eq(1)
            m.d.comb += self.bus.stb.eq(1)

        with m.If(self.bus.ack): #check in previous If/Elif if ack == 0
            m.d.comb += self.bus.cyc.eq(0)
            m.d.comb += self.bus.stb.eq(0)
    
        return m
