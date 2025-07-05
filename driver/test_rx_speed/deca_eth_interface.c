/*
 * Copyright (C) 2022 Konrad Gotfryd
 *
 * Basing on rtl8150.c
 *
 */

#include <linux/module.h>
#include <linux/slab.h>
#include <linux/usb.h>
#include <linux/timekeeping.h>

static const char driver_name [] = "deca_eth_interface";

static const struct usb_device_id deca_ethintf_table[] = {
	{USB_DEVICE(0x1209, 0x4711)},
	{}
};

MODULE_DEVICE_TABLE(usb, deca_ethintf_table);

#define POOL_SIZE 4

#define OUR_BUFFER_SIZE 2048

struct deca_ethintf {
	struct usb_device *usbdev;
	struct urb *rx_urb, *tx_urb;
	char *our_buffer;
	u64 received_count;
	u64 start_time;
	int print;
};

static int alloc_all_urbs(struct deca_ethintf *dev)
{
	dev->rx_urb = usb_alloc_urb(0, GFP_KERNEL);
	if (!dev->rx_urb)
		return 0;

	dev->tx_urb = usb_alloc_urb(0, GFP_KERNEL);
	if (!dev->tx_urb) {
		usb_free_urb(dev->rx_urb);
		return 0;
	}
	return 1;
}

static void free_all_urbs(struct deca_ethintf *dev)
{
        usb_free_urb(dev->rx_urb);
        usb_free_urb(dev->tx_urb);
}

static void unlink_all_urbs(struct deca_ethintf *dev)
{
        usb_kill_urb(dev->rx_urb);
        usb_kill_urb(dev->tx_urb);
}

static void read_bulk_callback(struct urb *urb)
{
	struct deca_ethintf *dev;
	if (!urb) {
		return;
	}

	dev = urb->context;
	if (!dev) {
		printk(KERN_ERR "%s():%d\n", __FUNCTION__, __LINE__);
		return;
	}

	int status = urb->status;
	if (!dev->start_time) {
		dev->start_time = ktime_get_ns();
	} else {
		dev->print = (dev->print + 1) % 1000;
		dev->received_count += urb->actual_length;
		if (!dev->print) {
			u64 time_delta = (ktime_get_ns() - dev->start_time) / 1000;
			if (time_delta) {
				pr_info("---> %s():%d: %llu B: %llu us\n",
					__func__, __LINE__,
					dev->received_count, time_delta);
				dev->start_time = ktime_get_ns();
				dev->received_count = 0;
			}
		}
	}

	switch(status) {
	case 0:
		break;
	case -ENOENT:
		pr_info("%s():%d\n", __func__, __LINE__);
		return;
	default:
		pr_info("%s():%d\n", __func__, __LINE__);
		goto goon;
	}


	if (!dev->rx_urb || !dev->usbdev) {
		pr_info("dupa\n");
		return;
	}
goon:
        usb_fill_bulk_urb(dev->rx_urb, dev->usbdev, usb_rcvbulkpipe(dev->usbdev, 2),
                      dev->our_buffer, OUR_BUFFER_SIZE, read_bulk_callback, dev);
        if ((status = usb_submit_urb(dev->rx_urb, GFP_ATOMIC))) {
		pr_info("---> %s():%d <---\n", __func__, __LINE__);
        }
}



static int deca_ethintf_probe(struct usb_interface *intf,
                              const struct usb_device_id *id)
{
	int res = 0;
	struct deca_ethintf *deca = kmalloc(sizeof(struct deca_ethintf), GFP_KERNEL);
	struct usb_device *usbdev = interface_to_usbdev(intf);

	deca->start_time = 0;
	deca->received_count = 0;
	deca->print = 0;

	printk(KERN_INFO "%s():%d\n", __FUNCTION__, __LINE__);

	deca->usbdev = usbdev;

	deca->our_buffer = kmalloc(OUR_BUFFER_SIZE, GFP_KERNEL);

	if (!alloc_all_urbs(deca)) {
		dev_err(&intf->dev, "out of memory\n");
		return -ENOMEM;
	}


        usb_set_intfdata(intf, deca);

        usb_fill_bulk_urb(deca->rx_urb, deca->usbdev, usb_rcvbulkpipe(deca->usbdev, 2),
                      deca->our_buffer, OUR_BUFFER_SIZE, read_bulk_callback, deca);
        if ((res = usb_submit_urb(deca->rx_urb, GFP_KERNEL))) {
		pr_info("--> %s():%d <--\n", __func__, __LINE__);
        }

	return res;
}

static void deca_ethintf_disconnect(struct usb_interface *intf)
{
	pr_info("--> %s():%d <--\n", __func__, __LINE__);
	struct deca_ethintf *deca = usb_get_intfdata(intf);
	usb_set_intfdata(intf, NULL);
	if (deca) {
		unlink_all_urbs(deca);
		free_all_urbs(deca);
		kfree(deca->our_buffer);
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

