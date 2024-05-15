#!/usr/bin/python

'Ditma demo with UAVs represented using CoppeliaSim'

import time
import os
import sys
import re

#Included to support sflow-rt
from json import dumps
from requests import put
from mininet.util import quietRun
from os import listdir, environ

from mininet.log import setLogLevel, info
from mn_wifi.link import wmediumd, adhoc
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.telemetry import telemetry
from mn_wifi.wmediumdConnector import interference



def topology(args):

    "Create a network."
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)

    info("*** Creating nodes\n")
    dr1 = net.addStation('dr1', mac='00:00:00:00:00:01', ip='10.0.0.1/8',
                         ip6='fe80::1', position='0,0,0')
    dr2 = net.addStation('dr2', mac='00:00:00:00:00:02', ip='10.0.0.2/8',
                         ip6='fe80::2', position='0,0,0')
    dr3 = net.addStation('dr3', mac='00:00:00:00:00:03', ip='10.0.0.3/8',
                         ip6='fe80::3', position='0,0,0')
    br1 = net.addSwitch('br1')

    net.setPropagationModel(model="logDistance", exp=4.5)

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Creating links\n")
    # MANET routing protocols supported by proto:
    # babel, batman_adv, batmand and olsr
    # WARNING: we may need to stop Network Manager if you want
    # to work with babel
    protocols = ['babel', 'batman_adv', 'batmand', 'olsrd', 'olsrd2']
    kwargs = dict()
    for proto in args:
        if proto in protocols:
            kwargs['proto'] = proto

    net.addLink(dr1, cls=adhoc, intf='dr1-wlan0',
                ssid='adhocNet', mode='g', channel=5, 
                ht_cap='HT40+', **kwargs)

    net.addLink(dr2, cls=adhoc, intf='dr2-wlan0',
                ssid='adhocNet', mode='g', channel=5, 
                ht_cap='HT40+', **kwargs)

    net.addLink(dr3, cls=adhoc, intf='dr3-wlan0',
                ssid='adhocNet', mode='g', channel=5, 
                ht_cap='HT40+', **kwargs)

    net.addLink(dr1, br1)
    net.addLink(dr2, br1)
    net.addLink(dr3, br1)

    info("*** Starting network\n")
    net.start()

    #Starting connection to sflow-rt for traffic monitoring
    for dr in net.stations:
        dr.cmd('tc qdisc add dev {}-wlan0 handle 1: root prio'.format(dr.name))
        dr.cmd('tc qdisc add dev {}-wlan0 handle ffff: ingress'.format(dr.name))
        dr.cmd('tc filter add dev {}-wlan0 parent 1: protocol all u32 match u32 '
               '0 0 action mirred egress mirror dev {}-eth1'.format(dr.name, dr.name))
        dr.cmd('tc filter add dev {}-wlan0 parent ffff: protocol all u32 match u32 '
               '0 0 action mirred egress mirror dev {}-eth1'.format(dr.name, dr.name))

    #Starting connection to Coppeliasim for topology generation
    #nodes = net.stations
    #telemetry(nodes=nodes, single=True, data_type='position')

    sta_drone = []
    for n in net.stations:
        sta_drone.append(n.name)
    sta_drone_send = ' '.join(map(str, sta_drone))

    # # set_socket_ip: localhost must be replaced by ip address
    # # of the network interface of your system
    # # The same must be done with socket_client.py
    info("*** \n Starting Socket Server\n")
    net.socketServer(ip='127.0.0.1', port=12345)
 
    info("*** Starting CoppeliaSim\n")
    path = os.path.dirname(os.path.abspath(__file__))
    os.system('{}/CoppeliaSim_Edu_V4_1_0_Ubuntu18_04/coppeliaSim.sh -s {}'
              '/simulation.ttt -gGUIITEMS_2 &'.format(path, path))
    time.sleep(10)

    info("*** Perform a simple test\n")
    simpleTest = 'python {}/simpleTest.py '.format(path) + sta_drone_send + ' &'
    os.system(simpleTest)

    time.sleep(5)

    info("*** Configure the node position\n")
    setNodePosition = 'python {}/setNodePosition.py '.format(path) + sta_drone_send + ' &'
    os.system(setNodePosition)

    info("*** Running sflow-rt\n")
    sflow_rt([br1], net.stations)

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    kill_process()
    net.stop()


def sflow_rt(br, drones):
    ifname = 'lo'
    collector = environ.get('COLLECTOR', '127.0.0.1')
    sampling = environ.get('SAMPLING', '10')
    polling = environ.get('POLLING', '10')
    sflow = 'ovs-vsctl -- --id=@sflow create sflow agent=%s target=%s ' \
            'sampling=%s polling=%s --' % (ifname, collector, sampling, polling)

    for b in br:
        sflow += ' -- set bridge %s sflow=@sflow' % b
        quietRun(sflow)

    agent = '127.0.0.1'
    topo = {'nodes': {}, 'links': {}}
    for b in br:
        topo['nodes'][b.name] = {'agent': agent, 'ports': {}}

    path = '/sys/devices/virtual/net/'
    for child in listdir(path):
        node = child[:3]
        if node in topo['nodes']:
            ifindex = open(path + child + '/ifindex').read().split('\n', 1)[0]
            topo['nodes'][node]['ports'][child] = {'ifindex': ifindex}

    for id, b1 in enumerate(br):
        if id < len(br) - 1:
            b2 = drones[id + 1]
            linkName = '{}-{}'.format(b1.name, b2.name)
            topo['links'][linkName] = {'node1': b1.name, 'port1': b1.intfs[0].name,
                                       'node2': b2.name, 'port2': b2.intfs[0].name}

    put('http://127.0.0.1:8008/topology/json', data=dumps(topo))


def kill_process():
    os.system('pkill -9 -f coppeliaSim')
    os.system('pkill -9 -f simpleTest.py')
    os.system('pkill -9 -f setNodePosition.py')
    os.system('rm examples/uav/data/*')


if __name__ == '__main__':
    setLogLevel('info')
    # Killing old processes
    kill_process()
    topology(sys.argv)
