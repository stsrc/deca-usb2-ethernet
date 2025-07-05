#!/usr/bin/env python3

from amaranth import *
from memory import WishboneRAM
from simple_ports_to_wb import SimplePortsToWb

__all__ = ["SptwMemory" ]

class SptwMemory(Elaboratable):
    def __init__(self):
        self.memory = WishboneRAM(addr_width=16)
        self.sptw = SimplePortsToWb(addr_width=4)

    def elaborate(self, platform):
        m = Module()
        m.submodules.memory = self.memory
        m.submodules.sptw = self.sptw
        m.d.comb += [ self.memory.bus.we.eq(self.sptw.bus.we),
                  self.memory.bus.cyc.eq(self.sptw.bus.cyc),
                  self.memory.bus.stb.eq(self.sptw.bus.stb),
                  self.memory.bus.adr.eq(self.sptw.bus.adr),
                  self.memory.bus.sel.eq(self.sptw.bus.sel),
                  self.sptw.bus.ack.eq(self.memory.bus.ack),
                  self.memory.bus.dat_w.eq(self.sptw.bus.dat_w),
                  self.sptw.bus.dat_r.eq(self.memory.bus.dat_r) ]

        return m
