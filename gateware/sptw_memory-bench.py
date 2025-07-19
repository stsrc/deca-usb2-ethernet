#!/usr/bin/env python3

from sptw_memory import SptwMemory
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = SptwMemory()

    def process():
        yield dut.sptw.wr_strb_in.eq(1)
        yield dut.sptw.address_in.eq(0)
        yield dut.sptw.data_in.eq(1)
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.sptw.wr_strb_in.eq(1)
        yield dut.sptw.address_in.eq(1)
        yield dut.sptw.data_in.eq(2)
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.sptw.wr_strb_in.eq(1)
        yield dut.sptw.address_in.eq(2)
        yield dut.sptw.data_in.eq(3)
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.sptw.wr_strb_in.eq(1)
        yield dut.sptw.address_in.eq(3)
        yield dut.sptw.data_in.eq(4)
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.sptw.wr_strb_in.eq(0)

        yield dut.sptw.address_in.eq(1)
        yield dut.sptw.rd_strb_in.eq(1)
        yield Tick()
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.sptw.rd_strb_in.eq(0)
        for _ in range(5):
            yield Tick()
        yield dut.sptw.address_in.eq(2)
        yield dut.sptw.rd_strb_in.eq(1)
        yield Tick()
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.sptw.rd_strb_in.eq(0)
        for _ in range(50):
            yield Tick()

    sim = Simulator(dut)
    sim.add_clock(1.0/60e6)
    sim.add_sync_process(process)

    with sim.write_vcd(f'sptw_memory.vcd'):
        sim.run()
