"""
    Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)"""

import re
from time import sleep
from six import string_types

from mininet.util import macColonHex, waitListening
from mininet.log import error, debug, output

from mn_wifi.sixLoWPAN.link import LowPANLink
from mn_wifi.sixLoWPAN.node import LowPANNode, OVSSensor
from mn_wifi.sixLoWPAN.module import module
from mn_wifi.sixLoWPAN.util import ipAdd6, netParse6


class Mininet_IoT(object):

    def __init__(self, apsensor=OVSSensor, sensor=LowPANNode,
                 ip6Base='2001:0:0:0:0:0:0:0/64'):

        self.apsensor = apsensor
        self.sensor = sensor
        self.ip6Base = ip6Base
        self.ip6BaseNum, self.prefixLen6 = netParse6(ip6Base)
        self.nextIP6 = 1  # start for address allocation
        self.apsensors = []
        self.sensors = []
        self.nwpans = 0

    def init_6lowpan_module(self, iot_module):
        sensors = self.sensors + self.apsensors
        module(sensors, self.nwpans, iot_module)
        return self.sensors, self.apsensors

    def pos_to_array(self, node):
        pos = node.params['position']
        if isinstance(pos, string_types):
            pos = pos.split(',')
        node.position = [float(pos[0]), float(pos[1]), float(pos[2])]
        node.params.pop('position', None)

    def configure6LowPANLink(self):
        sensors = self.sensors + self.apsensors
        for sensor in sensors:
            for wpan in range(len(sensor.params['wpan'])):
                port = 0 if isinstance(sensor, OVSSensor) else 1
                LowPANLink(sensor, wpan, port=port)

    def get_wpans(self, **params):
        "Count the number of virtual LoWPAN interfaces"
        return params.get('wpans', 1)

    def manage_wpan(self, node, **params):
        """gets number of wpans
        node: node
        params: parameters"""
        node.params['wpan'] = []
        wpans = self.get_wpans(**params)
        self.nwpans += wpans

        for wpan in range(wpans):
            node.params['wpan'].append(node.name + '-wpan' + str(wpan))
            node.params.pop("wpans", None)

    def addAPSensor(self, name, cls=None, **params):
        """Add AccessPoint as a Sensor.
           name: name of accesspoint to add
           cls: custom switch class/constructor (optional)
           returns: added accesspoint
           side effect: increments listenPort var ."""
        defaults = {'listenPort': self.listenPort,
                    'inNamespace': self.inNamespace
                    }
        defaults.update(params)
        if self.autoSetPositions:
            defaults['position'] = (round(self.nextPos_ap, 2), 50, 0)
            self.nextPos_ap += 100

        if not cls:
            cls = self.apsensor
        ap = cls(name, **defaults)
        if not self.inNamespace and self.listenPort:
            self.listenPort += 1
        self.nameToNode[name] = ap

        if 'position' in params:
            self.pos_to_array(ap)

        self.manage_wpan(ap, **defaults)
        self.apsensors.append(ap)
        return ap

    def addSensor(self, name, cls=None, **params):
        """Add Sensor node.
           name: name of station to add
           cls: custom 6LoWPAN class/constructor (optional)
           params: parameters for 6LoWPAN
           returns: added station"""
        # Default IP and MAC addresses
        defaults = {'ip6': ipAdd6(self.nextIP6,
                                  ipBaseNum=self.ip6BaseNum,
                                  prefixLen=self.prefixLen6) +
                           '/%s' % self.prefixLen6
                   }
        defaults.update(params)

        if self.autoSetPositions:
            defaults['position'] = ('%s,0,0' % self.nextPos_sta)
        if self.autoSetMacs:
            defaults['mac'] = macColonHex(self.nextIP6)
        if self.autoPinCpus:
            defaults['cores'] = self.nextCore
            self.nextCore = (self.nextCore + 1) % self.numCores
        self.nextIP6 += 1
        self.nextPos_sta += 1

        if not cls:
            cls = LowPANNode
        node = cls(name, **defaults)
        self.nameToNode[name] = node

        if 'position' in params:
            self.pos_to_array(node)

        self.manage_wpan(node, **defaults)
        self.sensors.append(node)
        return node

    def configRPLD(self, nodes):
        sleep(2)
        for node in nodes:
            node.configRPLD()

    def ping6(self, hosts=None, timeout=None):
        """Ping6 between all specified hosts.
           hosts: list of hosts
           timeout: time to wait for a response, as string
           returns: ploss packet loss percentage"""
        # should we check if running?
        packets = 0
        lost = 0
        ploss = None
        if not hosts:
            hosts = self.sensors
            output('*** Ping: testing ping reachability\n')
        for node in hosts:
            output('%s -> ' % node.name)
            for dest in hosts:
                if node != dest:
                    opts = ''
                    if timeout:
                        opts = '-W %s' % timeout
                    if dest.intfs:
                        result = node.cmdPrint('ping6 -c1 %s %s'
                                               % (opts, dest.IP()))
                        sent, received = self._parsePing(result)
                    else:
                        sent, received = 0, 0
                    packets += sent
                    if received > sent:
                        error('*** Error: received too many packets')
                        error('%s' % result)
                        node.cmdPrint('route')
                        exit(1)
                    lost += sent - received
                    output(('%s ' % dest.name) if received else 'X ')
            output('\n')
        if packets > 0:
            ploss = 100.0 * lost / packets
            received = packets - lost
            output("*** Results: %i%% dropped (%d/%d received)\n" %
                   (ploss, received, packets))
        else:
            ploss = 0
            output("*** Warning: No packets sent\n")
        return ploss

    def pingAll(self, timeout=None):
        """Ping between all hosts.
           returns: ploss packet loss percentage"""
        return self.ping6(timeout=timeout)

    def iperf(self, hosts=None, l4Type='TCP', udpBw='10M', fmt=None,
              seconds=5, port=5001):
        """Run iperf between two hosts.
           hosts: list of hosts; if None, uses first and last hosts
           l4Type: string, one of [ TCP, UDP ]
           udpBw: bandwidth target for UDP test
           fmt: iperf format argument if any
           seconds: iperf time to transmit
           port: iperf port
           returns: two-element array of [ server, client ] speeds
           note: send() is buffered, so client rate can be much higher than
           the actual transmission rate; on an unloaded system, server
           rate should be much closer to the actual receive rate"""
        sleep(2)
        nodes = self.sensors
        hosts = hosts or [nodes[0], nodes[-1]]
        assert len(hosts) == 2
        client, server = hosts
        output('*** Iperf: testing', l4Type, 'bandwidth between',
               client, 'and', server, '\n')
        server.cmd('killall -9 iperf')
        iperfArgs = 'iperf -p %d ' % port
        bwArgs = ''
        if l4Type == 'UDP':
            iperfArgs += '-u '
            bwArgs = '-b ' + udpBw + ' '
        elif l4Type != 'TCP':
            raise Exception('Unexpected l4 type: %s' % l4Type)
        if fmt:
            iperfArgs += '-f %s ' % fmt
        server.sendCmd(iperfArgs + '-s')
        if l4Type == 'TCP':
            if not waitListening(client, server.IP(), port):
                raise Exception('Could not connect to iperf on port %d'
                                % port)
        cliout = client.cmd(iperfArgs + '-t %d -c ' % seconds +
                            server.IP() + ' ' + bwArgs)
        debug('Client output: %s\n' % cliout)
        servout = ''
        # We want the last *b/sec from the iperf server output
        # for TCP, there are two of them because of waitListening
        count = 2 if l4Type == 'TCP' else 1
        while len(re.findall('/sec', servout)) < count:
            servout += server.monitor(timeoutms=5000)
        server.sendInt()
        servout += server.waitOutput()
        debug('Server output: %s\n' % servout)
        result = [self._parseIperf(servout), self._parseIperf(cliout)]
        if l4Type == 'UDP':
            result.insert(0, udpBw)
        output('*** Results: %s\n' % result)
        return result

    @staticmethod
    def kill_fakelb():
        "Kill fakelb"
        module.fakelb()
        sleep(0.1)

    def closeMininetWiFi(self):
        "Close Mininet-WiFi"
        module.stop()
