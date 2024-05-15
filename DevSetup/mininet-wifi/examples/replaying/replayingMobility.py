#!/usr/bin/python

'Replaying Mobility'

import os
import sys

from mininet.node import Controller
from mininet.log import setLogLevel, info
from mn_wifi.replaying import ReplayingMobility
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.link import wmediumd, adhoc
from mn_wifi.wmediumdConnector import interference


def topology(args):
    "Create a network."
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)

    info("*** Creating nodes\n")
    sta1 = net.addStation('sta1', mac='00:00:00:00:00:02',
                          ip='10.0.0.1/8', speed=4)
    sta2 = net.addStation('sta2', mac='00:00:00:00:00:03',
                          ip='10.0.0.2/8', speed=6)
    sta3 = net.addStation('sta3', mac='00:00:00:00:00:04',
                          ip='10.0.0.3/8', speed=3)
    sta4 = net.addStation('sta4', mac='00:00:00:00:00:05',
                          ip='10.0.0.4/8', speed=3)
    ap1 = net.addAccessPoint('ap1', ssid='new-ssid', mode='g', channel='1',
                             position='45,45,0')
    c1 = net.addController('c1', controller=Controller)

    info("*** Configuring Propagation Model\n")
    net.setPropagationModel(model="logDistance", exp=4.5)

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Creating links\n")
    net.addLink(sta3, cls=adhoc, intf='sta3-wlan0', ssid='adhocNet')
    net.addLink(sta4, cls=adhoc, intf='sta4-wlan0', ssid='adhocNet')

    net.isReplaying = True
    path = os.path.dirname(os.path.abspath(__file__)) + '/replayingMobility/'
    get_trace(sta1, '{}node1.dat'.format(path))
    get_trace(sta2, '{}node2.dat'.format(path))
    get_trace(sta3, '{}node3.dat'.format(path))
    get_trace(sta4, '{}node4.dat'.format(path))

    if '-p' not in args:
        net.plotGraph(max_x=200, max_y=200)

    info("*** Starting network\n")
    net.build()
    c1.start()
    ap1.start([c1])

    info("*** Replaying Mobility\n")
    ReplayingMobility(net)

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


def get_trace(sta, file_):
    file_ = open(file_, 'r')
    raw_data = file_.readlines()
    file_.close()

    sta.p = []
    pos = (-1000, 0, 0)
    sta.position = pos

    for data in raw_data:
        line = data.split()
        x = line[0]  # First Column
        y = line[1]  # Second Column
        pos = float(x), float(y), 0.0
        sta.p.append(pos)


if __name__ == '__main__':
    setLogLevel('info')
    topology(sys.argv)
