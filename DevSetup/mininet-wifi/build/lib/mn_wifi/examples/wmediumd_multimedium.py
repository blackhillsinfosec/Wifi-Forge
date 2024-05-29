#!/usr/bin/env python

"""
This example shows how to define multiple mediums.
By default, all interfaces share the same medium and the packet ordering takes into account all of their queues.
This behavior causes throughput to drop every time there is additional network load, even if networks are
independent of each other.

By defining interface sets of each medium, we can isolate packet orderings in the queues.
"""

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.link import wmediumd
from mn_wifi.net import Mininet_wifi
from mn_wifi.wmediumdConnector import interference


def topology():
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference,
                       ipBase='10.0.0.0/8')

    info('*** Add APs\n')
    ap1 = net.addAccessPoint('ap1', ssid='ap1-ssid', channel='5', 
                             position='337.0,424.0,0')
    net.addAccessPoint('ap2', ssid='ap2-ssid', channel='6',
                       position='1368.0,391.0,0')
    ap3 = net.addAccessPoint('ap3', ssid='ap3-ssid', channel='6', 
                             position='2368.0,391.0,0')

    info('*** Add hosts/stations\n')
    net.addStation('sta1', ip='10.0.0.1', position='192.0,384.0,0')
    sta2 = net.addStation('sta2', ip='10.0.0.2', position='237.0,443.0,0')
    sta3 = net.addStation('sta3', ip='10.0.0.3', position='1493.0,150.0,0')
    sta4 = net.addStation('sta4', ip='10.0.0.4', position='1374.0,656.0,0')
    sta5 = net.addStation('sta5', ip='10.0.0.5', position='2393.0,350.0,0')
    sta6 = net.addStation('sta6', ip='10.0.0.6', position='2374.0,426.0,0')

    info("*** Configuring Propagation Model\n")
    net.setPropagationModel(model="logDistance", exp=3)

    # Defining 3 mediums for packet ordering
    initial_mediums = (("sta1-wlan0", sta2, ap1),  # Medium #1
                       (sta3, sta4, "ap2-wlan1"),  # Medium #2
                       (sta5,))  # Medium #3
    net.setInitialMediums(initial_mediums)

    info("*** Configuring nodes\n")
    net.configureNodes()

    net.plotGraph(max_x=3000, max_y=1000)

    info('*** Starting network\n')
    net.start()

    info('*** Post configure nodes\n')
    # Adding ap3's first interface to medium #3
    ap3.setMediumId(3, intf=None)
    # Adding sta6-wlan0 interface to medium #3
    sta6.getNameToWintf("sta6-wlan0").setMediumId(3)

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()
