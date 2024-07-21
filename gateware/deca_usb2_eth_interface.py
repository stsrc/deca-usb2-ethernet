#!/usr/bin/env python3
#
# Copyright (c) 2021 Hans Baier <hansfbaier@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0
import os

from amaranth            import *

from eth_interface import EthInterface

from luna                import top_level_cli
from luna.usb2           import USBDevice

from usb_protocol.types                       import USBRequestType, USBTransferType, USBSynchronizationType, USBUsageType, USBDirection, USBStandardRequests
from usb_protocol.emitters                    import DeviceDescriptorCollection
from usb_protocol.emitters.descriptors        import standard

from luna.gateware.usb.usb2.device            import USBDevice
from luna.gateware.usb.usb2.endpoints.stream  import USBStreamInEndpoint, USBStreamOutEndpoint
from luna.gateware.usb.usb2.request           import USBRequestHandler, StallOnlyRequestHandler

from requesthandlers        import VendorRequestHandlers

class USB2EthernetInterface(Elaboratable):
    """ USB Ethernet interface """

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

        m.d.sync += resetsignal.eq(buttons.i[0])
        

        leds = Cat([platform.request("led", i).o for i in range(8)])

        # Generate our domain clocks/resets.
        m.submodules.car = platform.clock_domain_generator()

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

        m.d.comb += eth_interface.inject_data.usb_in_to_fifo.usb_stream_in.stream_eq(ep3_out.stream)
        m.d.comb += ep2_in.stream.stream_eq(eth_interface.inject_data.usb_out_from_fifo.usb_stream_out)

        m.d.comb += leds.eq(eth_interface.inject_data.leds)

        # Connect our device as a high speed device
        m.d.comb += [
            usb.connect          .eq(1),
            usb.full_speed_only  .eq(0),
        ]

        return m

if __name__ == "__main__":
    os.environ["LUNA_PLATFORM"] = "arrow_deca:ArrowDECAPlatform"
    top_level_cli(USB2EthernetInterface)
