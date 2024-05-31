#!/usr/bin/env python

'This example creates a simple network topology with 2 APs working in mesh mode'

from mininet.node import Controller
from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.node import UserAP
from mn_wifi.link import wmediumd, mesh
from mn_wifi.wmediumdConnector import interference
from mn_wifi.net import Mininet_wifi


def topology():
    "Create a network."
    net = Mininet_wifi(controller=Controller, link=wmediumd,
                       wmediumd_mode=interference)

    info("*** Creating nodes\n")
    sta1 = net.addAccessPoint('sta1', ip='192.168.0.1/24',
                              position='10,10,0', cls=UserAP, inNamespace=True)
    sta2 = net.addAccessPoint('sta2', ip='192.168.0.2/24',
                              position='10,20,0', cls=UserAP, inNamespace=True)
    c0 = net.addController('c0')

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Associating Stations\n")
    net.addLink(sta1, intf='sta1-wlan1', cls=mesh,
                ssid='mesh-ssid', channel=5)
    net.addLink(sta2, intf='sta2-wlan1', cls=mesh,
                ssid='mesh-ssid', channel=5)

    info("*** Starting network\n")
    net.build()
    c0.start()
    sta1.start([c0])
    sta2.start([c0])

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()
