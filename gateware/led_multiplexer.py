#!/usr/bin/env python3

from amaranth import *
import math

__all__ = [ "LEDMultiplexer" ]

class LEDMultiplexer(Elaboratable):
    def __init__(self, data_width = 8, input_count = 2, cool_down_time = 10000000):
        width = int(math.ceil(math.log2(input_count)))
        self.inputs = Array(Signal(data_width) for _ in range(2**width))
        self.do_switch = Signal()
        self.output = Signal(data_width)
        self.selected = Signal(width, reset = 0)
        self.cool_down_time_const = Signal(math.ceil(math.log2(cool_down_time)), 
                                           reset = cool_down_time)
        self.counter = Signal(math.ceil(math.log2(cool_down_time)), reset = 0)

    def elaborate(self, platform):
        m = Module()
       
        with m.FSM(reset="RESET"):
            with m.State("RESET"):
               m.next = "SWITCH"
            with m.State("SWITCH"):
                with m.If(self.do_switch):
                    m.d.sync += self.selected.eq(self.selected + 1)
                    m.d.sync += self.counter.eq(self.cool_down_time_const)
                    m.next = "COOL_DOWN"
            with m.State("COOL_DOWN"):
                with m.If(~self.do_switch):
                    m.d.sync += self.counter.eq(self.counter - 1)
                    with m.If(self.counter == 0):
                        m.next = "SWITCH"
                with m.Else():
                    m.d.sync += self.counter.eq(self.cool_down_time_const)


        m.d.comb += self.output.eq(self.inputs[self.selected])
        return m
