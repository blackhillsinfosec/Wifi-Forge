"""
    Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)"""

import re
from time import sleep
from six import string_types

from mininet.util import macColonHex, waitListening, ipAdd, netParse
from mininet.log import error, debug, output

from mn_wifi.wwan.link import WWANLink
from mn_wifi.wwan.node import WWANNode
from mn_wifi.wwan.module import module


class Mininet_WWAN(object):

    def __init__(self, modem=WWANNode, ipBase='10.0.0.0/8'):

        self.modem = modem
        self.ipBase = ipBase
        self.ipBaseNum, self.prefixLen = netParse(ipBase)
        #self.nextIP = 1  # start for address allocation
        self.apmodems = []
        self.modems = []
        self.nwwans = 0

    def init_wwan_module(self, wwan_module):
        modems = self.modems + self.apmodems
        module(modems, self.nwwans, wwan_module)
        return self.modems

    def pos_to_array(self, node):
        pos = node.params['position']
        if isinstance(pos, string_types):
            pos = pos.split(',')
        node.position = [float(pos[0]), float(pos[1]), float(pos[2])]
        node.params.pop('position', None)

    def configureWWANLink(self):
        modems = self.modems
        for modem in modems:
            for wwan in range(len(modem.params['wwan'])):
                WWANLink(modem, wwan, port=1)

    def get_wwans(self, **params):
        "Count the number of virtual wwan interfaces"
        return params.get('wwans', 1)

    def manage_wwan(self, node, **params):
        """gets number of wwans
        node: node
        params: parameters"""
        node.params['wwan'] = []
        wwans = self.get_wwans(**params)
        self.nwwans += wwans

        for wwan in range(wwans):
            node.params['wwan'].append(node.name + '-wwan' + str(wwan))
            node.params.pop("wwans", None)

    """def addWWANAPSensor(self, name, cls=None, **params):
        Add AccessPoint as a Sensor.
           name: name of accesspoint to add
           cls: custom switch class/constructor (optional)
           returns: added accesspoint
           side effect: increments listenPort var .
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

        self.manage_wwan(ap, **defaults)
        self.apmodems.append(ap)
        return ap"""

    def addModem(self, name, cls=None, **params):
        """Add Modem node.
           name: name of station to add
           cls: custom wwan class/constructor (optional)
           params: parameters for wwan
           returns: added station"""
        # Default IP and MAC addresses
        defaults = {'ip': ipAdd(self.nextIP,
                                  ipBaseNum=self.ipBaseNum,
                                  prefixLen=self.prefixLen) +
                           '/%s' % self.prefixLen
                   }
        defaults.update(params)

        if self.autoSetPositions:
            defaults['position'] = ('%s,0,0' % self.nextPos_sta)
        if self.autoSetMacs:
            defaults['mac'] = macColonHex(self.nextIP)
        if self.autoPinCpus:
            defaults['cores'] = self.nextCore
            self.nextCore = (self.nextCore + 1) % self.numCores
        self.nextIP += 1
        self.nextPos_sta += 1

        if not cls:
            cls = WWANNode
        node = cls(name, **defaults)
        self.nameToNode[name] = node

        if 'position' in params:
            self.pos_to_array(node)

        self.manage_wwan(node, **defaults)
        self.modems.append(node)
        return node

    def ping(self, hosts=None, timeout=None):
        """Ping between all specified hosts.
           hosts: list of hosts
           timeout: time to wait for a response, as string
           returns: ploss packet loss percentage"""
        # should we check if running?
        packets = 0
        lost = 0
        ploss = None
        if not hosts:
            hosts = self.modems
            output('*** Ping: testing ping reachability\n')
        for node in hosts:
            output('%s -> ' % node.name)
            for dest in hosts:
                if node != dest:
                    opts = ''
                    if timeout:
                        opts = '-W %s' % timeout
                    if dest.intfs:
                        result = node.cmdPrint('ping -c1 %s %s'
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
        return self.ping(timeout=timeout)

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
        nodes = self.modems
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

    def closeMininetWiFi(self):
        "Close Mininet-WiFi"
        module.stop()