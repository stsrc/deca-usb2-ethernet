#!/usr/bin/env python3
from amaranth.sim import Simulator, Tick
from amaranth.lib.fifo import *

if __name__ == "__main__":
    dut = SyncFIFO(width = 32, depth = 16)

    def process():
        yield dut.w_data.eq(1)
        yield dut.w_en.eq(1)
        yield Tick()
        yield dut.w_data.eq(2)
        yield dut.w_en.eq(1)
        yield Tick()
        yield dut.w_data.eq(3)
        yield dut.w_en.eq(1)
        yield Tick()
        yield dut.w_en.eq(0)
        yield dut.r_en.eq(1)
        yield Tick()
        yield Tick()
        yield Tick()
        yield Tick()

    sim = Simulator(dut)
    sim.add_clock(1.0/60e6)
    sim.add_sync_process(process)

    with sim.write_vcd(f'test_fifo.vcd'):
        sim.run()
