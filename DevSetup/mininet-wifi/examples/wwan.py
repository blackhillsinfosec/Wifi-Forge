#!/usr/bin/env python

"""
This example creates a simple wwan network topology

Requirements:
* Kernel 5.14+
    * https://github.com/torvalds/linux/blob/master/drivers/net/wwan/wwan_hwsim.c
* iproute2 (2-5.13+) util/install.sh -i does the work
* ModemManager (1-17.2+) util/install.sh -M does the work
"""

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi


def topology():
    "Create a network"
    net = Mininet_wifi()

    info("*** Creating nodes\n")
    net.addModem('m1')

    info("*** Configuring wifi nodes\n")
    net.configureNodes()

    info("*** Starting network\n")
    net.start()

    # The WWAN interface for a new data channel should be created with a
    # command like this:
    # m1.cmd('ip link add dev wwan0-2 parentdev wwan0 type wwan linkid 2')
    # where:
    # wwan0 is the modem HW device name
    # linkid is an identifier of the opened data channel

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()
