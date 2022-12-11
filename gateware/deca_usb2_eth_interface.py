#!/usr/bin/env python3
#
# Copyright (c) 2021 Hans Baier <hansfbaier@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0
import os

from amaranth            import *
from amaranth.lib.cdc    import FFSynchronizer

from amlib.io.i2s        import I2STransmitter, I2SReceiver
from amlib.stream.i2c    import I2CStreamTransmitter
from amlib.debug.ila     import StreamILA, ILACoreParameters
from amlib.utils         import EdgeToPulse, Timer

from eth_interface import EthInterface

from luna                import top_level_cli
from luna.usb2           import USBDevice, USBIsochronousInMemoryEndpoint, USBIsochronousOutStreamEndpoint, USBIsochronousInStreamEndpoint

#from luna.gateware.usb.usb2.endpoints.isochronous import USBIsochronousOutRawStreamEndpoint

from usb_protocol.types                       import USBRequestType, USBRequestRecipient, USBTransferType, USBSynchronizationType, USBUsageType, USBDirection, USBStandardRequests
from usb_protocol.types.descriptors.uac2      import AudioClassSpecificRequestCodes
from usb_protocol.emitters                    import DeviceDescriptorCollection
from usb_protocol.emitters.descriptors        import uac2, standard

from luna.gateware.platform                   import NullPin, get_appropriate_platform
from luna.gateware.usb.usb2.device            import USBDevice
from luna.gateware.usb.usb2.endpoints.stream  import USBMultibyteStreamInEndpoint, USBStreamInEndpoint, USBStreamOutEndpoint
from luna.gateware.usb.usb2.request           import USBRequestHandler, StallOnlyRequestHandler

from usb_stream_to_channels import USBStreamToChannels
from usb_stream_test import USBStreamToTest
from channels_to_usb_stream import ChannelsToUSBStream
from requesthandlers        import UAC2RequestHandlers, VendorRequestHandlers
from audio_init             import AudioInit

class USB2AudioInterface(Elaboratable):
    """ USB Audio Class v2 interface """

    def create_descriptors(self):
        """ Creates the descriptors that describe our eth topology. """

        descriptors = DeviceDescriptorCollection()

        with descriptors.DeviceDescriptor() as d:
            d.bcdUSB             = 2.00
            d.bDeviceClass       = 0xFF
            d.bDeviceSubclass    = 0xFF
            d.bDeviceProtocol    = 0x0
            d.idVendor           = 0x1209
            d.idProduct          = 0x4711

            d.iManufacturer      = "Konrad Gotfryd"
            d.iProduct           = "DECAface"
            d.iSerialNumber      = "4711"
            d.bcdDevice          = 1.00

            d.bNumConfigurations = 1

        with descriptors.ConfigurationDescriptor() as configDescr:
            # Interface Association

            # Interface Descriptor (Control)
            interfaceDescriptor = standard.InterfaceDescriptorEmitter()
            interfaceDescriptor.bInterfaceNumber = 0
            interfaceDescriptor.bAlternateSetting = 0
            interfaceDescriptor.bInterfaceClass = 0xFF
            interfaceDescriptor.bInterfaceSubclass = 0xFF
            interfaceDescriptor.bInterfaceProtocol = 0


            endpointDescriptor = standard.EndpointDescriptorEmitter()
            endpointDescriptor.bEndpointAddress = USBDirection.IN.to_endpoint_address(1) # EP 1 IN
            endpointDescriptor.bmAttributes = USBTransferType.INTERRUPT | \
                                              (USBSynchronizationType.NONE << 2) | \
                                              (USBUsageType.DATA << 4)
            endpointDescriptor.wMaxPacketSize = 8
            endpointDescriptor.bInterval = 11
            interfaceDescriptor.add_subordinate_descriptor(endpointDescriptor)

            endpointDescriptor = standard.EndpointDescriptorEmitter()
            endpointDescriptor.bEndpointAddress = USBDirection.IN.to_endpoint_address(2) # EP 2 IN
            endpointDescriptor.bmAttributes = USBTransferType.BULK | \
                                              (USBSynchronizationType.NONE << 2) | \
                                              (USBUsageType.DATA << 4)
            endpointDescriptor.wMaxPacketSize = 512
            endpointDescriptor.bInterval = 0
            interfaceDescriptor.add_subordinate_descriptor(endpointDescriptor)

            endpointDescriptor = standard.EndpointDescriptorEmitter()
            endpointDescriptor.bEndpointAddress = USBDirection.OUT.to_endpoint_address(3) # EP 3 OUT
            endpointDescriptor.bmAttributes = USBTransferType.BULK | \
                                              (USBSynchronizationType.NONE << 2) | \
                                              (USBUsageType.DATA << 4)
            endpointDescriptor.wMaxPacketSize = 512
            endpointDescriptor.bInterval = 0
            interfaceDescriptor.add_subordinate_descriptor(endpointDescriptor)

            configDescr.add_subordinate_descriptor(interfaceDescriptor)

        return descriptors


    def elaborate(self, platform):

        m = Module()

        m.submodules.eth_interface = eth_interface = DomainRenamer("usb")(EthInterface())

        buttons = platform.request("button")

        resetsignal = Signal()

        m.d.comb += [
            m.submodules.eth_interface.wb_clk.eq(ClockSignal("usb")),
            m.submodules.eth_interface.wb_rst.eq(resetsignal),
            ResetSignal("usb").eq(resetsignal)
        ]

        m.d.sync += resetsignal.eq(buttons[0])
        

        leds = Cat([platform.request("led", i) for i in range(8)])

        # Generate our domain clocks/resets.
        m.submodules.car = platform.clock_domain_generator()
        m.submodules.audio_init = audio_init = AudioInit()
        i2c_audio_pads = platform.request("i2c_audio")
        m.submodules.i2c = i2c = DomainRenamer("usb") \
            (I2CStreamTransmitter(i2c_audio_pads, int(60e6/400e3), clk_stretch=False))
        m.submodules.audio_init_delay = audio_init_delay = \
            Timer(width=28, load=int(120e6), reload=0, allow_restart=False)

        audio = platform.request("audio")
        debug = platform.request("debug")

        m.d.comb += [
            # wire up DAC/ADC
            audio.mclk.eq(ClockSignal("audio")),
            audio.reset.eq(ResetSignal("audio")),
            audio.spi_select.eq(0), # choose i2c
            audio_init_delay.start.eq(1),
            audio_init.start.eq(audio_init_delay.done),

            debug.bclk.eq(audio.bclk),
            debug.wclk.eq(audio.wclk),
            debug.adc.eq(audio.dout_mfp2),
        ]

        ulpi = platform.request(platform.default_usb_connection)
        m.submodules.usb = usb = USBDevice(bus=ulpi)

        # Add our standard control endpoint to the device.
        descriptors = self.create_descriptors()
        control_ep = usb.add_control_endpoint()
        control_ep.add_standard_request_handlers(descriptors, blacklist=[
            lambda setup:   (setup.type    == USBRequestType.STANDARD)
                          & (setup.request == USBStandardRequests.SET_INTERFACE)
        ])

        vendor_request_handler = VendorRequestHandlers()
        control_ep.add_request_handler(vendor_request_handler)
#        m.d.comb += leds.eq(vendor_request_handler.leds)

#        class_request_handler = UAC2RequestHandlers()
#        control_ep.add_request_handler(class_request_handler)

        # Attach class-request handlers that stall any reserved requests,
        # as we don't have or need any.
        stall_condition = lambda setup : \
            (setup.type == USBRequestType.RESERVED)
        control_ep.add_request_handler(StallOnlyRequestHandler(stall_condition))

        ep1_in = USBStreamInEndpoint(
            endpoint_number=1, # EP 1 IN INTERRUPT
            max_packet_size=8)
        usb.add_endpoint(ep1_in)

        ep2_in = USBStreamInEndpoint(
            endpoint_number=2, # EP 2 IN BULK
            max_packet_size=512)
        usb.add_endpoint(ep2_in)

        ep3_out = USBStreamOutEndpoint(
            endpoint_number=3, # EP 3 OUT BULK
            max_packet_size=512)
        usb.add_endpoint(ep3_out)

        m.d.comb += eth_interface.inject_data.usb_stream_in.stream_eq(ep3_out.stream)

        m.d.comb += leds.eq(eth_interface.inject_data.leds)

        # calculate bytes in frame for audio in
        audio_in_frame_bytes = Signal(4, reset=15)
        audio_in_frame_bytes_counting = Signal()

        # Connect our device as a high speed device
        m.d.comb += [
#            ep1_in.bytes_in_frame.eq(4),
#            ep2_in.bytes_in_frame.eq(audio_in_frame_bytes),
            usb.connect          .eq(1),
            usb.full_speed_only  .eq(0),
        ]

        # feedback endpoint
        feedbackValue      = Signal(32, reset=0x60000)
        bitPos             = Signal(5)

        # this tracks the number of audio frames since the last USB frame
        # 12.288MHz / 8kHz = 1536, so we need at least 11 bits = 2048
        # we need to capture 32 micro frames to get to the precision
        # required by the USB standard, so and that is 0xc000, so we
        # need 16 bits here
        audio_clock_counter = Signal(16)
        sof_counter         = Signal(5)

        audio_clock_usb = Signal()
        m.submodules.audio_clock_usb_sync = FFSynchronizer(ClockSignal("audio"), audio_clock_usb, o_domain="usb")
        m.submodules.audio_clock_usb_pulse = audio_clock_usb_pulse = DomainRenamer("usb")(EdgeToPulse())
        audio_clock_tick = Signal()
        m.d.usb += [
            audio_clock_usb_pulse.edge_in.eq(audio_clock_usb),
            audio_clock_tick.eq(audio_clock_usb_pulse.pulse_out),
        ]

        with m.If(audio_clock_tick):
            m.d.usb += audio_clock_counter.eq(audio_clock_counter + 1)

        with m.If(usb.sof_detected):
            m.d.usb += sof_counter.eq(sof_counter + 1)

            # according to USB2 standard chapter 5.12.4.2
            # we need 2**13 / 2**8 = 2**5 = 32 SOF-frames of
            # sample master frequency counter to get enough
            # precision for the sample frequency estimate
            # / 2**8 because the ADAT-clock = 256 times = 2**8
            # the sample frequency and sof_counter is 5 bits
            # so it wraps automatically every 32 SOFs
            with m.If(sof_counter == 0):
                m.d.usb += [
                    feedbackValue.eq(audio_clock_counter << 3),
                    audio_clock_counter.eq(0),
                ]

        m.d.comb += [
#            bitPos.eq(ep1_in.address << 3),
#            ep1_in.value.eq(0xff & (feedbackValue >> bitPos)),
        ]

 
        underflow_count = Signal(16)

        with m.If(~usb.suspended):
            m.d.sync += underflow_count.eq(underflow_count + 1)

        return m

if __name__ == "__main__":
    os.environ["LUNA_PLATFORM"] = "arrow_deca:ArrowDECAPlatform"
    top_level_cli(USB2AudioInterface)
