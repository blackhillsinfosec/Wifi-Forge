#!/usr/bin/python

"""
You need to activate the following apps if you want to run this code with ONOS:

onos> app activate fwd drivers.bmv2 drivers.mellanox pipelines.fabric
      proxyarp lldpprovider hostprovider segmentrouting
"""


import os
import sys

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.bmv2 import P4AP, P4Host
from mininet.node import RemoteController


def topology(remote_controller):
    'Create a network.'
    net = Mininet_wifi()

    info('*** Adding stations/hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1', cls=P4Host, mac="00:00:00:00:00:01")
    h2 = net.addHost('h2', ip='10.0.0.2', cls=P4Host, mac="00:00:00:00:00:02")
    sta1 = net.addStation('sta1', ip='10.0.0.3', mac="00:00:00:00:00:03")
    sta2 = net.addStation('sta2', ip='10.0.0.4', mac="00:00:00:00:00:04")

    args1 = dict()
    args2 = dict()
    if not remote_controller:
        path = os.path.dirname(os.path.abspath(__file__))
        json_file = path + '/ap-runtime.json'
        config1 = path + '/commands_ap1.txt'
        config2 = path + '/commands_ap2.txt'
        args1 = {'json': json_file, 'switch_config': config1}
        args2 = {'json': json_file, 'switch_config': config2}

    info('*** Adding P4APs\n')
    ap1 = net.addAccessPoint('ap1', cls=P4AP, netcfg=True, **args1)
    ap2 = net.addAccessPoint('ap2', cls=P4AP, netcfg=True, **args2)

    if remote_controller:
        info('*** Adding Controller\n')
        net.addController('c0', controller=RemoteController)

    net.configureNodes()

    info('*** Creating links\n')
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap2)
    net.addLink(h1, ap1)
    net.addLink(h2, ap2)

    info('*** Starting network\n')
    net.start()
    if not remote_controller:
        net.staticArp()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    remote_controller = True if '-r' in sys.argv else False
    topology(remote_controller)
