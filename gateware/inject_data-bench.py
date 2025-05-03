#!/usr/bin/env python3
from inject_data import InjectData
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = InjectData(simulation=True)

    def process_ethmac():
        for _ in range(200):
            yield Tick()

        yield dut.int.eq(1)
        yield Tick()
        yield dut.int.eq(0)

        for _ in range(200):
            yield Tick()

    def process():
        for _ in range(100):
            yield dut.simple_ports_to_wb.bus.ack.eq(1)
            yield Tick()
            yield dut.simple_ports_to_wb.bus.ack.eq(0)
            yield Tick()

        yield dut.simple_ports_to_wb.bus.dat_r.eq(0x00030004)
        yield dut.int.eq(1)
        yield Tick()
        yield dut.int.eq(0)
        yield Tick()

        for _ in range(100):
            yield dut.simple_ports_to_wb.bus.ack.eq(1)
            yield Tick()
            yield dut.simple_ports_to_wb.bus.ack.eq(0)
            yield Tick()

        yield dut.simple_ports_to_wb.bus.dat_r.eq(0x00030001)
        yield dut.int.eq(1)
        yield Tick()
        yield dut.int.eq(0)
        yield Tick()

        for _ in range(50):
            yield dut.simple_ports_to_wb.bus.ack.eq(1)
            yield Tick()
            yield dut.simple_ports_to_wb.bus.ack.eq(0)
            yield Tick()


    sim = Simulator(dut)
    sim.add_clock(1.0/60e6,)
    sim.add_sync_process(process)
    sim.add_sync_process(process_ethmac)

    with sim.write_vcd(f'inject_data.vcd'):
        sim.run()
