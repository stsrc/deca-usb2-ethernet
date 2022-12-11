#!/usr/bin/env python3
from inject_data2 import InjectData2
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = InjectData2(simulation=True)

    def process_usb():
        for _ in range(25):
            yield Tick()

        yield dut.usb_stream_in.payload.eq(1)
        yield dut.usb_stream_in.valid.eq(1)
        yield dut.usb_stream_in.first.eq(1)
        yield Tick()
        yield Tick()
        yield dut.usb_stream_in.first.eq(0)
        yield dut.usb_stream_in.payload.eq(2)
        yield Tick()
        yield dut.usb_stream_in.payload.eq(3)
        yield Tick()
        yield dut.usb_stream_in.payload.eq(4)
        yield Tick()
        yield dut.usb_stream_in.payload.eq(5)
        yield dut.usb_stream_in.last.eq(1)
        for _ in range(6):
            yield Tick()
        yield dut.usb_stream_in.last.eq(0)
        yield dut.usb_stream_in.valid.eq(0)
        yield Tick()

        for _ in range(25):
            yield Tick()

        yield dut.usb_stream_in.payload.eq(6)
        yield dut.usb_stream_in.valid.eq(1)
        yield dut.usb_stream_in.first.eq(1)
        yield Tick()
        yield Tick()
        yield dut.usb_stream_in.first.eq(0)
        yield dut.usb_stream_in.payload.eq(7)
        yield Tick()
        yield dut.usb_stream_in.payload.eq(8)
        yield dut.usb_stream_in.last.eq(1)
        yield Tick()
        yield dut.usb_stream_in.last.eq(0)
        yield dut.usb_stream_in.valid.eq(0)
        yield Tick()

        for _ in range(25):
            yield Tick()

    def process():
        for _ in range(200):
            yield dut.simple_ports_to_wb.bus.ack.eq(1)
            yield Tick()
            yield dut.simple_ports_to_wb.bus.ack.eq(0)
            yield Tick()
        yield Tick()

    sim = Simulator(dut)
    sim.add_clock(1.0/60e6,)
    sim.add_sync_process(process)
    sim.add_sync_process(process_usb)

    with sim.write_vcd(f'inject_data.vcd'):
        sim.run()
