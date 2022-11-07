#!/usr/bin/env python3
from channels_to_usb_stream import ChannelsToUSBStream
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = ChannelsToUSBStream(2)

    def send_one_frame(sample: int, channel: int):
        yield dut.channel_stream_in.channel_no.eq(channel)
        yield dut.channel_stream_in.payload.eq(sample)
        yield dut.channel_stream_in.valid.eq(1)
        yield

    def process():
        yield dut.usb_stream_out.ready.eq(1)
        yield
        yield from send_one_frame(0x030201, 0)
        yield from send_one_frame(0x131211, 1)
        yield
        yield
        yield
        yield from send_one_frame(0x232221, 0)
        yield
        yield
        yield
        yield from send_one_frame(0x333231, 1)
        yield
        yield
        yield
        yield dut.channel_stream_in.valid.eq(0)
        yield
        yield
        yield
        yield
        yield from send_one_frame(0x434241, 0)
        yield
        yield
        yield
        yield from send_one_frame(0x535251, 1)
        yield
        yield
        yield
        for _ in range(30): yield

    sim = Simulator(dut)
    sim.add_clock(1.0/60e6,)
    sim.add_sync_process(process)

    with sim.write_vcd(f'channels_to_usb_stream.vcd'):
        sim.run()