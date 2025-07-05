#!/usr/bin/env python3

from amaranth import *
from amlib.stream.uart import UARTTransmitter as UART

__all__ = [ "UARTTransmitter" ]

class UARTTransmitter(Elaboratable):
    def __init__(self):
        self.data_to_send = Signal(8, reset = 0)
        self.send = Signal(reset = 0)
        self.busy = Signal(reset = 0)
        self.tx = Signal()

    def elaborate(self, platform):
        m = Module()

        m.submodules.uart = uart = UART(divisor = 120) # divisor == 120 as 60MHz input

        m.d.comb += self.busy.eq(~uart.idle)
        m.d.comb += self.tx.eq(uart.tx)

        m.d.sync += uart.stream.valid.eq(0)
        m.d.sync += uart.stream.first.eq(0)
        m.d.sync += uart.stream.last.eq(0)

        with m.FSM(reset="IDLE"):
            with m.State("IDLE"):
                with m.If(uart.idle & self.send & uart.stream.ready):
                    m.d.sync += uart.stream.valid.eq(1)
                    m.d.sync += uart.stream.first.eq(1)
                    m.d.sync += uart.stream.payload.eq(self.data_to_send)
                    m.next = "END"
            with m.State("END"):
                with m.If(uart.stream.ready):
                    m.d.sync += uart.stream.valid.eq(1)
                    m.d.sync += uart.stream.last.eq(1)
                    m.d.sync += uart.stream.payload.eq(0x0a) # new line
                m.next = "IDLE"

        return m
