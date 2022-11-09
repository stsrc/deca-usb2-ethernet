#!/usr/bin/env python3
from simple_ports_to_wb import SimplePortsToWb
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = SimplePortsToWb()

    def write_data():
        yield dut.address_in.eq(0x10000000)
        yield dut.wr_strb_in.eq(1)
        yield dut.data_in.eq(0x01011010)

    def process():
        yield Tick()
        yield from write_data()
        for _ in range(5): yield Tick()

    sim = Simulator(dut)
    sim.add_clock(1.0/60e6,)
    sim.add_sync_process(process)

    with sim.write_vcd(f'simple_ports_to_wb.vcd'):
        sim.run()
