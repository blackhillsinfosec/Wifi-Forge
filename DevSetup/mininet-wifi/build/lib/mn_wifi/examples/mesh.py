#!/usr/bin/env python

"""
This example shows on how to enable the mesh mode
The wireless mesh network is based on IEEE 802.11s
"""

import sys

from mininet.log import setLogLevel, info
from mn_wifi.link import wmediumd, mesh
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.wmediumdConnector import interference


def topology(mobility):
    "Create a network."
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)

    info("*** Creating nodes\n")
    if mobility:
        sta1 = net.addStation('sta1')
        sta2 = net.addStation('sta2')
        sta3 = net.addStation('sta3')
    else:
        sta1 = net.addStation('sta1', position='10,10,0')
        sta2 = net.addStation('sta2', position='50,10,0')
        sta3 = net.addStation('sta3', position='90,10,0')

    info("*** Configuring Propagation Model\n")
    net.setPropagationModel(model="logDistance", exp=4)

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Creating links\n")
    net.addLink(sta1, cls=mesh, ssid='meshNet',
                intf='sta1-wlan0', channel=5, ht_cap='HT40+')  #, passwd='thisisreallysecret')
    net.addLink(sta2, cls=mesh, ssid='meshNet',
                intf='sta2-wlan0', channel=5, ht_cap='HT40+')  #, passwd='thisisreallysecret')
    net.addLink(sta3, cls=mesh, ssid='meshNet',
                intf='sta3-wlan0', channel=5, ht_cap='HT40+')  #, passwd='thisisreallysecret')

    if mobility:
        net.plotGraph(max_x=100, max_y=100)
        net.setMobilityModel(time=0, model='RandomDirection',
                             max_x=100, max_y=100,
                             min_v=0.5, max_v=0.8, seed=20)

    info("*** Starting network\n")
    net.build()

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    mobility = True if '-m' in sys.argv else False
    topology(mobility)
