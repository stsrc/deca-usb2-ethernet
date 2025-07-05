#!/usr/bin/env python3

from led_multiplexer import LEDMultiplexer
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = LEDMultiplexer(data_width = 8, input_count = 3, cool_down_time = 10)

    def process():
        yield dut.inputs[0].eq(0b00000001)
        yield dut.inputs[1].eq(0b00000010)
        yield dut.inputs[2].eq(0b00000011)
        yield dut.inputs[3].eq(0xff)
        yield Tick()
        yield Tick()
        yield dut.do_switch.eq(1)
        yield Tick()
        yield Tick()
        yield dut.do_switch.eq(0)
        yield Tick()
        yield dut.do_switch.eq(1)
        yield Tick()
        yield Tick()
        yield dut.do_switch.eq(0)
        for _ in range(12):
            yield Tick()
        yield dut.do_switch.eq(1)
        yield Tick()
        yield dut.do_switch.eq(0)
        for _ in range(12):
            yield Tick()
        yield dut.do_switch.eq(1)
        yield Tick()
        yield dut.do_switch.eq(0)
        for _ in range(12):
            yield Tick()
        yield dut.do_switch.eq(1)
        yield Tick()
        yield dut.do_switch.eq(0)
        for _ in range(12):
            yield Tick()

    sim = Simulator(dut)
    sim.add_clock(1.0/60e6)
    sim.add_sync_process(process)

    with sim.write_vcd(f'led_multiplexer.vcd'):
        sim.run()
