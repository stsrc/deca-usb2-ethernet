from amaranth        import *
from amaranth.build  import Platform

from amlib.stream  import StreamInterface

class USBStreamToTest(Elaboratable):
    def __init__(self):
        # ports
        self.usb_stream_in       = StreamInterface(name="usb_stream")
        self.leds_out  = Signal(8)

    def elaborate(self, platform: Platform) -> Module:
        m = Module()

        usb_valid        = Signal()
        usb_first        = Signal()
        usb_last         = Signal()
        usb_payload      = Signal(8)

        m.d.comb += [
            usb_first.eq(self.usb_stream_in.first),
            usb_last.eq(self.usb_stream_in.last),
            usb_valid.eq(self.usb_stream_in.valid),
            usb_payload.eq(self.usb_stream_in.payload),
            self.usb_stream_in.ready.eq(1),
#            self.usb_stream_in.ready.eq(usb_valid),
        ]

        with m.If(usb_valid):
            m.d.sync += self.leds_out.eq(usb_payload)

        return m
