#!/usr/bin/env python3

from memory import WishboneRAM
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = WishboneRAM(addr_width = 4)

    def process():
        yield dut.bus.we.eq(1)
        yield dut.bus.sel.eq(0xf)
        yield dut.bus.cyc.eq(1)
        yield dut.bus.stb.eq(1)
        yield dut.bus.adr.eq(0)
        yield dut.bus.dat_w.eq(1)
        yield Tick()
        yield Tick()
        yield dut.bus.adr.eq(1)
        yield dut.bus.dat_w.eq(2)
        yield Tick()
        yield Tick()
        yield dut.bus.adr.eq(2)
        yield dut.bus.dat_w.eq(3)
        yield Tick()
        yield Tick()
        yield dut.bus.adr.eq(3)
        yield dut.bus.dat_w.eq(4)
        yield Tick()
        yield Tick()
        yield dut.bus.cyc.eq(0)
        yield dut.bus.stb.eq(0)
        yield dut.bus.we.eq(0)
        for _ in range(5):
            yield Tick()
        yield dut.bus.cyc.eq(1)
        yield dut.bus.stb.eq(1)
        yield dut.bus.adr.eq(0)
        yield Tick()
        yield Tick()
        yield dut.bus.cyc.eq(0)
        yield dut.bus.stb.eq(0)
        yield Tick()
        yield dut.bus.cyc.eq(1)
        yield dut.bus.stb.eq(1)
        yield dut.bus.adr.eq(2)
        yield Tick()
        yield Tick()
        yield dut.bus.adr.eq(0)
        yield Tick()
        yield Tick()
        yield dut.bus.cyc.eq(0)
        yield dut.bus.stb.eq(0)
        for _ in range(50):
            yield Tick()

    sim = Simulator(dut)
    sim.add_clock(1.0/60e6)
    sim.add_sync_process(process)

    with sim.write_vcd(f'memory.vcd'):
        sim.run()
