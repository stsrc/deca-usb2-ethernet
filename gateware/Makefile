all:
	. venv/bin/activate
	time python3 deca_usb2_eth_interface.py --dry-run


eth_interface-bench:
	. venv/bin/activate  && time python3 eth_interface-bench.py
	gtkwave ./eth_interface.vcd
