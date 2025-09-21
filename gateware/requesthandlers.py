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
                                                 (((3 - cnt) * 8).as_unsigned())) |
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



#class VendorRequestHandlers(USBRequestHandler):
#    def __init__(self, simulation = False):
#        super().__init__()
#        self.leds = Signal(8, reset = 0)
#        self.count = Signal(2, reset = 0)
#
#        self.reg_addr = Signal(8, reset = 0)
#        self.data_in = Signal(32, reset = 0)
#        self.data_out = Signal(32, reset = 0)
#        self.op = Signal(reset = 0)
#        self.op_finish = Signal(reset = 0)
#        self.rd_wr = Signal(reset = 0)
#        self.cnt = Signal(2, reset = 0)
#        if not simulation:
#            self.delay = Signal(25, reset = 0)
#        else:
#            self.delay = Signal(8, reset = 0)
#        self.transmitter = StreamSerializer(data_length=4, domain="usb", stream_type=USBInStreamInterface, max_length_width=4)
#
#    def elaborate(self, platform):
#        m = Module()
#
#        m.submodules.transmitter = transmitter = self.transmitter
#
#        interface = self.interface
#        setup = self.interface.setup
#
#        m.d.comb += transmitter.start.eq(0)
#        m.d.comb += interface.handshakes_out.ack.eq(0)
#        m.d.comb += interface.handshakes_out.nak.eq(0)
#
#        m.d.comb += transmitter.stream.attach(self.interface.tx)
#        m.d.comb += [
#            Cat(transmitter.data).eq(self.data_in),
#            transmitter.max_length.eq(setup.length)
#        ]
#
#        m.d.comb += interface.claim.eq(0)
#        data_requested = Signal(reset = 0)
#        status_requested = Signal(reset = 0)
#
#        with m.If(setup.type == USBRequestType.VENDOR & setup.received):
#            with m.If(setup.request == 0x05):
#                m.d.comb += interface.claim.eq(1)
#                with m.If(interface.status_requested):
#                    m.d.comb += interface.handshakes_out.ack.eq(1)
#
#                with m.If(interface.data_requested):
#                    m.d.usb += data_requested.eq(1)
#
#        
#                with m.FSM(reset="IDLE"):
#                    with m.State("IDLE"):
#                        m.d.usb += self.op.eq(0)
#                        m.d.usb += self.reg_addr.eq(setup.value)
#                        with m.If(setup.is_in_request):
#                            m.d.usb += self.rd_wr.eq(0)
#                            m.next = "READ_REG"
#                
#                        with m.Else():
#                            with m.If(interface.rx.next):
#                                m.d.usb += self.data_out.eq(interface.rx.payload << 
#                                                            (((3 - self.cnt) * 8).as_unsigned()) |
#                                                            self.data_out)
#                                m.d.usb += self.cnt.eq(self.cnt + 1)
#                                with m.If(self.cnt == 3):
#                                    m.next = "WRITE_REG"
#        
#                    with m.State("READ_REG"):
#                        m.d.usb += self.op.eq(1)
#                        with m.If(self.op_finish):
#                            m.d.usb += self.op.eq(0)
#                            m.next = "SEND_REG"
#                            m.d.usb += self.delay.eq(1)
#        
#                    with m.State("SEND_REG"):
#                        with m.If(data_requested):
#                            m.d.comb += transmitter.start.eq(1)
#                            m.d.usb += data_requested.eq(0)
#                            m.d.usb += self.leds.eq(0b01010101)
#        
#                        m.d.comb += interface.claim.eq(1)
#                        m.d.usb += self.delay.eq(self.delay + 1)
#                        m.d.usb += self.leds.eq(0b11000000)
#                        with m.If(transmitter.done):
#                            with m.If(interface.handshakes_in.ack):
#                                m.next = "END_END_SEND"
#                            with m.Else():
#                                m.next = "END_SEND"
#                        with m.Elif(self.delay == 0):
#                            m.next = "IDLE"
#                            m.d.usb += self.leds.eq(0b00110000)
#                            m.d.comb += interface.handshakes_out.nak.eq(1)
#        
#                    with m.State("END_SEND"):
#                        m.d.comb += interface.claim.eq(1)
#                        with m.If(interface.handshakes_in.ack):
#                            m.next = "END_END_SEND"
#                    
#                    with m.State("END_END_SEND"):
#                        m.d.comb += interface.claim.eq(1)
#                        with m.If(interface.status_requested):
#                            m.d.comb += interface.handshakes_out.ack.eq(1)
#                            m.next = "IDLE"
#        
#                    with m.State("WRITE_REG"):
#                        m.d.comb += interface.claim.eq(1)
#                        m.d.usb += self.op.eq(1)
#                        m.d.usb += self.rd_wr.eq(1)
#                        with m.If(self.op_finish):
#                            m.d.usb += self.op.eq(0)
#                            m.d.usb += self.cnt.eq(0)
#                            m.d.usb += self.data_out.eq(0)
#                            m.d.usb += self.delay.eq(1)
#                            m.next = "WRITE_END"
#        
#                    with m.State("WRITE_END"):
#                        m.d.comb += interface.claim.eq(1)
#                        m.d.usb += self.delay.eq(self.delay + 1)
#                        with m.If(interface.rx_ready_for_response): # read how does it work
#                            m.d.comb += interface.handshakes_out.ack.eq(1)
#                            m.next = "IDLE"
#                            with m.If(status_requested):
#                                m.d.usb += status_requested.eq(0)
#                                m.d.comb += self.send_zlp()
#                        with m.Elif(self.delay == 0):
#                            m.next = "IDLE"
#                            m.d.comb += interface.handshakes_out.nak.eq(1)
#
#        return m
