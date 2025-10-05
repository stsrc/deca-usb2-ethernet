from amaranth import *
from luna.gateware.usb.usb2.request   import USBRequestHandler
from luna.gateware.stream.generator   import StreamSerializer

from usb_protocol.types                       import USBRequestType, USBRequestRecipient, USBTransferType, USBSynchronizationType, USBUsageType, USBDirection, USBStandardRequests
from usb_protocol.types.descriptors.uac2      import AudioClassSpecificRequestCodes
from luna.gateware.usb.stream                 import USBInStreamInterface

class VendorRequestHandlers(USBRequestHandler):
    def __init__(self):
        super().__init__()
        self.leds = Signal(8, reset = 0)
        self.count = Signal(2)

        self.reg_addr = Signal(8, reset = 0)
        self.data_in = Signal(32)
        self.data_out = Signal(32, reset = 0)
        self.op = Signal(reset = 0)
        self.op_finish = Signal()
        self.rd_wr = Signal(reset = 0)

    def elaborate(self, platform):
        m = Module()

        m.submodules.transmitter = transmitter = \
            StreamSerializer(data_length=4, domain="usb", stream_type=USBInStreamInterface, max_length_width=4)

        interface = self.interface
        setup = self.interface.setup
        cnt = Signal(6, reset = 0)
        dbg_cnt = Signal(6, reset = 0)

        dummy_tx = USBInStreamInterface()

        m.d.comb += transmitter.start.eq(0)
        m.d.comb += interface.handshakes_out.ack.eq(0)
        m.d.comb += interface.claim.eq(0)
        m.d.comb += self.interface.tx.valid.eq(0)
        m.d.comb += self.interface.tx.last.eq(0)

        m.d.comb += [
            Cat(transmitter.data).eq(self.data_in),
            transmitter.max_length.eq(4)
        ]

        m.d.comb += transmitter.stream.attach(dummy_tx)

        with m.If(setup.type == USBRequestType.VENDOR):
            m.d.sync += self.reg_addr.eq(setup.request)
            m.d.comb += interface.claim.eq(1)
            with m.If(setup.is_in_request): #REG RD

                m.d.comb += transmitter.stream.attach(self.interface.tx)

                with m.If(interface.data_requested):
                    m.d.sync += self.op.eq(1)
                    m.d.sync += self.rd_wr.eq(0)
                with m.If(self.op_finish):
                    m.d.sync += self.op.eq(0)
                    m.d.comb += transmitter.start.eq(1)
                with m.If(interface.status_requested):
                    m.d.comb += interface.handshakes_out.ack.eq(1)

#                m.d.sync += self.leds.eq(self.leds + 2)

            with m.Else():                          #REG WR
                with m.If(interface.rx.next):
                    m.d.sync += self.data_out.eq((interface.rx.payload <<
                                                 ((cnt * 8).as_unsigned())) |
                                                 self.data_out)
                    with m.If(interface.rx.payload == 0x0a):
                        m.d.sync += dbg_cnt.eq(dbg_cnt + 1)
                    m.d.sync += cnt.eq(cnt + 1)

                    m.d.sync += self.leds.eq(((cnt + 1) << 4) | (dbg_cnt + 1))

                with m.If(cnt >= 3):
                    m.d.sync += self.op.eq(1)
                    m.d.sync += self.rd_wr.eq(1)
                with m.If((cnt > 3) & self.op_finish):
                    m.d.sync += self.op.eq(0)
                    m.d.sync += self.data_out.eq(0)
                    m.d.sync += cnt.eq(0)
                    m.d.sync += dbg_cnt.eq(0)

            # Always ACK the data out...
                with m.If((~interface.rx.next) & interface.rx_ready_for_response):
                    m.d.comb += interface.handshakes_out.ack.eq(1)

            # ... and accept whatever the request was.
                with m.If((~interface.rx.next) & interface.status_requested):
                    m.d.comb += self.send_zlp()

#                    m.d.sync += self.leds.eq(self.leds + 2)

        return m
