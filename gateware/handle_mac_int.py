#!/usr/bin/env python3
#
# Copyright (c) 2022 Konrad Gotfryd <gotfrydkonrad@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0

from amaranth import *
from simple_ports_to_wb import SimplePortsToWb

__all__ = [ "HandleMacInt" ]

class HandleMacInt(Elaboratable):
    def __init__(self):
        self.simple_ports_to_wb = SimplePortsToWb()

        self.int = Signal()

        self.irq_state = Signal(32, reset = 0)
        self.new_irq = Signal(reset = 0)

    def get_bus(self):
        return self.simple_ports_to_wb.bus

    def elaborate(self, platform):
        m = Module()

        m.submodules.simple_ports_to_wb = self.simple_ports_to_wb

        m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(0)
        m.d.comb += self.simple_ports_to_wb.rd_strb_in.eq(0)
        m.d.comb += self.simple_ports_to_wb.data_in.eq(0)
        m.d.comb += self.simple_ports_to_wb.address_in.eq(0)

        m.d.sync += self.irq_state.eq(0)
        m.d.sync += self.new_irq.eq(0)

        with m.FSM(reset="RESET"):
            with m.State("RESET"):
                m.next = "IDLE"

            with m.State("IDLE"):
                with m.If(self.int):
                    m.next = "READ_IRQ"

            with m.State("READ_IRQ"):
                m.d.comb += self.simple_ports_to_wb.rd_strb_in.eq(1)
                m.d.comb += self.simple_ports_to_wb.data_in.eq(0)
                m.d.comb += self.simple_ports_to_wb.address_in.eq(0x04 >> 2)
                with m.If(self.simple_ports_to_wb.rd_op_rdy_out):
                    m.d.sync += self.irq_state.eq(self.simple_ports_to_wb.rd_data_out)
                    m.d.sync += self.new_irq.eq(1)
                    m.d.comb += self.simple_ports_to_wb.rd_strb_in.eq(0)
                    m.next = "CLEAR_IRQ"

            with m.State("CLEAR_IRQ"):
                m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.comb += self.simple_ports_to_wb.data_in.eq(0b01111111)
                m.d.comb += self.simple_ports_to_wb.address_in.eq(0x04 >> 2)
                with m.If(self.simple_ports_to_wb.wr_op_rdy_out):
                    m.next = "IDLE"
        return m
