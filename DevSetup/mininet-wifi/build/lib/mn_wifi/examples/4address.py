#!/usr/bin/env python

"""This example shows how to enable 4-address
Warning: It works only when network manager is stopped"""

import sys

from mininet.node import Controller
from mininet.log import setLogLevel, info
from mn_wifi.link import wmediumd, _4address
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.wmediumdConnector import interference


def topology(args):
    "Create a network."
    net = Mininet_wifi(controller=Controller, link=wmediumd,
                       wmediumd_mode=interference, config4addr=True)

    info("*** Creating nodes\n")
    ap1 = net.addAccessPoint('ap1', ssid="ap1-ssid", mode="g",
                             channel="1", position='30,30,0')
    ap2 = net.addAccessPoint('ap2', ssid="ap2-ssid", mode="g",
                             channel="1", position='40,60,0')
    ap3 = net.addAccessPoint('ap3', ssid="ap3-ssid", mode="g",
                             channel="1", position='50,30,0')
    sta1 = net.addStation('sta1', ip="192.168.0.1/24", position='31,32,0')
    sta2 = net.addStation('sta2', ip="192.168.0.2/24", position='32,34,0')
    sta3 = net.addStation('sta3', ip="192.168.0.3/24", position='41,62,0')
    sta4 = net.addStation('sta4', ip="192.168.0.4/24", position='42,64,0')
    sta5 = net.addStation('sta5', ip="192.168.0.5/24", position='51,32,0')
    sta6 = net.addStation('sta6', ip="192.168.0.6/24", position='52,34,0')
    c0 = net.addController('c0')

    info("*** Configuring Propagation Model\n")
    net.setPropagationModel(model="logDistance", exp=4.5)

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Adding Links\n")
    net.addLink(ap1, ap2, cls=_4address)  # ap1=ap, ap2=client
    net.addLink(ap1, ap3, cls=_4address)  # ap1=ap, ap3=client
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap1)
    net.addLink(sta3, ap2)
    net.addLink(sta4, ap2)
    net.addLink(sta5, ap3)
    net.addLink(sta6, ap3)

    if '-p' not in args:
        net.plotGraph(max_x=100, max_y=100)

    info("*** Starting network\n")
    net.build()
    c0.start()
    ap1.start([c0])
    ap2.start([c0])
    ap3.start([c0])

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology(sys.argv)
