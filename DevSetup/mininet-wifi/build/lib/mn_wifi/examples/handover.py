#!/usr/bin/env python

'Example for Handover'

import sys

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi


def topology(args):
    "Create a network."
    net = Mininet_wifi()

    info("*** Creating nodes\n")
    sta1_args, sta2_args = {}, {}
    if '-s' in args:
        sta1_args['position'], sta2_args['position'] = '20,30,0', '60,30,0'

    sta1 = net.addStation('sta1', mac='00:00:00:00:00:01', **sta1_args)
    sta2 = net.addStation('sta2', mac='00:00:00:00:00:02', **sta2_args)
    ap1 = net.addAccessPoint('ap1', ssid='ssid-ap1', channel='1', position='15,30,0')
    ap2 = net.addAccessPoint('ap2', ssid='ssid-ap2', channel='6', position='55,30,0')
    c1 = net.addController('c1')

    net.setPropagationModel(model="logDistance", exp=5)

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Creating links\n")
    net.addLink(ap1, ap2)

    if '-p' not in args:
        net.plotGraph(max_x=100, max_y=100)

    if '-s' not in args:
        net.startMobility(time=0)
        net.mobility(sta1, 'start', time=1, position='10,30,0')
        net.mobility(sta2, 'start', time=2, position='10,40,0')
        net.mobility(sta1, 'stop', time=10, position='60,30,0')
        net.mobility(sta2, 'stop', time=10, position='25,40,0')
        net.stopMobility(time=11)

    info("*** Starting network\n")
    net.build()
    c1.start()
    ap1.start([c1])
    ap2.start([c1])

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology(sys.argv)
