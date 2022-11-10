#!/usr/bin/env python3
from eth_interface import EthInterface
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = EthInterface(simulation=True)

    def process():
        for _ in range(1000):
            yield Tick()

    sim = Simulator(dut)
    sim.add_clock(1.0/60e6,)
    sim.add_sync_process(process)

    with sim.write_vcd(f'eth_interface.vcd'):
        sim.run()
