#!/usr/bin/env python3
#
# Copyright (c) 2021 Hans Baier <hansfbaier@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0
import os

from amaranth            import *
from amaranth.lib.cdc import FFSynchronizer

from eth_interface import EthInterface

from luna                import top_level_cli
from luna.usb2           import USBDevice

from usb_protocol.types                       import USBRequestType, USBTransferType, USBSynchronizationType, USBUsageType, USBDirection, USBStandardRequests
from usb_protocol.emitters                    import DeviceDescriptorCollection
from usb_protocol.emitters.descriptors        import standard

from luna.gateware.usb.usb2.device            import USBDevice
from luna.gateware.usb.usb2.endpoints.stream  import USBStreamInEndpoint, USBStreamOutEndpoint
from luna.gateware.usb.usb2.request           import USBRequestHandler, StallOnlyRequestHandler

from usb_out_from_fifo import USBOutFromFifo

from amaranth.lib.fifo import *
from requesthandlers        import VendorRequestHandlers
from led_multiplexer import LEDMultiplexer

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
            endpointDescriptor.bmAttributes = USBTransferType.BULK | \
                                              (USBSynchronizationType.NONE << 2) | \
                                              (USBUsageType.DATA << 4)
            endpointDescriptor.wMaxPacketSize = 512
            endpointDescriptor.bInterval = 0
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

        with_debug_usb = False
        m = Module()

        depth = int(1540 / 4 * 16)
#       if (simulation):
#           depth = int(64 / 4 * 16)

        m.submodules.led_multiplexer = led_multiplexer = DomainRenamer("usb")(LEDMultiplexer(input_count = 4))
        m.submodules.usb_out_from_fifo = usb_out_from_fifo = DomainRenamer("usb")(USBOutFromFifo(simulation = False))


        m.submodules.usb_out_fifo = out_fifo = DomainRenamer("usb")(SyncFIFO(width = 32, depth = depth))
        m.submodules.usb_out_fifo_size = out_fifo_size = DomainRenamer("usb")(SyncFIFO(width = 32, depth = 16))

        m.submodules.eth_interface = eth_interface = DomainRenamer("usb")(EthInterface())
       
        m.d.comb += [
                usb_out_from_fifo.fifo_r_rdy.eq(out_fifo.r_rdy),
                out_fifo.r_en.eq(usb_out_from_fifo.fifo_r_en),
                usb_out_from_fifo.fifo_r_data.eq(out_fifo.r_data),
                usb_out_from_fifo.fifo_count_r_rdy.eq(out_fifo_size.r_rdy),
                out_fifo_size.r_en.eq(usb_out_from_fifo.fifo_count_r_en),
                usb_out_from_fifo.fifo_count_r_data.eq(out_fifo_size.r_data),

                out_fifo.w_en.eq(eth_interface.inject_data.usb_out_fifo_w_en),
                eth_interface.inject_data.usb_out_fifo_w_rdy.eq(out_fifo.w_rdy),
                out_fifo.w_data.eq(eth_interface.inject_data.usb_out_fifo_w_data),
                out_fifo_size.w_en.eq(eth_interface.inject_data.usb_out_fifo_size_w_en),
                eth_interface.inject_data.usb_out_fifo_size_w_rdy.eq(out_fifo_size.w_rdy),
                out_fifo_size.w_data.eq(eth_interface.inject_data.usb_out_fifo_size_w_data),
        ]

        if with_debug_usb:
            m.submodules.usb_dbg_out_from_fifo = usb_dbg_out_from_fifo = USBOutFromFifo(simulation = False)
            m.submodules.usb_dbg_out_fifo = out_dbg_fifo = AsyncFIFO(width = 32, depth = 5, 
                                                             r_domain = "sync", w_domain = "fast")
            m.submodules.usb_dbg_out_fifo_size = out_dbg_fifo_size = AsyncFIFO(width = 11, depth = 5,
                                                             r_domain = "sync", w_domain = "fast")
            m.d.comb += [
                usb_dbg_out_from_fifo.fifo_r_rdy.eq(out_dbg_fifo.r_rdy),
                out_dbg_fifo.r_en.eq(usb_dbg_out_from_fifo.fifo_r_en),
                usb_dbg_out_from_fifo.fifo_r_data.eq(out_dbg_fifo.r_data),
                usb_dbg_out_from_fifo.fifo_count_r_rdy.eq(out_dbg_fifo_size.r_rdy),
                out_dbg_fifo_size.r_en.eq(usb_dbg_out_from_fifo.fifo_count_r_en),
                usb_dbg_out_from_fifo.fifo_count_r_data.eq(out_dbg_fifo_size.r_data),

                out_dbg_fifo.w_en.eq(eth_interface.inject_data.usb_out_dbg_fifo_w_en),
                eth_interface.inject_data.usb_out_dbg_fifo_w_rdy.eq(out_dbg_fifo.w_rdy),
                out_dbg_fifo.w_data.eq(eth_interface.inject_data.usb_out_dbg_fifo_w_data),
                out_dbg_fifo_size.w_en.eq(eth_interface.inject_data.usb_out_dbg_fifo_size_w_en),
                eth_interface.inject_data.usb_out_dbg_fifo_size_w_rdy.eq(out_dbg_fifo_size.w_rdy),
                out_dbg_fifo_size.w_data.eq(eth_interface.inject_data.usb_out_dbg_fifo_size_w_data),
            ]

        rst_button = platform.request("button", 0)
        act_button = platform.request("button", 1)

        start_usb = Signal()
        resetsignal = Signal()
        resetsignal_fast = Signal()
        #m.d.fast += [ resetsignal_fast.eq(resetsignal) ]

        m.d.comb += [
            m.submodules.eth_interface.wb_clk.eq(ClockSignal("usb")),
            m.submodules.eth_interface.wb_rst.eq(ResetSignal("usb")),
        #    ResetSignal("fast").eq(resetsignal_fast),
            ResetSignal("usb").eq(resetsignal),
        ]

        inject_data_leds_sync = Signal(8, reset = 0)
        inject_data_debug_received_sync = Signal(8, reset = 0)
        inject_data_leds__sync = Signal(8, reset = 0)

        m.submodules.fast_sync_led_synchro = led_synchro = FFSynchronizer(i = eth_interface.inject_data.leds, o = inject_data_leds_sync)

        m.submodules.fast_sync_debug_rcv_synchro = debug_rcv_synchro = FFSynchronizer(i = eth_interface.inject_data.debug_received, o = inject_data_debug_received_sync)

        m.submodules.fast_sync_led__synchro = led__synchro = FFSynchronizer(i = eth_interface.inject_data.leds_, o = inject_data_leds__sync)       

        m.d.sync += resetsignal.eq(rst_button.i[0])
        m.d.sync += start_usb.eq(act_button.i[0])

        leds = Cat([platform.request("led", i).o for i in range(8)])

        # Generate our domain clocks/resets.
        m.submodules.car = platform.clock_domain_generator()

        ulpi = platform.request(platform.default_usb_connection)
        m.submodules.usb = usb = DomainRenamer("usb")(USBDevice(bus=ulpi))

        # Add our standard control endpoint to the device.
        descriptors = self.create_descriptors()
        control_ep = usb.add_control_endpoint()
        control_ep.add_standard_request_handlers(descriptors, blacklist=[
            lambda setup:   (setup.type    == USBRequestType.STANDARD)
                          & (setup.request == USBStandardRequests.SET_INTERFACE)
        ])

        vendor_request_handler =  VendorRequestHandlers()
        control_ep.add_request_handler(vendor_request_handler)

        m.d.comb += [
                led_multiplexer.inputs[0].eq(vendor_request_handler.leds),
                led_multiplexer.inputs[1].eq(inject_data_leds_sync),
                led_multiplexer.inputs[2].eq(usb_out_from_fifo.leds),
                led_multiplexer.inputs[3].eq(inject_data_leds__sync),
                led_multiplexer.do_switch.eq(start_usb),
                leds.eq(led_multiplexer.output),
        ]

        m.d.comb += [
            eth_interface.inject_data.control_op.eq(vendor_request_handler.op),
            eth_interface.inject_data.control_data_in.eq(vendor_request_handler.data_out),
            eth_interface.inject_data.control_rd_wr.eq(vendor_request_handler.rd_wr),
            eth_interface.inject_data.control_reg.eq(vendor_request_handler.reg_addr),
            vendor_request_handler.data_in.eq(eth_interface.inject_data.control_data_out),
            vendor_request_handler.op_finish.eq(eth_interface.inject_data.control_op_finish)
        ]

        # Attach class-request handlers that stall any reserved requests,
        # as we don't have or need any.
        stall_condition = lambda setup : \
            (setup.type == USBRequestType.RESERVED)
        control_ep.add_request_handler(StallOnlyRequestHandler(stall_condition))

        ep1_in = USBStreamInEndpoint(
            endpoint_number=1, # EP 1 IN INTERRUPT
            max_packet_size=512)
        usb.add_endpoint(ep1_in)

        ep2_in = USBStreamInEndpoint(
            endpoint_number=2, # EP 2 IN BULK
            max_packet_size=512)
        usb.add_endpoint(ep2_in)

        ep3_out = USBStreamOutEndpoint(
            endpoint_number=3, # EP 3 OUT BULK
            max_packet_size=512)
        usb.add_endpoint(ep3_out)

        m.d.comb += eth_interface.usb_in_to_fifo.usb_stream_in.stream_eq(ep3_out.stream)
        m.d.comb += ep2_in.stream.stream_eq(usb_out_from_fifo.usb_stream_out)

        if with_debug_usb:
            m.d.comb += ep1_in.stream.stream_eq(usb_dbg_out_from_fifo.usb_stream_out)

#        m.d.comb += leds.eq(usb_in_to_fifo.leds)
#        m.d.comb += leds.eq(eth_interface.inject_data.leds)
#        m.d.comb += leds.eq(usb_out_from_fifo.leds)

        m.d.comb += eth_interface.inject_data.start_usb.eq(start_usb)

        # Connect our device as a high speed device
        m.d.comb += [
            usb.connect          .eq(1),
            usb.full_speed_only  .eq(0),
        ]

        return m

if __name__ == "__main__":
    os.environ["LUNA_PLATFORM"] = "arrow_deca:ArrowDECAPlatform"
    top_level_cli(USB2EthernetInterface)
