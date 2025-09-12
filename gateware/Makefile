all:
	. venv/bin/activate && \
		pip install amaranth-yosys==0.40.0.0.post100 && \
		time python3 deca_usb2_eth_interface.py --keep-files

inject_data-bench:
	. venv/bin/activate && \
		time python3 inject_data-bench.py
	gtkwave ./inject_data.vcd

eth_interface-bench:
	. venv/bin/activate && \
		time python3 eth_interface-bench.py
	gtkwave ./eth_interface.vcd

simple_ports_to_wb-bench:
	. venv/bin/activate && \
		time python3 simple_ports_to_wb-bench.py
	gtkwave ./simple_ports_to_wb.vcd

led_multiplexer-bench:
	. venv/bin/activate && \
		time python3 led_multiplexer-bench.py
	gtkwave ./led_multiplexer.vcd

memory-bench:
	. venv/bin/activate && \
		time python3 memory-bench.py
	gtkwave ./memory.vcd

test-fifo:
	. venv/bin/activate && \
		time python3 test_fifo.py
	gtkwave ./test_fifo.vcd

sptw_memory-bench:
	. venv/bin/activate && \
		time python3 sptw_memory-bench.py
	gtkwave ./sptw_memory.vcd

load:
	quartus_pgm -m jtag -c "Arrow MAX 10 DECA" -o 'p;build/top.sof@1'

init_env:
	python3 -m venv venv && \
		. venv/bin/activate && \
		pip3 install -r requirements.txt
