from uart_transmitter import UARTTransmitter
from amaranth.sim import Simulator, Tick

if __name__ == "__main__":
    dut = UARTTransmitter()

    def process():
        yield Tick()
        yield dut.data_to_send.eq(0x10)
        yield dut.send.eq(1)
        yield Tick()
        yield dut.send.eq(0)
        for _ in range(10):
            for _ in range(120):
                yield Tick()
        yield Tick()
        yield dut.data_to_send.eq(0xaa)
        yield dut.send.eq(1)
        yield Tick()
        yield dut.send.eq(0)
        for _ in range(10):
            for _ in range(120):
                yield Tick()

    sim = Simulator(dut)
    sim.add_clock(1.0 / 60e6,)
    sim.add_sync_process(process)
    with sim.write_vcd(f'uart_transmitter.vcd'):
        sim.run()
