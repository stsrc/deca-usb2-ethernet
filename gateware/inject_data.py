#!/usr/bin/env python3
#
# Copyright (c) 2022 Konrad Gotfryd <gotfrydkonrad@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0

import os

from amaranth import *
from amaranth.lib.fifo import *
from simple_ports_to_wb import SimplePortsToWb
from amlib.stream  import StreamInterface
from uart_transmitter import UARTTransmitter

__all__ = ["InjectData"]

class InjectData(Elaboratable):
    def __init__(self, simulation):
        self.simple_ports_to_wb = SimplePortsToWb()

        self.leds = Signal(8, reset = 0)
        self.wait_counter = Signal(26, reset = 0)
        self.phy_resetn = Signal(reset = 0)
        self.simulation = simulation

        self.head = Signal(4, reset = 0)
        self.tail = Signal(4, reset = 0)

        self.rd_head = Signal(4, reset = 0)
        self.rd_tail = Signal(4, reset = 0)

        self.int = Signal()
        self.rx_pkt_len = Signal(16, reset = 0)

        self.busy_counter = Signal(8, reset = 0)

        self.usb_in_fifo_r_en = Signal(reset = 0)
        self.usb_in_fifo_r_rdy = Signal()
        self.usb_in_fifo_r_data = Signal(32)

        self.usb_in_fifo_size_r_en = Signal(reset = 0)
        self.usb_in_fifo_size_r_rdy = Signal()
        self.usb_in_fifo_size_r_data = Signal(11)

        self.usb_out_fifo_w_en = Signal(reset = 0)
        self.usb_out_fifo_w_rdy = Signal()
        self.usb_out_fifo_w_data = Signal(32)

        self.usb_out_fifo_size_w_en = Signal(reset = 0)
        self.usb_out_fifo_size_w_rdy = Signal()
        self.usb_out_fifo_size_w_data = Signal(11)

        self.usb_out_dbg_fifo_w_en = Signal(reset = 0)
        self.usb_out_dbg_fifo_w_rdy = Signal()
        self.usb_out_dbg_fifo_w_data = Signal(32)

        self.usb_out_dbg_fifo_size_w_en = Signal(reset = 0)
        self.usb_out_dbg_fifo_size_w_rdy = Signal()
        self.usb_out_dbg_fifo_size_w_data = Signal(11)

        self.test_cnt = Signal(12)
        self.test_cnt_const = Signal(12)

        self.start_usb = Signal()
        self.uart = UARTTransmitter()

        self.debug_received = Signal(8, reset = 0)

        self.irq_state = Signal(32)
        self.new_irq = Signal()
    def get_bus(self):
        return self.simple_ports_to_wb.bus

    def elaborate(self, platform):
        m = Module()
        m.submodules.simple_ports_to_wb = self.simple_ports_to_wb
        m.submodules.uart = uart = self.uart

        m.d.sync += self.usb_out_fifo_w_en.eq(0)
        m.d.sync += self.usb_out_fifo_size_w_en.eq(0)

        m.d.sync += self.usb_in_fifo_r_en.eq(0)
        m.d.sync += self.usb_in_fifo_size_r_en.eq(0)

        m.d.sync += self.usb_out_dbg_fifo_w_en.eq(0)
        m.d.sync += self.usb_out_dbg_fifo_size_w_en.eq(0)

        payload = Signal(32, reset = 0)
        counter = Signal(16, reset = 0)
        tx_pkt_len = Signal(11, reset = 0)

        send_packet = Signal(reset = 0)
        clear_tx_desc = Signal(reset = 0)
        pass_data = Signal(reset = 0)
        rd_tmp = Signal(4, reset = 0)
        wr_tmp = Signal(4, reset = 0)

        debug_counter = Signal(16, reset = 0)
        
        m.d.sync += self.test_cnt_const.eq(2044)

        m.d.sync += uart.send.eq(0)

        m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(0)
        m.d.comb += self.simple_ports_to_wb.rd_strb_in.eq(0)
        m.d.comb += self.simple_ports_to_wb.data_in.eq(0)
        m.d.comb += self.simple_ports_to_wb.address_in.eq(0)

        m.d.sync += rd_tmp.eq(self.rd_tail)
        m.d.sync += wr_tmp.eq(self.tail)
       
        m.d.sync += self.leds.eq((rd_tmp << 4) | wr_tmp)

        with m.FSM(reset="RESET"):
            with m.State("RESET"):
                m.d.sync += self.wait_counter.eq(0)
                m.d.sync += self.phy_resetn.eq(0)
                m.d.sync += self.busy_counter.eq(0)
                m.next = "WAIT_BEFORE_START"

            with m.State("WAIT_BEFORE_START"):
                m.d.sync += self.wait_counter.eq(self.wait_counter + 1)

                if self.simulation:
                    m.d.sync += self.wait_counter.eq(30000000)

                with m.If (self.wait_counter == 30000000):
                    m.next = "WRITE_ETHMAC_INT_MASK"
                    m.d.sync += self.wait_counter.eq(0)

            with m.State("WRITE_ETHMAC_INT_MASK"):
                m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.comb += self.simple_ports_to_wb.data_in.eq(0x0000007f)
                m.d.comb += self.simple_ports_to_wb.address_in.eq(0x08 >> 2)
                with m.If(self.simple_ports_to_wb.wr_op_rdy_out):
                    m.next = "WRITE_ETHMAC_MAC_ADDR0"

            with m.State("WRITE_ETHMAC_MAC_ADDR0"):
                m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.comb += self.simple_ports_to_wb.data_in.eq(0x0a0a_0a0a)
                m.d.comb += self.simple_ports_to_wb.address_in.eq(0x40 >> 2)
                with m.If(self.simple_ports_to_wb.wr_op_rdy_out):
                    m.next = "WRITE_ETHMAC_MAC_ADDR1"

            with m.State("WRITE_ETHMAC_MAC_ADDR1"):
                m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.comb += self.simple_ports_to_wb.data_in.eq(0x0000_0a0a)
                m.d.comb += self.simple_ports_to_wb.address_in.eq(0x44 >> 2)
                with m.If(self.simple_ports_to_wb.wr_op_rdy_out):
                    m.next = "WRITE_ETHMAC_MODER"
                    m.d.sync += self.phy_resetn.eq(1)

            with m.State("WRITE_ETHMAC_MODER"):
                m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.comb += self.simple_ports_to_wb.data_in.eq(0x0000a003 | (0x01 << 10)) # crc add enabled
                m.d.comb += self.simple_ports_to_wb.address_in.eq(0x00 >> 2)
                with m.If(self.simple_ports_to_wb.wr_op_rdy_out):
                    m.next = "WRITE_ETHMAC_RX_BUF_DESC_0"

            with m.State("WRITE_ETHMAC_RX_BUF_DESC_0"):
                m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(1)
                if self.simulation:
                    m.d.comb += self.simple_ports_to_wb.data_in.eq(0x1000_0000 + 
                                                                  (16 * (16 + self.rd_head)))
                else:
                    m.d.comb += self.simple_ports_to_wb.data_in.eq(0x1000_0000 + 
                                                                   (2048 * (16 + self.rd_head)))
                m.d.comb += self.simple_ports_to_wb.address_in.eq((0x400 + 
                                                                  (64 + self.rd_head) * 8 + 4) >> 2)
                with m.If(self.simple_ports_to_wb.wr_op_rdy_out):
                    m.next = "WRITE_ETHMAC_RX_BUF_DESC_1"

            with m.State("WRITE_ETHMAC_RX_BUF_DESC_1"):
                m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(1)
                with m.If(self.rd_head != 15):
                    m.d.comb += self.simple_ports_to_wb.data_in.eq(0x0000c000)
                with m.Else():
                    m.d.comb += self.simple_ports_to_wb.data_in.eq(0x0000e000)
                m.d.comb += self.simple_ports_to_wb.address_in.eq((0x400 + 
                                                                  (64 + self.rd_head) * 8) >> 2)
                with m.If(self.simple_ports_to_wb.wr_op_rdy_out):
                    with m.If(((self.rd_head + 1) % 16) != self.rd_tail): 
                        m.d.sync += self.rd_head.eq((self.rd_head + 1) % 16)
                        m.next = "WRITE_ETHMAC_RX_BUF_DESC_0"
                    with m.Else():
                        m.next = "WRITE_ETHMAC_TX_BUF_DESC_0"

            with m.State("WRITE_ETHMAC_TX_BUF_DESC_0"):
                m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(1)
                if self.simulation:
                    m.d.comb += self.simple_ports_to_wb.data_in.eq(0x1000_0000 + (16 * self.head))
                else:
                    m.d.comb += self.simple_ports_to_wb.data_in.eq(0x1000_0000 + (2048 * self.head))

                m.d.comb += self.simple_ports_to_wb.address_in.eq((0x400 + self.head * 8 + 4) >> 2)
                with m.If(self.simple_ports_to_wb.wr_op_rdy_out):
                    m.d.sync += self.head.eq((self.head + 1) % 16)
                    with m.If(((self.head + 1) % 16) == 0):
                        m.next = "IDLE"
                    with m.Else():
                        m.next = "WRITE_ETHMAC_TX_BUF_DESC_0"

            with m.State("IDLE"):
                dummy_send = 0
                if dummy_send:
                    m.d.sync += self.usb_out_fifo_w_en.eq(0)
                    m.d.sync += self.usb_out_fifo_size_w_en.eq(0)
                    m.d.sync += self.usb_in_fifo_r_en.eq(1)
                    m.d.sync += self.usb_in_fifo_size_r_en.eq(1)
                    with m.If(self.start_usb):
                        m.next = "TEST_SEND_PREP"
                else:
                    m.d.sync += self.usb_out_dbg_fifo_w_data.eq(1 << 31 | self.head << 24 | self.tail << 16)
                    m.d.sync += self.usb_out_dbg_fifo_size_w_data.eq(4)
                    m.d.sync += self.usb_out_dbg_fifo_w_en.eq(1)
                    m.d.sync += self.usb_out_dbg_fifo_size_w_en.eq(1)

                    with m.If(send_packet):
                        m.d.sync += send_packet.eq(0)
                        m.next = "GET_RX_PACKET_LENGTH"
                    with m.Elif(clear_tx_desc):
                        m.d.sync += clear_tx_desc.eq(0)
                        m.next = "CLEAR_TX_DESC"
                    with m.Elif((self.usb_in_fifo_r_rdy == 1) & 
                              (self.usb_in_fifo_size_r_rdy == 1) &
                              ((self.head + 1) % 16 != self.tail)):
                        m.d.sync += tx_pkt_len.eq(self.usb_in_fifo_size_r_data)
                        m.d.sync += counter.eq(0)
                        m.d.sync += self.usb_in_fifo_size_r_en.eq(1)
                        m.next = "WRITE_DATA_PREPARE"
           
            with m.State("CLEAR_TX_DESC"):
                m.d.comb += self.simple_ports_to_wb.rd_strb_in.eq(1)
                m.d.comb += self.simple_ports_to_wb.address_in.eq((0x400 + self.tail * 8) >> 2)
                with m.If(self.simple_ports_to_wb.rd_op_rdy_out):
                    m.d.comb += self.simple_ports_to_wb.rd_strb_in.eq(0)
                    with m.If((self.simple_ports_to_wb.rd_data_out & 0x8000) == 0):
                        m.d.sync += self.tail.eq((self.tail + 1) % 16)
                        with m.If(((self.tail + 1) % 16) != self.head):
                            m.next = "CLEAR_TX_DESC_WAIT"
                        with m.Else():
                            m.next = "IDLE"
                    with m.Else():
                        m.next = "IDLE"

            with m.State("CLEAR_TX_DESC_WAIT"):
                m.next = "CLEAR_TX_DESC"

            with m.State("GET_RX_PACKET_LENGTH"):
                m.d.comb += self.simple_ports_to_wb.rd_strb_in.eq(1)
                m.d.comb += self.simple_ports_to_wb.data_in.eq(0)
                m.d.comb += self.simple_ports_to_wb.address_in.eq((0x400 + 
                                                                  (64 + self.rd_tail) * 8) >> 2)
                with m.If(self.simple_ports_to_wb.rd_op_rdy_out):
                    m.d.comb += self.simple_ports_to_wb.rd_strb_in.eq(0)
                    m.d.sync += self.rx_pkt_len.eq(self.simple_ports_to_wb.rd_data_out >> 16)
                    m.d.sync += counter.eq(0)
                    with m.If(((self.simple_ports_to_wb.rd_data_out >> 16) != 0) &
                              (((self.simple_ports_to_wb.rd_data_out >> 15) & 1) == 0)):
                        m.next = "GET_PACKET_DATA"
                    with m.Else():
                        m.next = "IDLE"

            with m.State("TEST_SEND_PREP"):
                m.d.sync += self.test_cnt.eq(self.test_cnt_const)
                with m.If(self.usb_out_fifo_w_rdy):
                    m.next = "TEST_SEND"

            with m.State("TEST_SEND"):
                with m.If(self.test_cnt != 0):
                    with m.If(self.usb_out_fifo_w_rdy):
                        m.d.sync += self.test_cnt.eq(self.test_cnt - 4)
                        m.d.sync += self.usb_out_fifo_w_data.eq(0x10111213)
                        m.d.sync += self.usb_out_fifo_w_en.eq(1)
                        with m.If(self.test_cnt == 4):
                            m.d.sync += self.usb_out_fifo_size_w_en.eq(1)
                            m.d.sync += self.usb_out_fifo_size_w_data.eq(self.test_cnt_const)
                            m.next = "IDLE"
                with m.Else():
                    m.d.sync += self.usb_out_fifo_w_en.eq(0)
                    m.d.sync += self.usb_out_fifo_size_w_en.eq(0)

            with m.State("GET_PACKET_DATA"):
                m.d.sync += self.usb_out_fifo_w_en.eq(0)

                m.d.comb += self.simple_ports_to_wb.rd_strb_in.eq(1)
                if self.simulation:
                    m.d.comb += self.simple_ports_to_wb.address_in.eq(0x0400_0000 + ((16 * (16 + self.rd_tail) + counter) >> 2))
                else:
                    m.d.comb += self.simple_ports_to_wb.address_in.eq(0x0400_0000 + ((2048 * (16 + self.rd_tail) + counter) >> 2))
                with m.If(self.simple_ports_to_wb.rd_op_rdy_out):
                    m.d.comb += self.simple_ports_to_wb.rd_strb_in.eq(0)
                    m.d.sync += self.usb_out_fifo_w_data.eq(self.simple_ports_to_wb.rd_data_out)
                    m.d.sync += pass_data.eq(1)
                with m.If(pass_data):
                    # TODO why wr operations do not need clearing?
                    m.d.comb += self.simple_ports_to_wb.rd_strb_in.eq(0) 
                with m.If((self.simple_ports_to_wb.rd_op_rdy_out | pass_data) & 
                        self.usb_out_fifo_w_rdy & self.usb_out_fifo_size_w_rdy):
                    m.d.sync += pass_data.eq(0)
                    m.d.sync += self.usb_out_fifo_w_en.eq(1)
                    m.d.sync += counter.eq(counter + 4)
                    with m.If(counter + 4 < self.rx_pkt_len):
                        m.next = "GET_PACKET_DATA"
                    with m.Else():
                        m.next = "RESET_ETHMAC_RX_BUF_DESC_1"
                        m.d.sync += self.usb_out_fifo_size_w_data.eq(self.rx_pkt_len)
                        m.d.sync += self.usb_out_fifo_size_w_en.eq(1)

            with m.State("RESET_ETHMAC_RX_BUF_DESC_1"):
                m.d.sync += self.usb_out_fifo_w_en.eq(0)
                m.d.sync += self.usb_out_fifo_size_w_en.eq(0)
                m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(1)
                with m.If(self.rd_tail != 15):
                    m.d.comb += self.simple_ports_to_wb.data_in.eq(0x0000c000)
                with m.Else():
                    m.d.comb += self.simple_ports_to_wb.data_in.eq(0x0000e000)
                m.d.comb += self.simple_ports_to_wb.address_in.eq((0x400 + 
                                                                  (64 + self.rd_tail) * 8) >> 2)
                with m.If(self.simple_ports_to_wb.wr_op_rdy_out):
                        m.d.sync += self.rd_tail.eq((self.rd_tail + 1) % 16) 
                        m.next = "GET_RX_PACKET_LENGTH"

            with m.State("WRITE_DATA_PREPARE"):
                m.d.sync += self.usb_in_fifo_size_r_en.eq(0)
                with m.If(self.usb_in_fifo_r_rdy):
                    m.d.sync += payload.eq(self.usb_in_fifo_r_data)
                    m.d.sync += self.usb_in_fifo_r_en.eq(1)

                    m.next = "WRITE_DATA"

            #TODO: check what happens if we have to wait for wb to end transaction...
            with m.State("WRITE_DATA"):

                m.d.sync += self.usb_in_fifo_r_en.eq(0)
                m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(1)
                m.d.comb += self.simple_ports_to_wb.data_in.eq(payload)
                if self.simulation:
                    m.d.comb += self.simple_ports_to_wb.address_in.eq(0x0400_0000 + ((16 * self.head + counter) >> 2))
                else:
                    m.d.comb += self.simple_ports_to_wb.address_in.eq(0x0400_0000 + ((2048 * self.head + counter) >> 2))
                with m.If(self.simple_ports_to_wb.wr_op_rdy_out):
                    m.d.sync += counter.eq(counter + 4)
                    with m.If(counter + 4 < tx_pkt_len):
                        m.next = "WRITE_DATA_PREPARE"
                    with m.Else():
                        m.next = "WRITE_ETHMAC_TX_BUF_DESC_1"

            with m.State("WRITE_ETHMAC_TX_BUF_DESC_1"):
                m.d.sync += debug_counter.eq(0)
                m.d.comb += self.simple_ports_to_wb.wr_strb_in.eq(1)
                with m.If(self.head != 15):
                    m.d.comb += self.simple_ports_to_wb.data_in.eq((tx_pkt_len << 16) | 0xc000)
                with m.Else():
                    m.d.comb += self.simple_ports_to_wb.data_in.eq((tx_pkt_len << 16) | 0xe000)
                m.d.comb += self.simple_ports_to_wb.address_in.eq((0x400 + self.head * 8) >> 2)
                with m.If(self.simple_ports_to_wb.wr_op_rdy_out):
                    m.d.sync += counter.eq(0)
                    m.d.sync += self.head.eq((self.head + 1) % 16)
                    m.next = "IDLE"

        with m.If(self.new_irq):
#            m.d.sync += self.leds.eq(0b10101010)
            with m.If(self.irq_state & 0b00000011):
                m.d.sync += clear_tx_desc.eq(1)
            with m.If(self.irq_state & 0b00001100):
                m.d.sync += send_packet.eq(1)
            with m.If(self.irq_state & 0b00010000):
                m.d.sync += self.busy_counter.eq(self.busy_counter + 1)


        return m
