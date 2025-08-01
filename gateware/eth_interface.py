import os

from amaranth            import *
from amaranth.lib.fifo import *

from amaranth.lib.wiring import connect
from amaranth_soc.wishbone.bus import Interface, Decoder, Arbiter
from amaranth_soc.memory import MemoryMap

from inject_data import InjectData
from handle_mac_int import HandleMacInt

from memory import WishboneRAM
from usb_in_to_fifo import USBInToFifo

__all__ = ["EthInterface"]
class EthInterface(Elaboratable):
    def __init__(self, simulation=False) :
        self.wb_clk = Signal()
        self.wb_rst = Signal()

        self.simulation = simulation
        self.leds = Signal(8)
        self.wb_mac_mux = Interface(addr_width = 32, data_width = 32, granularity = 8, 
                                    features = { "err" })
        self.wb_mux_mac = Interface(addr_width = 10, data_width = 32, granularity = 8, 
                                    features = { "err" })
        self.inject_data = InjectData(simulation) 

        self.handle_mac_int = HandleMacInt()

        depth = int(1540 / 4 * 16)
        if (simulation):
            depth = int(64 / 4 * 16)
        self.usb_in_fifo = (SyncFIFO(width = 32, depth = depth))
        self.usb_in_fifo_size = (SyncFIFO(width = 32, depth = 16))

        self.usb_in_to_fifo = USBInToFifo(simulation = simulation)

    def elaborate(self, platform):
        m = Module()

        if not self.simulation:
            prefix = "./ethmac/trunk/rtl/verilog/"
            paths = { "eth_clockgen.v", "eth_cop.v", "eth_crc.v", "eth_fifo.v", "eth_maccontrol.v",
                      "ethmac_defines.v", "eth_macstatus.v", "ethmac.v", "eth_miim.v", "eth_outputcontrol.v",
                      "eth_random.v", "eth_receivecontrol.v", "eth_registers.v", "eth_register.v",
                      "eth_rxaddrcheck.v", "eth_rxcounters.v", "eth_rxethmac.v", "eth_rxstatem.v",
                      "eth_shiftreg.v", "eth_spram_256x32.v", "eth_top.v", "eth_transmitcontrol.v",
                      "eth_txcounters.v", "eth_txethmac.v", "eth_txstatem.v", "eth_wishbone.v", "timescale.v" }

            for path in paths:
                content = open(prefix + path, "r")
                platform.add_file(prefix + path, content)

        mtxerr_pad = Signal()
        md_pad_o = Signal()
        md_padoe = Signal()
        mac_int = Signal()

        m.submodules.usb_in_fifo = in_fifo = self.usb_in_fifo
        m.submodules.usb_in_fifo_size = in_fifo_size = self.usb_in_fifo_size
        m.submodules.usb_in_to_fifo = usb_in_to_fifo = self.usb_in_to_fifo

        m.submodules.inject_data = inject_data = self.inject_data
        m.submodules.handle_mac_int = self.handle_mac_int

        m.d.comb += self.handle_mac_int.int.eq(mac_int)
        m.d.comb += [ 
                self.inject_data.irq_state.eq(self.handle_mac_int.irq_state),
                self.inject_data.new_irq.eq(self.handle_mac_int.new_irq),

                usb_in_to_fifo.fifo_w_rdy.eq(in_fifo.w_rdy), 
                in_fifo.w_en.eq(usb_in_to_fifo.fifo_w_en),
                in_fifo.w_data.eq(usb_in_to_fifo.fifo_w_data),
                usb_in_to_fifo.fifo_count_w_rdy.eq(in_fifo_size.w_rdy),
                in_fifo_size.w_en.eq(usb_in_to_fifo.fifo_count_w_en),
                in_fifo_size.w_data.eq(usb_in_to_fifo.fifo_count_w_data),

                in_fifo.r_en.eq(inject_data.usb_in_fifo_r_en),
                inject_data.usb_in_fifo_r_rdy.eq(in_fifo.r_rdy),
                inject_data.usb_in_fifo_r_data.eq(in_fifo.r_data),
                in_fifo_size.r_en.eq(inject_data.usb_in_fifo_size_r_en),
                inject_data.usb_in_fifo_size_r_rdy.eq(in_fifo_size.r_rdy),
                inject_data.usb_in_fifo_size_r_data.eq(in_fifo_size.r_data),
        ]

        if self.simulation:
            m.submodules.wb_ram = WishboneRAM(addr_width=10, 
                                              data_width = 32, 
                                              granularity = 8, 
                                              simulate = self.simulation)
        else:
            m.submodules.wb_ram = WishboneRAM(addr_width=16,
                                              data_width = 32, 
                                              granularity = 8, 
                                              simulate = self.simulation) # will be addr_width=15

        m.submodules.wb_arbiter = wb_arbiter = Arbiter(addr_width = 32, 
                                                       data_width = 32, 
                                                       granularity = 8, 
                                                       features = { "err" })
        m.submodules.wb_decoder = wb_decoder = Decoder(addr_width = 32, 
                                                       data_width = 32, 
                                                       granularity = 8, 
                                                       features = { "err" })

        self.wb_mux_mac.memory_map = MemoryMap(addr_width = 12, data_width = 8)
        wb_decoder.add(self.wb_mux_mac, addr = 0x00000000)
        wb_decoder.add(m.submodules.wb_ram.bus, addr = 0x10000000)

        wb_arbiter.add(self.handle_mac_int.get_bus())
        wb_arbiter.add(m.submodules.inject_data.get_bus())
        wb_arbiter.add(self.wb_mac_mux)
        
        m.d.comb += wb_arbiter.bus.connect(wb_decoder.bus)         

        if not self.simulation:
            phy = platform.request("phy")

            m.d.comb += [
                phy.resetn.eq(self.inject_data.phy_resetn),
                phy.mdio.o.eq(md_pad_o),
                phy.mdio.oe.eq(md_padoe)
            ]

            m.d.comb += self.leds.eq(self.wb_mac_mux.adr[0:8])

            m.submodules.mac = Instance("eth_top",
                i_wb_clk_i = self.wb_clk, # testbench shows 40MHz as a clock
                i_wb_rst_i = self.wb_rst, # active high!
                i_wb_dat_i = self.wb_mux_mac.dat_w,
                o_wb_dat_o = self.wb_mux_mac.dat_r,

                i_wb_adr_i = self.wb_mux_mac.adr, 
                i_wb_sel_i = self.wb_mux_mac.sel, 
                i_wb_we_i  = self.wb_mux_mac.we, 
                i_wb_cyc_i = self.wb_mux_mac.cyc, 
                i_wb_stb_i = self.wb_mux_mac.stb, 
                o_wb_ack_o = self.wb_mux_mac.ack, 
                o_wb_err_o = self.wb_mux_mac.err,
    
                o_m_wb_adr_o = self.wb_mac_mux.adr[0:30], 
                o_m_wb_sel_o = self.wb_mac_mux.sel, 
                o_m_wb_we_o  = self.wb_mac_mux.we,
                o_m_wb_dat_o = self.wb_mac_mux.dat_w, 
                i_m_wb_dat_i = self.wb_mac_mux.dat_r, 
                o_m_wb_cyc_o = self.wb_mac_mux.cyc,
                o_m_wb_stb_o = self.wb_mac_mux.stb, 
                i_m_wb_ack_i = self.wb_mac_mux.ack, 
                i_m_wb_err_i = self.wb_mac_mux.err,

                i_mtx_clk_pad_i = phy.tx_clk, 
                o_mtxd_pad_o = phy.txd, 
                o_mtxen_pad_o = phy.tx_en, 
                o_mtxerr_pad_o = mtxerr_pad,

                i_mrx_clk_pad_i = phy.rx_clk, 
                i_mrxd_pad_i = phy.rxd, 
                i_mrxdv_pad_i = phy.rx_dv, 
                i_mrxerr_pad_i = phy.rx_er, 

                i_mcoll_pad_i = phy.col, 
                i_mcrs_pad_i = phy.crs,

                o_mdc_pad_o = phy.mdc, 
                i_md_pad_i = phy.mdio.i, 
                o_md_pad_o = md_pad_o, 
                o_md_padoe_o = md_padoe,

                o_int_o = mac_int
            )

        return m
