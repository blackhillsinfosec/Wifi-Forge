#!/usr/bin/env python

"""
NOTE: you have to install wireless-regdb and CRDA
      please refer to https://mininet-wifi.github.io/80211p/
"""

from mininet.log import setLogLevel, info
from mn_wifi.link import wmediumd, ITSLink
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.wmediumdConnector import interference


def topology():
    "Create a network."
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)

    info("*** Creating nodes\n")
    sta1 = net.addStation('sta1', ip='10.0.0.1/8', position='100,150,0')
    sta2 = net.addStation('sta2', ip='10.0.0.2/8', position='150,150,0')
    sta3 = net.addStation('sta3', ip='10.0.0.3/8', position='200,150,0')

    info("*** Configuring Propagation Model\n")
    net.setPropagationModel(model="logDistance", exp=3.5)

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Plotting Graph\n")
    net.plotGraph(max_x=300, max_y=300)

    info("*** Starting ITS Links\n")
    net.addLink(sta1, intf='sta1-wlan0', cls=ITSLink,
                band=20, channel=181, proto='batman_adv')
    net.addLink(sta2, intf='sta2-wlan0', cls=ITSLink,
                band=20, channel=181, proto='batman_adv')
    net.addLink(sta3, intf='sta3-wlan0', cls=ITSLink,
                band=20, channel=181, proto='batman_adv')

    info("*** Starting network\n")
    net.build()

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()
