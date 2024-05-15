#!/usr/bin/python

"Replaying RSSI"
import os

from mininet.log import setLogLevel, info
from mn_wifi.replaying import ReplayingRSSI
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi


def topology():
    "Create a network."
    net = Mininet_wifi()

    info("*** Creating nodes\n")
    sta1 = net.addStation('sta1', mac='00:00:00:00:00:02',
                          ip='10.0.0.2/8', position='40,50,0')
    sta2 = net.addStation('sta2', mac='00:00:00:00:00:03',
                          ip='10.0.0.3/8', position='40,40,0')
    ap1 = net.addAccessPoint('ap1', ssid='new-ssid', mode='g', channel='1',
                             position='50,50,0')
    c1 = net.addController('c1')

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Starting network\n")
    net.build()
    c1.start()
    ap1.start([c1])

    info("*** Plotting Graph\n")
    net.plotGraph(max_x=100, max_y=100)

    path = os.path.dirname(os.path.abspath(__file__)) + '/replayingRSSI/'
    get_trace(sta1, '{}node1_rssiData.dat'.format(path))
    get_trace(sta2, '{}node2_rssiData.dat'.format(path))

    info("*** Replaying RSSI\n")
    ReplayingRSSI(net)

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


def get_trace(node, file):
    file = open(file, 'r')
    raw_data = file.readlines()
    file.close()

    node.pos = '0,0,0'
    node.time = []
    node.rssi = []

    for data in raw_data:
        line = data.split()
        node.time.append(float(line[0]))  #First Column = Time
        node.rssi.append(float(line[1]))  #Second Column = RSSI


if __name__ == '__main__':
    setLogLevel('info')
    topology()
