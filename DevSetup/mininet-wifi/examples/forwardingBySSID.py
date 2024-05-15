#!/usr/bin/env python

"""Before running this script please stop network-manager:
service network-manager stop

This example shows how to create multiple SSID at the same AP and ideas
around SSID-based packet forwarding

            --------
             ssid-4
            --------
               |
               |
  ------      (5)     -------
  ssid-1---(2)ap1(4)---ssid-3
  ------      (3)     -------
               |
               |
            --------
             ssid-2
            --------"""

import sys
from time import sleep

from mininet.log import setLogLevel, info
from mn_wifi.node import UserAP
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi


def topology(args):
    "Create a network."
    net = Mininet_wifi(accessPoint=UserAP, autoAssociation=False)

    info("*** Creating nodes\n")
    sta1 = net.addStation('sta1', position='10,60,0')
    sta2 = net.addStation('sta2', position='20,15,0')
    sta3 = net.addStation('sta3', position='10,25,0')
    sta4 = net.addStation('sta4', position='50,30,0')
    sta5 = net.addStation('sta5', position='45,65,0')
    ap1 = net.addAccessPoint('ap1', vssids=['ssid1,ssid2,ssid3,ssid4'],
                             ssid='ssid', mode="g", channel="1", position='30,40,0')
    c0 = net.addController('c0')

    info("*** Configuring nodes\n")
    net.configureNodes()

    if '-p' not in args:
        net.plotGraph(max_x=100, max_y=100)

    sta1.setRange(15, intf=sta1.params['wlan'][0])
    sta2.setRange(15, intf=sta2.params['wlan'][0])
    sta3.setRange(15, intf=sta3.params['wlan'][0])
    sta4.setRange(15, intf=sta4.params['wlan'][0])
    sta5.setRange(15, intf=sta5.params['wlan'][0])

    info("*** Starting network\n")
    net.build()
    c0.start()
    ap1.start([c0])

    sleep(2)
    cmd = 'iw dev {} connect {} {}'
    intf = ap1.wintfs[0].vssid
    sta1.cmd(cmd.format(sta1.params['wlan'][0], intf[0], ap1.wintfs[1].mac))
    sta2.cmd(cmd.format(sta2.params['wlan'][0], intf[1], ap1.wintfs[2].mac))
    sta3.cmd(cmd.format(sta3.params['wlan'][0], intf[1], ap1.wintfs[2].mac))
    sta4.cmd(cmd.format(sta4.params['wlan'][0], intf[2], ap1.wintfs[3].mac))
    sta5.cmd(cmd.format(sta5.params['wlan'][0], intf[3], ap1.wintfs[4].mac))

    ap1.cmd('dpctl unix:/tmp/ap1 meter-mod cmd=add,flags=1,meter=1 '
            'drop:rate=100')
    ap1.cmd('dpctl unix:/tmp/ap1 meter-mod cmd=add,flags=1,meter=2 '
            'drop:rate=200')
    ap1.cmd('dpctl unix:/tmp/ap1 meter-mod cmd=add,flags=1,meter=3 '
            'drop:rate=300')
    ap1.cmd('dpctl unix:/tmp/ap1 meter-mod cmd=add,flags=1,meter=4 '
            'drop:rate=400')
    ap1.cmd('dpctl unix:/tmp/ap1 flow-mod table=0,cmd=add in_port=2 '
            'meter:1 apply:output=flood')
    ap1.cmd('dpctl unix:/tmp/ap1 flow-mod table=0,cmd=add in_port=3 '
            'meter:2 apply:output=flood')
    ap1.cmd('dpctl unix:/tmp/ap1 flow-mod table=0,cmd=add in_port=4 '
            'meter:3 apply:output=flood')
    ap1.cmd('dpctl unix:/tmp/ap1 flow-mod table=0,cmd=add in_port=5 '
            'meter:4 apply:output=flood')

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology(sys.argv)
