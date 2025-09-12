#!/usr/bin/env python3
from requesthandlers import VendorRequestHandlers
from usb_protocol.types import USBRequestType
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = VendorRequestHandlers()

    def process():
        yield dut.op_finish.eq(0)
        yield Tick()
        yield dut.interface.setup.type.eq(USBRequestType.VENDOR)
        yield dut.interface.setup.request.eq(0xa5)
        yield dut.interface.setup.is_in_request.eq(1)
        yield dut.interface.data_requested.eq(1)
        yield dut.interface.status_requested.eq(1)
        yield dut.interface.setup.length.eq(4)
        for i in range(5):
            yield Tick()
        yield dut.data_in.eq(0xaabbccdd)
        yield dut.op_finish.eq(1)
        yield Tick()
        yield dut.op_finish.eq(0)
        yield dut.interface.tx.ready.eq(1)
        for i in range(4):
            yield Tick()
        yield dut.interface.tx.ready.eq(0)
        yield Tick()
        yield dut.interface.setup.is_in_request.eq(0)
        yield dut.interface.rx.payload.eq(0x01)
        yield dut.interface.rx.next.eq(1)
        yield Tick()
        yield dut.interface.rx.payload.eq(0x02)
        yield dut.interface.rx.next.eq(1)
        yield Tick()
        yield dut.interface.rx.payload.eq(0x03)
        yield dut.interface.rx.next.eq(1)
        yield Tick()
        yield dut.interface.rx.payload.eq(0x04)
        yield dut.interface.rx.next.eq(1)
        yield Tick()
        yield dut.interface.rx.next.eq(0)
        for i in range(3):
            yield Tick()
        yield dut.op_finish.eq(1)
        yield Tick()
        yield dut.op_finish.eq(0)
        for i in range(16):
            yield Tick()

    sim = Simulator(dut)
    sim.add_clock(1.0/60e6)
    sim.add_sync_process(process)

    with sim.write_vcd('requesthandlers.vcd'):
        sim.run()
