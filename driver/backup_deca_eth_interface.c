/*
 * Copyright (C) 2022 Konrad Gotfryd
 *
 * Basing on rtl8150.c
 *
 */

#include <linux/module.h>
#include <linux/netdevice.h>
#include <linux/etherdevice.h>
#include <linux/mii.h>
#include <linux/slab.h>
#include <linux/usb.h>
#include <linux/usb/usbnet.h>

static const char driver_name [] = "deca_eth_interface";

static const struct ethtool_ops test_ethtool_ops = {0};

static int test_bind(struct usbnet *dev, struct usb_interface *intf) {
	pr_info("---> bind <---\n");
	u8 node_id[ETH_ALEN] = {0x0a, 0x0a, 0x0a, 0x0a, 0x0a, 0x0a};
	dev->net->ethtool_ops = &test_ethtool_ops;
        dev_addr_set(dev->net, node_id);
	return usbnet_get_endpoints(dev, intf);
}

static const struct driver_info deca_usb_info = {
	.description = "USB Ethernet 100M FPGA device",
	.flags = FLAG_ETHER | FLAG_NO_SETINT,
	.data = 0,
	.bind = test_bind
};

static const struct usb_device_id deca_ethintf_table[] = {
	{USB_DEVICE(0x1209, 0x4711),
	 .driver_info = (kernel_ulong_t) &deca_usb_info },
	{}
};

MODULE_DEVICE_TABLE(usb, deca_ethintf_table);


static int deca_ethintf_suspend(struct usb_interface *intf,
				pm_message_t message)
{
	return 0;
}

static struct usb_driver deca_ethintf = {
	.name = driver_name,
	.id_table = deca_ethintf_table,
	.probe = usbnet_probe,
	.disconnect = usbnet_disconnect,
	.suspend = deca_ethintf_suspend
};

module_usb_driver(deca_ethintf);

MODULE_LICENSE("GPL");

