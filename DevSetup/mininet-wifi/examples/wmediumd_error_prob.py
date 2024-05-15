#!/usr/bin/env python

"Setting the error prob with wmediumd"

import sys

from mininet.node import Controller
from mininet.log import setLogLevel, info
from mn_wifi.link import wmediumd
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.wmediumdConnector import error_prob


def topology(args):

    "Create a network."
    net = Mininet_wifi(controller=Controller, link=wmediumd,
                       wmediumd_mode=error_prob)

    info("*** Creating nodes\n")
    ap1 = net.addAccessPoint('ap1', ssid='new-ssid', mode='a', channel='36',
                             position='15,30,0')
    sta1 = net.addStation('sta1', mac='00:00:00:00:00:02', ip='10.0.0.1/8',
                          position='10,20,0')
    sta2 = net.addStation('sta2', mac='00:00:00:00:00:03', ip='10.0.0.2/8',
                          position='20,50,0')
    sta3 = net.addStation('sta3', mac='00:00:00:00:00:04', ip='10.0.0.3/8',
                          position='20,60,10')
    c1 = net.addController('c1')

    info("*** Configuring nodes\n")
    net.configureNodes()

    net.addLink(sta1, ap1, error_prob=0.01)
    net.addLink(sta2, ap1, error_prob=0.02)
    net.addLink(sta3, ap1, error_prob=1)

    if '-p' not in args:
        net.plotGraph(max_x=100, max_y=100)

    info("*** Starting network\n")
    net.build()
    c1.start()
    ap1.start([c1])

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology(sys.argv)
