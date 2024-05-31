#!/usr/bin/env python

'This example runs stations in AP mode'

import sys

from mininet.log import setLogLevel, info
from mn_wifi.link import wmediumd
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.wmediumdConnector import interference


def topology(args):
    'Create a network.'
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)

    info("*** Creating nodes\n")
    if '-m' in args:
        sta1 = net.addStation('sta1', mac='00:00:00:00:00:01',
                              ip='192.168.0.1/24')
    else:
        sta1 = net.addStation('sta1', mac='00:00:00:00:00:01',
                              ip='192.168.0.1/24', position='20,60,0')
    sta2 = net.addStation('sta2', mac='00:00:00:00:00:02', ip='192.168.1.1/24',
                          position='90,60,0')
    ap1 = net.addStation('ap1', mac='02:00:00:00:01:00',
                         ip='192.168.0.10/24', position='40,60,0')
    ap2 = net.addStation('ap2', mac='02:00:00:00:02:00',
                         ip='192.168.1.10/24', position='70,60,0')

    net.setPropagationModel(model="logDistance", exp=4.5)

    info("*** Configuring nodes\n")
    net.configureNodes()

    ap1.setMasterMode(intf='ap1-wlan0', ssid='ap1-ssid', channel='1', mode='n2')
    ap2.setMasterMode(intf='ap2-wlan0', ssid='ap2-ssid', channel='6', mode='n2')

    info("*** Adding Link\n")
    net.addLink(ap1, ap2)  # wired connection

    if '-p' not in args:
        info("*** Plotting Graph\n")
        net.plotGraph(max_x=120, max_y=120)

    if '-m' in args:
        net.startMobility(time=1)
        net.mobility(sta1, 'start', time=2, position='20.0,60.0,0.0')
        net.mobility(sta1, 'stop', time=6, position='100.0,60.0,0.0')
        net.stopMobility(time=7)

    info("*** Starting network\n")
    net.build()

    ap1.cmd('echo 1 > /proc/sys/net/ipv4/ip_forward')
    ap2.cmd('echo 1 > /proc/sys/net/ipv4/ip_forward')

    ap1.setIP('192.168.0.10/24', intf='ap1-wlan0')
    ap1.setIP('192.168.2.1/24', intf='ap1-eth1')
    ap2.setIP('192.168.1.10/24', intf='ap2-wlan0')
    ap2.setIP('192.168.2.2/24', intf='ap2-eth1')
    ap1.cmd('route add -net 192.168.1.0/24 gw 192.168.2.2')
    ap2.cmd('route add -net 192.168.0.0/24 gw 192.168.2.1')
    sta1.cmd('route add -net 192.168.1.0/24 gw 192.168.0.10')
    sta1.cmd('route add -net 192.168.2.0/24 gw 192.168.0.10')
    sta2.cmd('route add -net 192.168.0.0/24 gw 192.168.1.10')
    sta2.cmd('route add -net 192.168.2.0/24 gw 192.168.1.10')

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology(sys.argv)
