/*
 * Copyright (C) 2022 Konrad Gotfryd
 */

#include <linux/module.h>

static int __init deca_eth_interface_init(void)
{
        printk(KERN_INFO "deca_eth_interface: init\n");
        return 0;
}

static void __exit deca_eth_interface_exit(void)
{
        printk(KERN_INFO "deca_eth_interface: exit\n");
}

module_init(deca_eth_interface_init);
module_exit(deca_eth_interface_exit);

MODULE_LICENSE("GPL");

