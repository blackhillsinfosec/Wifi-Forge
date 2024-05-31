#!/usr/bin/env python

'Setting position of the nodes'

import sys

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi


"""
We are still trying to enable 6GHz on hwsim
Initial code has been submitted to the Linux Kernel:
https://github.com/torvalds/linux/commit/28881922abd786a1e62a4ca77394a84373dd5279

Both wpa3 and ieee80211w are requirements for 6GHz
"""


def topology(args):

    "Starting network"
    net = Mininet_wifi()

    info("*** Creating nodes\n")
    ap1 = net.addAccessPoint('ap1', ssid='new-ssid', mac='00:00:00:00:00:01',
                             mode='ax', channel='21', encrypt='wpa3',
                             failMode="standalone", datapath='user',
                             passwd='123456789a', ieee80211w='2',
                             position='50,50,0')
    net.addStation('sta1', mac='00:00:00:00:00:02', ip='10.0.0.1/8',
                   position='30,60,0')
    net.addStation('sta2', mac='00:00:00:00:00:03', ip='10.0.0.2/8',
                   position='70,30,0')

    info("*** Configuring propagation model\n")
    net.setPropagationModel(model="logDistance", exp=4.5)

    # modified module
    #net.setModule('./mac80211_hwsim.ko')

    info("*** Configuring nodes\n")
    net.configureNodes()

    if '-p' not in args:
        net.plotGraph(max_x=100, max_y=100)

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
