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
        self.arp_packet = [0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x0a, 0x0a,
                           0x0a, 0x0a, 0x0a, 0x0a, 0x08, 0x06, 0x00, 0x01,
                           0x08, 0x00, 0x06, 0x04, 0x00, 0x01, 0x0a, 0x0a,
                           0x0a, 0x0a, 0x0a, 0x0a,  192,  168,    0,   66,
                              0,    0,    0,    0,    0,    0,  192,  168,
                              0,  135,    0,    0,    0,    0,    0,    0,
                              0,    0,    0,    0,    0,    0,    0,    0,
                              0,    0,    0,    0, 0x9e, 0x59, 0x7b, 0xf9]

    def get_bus(self):
        return self.simple_ports_to_wb.bus

    def elaborate(self, platform):
        m = Module()
        m.submodules.simple_ports_to_wb = self.simple_ports_to_wb
        # TODO: check if clock is properly assigned, should be usb_clk something
        with m.FSM(reset="IDLE"):
            with m.State("IDLE"):
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0)
                m.next = "READING"
            with m.State("READING"):
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "IDLE"
        return m
