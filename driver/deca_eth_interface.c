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

static const char driver_name[] = "deca_eth_interface";

static const struct usb_device_id deca_ethintf_table[] = {
	{USB_DEVICE(0x1209, 0x4711)},
	{}
};

MODULE_DEVICE_TABLE(usb, deca_ethintf_table);

#define TX_QUEUE_LIMIT 16

#define DEBUG_PRINT() pr_info("%s():%d\n", __func__, __LINE__)

struct deca_ethintf {
	struct net_device *netdev;
	struct usb_device *usbdev;
	struct urb *intr_urb, *rx_urb;
	struct sk_buff *rx_skb;
	u8 *intr_buff;
	int intr_interval;
	int tx_queue_cnt;
};

struct deca_skb_data {
	struct deca_ethintf *deca;
};

#define DECA_REQT_READ	0xc0
#define DECA_REQT_WRITE      0x40
#define DECA_REQ_GET_REGS    0x05
#define DECA_REQ_SET_REGS    0x05

#define INTBUFSIZE 4
#define DECA_MTU 1536

static int alloc_urb(struct deca_ethintf *dev)
{
	dev->intr_urb = usb_alloc_urb(0, GFP_KERNEL);
	if (!dev->intr_urb) {
		return 0;
	}
	dev->rx_urb = usb_alloc_urb(0, GFP_KERNEL);
	if (!dev->rx_urb) {
		usb_free_urb(dev->intr_urb);
		return 0;
	}
	return 1;
}

static void free_urb(struct deca_ethintf *dev)
{
	usb_free_urb(dev->intr_urb);
	usb_free_urb(dev->rx_urb);
}

static void unlink_urb(struct deca_ethintf *dev)
{
	usb_kill_urb(dev->intr_urb);
	usb_kill_urb(dev->rx_urb);
}

static void free_rx_skb(struct deca_ethintf *dev)
{
	if (dev->rx_skb) {
		dev_kfree_skb(dev->rx_skb);
	}
}

static void read_bulk_callback(struct urb *urb);

static int fill_rx(struct deca_ethintf *dev)
{
	int status;
	struct sk_buff *skb = dev_alloc_skb(DECA_MTU);
	struct urb *urb = dev->rx_urb;

	if (!skb) {
		DEBUG_PRINT();
		return -ENOMEM;
	}
	dev->rx_skb = skb;
	usb_fill_bulk_urb(urb, dev->usbdev, usb_rcvbulkpipe(dev->usbdev, 2),
			  skb->data, DECA_MTU, read_bulk_callback, dev);
	status = usb_submit_urb(urb, GFP_KERNEL);
	if (status) {
		if (status == -ENODEV)
			netif_device_detach(dev->netdev);
		pr_info("rx_urb submit failed: %d\n", status);
		return -ENODEV;
	}
	return 0;
}

static void read_bulk_callback(struct urb *urb)
{
	struct deca_ethintf *dev = urb->context;
	int status = urb->status;
	struct net_device *netdev;

	if (!dev) {
		DEBUG_PRINT();
		goto goon;
	}

	netdev = dev->netdev;
	if (!netif_device_present(netdev)) {
		DEBUG_PRINT();
		dev_kfree_skb(dev->rx_skb);
		dev->rx_skb = NULL;
		return;
	}

	switch (status) {
	case 0:
		break;
	case -ENOENT:
		DEBUG_PRINT();
		dev_kfree_skb(dev->rx_skb);
		dev->rx_skb = NULL;
		goto goon;
	default:
		DEBUG_PRINT();
		dev_kfree_skb(dev->rx_skb);
		dev->rx_skb = NULL;
		goto goon;
	}

	if (urb->actual_length < 4) {
		DEBUG_PRINT();
		dev_kfree_skb(dev->rx_skb);
		dev->rx_skb = NULL;
		goto goon;
	}

	skb_put(dev->rx_skb, urb->actual_length);
	dev->rx_skb->protocol = eth_type_trans(dev->rx_skb, netdev);
	netif_rx(dev->rx_skb);
	netdev->stats.rx_packets++;
	netdev->stats.rx_bytes += urb->actual_length;

goon:
	dev->rx_skb = dev_alloc_skb(DECA_MTU);
	usb_fill_bulk_urb(urb, dev->usbdev, usb_rcvbulkpipe(dev->usbdev, 2),
			  dev->rx_skb->data, DECA_MTU, read_bulk_callback, dev);
	status = usb_submit_urb(urb, GFP_ATOMIC);
	if (status) {
		if (status == -ENODEV)
			netif_device_detach(dev->netdev);
		pr_info("rx_urb submit failed: %d\n", status);
	}
}

#if 0
static void read_intr_callback(struct urb *urb)
{
	struct deca_ethintf *dev;
	int status = urb->status;

	dev = urb->context;
	if (!dev) {
		printk(KERN_ERR "%s():%d\n", __func__, __LINE__);
		return;
	}

	switch (status) {
	case 0:
		break;
	case -ENOENT:
		DEBUG_PRINT();
		return;
	default:
		DEBUG_PRINT();
		return;
	}

	usb_fill_bulk_urb(dev->intr_urb, dev->usbdev, usb_rcvbulkpipe(dev->usbdev, 1),
		      dev->intr_buff, INTBUFSIZE, read_intr_callback, dev);
	status = usb_submit_urb(dev->intr_urb, GFP_ATOMIC);
	if (status) {
		pr_info("%s():%d, status = %d\n", __func__, __LINE__, status);
	}
}
#endif

static void write_bulk_callback(struct urb *urb)
{
	struct deca_ethintf *deca;
	struct sk_buff *skb;

	skb = urb->context;
	if (!skb) {
		DEBUG_PRINT();
		return;
	}
	deca = ((struct deca_skb_data *)skb->cb)->deca;
	if (!deca) {
		dev_kfree_skb_irq(skb);
		DEBUG_PRINT();
		return;
	}

	netif_trans_update(deca->netdev);
	if (--deca->tx_queue_cnt == (TX_QUEUE_LIMIT - 1) &&
			netif_queue_stopped(deca->netdev)) {
		netif_wake_queue(deca->netdev);
	}

	deca->netdev->stats.tx_packets++;
	deca->netdev->stats.tx_bytes += skb->len;

	dev_kfree_skb_irq(skb);
	usb_free_urb(urb);
}

static netdev_tx_t deca_ethintf_start_xmit(struct sk_buff *skb,
					   struct net_device *netdev)
{
	struct deca_skb_data *data;
	struct deca_ethintf *dev = netdev_priv(netdev);
	int count, res;
	struct urb *urb;
	u8 *hdr;

	if (!skb) {
		DEBUG_PRINT();
		return NETDEV_TX_OK;
	}

	count = skb->len;
	if (count > DECA_MTU) {
		pr_info("Dropping packet bigger than mtu limit!\n");
		goto drop;
	} else if (count <= 4) {
		pr_info("dropping smaller than 4 bytes\n");
		goto drop;
	}

	if (netif_queue_stopped(netdev)) {
		DEBUG_PRINT();
		goto drop;
	}

	hdr = skb_push(skb, 2);
	*(u16 *)hdr = cpu_to_be16((u16)count);
	count = skb->len;

	data = (struct deca_skb_data *) skb->cb;
	data->deca = dev;

	urb = usb_alloc_urb(0, GFP_ATOMIC);

	usb_fill_bulk_urb(urb, dev->usbdev, usb_sndbulkpipe(dev->usbdev, 3),
			  skb->data, count, write_bulk_callback, skb);

	res = usb_submit_urb(urb, GFP_ATOMIC);
	if (res) {
		/* Can we get/handle EPIPE here? */
		if (res == -ENODEV) {
			netif_device_detach(netdev);
			usb_free_urb(urb);
			goto drop;
		} else {
			dev_warn(&netdev->dev, "failed urb %d\n", res);
			netdev->stats.tx_errors++;
			usb_free_urb(urb);
			goto drop;
		}
	} else {
		netif_trans_update(netdev);
		if (++dev->tx_queue_cnt == TX_QUEUE_LIMIT) {
			netif_stop_queue(netdev);
		}
	}
	return NETDEV_TX_OK;
drop:
	if (skb) {
		dev_kfree_skb_any(skb);
	}
	return NETDEV_TX_OK;
}

static void deca_ethintf_tx_timeout(struct net_device *netdev, unsigned int txqueue)
{
	DEBUG_PRINT();
	dev_warn(&netdev->dev, "Tx timeout, txqueue = %u\n", txqueue);
	netdev->stats.tx_errors++;
}


static int deca_ethintf_open(struct net_device *netdev)
{
	int res = 0;
	struct deca_ethintf *dev = netdev_priv(netdev);

#if 0
	usb_fill_bulk_urb(dev->intr_urb, dev->usbdev, usb_rcvbulkpipe(dev->usbdev, 1),
		      dev->intr_buff, INTBUFSIZE, read_intr_callback, dev);
	res = usb_submit_urb(dev->intr_urb, GFP_KERNEL);
	if (res) {
		if (res == -ENODEV)
			netif_device_detach(dev->netdev);
		dev_warn(&netdev->dev, "intr_urb submit failed: %d\n", res);
		return res;
	}
#endif

	if (fill_rx(dev)) {
		return -ENOMEM;
	}

	netif_carrier_on(netdev);
	netif_start_queue(netdev);

	return res;
}

static int deca_ethintf_close(struct net_device *netdev)
{
	struct deca_ethintf *deca = netdev_priv(netdev);

	netif_stop_queue(netdev);
	unlink_urb(deca);
	return 0;
}

static void deca_ethintf_set_multicast(struct net_device *netdev)
{
}

static const struct net_device_ops deca_ethintf_netdev_ops = {
	.ndo_open = deca_ethintf_open,
	.ndo_stop = deca_ethintf_close,
	.ndo_start_xmit = deca_ethintf_start_xmit,
	.ndo_tx_timeout = deca_ethintf_tx_timeout,
	.ndo_set_rx_mode = deca_ethintf_set_multicast,
	.ndo_set_mac_address = eth_mac_addr,
	.ndo_validate_addr = eth_validate_addr,
};


static void deca_ethintf_get_drvinfo(struct net_device *netdev,
				    struct ethtool_drvinfo *info)
{
}

static int deca_ethintf_get_link_ksettings(struct net_device *netdev,
					   struct ethtool_link_ksettings *ecmd)
{
	DEBUG_PRINT();
	ecmd->base.speed = SPEED_100;
	ecmd->base.autoneg = AUTONEG_DISABLE;
	ecmd->base.duplex = DUPLEX_HALF;
	ecmd->base.port = PORT_TP;
	ecmd->base.phy_address = 0;
	return 0;
}

static int deca_ethintf_set_link_ksettings(struct net_device *netdev,
					   const struct ethtool_link_ksettings *ecmd)
{
	DEBUG_PRINT();
	return 0;
}

static const struct ethtool_ops ops = {
	.get_drvinfo = deca_ethintf_get_drvinfo,
	.get_link = ethtool_op_get_link,
	.get_link_ksettings = deca_ethintf_get_link_ksettings,
	.set_link_ksettings = deca_ethintf_set_link_ksettings,
};

static u8 node_id[6] = {0x0a, 0x0a, 0x0a, 0x0a, 0x0a, 0x0a};
static void set_ethernet_addr(struct deca_ethintf *dev)
{
	eth_hw_addr_set(dev->netdev, node_id);
}

static int deca_ethintf_probe(struct usb_interface *intf,
			      const struct usb_device_id *id)
{
	struct net_device *netdev;
	struct deca_ethintf *deca;
	struct usb_device *usbdev = interface_to_usbdev(intf);

	printk(KERN_INFO "%s():%d\n", __func__, __LINE__);

	netdev = alloc_etherdev(sizeof(struct deca_ethintf));
	if (!netdev) {
		printk(KERN_ERR "%s():%d, alloc_etherdev() failed!",
			__func__, __LINE__);
		return -ENOMEM;
	}
	deca = netdev_priv(netdev);

	deca->usbdev = usbdev;
	deca->netdev = netdev;
	deca->intr_interval = 100; // 100ms
	netdev->netdev_ops = &deca_ethintf_netdev_ops;
	netdev->ethtool_ops = &ops;

	deca->intr_buff = kmalloc(INTBUFSIZE, GFP_KERNEL);
	if (!deca->intr_buff) {
		free_netdev(netdev);
		return -ENOMEM;
	}

	if (!alloc_urb(deca)) {
		dev_err(&intf->dev, "out of memory\n");
		free_netdev(netdev);
		return -ENOMEM;
	}

	set_ethernet_addr(deca);

	usb_set_intfdata(intf, deca);
	SET_NETDEV_DEV(netdev, &intf->dev);
	if (register_netdev(netdev) != 0) {
		dev_err(&intf->dev, "couldn't register the device\n");
		usb_set_intfdata(intf, NULL);
		unlink_urb(deca);
		free_urb(deca);
		free_rx_skb(deca);
		free_netdev(netdev);
		return -EIO;
	}
	return 0;
}

static void deca_ethintf_disconnect(struct usb_interface *intf)
{
	struct deca_ethintf *deca = usb_get_intfdata(intf);

	DEBUG_PRINT();
	usb_set_intfdata(intf, NULL);
	if (deca) {
		unregister_netdev(deca->netdev);
		unlink_urb(deca);
		free_urb(deca);
		free_rx_skb(deca);
		free_netdev(deca->netdev);
	}
}

static int deca_ethintf_suspend(struct usb_interface *intf,
				pm_message_t message)
{
	DEBUG_PRINT();
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

