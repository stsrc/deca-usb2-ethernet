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

#include <linux/usb.h>

static const char driver_name [] = "deca_eth_interface";

static const struct usb_device_id deca_ethintf_table[] = {
	{USB_DEVICE(0x1209, 0x4711)},
	{}
};

MODULE_DEVICE_TABLE(usb, deca_ethintf_table);

struct deca_ethintf {
	struct net_device *netdev;
};

static int deca_ethintf_open(struct net_device *netdev)
{
	return -ENOMEM;
}

static int deca_ethintf_close(struct net_device *netdev)
{
	return 0;
}

static const struct net_device_ops  deca_ethintf_netdev_ops = {
	.ndo_open = deca_ethintf_open,
	.ndo_stop = deca_ethintf_close
};

static int deca_ethintf_probe(struct usb_interface *intf,
                              const struct usb_device_id *id)
{
	struct net_device *netdev;
	struct deca_ethintf *deca;

	printk(KERN_INFO "%s():%d", __FUNCTION__, __LINE__);

	netdev = alloc_etherdev(sizeof(struct deca_ethintf));
	if (!netdev) {
		printk(KERN_ERR "%s():%d, alloc_etherdev() failed!",
		       __FUNCTION__, __LINE__);
		return -ENOMEM;
	}

	deca = netdev_priv(netdev);
	deca->netdev = netdev;

	netdev->netdev_ops = &deca_ethintf_netdev_ops;

	return 0;
}

static struct usb_driver deca_ethintf = {
	.name = driver_name,
	.id_table = deca_ethintf_table,
	.probe = deca_ethintf_probe
};

module_usb_driver(deca_ethintf);

MODULE_LICENSE("GPL");

