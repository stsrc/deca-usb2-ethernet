#!/usr/bin/env python3
from inject_data import InjectData
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = InjectData()

    def process():
        yield Tick()
        yield Tick()
        yield Tick()
        for _ in range(16 + 4):
            yield dut.simple_ports_to_wb.bus.ack.eq(1)
            yield Tick()
            yield dut.simple_ports_to_wb.bus.ack.eq(0)
            yield Tick()
        yield Tick()

    sim = Simulator(dut)
    sim.add_clock(1.0/60e6,)
    sim.add_sync_process(process)

    with sim.write_vcd(f'inject_data.vcd'):
        sim.run()
