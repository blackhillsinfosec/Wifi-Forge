#!/usr/bin/env python

from json import dumps
from requests import put
from os import listdir, environ


from mininet.log import setLogLevel, info
from mininet.util import quietRun
from mn_wifi.link import wmediumd, mesh
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.wmediumdConnector import interference


def topology():
    "Create a network."
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)

    info("*** Creating nodes\n")
    sta1 = net.addStation('sta1', mac='00:00:00:00:00:11', position='1,1,0')
    sta2 = net.addStation('sta2', mac='00:00:00:00:00:12', position='91,11,0')
    ap1 = net.addAccessPoint('ap1', wlans=2, ssid='ssid1', failMode='standalone',
                             position='10,10,0')
    ap2 = net.addAccessPoint('ap2', wlans=2, ssid='ssid2', failMode='standalone',
                             position='50,10,0')
    ap3 = net.addAccessPoint('ap3', wlans=2, ssid='ssid3', failMode='standalone',
                             position='90,10,0')

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Associating Stations\n")
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap3)
    net.addLink(ap1, intf='ap1-wlan2', cls=mesh, ssid='mesh-ssid', channel=5)
    net.addLink(ap2, intf='ap2-wlan2', cls=mesh, ssid='mesh-ssid', channel=5)
    net.addLink(ap3, intf='ap3-wlan2', cls=mesh, ssid='mesh-ssid', channel=5)

    info("*** Starting network\n")
    net.start()

    info("*** Sending data to sflow-rt\n")
    sflow_rt(net.aps)

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


def sflow_rt(aps):
    ifname = 'lo'
    collector = environ.get('COLLECTOR', '127.0.0.1')
    sampling = environ.get('SAMPLING', '10')
    polling = environ.get('POLLING', '10')
    sflow = 'ovs-vsctl -- --id=@sflow create sflow agent=%s target=%s ' \
            'sampling=%s polling=%s --' % (ifname, collector, sampling, polling)

    for ap in aps:
        sflow += ' -- set bridge %s sflow=@sflow' % ap
        quietRun(sflow)

    agent = '127.0.0.1'
    topo = {'nodes': {}, 'links': {}}
    for ap in aps:
        topo['nodes'][ap.name] = {'agent': agent, 'ports': {}}

    path = '/sys/devices/virtual/mac80211_hwsim/'
    # /sys/devices/virtual/net/ can be used in place of the path above
    for child in listdir(path):
        dir_ = path + '{}'.format(child + '/net/')
        for child_ in listdir(dir_):
            node = child_[:3]
            if node in topo['nodes']:
                ifindex = open(dir_ + child_ + '/ifindex').read().split('\n', 1)[0]
                topo['nodes'][node]['ports'][child_] = {'ifindex': ifindex}

    for id, ap1 in enumerate(aps):
        if id < len(aps) - 1:
            ap2 = aps[id + 1]
            linkName = '{}-{}'.format(ap1.name, ap2.name)
            topo['links'][linkName] = {'node1': ap1.name, 'port1': ap1.wintfs[1].name,
                                       'node2': ap2.name, 'port2': ap2.wintfs[1].name}

    put('http://127.0.0.1:8008/topology/json', data=dumps(topo))


if __name__ == '__main__':
    setLogLevel('info')
    topology()
