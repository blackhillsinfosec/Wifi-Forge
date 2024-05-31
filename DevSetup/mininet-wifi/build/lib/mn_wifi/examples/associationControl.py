#!/usr/bin/env python

'Setting mechanism to optimize the use of APs'

import sys

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi


def topology():

    ac_method = 'ssf'
    if '-llf' in sys.argv:
        ac_method = 'llf'

    "Create a network."
    net = Mininet_wifi(ac_method=ac_method)

    info("*** Creating nodes\n")
    for n in range(1, 10):
        net.addStation('sta%d' % n, mac='00:00:00:00:00:%02d' % n,
                       ip='10.0.0.%d/8' % n, position='%s,40,0' % (45+n))
    net.addStation('sta10', mac='00:00:00:00:00:10',
                   ip='10.0.0.10/8', position='79,45,0')
    ap1 = net.addAccessPoint('ap1', ssid='ssid-ap1', mode='g', channel='6',
                             mac='00:00:00:00:01:00', position='70,50,0')
    ap2 = net.addAccessPoint('ap2', ssid='ssid-ap2', mode='g', channel='11',
                             mac='00:00:00:00:02:00', position='90,50,0')
    c1 = net.addController('c1')

    net.setPropagationModel(model="logDistance", exp=5)

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Associating and Creating links\n")
    net.addLink(ap1, ap2)

    net.plotGraph(max_x=120, max_y=120)

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
    topology()
