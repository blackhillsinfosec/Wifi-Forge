#!/usr/bin/env python

import sys

from mininet.log import setLogLevel, info
from mn_wifi.sixLoWPAN.link import LoWPAN
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi

"""This example creates a simple network topology with 4 nodes

       sensor1 (root)
      /       \
    /          \
sensor2      sensor3
               |
               |
             sensor4
"""


def topology():
    "Create a network."
    net = Mininet_wifi(iot_module='mac802154_hwsim')
    # iot_module: fakelb or mac802154_hwsim
    # mac802154_hwsim is supported from kernel 4.18

    info("*** Creating nodes\n")
    # There is no need to set the node position.
    # Signal range and position won't work as we expect
    # because there is no wmediumd-like code for mac802154_hwim yet.
    # However, you may want to add mobility and node position
    # and use wpan-hwsim for some purposes.
    # dodag_root and storing mode only work with RPLD
    # supported storing modes:
    # **** RPL_DIO_NO_DOWNWARD_ROUTES_MAINT = 0
    # **** RPL_DIO_NONSTORING = 1
    # **** RPL_DIO_STORING_NO_MULTICAST = 2
    # **** RPL_DIO_STORING_MULTICAST = 3
    sensor1 = net.addSensor('sensor1', ip6='fe80::1/64', panid='0xbeef',
                            dodag_root=True, storing_mode=2)
    sensor2 = net.addSensor('sensor2', ip6='fe80::2/64', panid='0xbeef',
                            storing_mode=2)
    sensor3 = net.addSensor('sensor3', ip6='fe80::3/64', panid='0xbeef',
                            storing_mode=2)
    sensor4 = net.addSensor('sensor4', ip6='fe80::4/64', panid='0xbeef',
                            storing_mode=2)

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Adding links\n")
    net.addLink(sensor1, sensor2, cls=LoWPAN)
    net.addLink(sensor1, sensor3, cls=LoWPAN)
    net.addLink(sensor3, sensor4, cls=LoWPAN)

    info("*** Starting network\n")
    net.build()

    if '-r' in sys.argv:
        info("*** Configuring RPLD\n")
        # You must have the nonstoring_mode branch from https://github.com/linux-wpan/rpld
        net.configRPLD(net.sensors)

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()
