#
# This file has been adopted from the LUNA project
#
# Copyright (c) 2020 Great Scott Gadgets <info@greatscottgadgets.com>
# SPDX-License-Identifier: BSD-3-Clause

import math

from enum      import Enum
from functools import reduce
from operator  import or_

from amaranth         import Elaboratable, Record, Module, Cat, Array, Repl, Signal, Instance, ClockSignal
from amaranth_soc     import wishbone, memory

#from mem       import Memory
from amaranth import Memory

class WishboneRAM(Elaboratable):
    """ Simple Wishbone-connected RAM. """

    @staticmethod
    def _initialization_value(value, data_width, granularity, byteorder):
        """ Converts a provided value into a valid Memory-initializer array.

        Parameters should match those provied to __init__
        """

        # If this is a filename, read the file's contents before processing.
        if isinstance(value, str):
            with open(value, "rb") as f:
                value = f.read()

        # If we don't have bytes, read this direction.
        if not isinstance(value, bytes):
            return value

        bytes_per_chunk = data_width // granularity

        words = (value[pos:pos + bytes_per_chunk] for pos in range(0, len(value), bytes_per_chunk))
        return [int.from_bytes(word, byteorder=byteorder) for word in words]

    def __init__(self, *, addr_width, data_width=32, granularity=8, init=None,
            read_only=False, byteorder="little", name="ram", simulate):
        """
        Parameters:
            addr_width  -- The -bus- address width for the relevant memory. Determines the size
                           of the memory.
            data_width  -- The width of each memory word.
            granularity -- The number of bits of data per each address.
            init        -- Optional. The initial value of the relevant memory. Should be an array of integers, a
                           filename, or a bytes-like object. If bytes are provided, the byteorder parametera allows
                           control over their interpretation. If a filename is provided, this filename will not be read
                           until elaboration; this allows reading the file to be deferred until the very last minute in
                           e.g. systems that generate the relevant file during build.
            read_only   -- If true, this will ignore writes to this memory, so it effectively
                           acts as a ROM fixed to its initialization value.
            byteorder   -- Sets the byte order of the initializer value. Ignored unless a bytes-type initializer is provided.
            name        -- A descriptive name for the given memory.
        """

        self.name          = name
        self.read_only     = read_only
        self.data_width    = data_width
        self.initial_value = init
        self.byteorder     = byteorder

        # Our granularity determines how many bits of data exist per single address.
        # Often, this isn't the same as our data width; which means we'll wind up with
        # two different address widths: a 'local' one where each address corresponds to a
        # data value in memory; and a 'bus' one where each address corresponds to a granularity-
        # sized chunk of memory.
        self.granularity   = granularity
        self.bus_addr_width = addr_width

        # Our bus addresses are more granular than our local addresses.
        # Figure out how many more bits exist in our bus addresses, and use
        # that to figure out our local bus size.
        self.bytes_per_word   = data_width // granularity
        self.bits_in_bus_only = int(math.log2(self.bytes_per_word))
        self.local_addr_width = self.bus_addr_width - self.bits_in_bus_only

        # Create our wishbone interface.
        # Note that we provide the -local- address to the Interface object; as it automatically factors
        # in our extra bits as it computes our granularity.
        self.bus = wishbone.Interface(addr_width=self.local_addr_width, data_width=data_width, granularity=granularity)
        self.bus.memory_map = memory.MemoryMap(addr_width=self.bus_addr_width, data_width=granularity)
        self.bus.memory_map._frozen = False
        self.bus.memory_map.add_resource(self, name=name, size=2 ** addr_width)

        self.simulate = simulate

        self.counter = Signal(2)

    def elaborate(self, platform):
        m = Module()

        local_address_bits = self.bus.adr[:self.local_addr_width]
        ram_cs = Signal(reset = 0)
        ram_we = Signal(reset = 0)
        ram_oe = Signal(reset = 0)
        ram_data_in = Signal(self.data_width, reset = 0)
        ram_data_out = Signal(self.data_width)
        data_ready = Signal(reset = 0)
        flag = Signal(1, reset = 0)
        if not self.simulate:
            file="./synchr_memory.vhd"
            content = open(file, "r")
            platform.add_file(file, content)
            memory = Instance("ram_sp_ar_aw",
                i_clk = ClockSignal("usb"),
                i_address = local_address_bits,
                i_dat_in = ram_data_in,
                o_dat_out = ram_data_out,
                i_cs = ram_cs,
                i_we = ram_we,
                i_oe = ram_oe
            )
            m.submodules.memory = memory
            m.d.comb += ram_we.eq(
                    self.bus.cyc & 
                    self.bus.stb & 
                    self.bus.we)
            m.d.comb += ram_cs.eq(1)
            m.d.comb += ram_oe.eq(1)
            m.d.comb += ram_data_in.eq(self.bus.dat_w)
            m.d.comb += self.bus.dat_r.eq(ram_data_out)
            with m.If(self.bus.cyc & self.bus.stb):
                m.d.sync += flag.eq(1)
            with m.If(flag):
                m.d.sync += flag.eq(0)
            m.d.comb += self.bus.ack.eq(flag)
        else:
            # Create the the memory used to store our data.
            memory_depth = 2 ** self.local_addr_width
            memory = Memory(width=self.data_width, depth=memory_depth, name=self.name, simulate=self.simulate)
            # Grab a reference to the bits of our Wishbone bus that are relevant to us.
    
            # Create a read port, and connect it to our Wishbone bus.
            m.submodules.rdport = read_port = memory.read_port()
            m.d.sync += [
                read_port.addr.eq(local_address_bits),
                self.bus.dat_r.eq(read_port.data)
            ]
    
            # If this is a read/write memory, create a write port, as well.
            if not self.read_only:
                m.submodules.wrport = write_port = memory.write_port(granularity=self.granularity)
                m.d.sync += [
                    write_port.addr.eq(local_address_bits),
                    write_port.data.eq(self.bus.dat_w)
                ]
    
                # Generate the write enables for each of our words.
                for i in range(self.bytes_per_word):
                    m.d.sync += write_port.en[i].eq(
                        self.bus.cyc &    # Transaction is active.
                        self.bus.stb &    # Valid data is being provided.
                        self.bus.we  &    # This is a write.
                        self.bus.sel[i]   # The relevant setion of the datum is being targeted.
                    )
    
            m.d.sync += self.bus.ack.eq(0)
            with m.If((self.bus.cyc == 1) & (self.bus.stb == 1)):
                 m.d.sync += self.bus.ack.eq(1)

        return m

