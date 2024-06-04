#!/usr/bin/env python3
from eth_interface import EthInterface
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = EthInterface(simulation=True)
    inject = dut.inject_data

    def process_usb():
        for _ in range(25):
            yield Tick()

        yield inject.usb_stream_in.payload.eq(1)
        yield inject.usb_stream_in.valid.eq(1)
        yield inject.usb_stream_in.first.eq(1)
        yield Tick()
        yield Tick()
        yield inject.usb_stream_in.first.eq(0)
        yield inject.usb_stream_in.payload.eq(2)
        yield Tick()
        yield inject.usb_stream_in.payload.eq(3)
        yield Tick()
        yield inject.usb_stream_in.payload.eq(4)
        yield inject.usb_stream_in.last.eq(1)
        yield Tick()
        yield inject.usb_stream_in.last.eq(0)
        yield inject.usb_stream_in.valid.eq(0)
        for _ in range(10):
            yield Tick()

        yield inject.usb_stream_out.ready.eq(1)
        yield Tick()

        for _ in range(25):
            yield Tick()

        yield inject.usb_stream_out.ready.eq(0)
        yield Tick()
    
        yield inject.usb_stream_in.payload.eq(5)
        yield inject.usb_stream_in.valid.eq(1)
        yield inject.usb_stream_in.first.eq(1)
        yield Tick()
        yield Tick()
        yield inject.usb_stream_in.first.eq(0)
        yield inject.usb_stream_in.payload.eq(6)
        yield Tick()
        yield inject.usb_stream_in.payload.eq(7)
        yield Tick()
        yield inject.usb_stream_in.payload.eq(8)
        yield inject.usb_stream_in.last.eq(1)
        yield Tick()
        yield inject.usb_stream_in.last.eq(0)
        yield inject.usb_stream_in.valid.eq(0)
        for _ in range(10):
            yield Tick()

        yield inject.usb_stream_out.ready.eq(1)
        yield Tick()

        for _ in range(25):
            yield Tick()

        yield inject.usb_stream_out.ready.eq(0)
        yield Tick()

    def process():
        for _ in range(1000):
            yield Tick()

    sim = Simulator(dut)
    sim.add_clock(1.0/60e6,)
    sim.add_sync_process(process)
    sim.add_sync_process(process_usb)

    with sim.write_vcd(f'eth_interface.vcd'):
        sim.run()
