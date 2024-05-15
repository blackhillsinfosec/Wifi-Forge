#!/usr/bin/env python

'This example show how to configure Propagation Models'

import sys

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi


def topology(args):

    "Create a network."
    net = Mininet_wifi()

    info("*** Creating nodes\n")
    net.addStation('sta1', antennaHeight='1', antennaGain='5')
    net.addStation('sta2', antennaHeight='1', antennaGain='5')
    ap1 = net.addAccessPoint('ap1', ssid='new-ssid', model='DI524',
                             mode='g', channel='1', position='50,50,0')
    c1 = net.addController('c1')

    info("*** Configuring propagation model\n")
    net.setPropagationModel(model="logDistance", exp=4)

    info("*** Configuring nodes\n")
    net.configureNodes()

    if '-p' not in args:
        net.plotGraph(max_x=100, max_y=100)

    net.setMobilityModel(time=0, model='RandomWayPoint', max_x=100, max_y=100,
                         min_v=0.5, max_v=0.5, seed=20)

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
