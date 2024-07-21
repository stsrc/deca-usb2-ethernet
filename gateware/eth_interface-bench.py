#!/usr/bin/env python3
from eth_interface import EthInterface
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = EthInterface(simulation=True)
    inject = dut.inject_data

    def process_usb():
        for _ in range(25):
            yield Tick()

        yield inject.usb_in_to_fifo.usb_stream_in.payload.eq(1)
        yield inject.usb_in_to_fifo.usb_stream_in.valid.eq(1)
        yield inject.usb_in_to_fifo.usb_stream_in.first.eq(1)
        yield Tick()
        yield inject.usb_in_to_fifo.usb_stream_in.first.eq(0)
        yield inject.usb_in_to_fifo.usb_stream_in.payload.eq(2)
        yield Tick()
        yield inject.usb_in_to_fifo.usb_stream_in.payload.eq(3)
        yield Tick()
        yield inject.usb_in_to_fifo.usb_stream_in.payload.eq(4)
        yield inject.usb_in_to_fifo.usb_stream_in.last.eq(1)

        yield Tick()

        yield inject.usb_in_to_fifo.usb_stream_in.last.eq(0)
        yield inject.usb_in_to_fifo.usb_stream_in.valid.eq(0)

        for _ in range(11):
            yield Tick()

        yield dut.wb_mux_mac.ack.eq(1)
        yield Tick()
        yield dut.wb_mux_mac.ack.eq(0)

    
        yield inject.usb_in_to_fifo.usb_stream_in.payload.eq(5)
        yield inject.usb_in_to_fifo.usb_stream_in.valid.eq(1)
        yield inject.usb_in_to_fifo.usb_stream_in.first.eq(1)
        yield Tick()
        yield inject.usb_in_to_fifo.usb_stream_in.first.eq(0)
        yield inject.usb_in_to_fifo.usb_stream_in.payload.eq(6)
        yield Tick()
        yield inject.usb_in_to_fifo.usb_stream_in.payload.eq(7)
        yield Tick()
        yield inject.usb_in_to_fifo.usb_stream_in.payload.eq(8)
        yield Tick()
        yield inject.usb_in_to_fifo.usb_stream_in.payload.eq(9)
        yield Tick()
        yield inject.usb_in_to_fifo.usb_stream_in.payload.eq(10)
        yield Tick()
        yield inject.usb_in_to_fifo.usb_stream_in.payload.eq(11)
        yield Tick()
        yield inject.usb_in_to_fifo.usb_stream_in.payload.eq(12)
        yield inject.usb_in_to_fifo.usb_stream_in.last.eq(1)
        yield Tick()
        yield inject.usb_in_to_fifo.usb_stream_in.last.eq(0)
        yield inject.usb_in_to_fifo.usb_stream_in.valid.eq(0)

        for _ in range(18):
            yield Tick()

        yield dut.wb_mux_mac.ack.eq(1)
        yield Tick()
        yield dut.wb_mux_mac.ack.eq(0)




        yield Tick()
        yield dut.wb_mac_mux.dat_w.eq(0x0a0b0c0d)
        yield dut.wb_mac_mux.we.eq(1)
        yield dut.wb_mac_mux.cyc.eq(1)
        yield dut.wb_mac_mux.stb.eq(1)
        yield dut.wb_mac_mux.sel.eq(0b1111)
        yield dut.wb_mac_mux.adr.eq(0x04000040)
        yield Tick()
        yield Tick()
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.wb_mac_mux.dat_w.eq(0)
        yield dut.wb_mac_mux.we.eq(0)
        yield dut.wb_mac_mux.cyc.eq(0)
        yield dut.wb_mac_mux.stb.eq(0)
        yield dut.wb_mac_mux.adr.eq(0)
        yield Tick()
 

        yield Tick()
        yield dut.wb_mac_mux.dat_w.eq(0x0e0f1011)
        yield dut.wb_mac_mux.we.eq(1)
        yield dut.wb_mac_mux.cyc.eq(1)
        yield dut.wb_mac_mux.stb.eq(1)
        yield dut.wb_mac_mux.sel.eq(0b1111)
        yield dut.wb_mac_mux.adr.eq(0x04000044)
        yield Tick()
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.wb_mac_mux.dat_w.eq(0)
        yield dut.wb_mac_mux.we.eq(0)
        yield dut.wb_mac_mux.cyc.eq(0)
        yield dut.wb_mac_mux.stb.eq(0)
        yield dut.wb_mac_mux.adr.eq(0)
        yield Tick()

        yield Tick()
        yield dut.wb_mac_mux.dat_w.eq(0x12131415)
        yield dut.wb_mac_mux.we.eq(1)
        yield dut.wb_mac_mux.cyc.eq(1)
        yield dut.wb_mac_mux.stb.eq(1)
        yield dut.wb_mac_mux.sel.eq(0b1111)
        yield dut.wb_mac_mux.adr.eq(0x04000045)
        yield Tick()
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.wb_mac_mux.dat_w.eq(0)
        yield dut.wb_mac_mux.we.eq(0)
        yield dut.wb_mac_mux.cyc.eq(0)
        yield dut.wb_mac_mux.stb.eq(0)
        yield dut.wb_mac_mux.adr.eq(0)
        yield Tick()

        yield Tick()
        yield inject.int.eq(1)
        yield Tick()
        yield inject.int.eq(0)
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.wb_mux_mac.dat_r.eq(0b00001100)
        yield dut.wb_mux_mac.ack.eq(1)
        yield Tick()
        yield dut.wb_mux_mac.dat_r.eq(0)
        yield dut.wb_mux_mac.ack.eq(0)
        yield Tick()
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.wb_mux_mac.ack.eq(1)
        yield Tick()
        yield dut.wb_mux_mac.ack.eq(0)
        yield Tick()
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.wb_mux_mac.dat_r.eq(4 << 16)
        yield dut.wb_mux_mac.ack.eq(1)
        yield Tick()
        yield dut.wb_mux_mac.dat_r.eq(0)
        yield dut.wb_mux_mac.ack.eq(0)

        for _ in range(9):
            yield Tick()

        yield dut.wb_mux_mac.ack.eq(1)
        yield Tick()
        yield dut.wb_mux_mac.ack.eq(0)

        for _ in range(16):
            yield Tick()

        yield inject.usb_out_from_fifo.usb_stream_out.ready.eq(1)
        for _ in range(4):
            yield Tick()
        yield inject.usb_out_from_fifo.usb_stream_out.ready.eq(0)
        yield Tick()

        yield Tick()
        yield inject.int.eq(1)
        yield Tick()
        yield inject.int.eq(0)
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.wb_mux_mac.dat_r.eq(0b00001100)
        yield dut.wb_mux_mac.ack.eq(1)
        yield Tick()
        yield dut.wb_mux_mac.dat_r.eq(0)
        yield dut.wb_mux_mac.ack.eq(0)
        yield Tick()
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.wb_mux_mac.ack.eq(1)
        yield Tick()
        yield dut.wb_mux_mac.ack.eq(0)
        yield Tick()
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.wb_mux_mac.dat_r.eq(8 << 16)
        yield dut.wb_mux_mac.ack.eq(1)
        yield Tick()
        yield dut.wb_mux_mac.dat_r.eq(0)
        yield dut.wb_mux_mac.ack.eq(0)

        for _ in range(16):
            yield Tick()

        yield dut.wb_mux_mac.ack.eq(1)
        yield Tick()
        yield dut.wb_mux_mac.ack.eq(0)


        for _ in range(16):
            yield Tick()

        yield inject.usb_out_from_fifo.usb_stream_out.ready.eq(1)
        for _ in range(9):
            yield Tick()
        yield inject.usb_out_from_fifo.usb_stream_out.ready.eq(0)

    def process():
        for _ in range(1500):
            yield Tick()

    sim = Simulator(dut)
    sim.add_clock(1.0/50e6,)
    sim.add_sync_process(process)
    sim.add_sync_process(process_usb)

    with sim.write_vcd(f'eth_interface.vcd'):
        sim.run()
