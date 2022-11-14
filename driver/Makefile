ifneq ($(KERNELRELEASE),)
	obj-m := deca_eth_interface.o 

else
	KERNELDIR ?= /lib/modules/$(shell uname -r)/build
	PWD := $(shell pwd)

default:
	$(MAKE) -C $(KERNELDIR) M=$(PWD) modules

clean:
	rm -f *.o *.ko *.mod.c modules.order Module.symvers

endif
