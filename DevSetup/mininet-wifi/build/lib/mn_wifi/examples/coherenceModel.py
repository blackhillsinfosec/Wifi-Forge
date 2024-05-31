#!/usr/bin/env python

'Setting the position of Nodes and providing mobility using mobility models'
import sys

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi


def topology(args):
    "Create a network."
    net = Mininet_wifi()

    info("*** Creating nodes\n")
    net.addStation('sta1', mac='00:00:00:00:00:02', ip='10.0.0.2/8')
    net.addStation('sta2', mac='00:00:00:00:00:03', ip='10.0.0.3/8')
    ap1 = net.addAccessPoint('ap1', wlans=2, ssid='ssid1,ssid2', mode='g',
                             channel='1', failMode="standalone",
                             position='50,50,0')

    info("*** Configuring nodes\n")
    net.configureNodes()

    if '-p' not in args:
        net.plotGraph(max_x=300, max_y=300)

    net.setMobilityModel(time=1, model='CRP',
                         pointlist=[(100,11,0), (101, 12,0), (102, 13,0), (103,14,0), (104, 15,0), (105, 16,0), 
                                    (106,17,0), (107,18,0), (108,19,0), (109,20,0), (110,21,0), (111,22,0)])

    info("*** Starting network\n")
    net.build()
    ap1.start([])

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology(sys.argv)
