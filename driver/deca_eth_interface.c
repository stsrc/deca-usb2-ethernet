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
	struct urb *rx_urb, *tx_urb, *intr_urb;
	u8 *intr_buff;
	int intr_interval;
	struct sk_buff *tx_skb, *rx_skb;
	struct sk_buff *rx_skb_pool[4];
	struct tasklet_struct tl;
	spinlock_t rx_pool_lock;
};

#define DECA_REQT_READ       0xc0
#define DECA_REQT_WRITE      0x40
#define DECA_REQ_GET_REGS    0x05
#define DECA_REQ_SET_REGS    0x05

#define INTBUFSIZE 8
#define DECA_MTU 1540

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

        dev->intr_urb = usb_alloc_urb(0, GFP_KERNEL);
        if (!dev->intr_urb) {
                usb_free_urb(dev->rx_urb);
                usb_free_urb(dev->tx_urb);
                return 0;
        }

	return 1;
}

static void free_all_urbs(struct deca_ethintf *dev)
{
        usb_free_urb(dev->rx_urb);
        usb_free_urb(dev->tx_urb);
        usb_free_urb(dev->intr_urb);
}

static void unlink_all_urbs(struct deca_ethintf *dev)
{
        usb_kill_urb(dev->rx_urb);
        usb_kill_urb(dev->tx_urb);
        usb_kill_urb(dev->intr_urb);
}

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

static void intr_callback(struct urb *urb)
{
	printk(KERN_ERR "%s():%d\n", __FUNCTION__, __LINE__);
}

static void fill_skb_pool(struct deca_ethintf *dev)
{
        struct sk_buff *skb;
        int i;

        for (i = 0; i < 4; i++) {
                if (dev->rx_skb_pool[i])
                        continue;
                skb = dev_alloc_skb(DECA_MTU);
                if (!skb) {
                        return;
                }
                dev->rx_skb_pool[i] = skb;
        }
}

static void free_skb_pool(struct deca_ethintf *dev)
{
        int i;

        for (i = 0; i < 4; i++)
                dev_kfree_skb(dev->rx_skb_pool[i]);
}


static inline struct sk_buff *pull_skb(struct deca_ethintf *dev)
{
        struct sk_buff *skb;
        int i;

        for (i = 0; i < 4; i++) {
                if (dev->rx_skb_pool[i]) {
                        skb = dev->rx_skb_pool[i];
                        dev->rx_skb_pool[i] = NULL;
                        return skb;
                }
        }
        return NULL;
}

static void read_bulk_callback(struct urb *urb)
{
	struct deca_ethintf *dev;
	int status = urb->status;
	struct net_device *netdev;
	struct sk_buff *skb;
	unsigned long flags = 0;

//	printk(KERN_ERR "%s():%d\n", __FUNCTION__, __LINE__);

	dev = urb->context;
	if (!dev) {
		printk(KERN_ERR "%s():%d\n", __FUNCTION__, __LINE__);
		return;
	}

	netdev = dev->netdev;
	if (!netif_device_present(netdev)) {
		return;
	}

	skb = dev->rx_skb;

//	printk(KERN_ERR "0x%02x 0x%02x 0x%02x 0x%02x\n", skb->data[0], skb->data[1], skb->data[2], skb->data[3]);

	skb_put(skb, urb->actual_length);
	dev->rx_skb->protocol = eth_type_trans(dev->rx_skb, netdev);
	netif_rx(skb);
        netdev->stats.rx_packets++;
        netdev->stats.rx_bytes += urb->actual_length;

	spin_lock_irqsave(&dev->rx_pool_lock, flags);
	dev->rx_skb = pull_skb(dev);
	spin_unlock_irqrestore(&dev->rx_pool_lock, flags);

	if (!dev->rx_skb) {
		goto resched;
	}

        usb_fill_bulk_urb(dev->rx_urb, dev->usbdev, usb_rcvbulkpipe(dev->usbdev, 2),
                      dev->rx_skb->data, DECA_MTU, read_bulk_callback, dev);
        if ((status = usb_submit_urb(dev->rx_urb, GFP_KERNEL))) {
                if (status == -ENODEV)
                        netif_device_detach(dev->netdev);
                dev_warn(&netdev->dev, "rx_urb submit failed: %d\n", status);
        }

	return;

resched:
	tasklet_schedule(&dev->tl);
}

static void write_bulk_callback(struct urb *urb)
{
        struct deca_ethintf *dev;
        int status = urb->status;

//	printk(KERN_ERR "%s():%d\n", __FUNCTION__, __LINE__);

        dev = urb->context;
        if (!dev)
                return;
        dev_kfree_skb_irq(dev->tx_skb);
        if (!netif_device_present(dev->netdev))
                return;
        if (status)
                dev_info(&urb->dev->dev, "%s: Tx status %d\n",
                         dev->netdev->name, status);
        netif_trans_update(dev->netdev);
        netif_wake_queue(dev->netdev);
}

static netdev_tx_t deca_ethintf_start_xmit(struct sk_buff *skb,
                                           struct net_device *netdev)
{
        struct deca_ethintf *dev = netdev_priv(netdev);
        int count, res;

        netif_stop_queue(netdev);
        dev->tx_skb = skb;
	count = skb->len;

	usb_fill_bulk_urb(dev->tx_urb, dev->usbdev, usb_sndbulkpipe(dev->usbdev, 3),
                          skb->data, count, write_bulk_callback, dev);
        if ((res = usb_submit_urb(dev->tx_urb, GFP_ATOMIC))) {
                /* Can we get/handle EPIPE here? */
                if (res == -ENODEV)
                        netif_device_detach(dev->netdev);
                else {
                        dev_warn(&netdev->dev, "failed tx_urb %d\n", res);
                        netdev->stats.tx_errors++;
                        netif_start_queue(netdev);
                }
        } else {
                netdev->stats.tx_packets++;
                netdev->stats.tx_bytes += skb->len;
                netif_trans_update(netdev);
        }

        return NETDEV_TX_OK;
}

static void deca_ethintf_tx_timeout(struct net_device *netdev)
{
        struct deca_ethintf *dev = netdev_priv(netdev);
        dev_warn(&netdev->dev, "Tx timeout.\n");
        usb_unlink_urb(dev->tx_urb);
        netdev->stats.tx_errors++;
}


static int deca_ethintf_open(struct net_device *netdev)
{
	int res = 0;
	struct deca_ethintf *dev = netdev_priv(netdev);

/*        usb_fill_int_urb(dev->intr_urb, dev->usbdev, usb_rcvintpipe(dev->usbdev, 1),
                     dev->intr_buff, INTBUFSIZE, intr_callback,
                     dev, dev->intr_interval);
        if ((res = usb_submit_urb(dev->intr_urb, GFP_KERNEL))) {
                if (res == -ENODEV)
                        netif_device_detach(dev->netdev);
                dev_warn(&netdev->dev, "intr_urb submit failed: %d\n", res);
                return res;
        }
*/
	if (!dev->rx_skb) {
		dev->rx_skb = pull_skb(dev);
		if (!dev->rx_skb)
			return -ENOMEM;
	}

        usb_fill_bulk_urb(dev->rx_urb, dev->usbdev, usb_rcvbulkpipe(dev->usbdev, 2),
                      dev->rx_skb->data, DECA_MTU, read_bulk_callback, dev);
        if ((res = usb_submit_urb(dev->rx_urb, GFP_KERNEL))) {
                if (res == -ENODEV)
                        netif_device_detach(dev->netdev);
                dev_warn(&netdev->dev, "rx_urb submit failed: %d\n", res);
                usb_kill_urb(dev->intr_urb);
                return res;
        }

//        enable_net_traffic(dev);
//        set_carrier(netdev);
	netif_carrier_on(netdev);
	netif_start_queue(netdev);

	return res;
}

static int deca_ethintf_close(struct net_device *netdev)
{
	struct deca_ethintf *deca = netdev_priv(netdev);
	netif_stop_queue(netdev);
	unlink_all_urbs(deca);
	return 0;
}

static void deca_ethintf_set_multicast(struct net_device *netdev)
{
}

static int deca_ethintf_set_mac_address(struct net_device *netdev, void *p)
{
	return 0;
}

static int deca_ethintf_ioctl(struct net_device *netdev, struct ifreq *rq, int cmd)
{
	return 0;
}

static const struct net_device_ops deca_ethintf_netdev_ops = {
	.ndo_open = deca_ethintf_open,
	.ndo_stop = deca_ethintf_close,
	.ndo_do_ioctl = deca_ethintf_ioctl,
        .ndo_start_xmit = deca_ethintf_start_xmit,
	.ndo_tx_timeout = deca_ethintf_tx_timeout,
        .ndo_set_rx_mode = deca_ethintf_set_multicast,
        .ndo_set_mac_address = deca_ethintf_set_mac_address,
        .ndo_validate_addr = eth_validate_addr,
};

static void deca_ethintf_get_drvinfo(struct net_device *netdev,
				     struct ethtool_drvinfo *info)
{
}

static int deca_ethintf_get_link_ksettings(struct net_device *netdev,
                                           struct ethtool_link_ksettings *ecmd)
{
	return 0;
}

static const struct ethtool_ops ops = {
        .get_drvinfo = deca_ethintf_get_drvinfo,
        .get_link = ethtool_op_get_link,
        .get_link_ksettings = deca_ethintf_get_link_ksettings,
};

static void set_ethernet_addr(struct deca_ethintf *dev)
{
	u8 node_id[ETH_ALEN] = {0x0a, 0x0a, 0x0a, 0x0a, 0x0a, 0x0a};
	ether_addr_copy(dev->netdev->dev_addr, node_id);
}

static void rx_fixup(unsigned long data)
{
	struct deca_ethintf *dev = (struct deca_ethintf *)data;
	struct sk_buff *skb;
        int status;
	struct net_device *netdev = dev->netdev;

	spin_lock_irq(&dev->rx_pool_lock);
	fill_skb_pool(dev);
        spin_unlock_irq(&dev->rx_pool_lock);

	spin_lock_irq(&dev->rx_pool_lock);
        skb = pull_skb(dev);
        spin_unlock_irq(&dev->rx_pool_lock);

	if (skb) {
		dev->rx_skb = skb;
	} else {
		printk(KERN_ERR "rx_fixup failed!\n");
		goto tlresched;
	}

        usb_fill_bulk_urb(dev->rx_urb, dev->usbdev, usb_rcvbulkpipe(dev->usbdev, 2),
                      dev->rx_skb->data, DECA_MTU, read_bulk_callback, dev);
        if ((status = usb_submit_urb(dev->rx_urb, GFP_KERNEL))) {
                if (status == -ENODEV)
                        netif_device_detach(dev->netdev);
                dev_warn(&netdev->dev, "rx_urb submit failed: %d\n", status);
        }
	return;

tlresched:
	tasklet_schedule(&dev->tl);
}

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

        tasklet_init(&deca->tl, rx_fixup, (unsigned long) deca);
        spin_lock_init(&deca->rx_pool_lock);

	deca->usbdev = usbdev;
	deca->netdev = netdev;
	deca->intr_interval = 100; // 100ms

	netdev->netdev_ops = &deca_ethintf_netdev_ops;
	netdev->ethtool_ops = &ops;
//	netdev->watchdog_timeo = (HZ);

        deca->intr_buff = kmalloc(INTBUFSIZE, GFP_KERNEL);
        if (!deca->intr_buff) {
                free_netdev(netdev);
                return -ENOMEM;
        }

	if (!alloc_all_urbs(deca)) {
		dev_err(&intf->dev, "out of memory\n");
                free_netdev(netdev);
		return -ENOMEM;
	}

	fill_skb_pool(deca);

	set_ethernet_addr(deca);

        usb_set_intfdata(intf, deca);
        SET_NETDEV_DEV(netdev, &intf->dev);

       if (register_netdev(netdev) != 0) {
                dev_err(&intf->dev, "couldn't register the device\n");
		usb_set_intfdata(intf, NULL);
		free_all_urbs(deca);
                free_netdev(netdev);
		return -EIO;
        }


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
	usb_set_intfdata(intf, NULL);
	if (deca) {
		unregister_netdev(deca->netdev);
		unlink_all_urbs(deca);
		free_all_urbs(deca);
		free_skb_pool(deca);
                dev_kfree_skb(deca->rx_skb);
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

