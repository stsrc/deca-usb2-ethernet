#!/usr/bin/env python3
#
# Copyright (c) 2022 Konrad Gotfryd <gotfrydkonrad@gmail.com>
# SPDX-License-Identifier: CERN-OHL-W-2.0

import os

from amaranth import *
from simple_ports_to_wb import SimplePortsToWb

__all__ = ["InjectData"]

class InjectData(Elaboratable):
    def __init__(self):
        self.bus = None

    def elaborate(self, platform):
        m = Module()
        m.submodules.simple_ports_to_wb = SimplePortsToWb() 
        self.bus = m.submodules.simple_ports_to_wb.bus
        return m
