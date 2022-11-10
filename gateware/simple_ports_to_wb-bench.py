#!/usr/bin/env python3
from simple_ports_to_wb import SimplePortsToWb
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = SimplePortsToWb()

    def process_wr():
        yield dut.address_in.eq(0x10000000)
        yield dut.wr_strb_in.eq(1)
        yield dut.data_in.eq(0x01011010)
        yield dut.sel_in.eq(0b1111)
        yield Tick()
        yield dut.wr_strb_in.eq(0)
        yield Tick()
        yield dut.bus.ack.eq(1)
        yield Tick()
        yield dut.bus.ack.eq(0)
        yield Tick()

    def process_rd():
        yield dut.address_in.eq(0x10000001)
        yield dut.rd_strb_in.eq(1)
        yield dut.sel_in.eq(0b1111)
        yield Tick()
        yield dut.rd_strb_in.eq(0)
        yield Tick()
        yield dut.bus.dat_r.eq(0x11110000)
        yield dut.bus.ack.eq(1)
        yield Tick()
        yield dut.bus.dat_r.eq(0)
        yield dut.bus.ack.eq(0)
        yield Tick()

    def process():
        yield Tick()
        yield from process_wr()
        yield from process_rd()

    sim = Simulator(dut)
    sim.add_clock(1.0/60e6,)
    sim.add_sync_process(process)

    with sim.write_vcd(f'simple_ports_to_wb.vcd'):
        sim.run()
