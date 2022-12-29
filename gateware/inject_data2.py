#!/usr/bin/env python3
#
# Copyright (c) 2022 Konrad Gotfryd <gotfrydkonrad@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0

import os

from amaranth import *
from simple_ports_to_wb import SimplePortsToWb
from amlib.stream  import StreamInterface

__all__ = ["InjectData2"]

class InjectData2(Elaboratable):
    def __init__(self, simulation):
        self.simple_ports_to_wb = SimplePortsToWb()

        self.leds = Signal(8)
        self.wait_counter = Signal(26)
        self.phy_resetn = Signal()
        self.simulation = simulation

        self.head = Signal(6)
        self.tail = Signal(6)
        self.end = Signal()

        self.rd_head = Signal(6)
        self.rd_tail = Signal(6)

        self.usb_stream_in = StreamInterface(name="usb_stream_in")
        self.usb_stream_out = StreamInterface(name="usb_stream_out")

        self.int = Signal()
        self.rx_pkt_len = Signal(16)

    def get_bus(self):
        return self.simple_ports_to_wb.bus

    def elaborate(self, platform):
        m = Module()
        m.submodules.simple_ports_to_wb = self.simple_ports_to_wb

        usb_valid = Signal()
        usb_first = Signal()
        usb_last = Signal()
        usb_payload = Signal(8)
        payload = Signal(32)
        counter = Signal(11)
        counter2 = Signal(11)
        interrupt_generated = Signal()
        irq_state = Signal(32)
        send_packet = Signal()
        clear_tx_desc = Signal()

        m.d.comb += [
            usb_first.eq(self.usb_stream_in.first),
            usb_last.eq(self.usb_stream_in.last),
            usb_valid.eq(self.usb_stream_in.valid),
            usb_payload.eq(self.usb_stream_in.payload)
        ]

        with m.If(self.int):
            m.d.sync += interrupt_generated.eq(1)

        with m.FSM(reset="RESET"):
            with m.State("RESET"):
#                m.d.sync += self.leds.eq(1)
                m.d.sync += self.wait_counter.eq(0)
                m.d.sync += self.phy_resetn.eq(0)
                m.next = "WAIT_BEFORE_START"

            with m.State("WAIT_BEFORE_START"):
#                m.d.sync += self.leds.eq(2)

                m.d.sync += self.wait_counter.eq(self.wait_counter + 1)

                if self.simulation:
                    m.d.sync += self.wait_counter.eq(30000000)

                with m.If (self.wait_counter == 30000000):
                    m.next = "WRITE_ETHMAC_INT_MASK"
                    m.d.sync += self.wait_counter.eq(0)

            with m.State("WRITE_ETHMAC_INT_MASK"):
#                m.d.sync += self.leds.eq(3)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000007f)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x08 >> 2)
                m.next = "WRITE_ETHMAC_INT_MASK_WAIT"

            with m.State("WRITE_ETHMAC_INT_MASK_WAIT"):
#                m.d.sync += self.leds.eq(4)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_MAC_ADDR0"

            with m.State("WRITE_ETHMAC_MAC_ADDR0"):
#                m.d.sync += self.leds.eq(5)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0a0a_0a0a)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x40 >> 2)
                m.next = "WRITE_ETHMAC_MAC_ADDR0_WAIT"

            with m.State("WRITE_ETHMAC_MAC_ADDR0_WAIT"):
#                m.d.sync += self.leds.eq(6)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_MAC_ADDR1"

            with m.State("WRITE_ETHMAC_MAC_ADDR1"):
#                m.d.sync += self.leds.eq(7)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000_0a0a)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x44 >> 2)
                m.next = "WRITE_ETHMAC_MAC_ADDR1_WAIT"

            with m.State("WRITE_ETHMAC_MAC_ADDR1_WAIT"):
#                m.d.sync += self.leds.eq(8)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_MODER"
                    m.d.sync += self.phy_resetn.eq(1)

            with m.State("WRITE_ETHMAC_MODER"):
#                m.d.sync += self.leds.eq(9)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000a003) # crc add enabled
#                m.d.sync += self.simple_ports_to_wb.data_in.eq(0x00008003) # crc add disabled
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x00 >> 2)
                m.next = "WRITE_ETHMAC_MODER_WAIT"

            with m.State("WRITE_ETHMAC_MODER_WAIT"):
#                m.d.sync += self.leds.eq(10)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_RX_BUF_DESC_0"

            with m.State("WRITE_ETHMAC_RX_BUF_DESC_0"):
#                m.d.sync += self.leds.eq(11)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                if self.simulation:
                    m.d.sync += self.simple_ports_to_wb.data_in.eq(0x1000_0000 + 
                                                                  (16 * (16 + self.rd_head)))
                else:
                    m.d.sync += self.simple_ports_to_wb.data_in.eq(0x1000_0000 + 
                                                                   (2048 * (16 + self.rd_head)))
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq((0x400 + 
                                                                  (64 + self.rd_head) * 8 + 4) >> 2)

                m.next = "WRITE_ETHMAC_RX_BUF_DESC_0_WAIT"

            with m.State("WRITE_ETHMAC_RX_BUF_DESC_0_WAIT"):
#                m.d.sync += self.leds.eq(12)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_RX_BUF_DESC_1"

            with m.State("WRITE_ETHMAC_RX_BUF_DESC_1"):
#                m.d.sync += self.leds.eq(13)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                with m.If(self.rd_head != 15):
                    m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000c000)
                with m.Else():
                    m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000e000)
                m.d.sync += self.simple_ports_to_wb.address_in.eq((0x400 + 
                                                                  (64 + self.rd_head) * 8) >> 2)
                m.next = "WRITE_ETHMAC_RX_BUF_DESC_1_WAIT"

            with m.State("WRITE_ETHMAC_RX_BUF_DESC_1_WAIT"):
#                m.d.sync += self.leds.eq(14)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    with m.If(((self.rd_head + 1) % 16) != self.rd_tail): 
                        m.d.sync += self.rd_head.eq(self.rd_head + 1 % 16)
                        m.next = "WRITE_ETHMAC_RX_BUF_DESC_0"
                    with m.Else():
                        m.next = "IDLE"

            with m.State("IDLE"):
#                m.d.sync += self.leds.eq(0)
                m.d.comb += self.usb_stream_out.valid.eq(0)

                with m.If(usb_valid & ((self.head + 1) % 16 != self.tail)):
                    m.next = "WRITE_DATA_PREPARE"
                with m.Elif(clear_tx_desc):
                    m.d.sync += clear_tx_desc.eq(0)
                    m.next = "CLEAR_TX_DESC"
                with m.Elif(send_packet):
                    m.d.sync += send_packet.eq(0)
                    m.next = "GET_RX_PACKET_LENGTH"
                with m.Elif(interrupt_generated):
                    m.next = "READ_IRQ"
                    m.d.sync += interrupt_generated.eq(0)
           
            with m.State("CLEAR_TX_DESC"):
#                m.d.sync += self.leds.eq(0)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq((0x400 + self.tail * 8) >> 2)
                m.next = "CLEAR_TX_DESC_WAIT"

            with m.State("CLEAR_TX_DESC_WAIT"):
#                m.d.sync += self.leds.eq(0)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    with m.If(~(self.simple_ports_to_wb.data_out & 0x8000)):
                        m.d.sync += self.tail.eq((self.tail + 1) % 16)
                        with m.If(((self.tail + 1) % 16) != self.head):
                            m.next = "CLEAR_TX_DESC"
                        with m.Else():
                            m.next = "IDLE"
                    with m.Else():
                        m.next = "IDLE"

            with m.State("READ_IRQ"):
#                m.d.sync += self.leds.eq(0)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x04 >> 2)
                m.next = "READ_IRQ_WAIT"

            with m.State("READ_IRQ_WAIT"):
#                m.d.sync += self.leds.eq(0)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.d.sync += irq_state.eq(self.simple_ports_to_wb.data_out)
                    m.next = "IRQ_CHECK"

            with m.State("IRQ_CHECK"):
#                m.d.sync += self.leds.eq(0)
                with m.If(irq_state & 0b00000011):
                    m.d.sync += clear_tx_desc.eq(1)
                with m.If(irq_state & 0b00001100):
                    m.d.sync += send_packet.eq(1)
                m.next = "WRITE_IRQ"

            with m.State("WRITE_IRQ"):
#                m.d.sync += self.leds.eq(0)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq(0x04 >> 2)
                m.next = "WRITE_IRQ_WAIT"

            with m.State("WRITE_IRQ_WAIT"):
#                m.d.sync += self.leds.eq(0)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "IDLE"

            with m.State("GET_RX_PACKET_LENGTH"):
#                m.d.sync += self.leds.eq(1)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(0)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq((0x400 + 
                                                                  (64 + self.rd_tail) * 8) >> 2)
                m.next = "GET_RX_PACKET_LENGTH_WAIT"

            with m.State("GET_RX_PACKET_LENGTH_WAIT"):
#                m.d.sync += self.leds.eq(2)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.d.sync += self.rx_pkt_len.eq(self.simple_ports_to_wb.data_out >> 16)
                    m.d.sync += counter.eq(0)
                    with m.If(self.simple_ports_to_wb.data_out >> 16):
                        m.next = "GET_PACKET_DATA"
                    with m.Else():
                        m.next = "IDLE"

            with m.State("GET_PACKET_DATA"):
#                m.d.sync += self.leds.eq(4)
                m.d.comb += self.usb_stream_out.valid.eq(0)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                if self.simulation:
                    m.d.sync += self.simple_ports_to_wb.address_in.eq(0x0400_0000 + ((16 * (16 + self.rd_tail) + counter) >> 2))
                else:
                    m.d.sync += self.simple_ports_to_wb.address_in.eq(0x0400_0000 + ((2048 * (16 + self.rd_tail) + counter) >> 2))
                m.next = "GET_PACKET_DATA_WAIT"

            with m.State("GET_PACKET_DATA_WAIT"):
#                m.d.sync += self.leds.eq(8)
                m.d.sync += self.simple_ports_to_wb.rd_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.d.sync += payload.eq(self.simple_ports_to_wb.data_out)
                    m.next = "SEND_DATA_TO_USB"

            with m.State("SEND_DATA_TO_USB"):
#                m.d.sync += self.leds.eq(16)
                with m.If(self.usb_stream_out.ready):
                    m.d.comb += self.usb_stream_out.valid.eq(1)
                    #TODO what about last i.e. 3 packets? is it alligned properly?
                    m.d.comb += self.usb_stream_out.payload.eq(payload >> ((3 - (counter % 4)) * 8))
                    m.d.sync += self.leds.eq(payload >> ((3 - (counter % 4)) * 8))
                    with m.If(counter == 0):
                        m.d.comb += self.usb_stream_out.first.eq(1)
                    with m.Else():
                        m.d.comb += self.usb_stream_out.first.eq(0)
                    
                    with m.If(counter == (self.rx_pkt_len - 1)):
                        m.d.sync += counter.eq(0)
                        m.d.comb += self.usb_stream_out.last.eq(1)
                        m.d.sync += payload.eq(0)
                        m.next = "RESET_ETHMAC_RX_BUF_DESC_1"
                    with m.Else():
                        m.d.comb += self.usb_stream_out.last.eq(0)
                        m.d.sync += counter.eq(counter + 1)
                        with m.If((counter + 1) % 4 == 0):
                            m.next = "GET_PACKET_DATA"
    
                with m.Else():
                    m.d.comb += self.usb_stream_out.valid.eq(0)

            with m.State("RESET_ETHMAC_RX_BUF_DESC_1"):
#                m.d.sync += self.leds.eq(32)
                m.d.comb += self.usb_stream_out.valid.eq(0)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                with m.If(self.rd_tail != 15):
                    m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000c000)
                with m.Else():
                    m.d.sync += self.simple_ports_to_wb.data_in.eq(0x0000e000)
                m.d.sync += self.simple_ports_to_wb.address_in.eq((0x400 + 
                                                                  (64 + self.rd_tail) * 8) >> 2)
                m.next = "RESET_ETHMAC_RX_BUF_DESC_1_WAIT"

            with m.State("RESET_ETHMAC_RX_BUF_DESC_1_WAIT"):
#                m.d.sync += self.leds.eq(64)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                        m.d.sync += self.rd_tail.eq((self.rd_tail + 1) % 16) 
                        m.next = "IDLE"

            with m.State("WRITE_DATA_PREPARE"):
#                m.d.sync += self.leds.eq(0)
                with m.If(usb_valid):
                    m.d.comb += self.usb_stream_in.ready.eq(1)
                    m.d.sync += counter.eq(counter + 1)
                    m.d.sync += payload.eq((usb_payload << ( (3 - (counter % 4)) * 8)) | payload)
                    with m.If(usb_last):
                        m.d.sync += self.end.eq(1)
                        m.next = "WRITE_DATA"
                    with m.Elif((counter + 1) % 4 == 0):
                        m.next = "WRITE_DATA"

            #TODO: check what happens if we have to wait for wb to end transaction...
            with m.State("WRITE_DATA"):
#                m.d.sync += self.leds.eq(0)
                m.d.comb += self.usb_stream_in.ready.eq(0)

                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.sync += self.simple_ports_to_wb.data_in.eq(payload)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)

                if self.simulation:
                    m.d.sync += self.simple_ports_to_wb.address_in.eq(0x0400_0000 + ((16 * self.head + counter2) >> 2))
                else:
                    m.d.sync += self.simple_ports_to_wb.address_in.eq(0x0400_0000 + ((2048 * self.head + counter2) >> 2))
                m.d.sync += counter2.eq(counter)
                m.next = "WRITE_DATA_WAIT"

            with m.State("WRITE_DATA_WAIT"):
#                m.d.sync += self.leds.eq(0)
                m.d.sync += payload.eq(0)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out & (~self.end)):
                    m.next = "WRITE_DATA_PREPARE"
                with m.Elif(self.simple_ports_to_wb.op_rdy_out & self.end):
                    m.d.sync += self.end.eq(0)
                    m.next = "WRITE_ETHMAC_TX_BUF_DESC_0"

            with m.State("WRITE_ETHMAC_TX_BUF_DESC_0"):
#                m.d.sync += self.leds.eq(0)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)

                if self.simulation:
                    m.d.sync += self.simple_ports_to_wb.data_in.eq(0x1000_0000 + (16 * self.head))

                else:
                    m.d.sync += self.simple_ports_to_wb.data_in.eq(0x1000_0000 + (2048 * self.head))

                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq((0x400 + self.head * 8 + 4) >> 2)
                m.next = "WRITE_ETHMAC_TX_BUF_DESC_0_WAIT"

            with m.State("WRITE_ETHMAC_TX_BUF_DESC_0_WAIT"):
#                m.d.sync += self.leds.eq(0)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.next = "WRITE_ETHMAC_TX_BUF_DESC_1"

            with m.State("WRITE_ETHMAC_TX_BUF_DESC_1"):
#                m.d.sync += self.leds.eq(0)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(1)
                with m.If(self.head != 15):
                    m.d.sync += self.simple_ports_to_wb.data_in.eq((counter << 16) | 0xc000)
                with m.Else():
                    m.d.sync += self.simple_ports_to_wb.data_in.eq((counter << 16) | 0xe000)
                m.d.sync += self.simple_ports_to_wb.sel_in.eq(0b1111)
                m.d.sync += self.simple_ports_to_wb.address_in.eq((0x400 + self.head * 8) >> 2)
                m.next = "WRITE_ETHMAC_TX_BUF_DESC_1_WAIT"

            with m.State("WRITE_ETHMAC_TX_BUF_DESC_1_WAIT"):
#                m.d.sync += self.leds.eq(0)
                m.d.sync += self.simple_ports_to_wb.wr_strb_in.eq(0)
                with m.If(self.simple_ports_to_wb.op_rdy_out):
                    m.d.sync += counter2.eq(0)
                    m.d.sync += counter.eq(0)
                    m.d.sync += self.head.eq((self.head + 1) % 16)
                    m.next = "IDLE"

        return m
