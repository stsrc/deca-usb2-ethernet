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

static const char driver_name [] = "deca_eth_interface";

static const struct usb_device_id deca_ethintf_table[] = {
	{USB_DEVICE(0x1209, 0x4711)},
	{}
};

MODULE_DEVICE_TABLE(usb, deca_ethintf_table);

struct deca_ethintf {
	struct net_device *netdev;
	struct usb_device *usbdev;
};

#define DECA_REQT_READ       0xc0
#define DECA_REQT_WRITE      0x40
#define DECA_REQ_GET_REGS    0x05
#define DECA_REQ_SET_REGS    0x05

static int get_registers(struct deca_ethintf *dev,
			 u16 indx,
			 u16 size,
			 void *data)
{
        void *buf;
        int ret;

        buf = kmalloc(size, GFP_NOIO);
        if (!buf)
                return -ENOMEM;

        ret = usb_control_msg(dev->usbdev, usb_rcvctrlpipe(dev->usbdev, 0),
                              DECA_REQ_GET_REGS, DECA_REQT_READ,
                              indx, 0, buf, size, 500);
        if (ret > 0 && ret <= size)
                memcpy(data, buf, ret);
        kfree(buf);
        return ret;
}

static int set_registers(struct deca_ethintf *dev,
			 u16 indx,
			 u16 size,
			 const void *data)
{
        void *buf;
        int ret;

        buf = kmemdup(data, size, GFP_NOIO);
        if (!buf)
                return -ENOMEM;

        ret = usb_control_msg(dev->usbdev, usb_sndctrlpipe(dev->usbdev, 0),
                              DECA_REQ_SET_REGS, DECA_REQT_WRITE,
                              indx, 0, buf, size, 500);
        kfree(buf);
        return ret;
}



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
	uint8_t val;
	int ret;
	struct usb_device *usbdev = interface_to_usbdev(intf);

	printk(KERN_INFO "%s():%d\n", __FUNCTION__, __LINE__);

	netdev = alloc_etherdev(sizeof(struct deca_ethintf));
	if (!netdev) {
		printk(KERN_ERR "%s():%d, alloc_etherdev() failed!",
		       __FUNCTION__, __LINE__);
		return -ENOMEM;
	}

	deca = netdev_priv(netdev);
	deca->usbdev = usbdev;
	deca->netdev = netdev;

	netdev->netdev_ops = &deca_ethintf_netdev_ops;

	val = 0b00001111;

	ret = set_registers(deca, 0, 1, &val);
	printk(KERN_INFO "---> set_registers = %d <---\n", ret);
	ret = get_registers(deca, 0, 1, &val);
	printk(KERN_INFO "---> get_registers = %d <---\n", ret);
	printk(KERN_INFO "---> val = 0x%02x <---\n", val);

	return 0;
}

static void deca_ethintf_disconnect(struct usb_interface *intf)
{
	struct deca_ethintf *deca = usb_get_intfdata(intf);
	if (deca) {
		free_netdev(deca->netdev);
	}
}

static int deca_ethintf_suspend(struct usb_interface *intf,
				pm_message_t message)
{
	return 0;
}

static struct usb_driver deca_ethintf = {
	.name = driver_name,
	.id_table = deca_ethintf_table,
	.probe = deca_ethintf_probe,
	.disconnect = deca_ethintf_disconnect,
	.suspend = deca_ethintf_suspend
};

module_usb_driver(deca_ethintf);

MODULE_LICENSE("GPL");

