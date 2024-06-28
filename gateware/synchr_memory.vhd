-------------------------------------------------------
-- Design Name : ram_sp_ar_aw
-- File Name   : ram_sp_ar_aw.vhd
-- Function    : Asynchronous read write RAM 
-- Coder       : Deepak Kumar Tala (Verilog)
-- Translator  : Alexander H Pham (VHDL)
-------------------------------------------------------
library ieee;
    use ieee.std_logic_1164.all;
    use ieee.std_logic_unsigned.all;

entity ram_sp_ar_aw is
    generic (
        DATA_WIDTH :integer := 32;
        ADDR_WIDTH :integer := 14
    );
    port (
        clk     :in std_logic;
        address :in    std_logic_vector (ADDR_WIDTH-1 downto 0); -- address Input
        dat_in  :in std_logic_vector (DATA_WIDTH-1 downto 0); -- data in
        dat_out :out std_logic_vector (DATA_WIDTH-1 downto 0); -- data out
        cs      :in    std_logic;                                -- Chip Select
        we      :in    std_logic;                                -- Write Enable/Read Enable
        oe      :in    std_logic                                 -- Output Enable
    );
end entity;
architecture rtl of ram_sp_ar_aw is
   ----------------Internal variables----------------
    constant RAM_DEPTH :integer := 2**ADDR_WIDTH;

    signal data :std_logic_vector (DATA_WIDTH-1 downto 0);

    type RAM is array (integer range <>)of std_logic_vector (DATA_WIDTH-1 downto 0);
    signal mem : RAM (0 to RAM_DEPTH-1);
begin

   ----------------Code Starts Here------------------
   -- Tri-State Buffer control
    dat_out <= data when (cs = '1' and oe = '1' and we = '0') else (others=>'Z');

   -- Memory Write Block
    MEM_WRITE:
    process (clk, address, dat_in, cs, we) begin
       if rising_edge(clk) then
	       if (cs = '1' and we = '1') then
		   mem(conv_integer(address)) <= dat_in;
	       end if;
       end if;
    end process;

   -- Memory Read Block
    MEM_READ:
    process (clk, address, cs, we, oe, mem) begin
	if rising_edge(clk) then
		if (cs = '1' and we = '0' and oe = '1')  then
	             data <= mem(conv_integer(address));
		end if;
	end if;
    end process;

end architecture;
