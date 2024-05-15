"""
    Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
    author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)
"""

import re
import socket

from itertools import chain, groupby
from threading import Thread as thread
from time import sleep
from sys import exit

from mininet.cli import CLI
from mininet.link import Link, TCLink, TCULink
from mininet.log import info, error, debug, output, warn
from mininet.net import Mininet
from mininet.node import Node
from mininet.nodelib import NAT
from mininet.term import makeTerms
from mininet.util import (macColonHex, ipStr, ipParse, ipAdd,
                          waitListening, BaseString)
from six import string_types

from mn_wifi.clean import Cleanup as CleanupWifi
from mn_wifi.energy import Energy
from mn_wifi.link import IntfWireless, wmediumd, _4address, HostapdConfig, \
    WirelessLink, TCWirelessLink, ITSLink, WifiDirectLink, adhoc, mesh, \
    master, managed, physicalMesh, PhysicalWifiDirectLink, _4addrClient, \
    _4addrAP, phyAP
from mn_wifi.mobility import Tracked as TrackedMob, model as MobModel, \
    Mobility as mob, ConfigMobility, ConfigMobLinks
from mn_wifi.module import Mac80211Hwsim
from mn_wifi.node import AP, Station, Car, OVSKernelAP, physicalAP
from mn_wifi.plot import Plot2D, Plot3D, PlotGraph
from mn_wifi.propagationModels import PropagationModel as ppm
from mn_wifi.sixLoWPAN.link import LowPANLink, LoWPAN
from mn_wifi.sixLoWPAN.net import Mininet_IoT
from mn_wifi.sixLoWPAN.node import OVSSensor, LowPANNode
from mn_wifi.sixLoWPAN.util import ipAdd6
from mn_wifi.telemetry import parseData, telemetry as run_telemetry
from mn_wifi.vanet import vanet
from mn_wifi.wmediumdConnector import error_prob, snr, interference
from mn_wifi.wwan.link import WWANLink
from mn_wifi.wwan.net import Mininet_WWAN
from mn_wifi.wwan.node import WWANNode

VERSION = "2.6"


class Mininet_wifi(Mininet, Mininet_IoT, Mininet_WWAN):

    def __init__(self, accessPoint=OVSKernelAP, station=Station, car=Car,
                 sensor=LowPANNode, apsensor=OVSSensor, modem=WWANNode, link=WirelessLink,
                 ssid="new-ssid", mode="g", encrypt="", passwd=None, ieee80211w=None,
                 channel=1, freq=2.4, band=20, wmediumd_mode=snr, roads=0, fading_cof=0,
                 autoAssociation=True, allAutoAssociation=True, autoSetPositions=False,
                 configWiFiDirect=False, config4addr=False, noise_th=-91, cca_th=-90,
                 disable_tcp_checksum=False, ifb=False, client_isolation=False,
                 plot=False, plot3d=False, docker=False, container='mininet-wifi',
                 ssh_user='alpha', rec_rssi=False, iot_module='mac802154_hwsim',
                 wwan_module='wwan_hwsim', json_file=None, ac_method=None, **kwargs):
        """Create Mininet object.

           accessPoint: default Access Point class
           station: default Station class/constructor
           car: default Car class/constructor
           sensor: default Sensor class/constructor
           apsensor: default AP Sensor class/constructor
           modem: default Modem class/constructor
           link: default Link class/constructor
           ieee80211w: enable ieee80211w
           ssid: wifi ssid
           mode: wifi mode
           encrypt: wifi encrypt protocol
           passwd: passphrase
           channel: wifi channel
           freq: wifi freq
           band: bandwidth channel
           wmediumd_mode: default wmediumd mode
           roads: number of roads
           fading_cof: fadding coefficient
           autoSetPositions: auto set positions
           configWiFiDirect: configure wifi direct
           config4addr: configure 4 address
           noise_th: noise threshold
           cca_th: cca threshold
           ifb: Intermediate Functional Block
           client_isolation: enables client isolation
           plot: plot graph
           plot3d: plot3d graph
           iot_module: default iot module
           wwan_module: default wwan module
           rec_rssi: sends rssi to mac80211_hwsim by using hwsim_mgmt
           json_file: json file dir - useful for P4
           ac_method: association control method"""
        self.station = station
        self.accessPoint = accessPoint
        self.car = car
        self.nextPos_sta = 1  # start for sta position allocation
        self.nextPos_ap = 1  # start for ap position allocation
        self.autoSetPositions = autoSetPositions
        self.ssid = ssid
        self.mode = mode
        self.encrypt = encrypt
        self.passwd = passwd
        self.ieee80211w = ieee80211w
        self.channel = channel
        self.freq = freq
        self.band = band
        self.wmediumd_mode = wmediumd_mode
        self.aps = []
        self.cars = []
        self.stations = []
        self.autoAssociation = autoAssociation  # does not include mobility
        self.allAutoAssociation = allAutoAssociation  # includes mobility
        self.draw = False
        self.isReplaying = False
        self.reverse = False
        self.alt_module = None
        self.mob_check = False
        self.mob_model = None
        self.ac_method = ac_method
        self.docker = docker
        self.container = container
        self.ssh_user = ssh_user
        self.ifb = ifb  # Support to Intermediate Functional Block (IFB) Devices
        self.json_file = json_file
        self.client_isolation = client_isolation
        self.init_plot = plot
        self.init_Plot3D = plot3d
        self.cca_th = cca_th
        self.configWiFiDirect = configWiFiDirect
        self.config4addr = config4addr
        self.fading_cof = fading_cof
        self.noise_th = noise_th
        self.disable_tcp_checksum = disable_tcp_checksum
        self.plot = Plot2D
        self.rec_rssi = rec_rssi
        self.roads = roads
        self.iot_module = iot_module
        self.wwan_module = wwan_module
        self.ifbIntf = 0
        self.mob_start_time = 0
        self.mob_stop_time = 0
        self.mob_rep = 1
        self.seed = 1
        self.min_v = 1
        self.max_v = 10
        self.min_x = 0
        self.min_y = 0
        self.min_z = 0
        self.max_x = 100
        self.max_y = 100
        self.max_z = 0
        self.min_wt = 1
        self.max_wt = 5
        self.n_groups = 1
        self.wlinks = []
        self.pointlist = []
        self.initial_mediums = []

        if autoSetPositions and link == wmediumd:
            self.wmediumd_mode = interference

        if not allAutoAssociation:
            self.autoAssociation = False
            mob.allAutoAssociation = False

        # we need this for scenarios where there is no mobility
        if self.ac_method:
            mob.ac = self.ac_method

        Mininet_IoT.__init__(self, sensor=sensor, apsensor=apsensor)
        Mininet_WWAN.__init__(self, modem=modem)
        Mininet.__init__(self, link=link, **kwargs)

    def socketServer(self, **kwargs):
        thread(target=self.start_socket, kwargs=kwargs).start()

    def start_socket(self, ip='127.0.0.1', port=12345):
        CleanupWifi.socket_port = port

        if ':' in ip:
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ip, port))
        s.listen(1)

        while True:
            conn, addr = s.accept()
            try:
                thread(target=self.get_socket_data, args=(conn, addr)).start()
            except:
                info("Thread did not start.\n")

    def get_socket_data(self, conn, addr):
        while True:
            try:
                cmd = conn.recv(1024).decode('utf-8')
                pos = None
                if 'setPosition' in cmd:
                    pos = cmd.split('("')[1].split(')"')[0][:-2]
                data = cmd.split('.')
                if data[0] == 'set':
                    node = self.getNodeByName(data[1])
                    if len(data) < 3:
                        data = 'usage: set.node.method()'
                    else:
                        if data[2] == 'sumo':
                            mod = __import__('mn_wifi.sumo.function', fromlist=[data[3]])
                            method_to_call = getattr(mod, data[3])
                            node = self.getNodeByName(data[1])
                            node.sumo = method_to_call
                            node.sumoargs = str(data[4])
                            data = 'command accepted!'
                        else:
                            attr = data[2].split('(')
                            if hasattr(node, attr[0]):
                                method_to_call = getattr(node, attr[0])
                                if 'intf' in attr[1]:
                                    val = attr[1].split(', intf=')
                                    intf = val[1][:-1]
                                    val = val[0]
                                    method_to_call(val, intf=intf)
                                else:
                                    val = pos if pos else attr[1].split(')')[0]
                                    method_to_call(val.replace('"', '').replace("'", ""))
                                    data = 'command accepted!'
                            else:
                                data = 'unrecognized method!'
                elif data[0] == 'get':
                    node = self.getNodeByName(data[1])
                    if len(data) < 3:
                        data = 'usage: get.node.attr'
                    else:
                        if 'wintfs' in data[2]:
                            i = int(data[2][7:-1])
                            wintfs = getattr(node, 'wintfs')[i]
                            data = getattr(wintfs, data[3])
                        else:
                            data = getattr(node, data[2])
                else:
                    try:
                        cmd = ''
                        for d in range(1, len(data)):
                            cmd = cmd + data[d] + ' '
                        node = self.getNodeByName(data[0])
                        node.pexec(cmd)
                        data = 'command accepted!'
                    except:
                        data = 'unrecognized option {}:'.format(data[0])
                conn.send(str(data).encode('utf-8'))
                break
            except:
                conn.close()

    def waitConnected(self, timeout=None, delay=.5):
        """wait for each switch to connect to a controller,
           up to 5 seconds
           timeout: time to wait, or None to wait indefinitely
           delay: seconds to sleep per iteration
           returns: True if all switches are connected"""
        info('*** Waiting for switches/aps to connect\n')
        time = 0
        L2nodes = self.switches + self.aps + self.apsensors + self.modems
        remaining = list(L2nodes)
        while True:
            for switch in tuple(remaining):
                if switch.connected():
                    info(switch)
                    remaining.remove(switch)
            if not remaining:
                info('\n')
                return True
            if timeout is not None and time > timeout:
                break
            sleep(delay)
            time += delay
        warn('Timed out after {} seconds\n'.format(time))
        for switch in remaining:
            if not switch.connected():
                warn('Warning: {} is not connected '
                     'to a controller\n'.format(switch.name))
            else:
                remaining.remove(switch)
        return not remaining

    def delNode(self, node, nodes=None):
        """Delete node
           node: node to delete
           nodes: optional list to delete from (e.g. self.hosts)"""
        if nodes is None:
            nodes = (self.hosts if node in self.hosts else
                     (self.switches if node in self.switches else
                      (self.controllers if node in self.controllers else [])))
        node.stop(deleteIntfs=True)
        node.terminate()
        nodes.remove(node)
        del self.nameToNode[node.name]

    def pos_to_array(self, node):
        pos = node.params['position']
        if isinstance(pos, string_types):
            pos = pos.split(',')
        #adds a dummy z-axis to avoid out of boundary errors
        if len(pos) == 2:
            pos.append(0)
            
        node.position = [float(pos[0]), float(pos[1]), float(pos[2])]
        node.params.pop('position', None)

    def count_ifaces(self):
        "Count the number of virtual wifi interfaces"
        nodes = self.stations + self.cars + self.aps
        nradios = 0
        for node in nodes:
            nradios += len(node.params['wlan'])
        return nodes, nradios

    def config_runtime_node(self, node):
        self.configNode(node)
        node.wmIfaces = []
        for intf in node.wintfs.values():
            intf.ipLink('up')
            if isinstance(node, AP):
                self.configMasterIntf(node, intf.id)
                if not intf.mac:
                    intf.mac = intf.getMAC()
                intf.setMAC(intf.mac)
                intf = node.wintfs[intf.id]
                HostapdConfig(intf)
            else:
                intf.setMAC(intf.mac)
                intf.setIP(intf.ip, intf.prefixLen)
            if self.link == wmediumd:
                intf.sendIntfTowmediumd()
            if self.draw or hasattr(node, 'position'):
                intf.setTxPower(intf.txpower)
                intf.setAntennaGain(intf.antennaGain)
                intf.node.lastpos = 0, 0, 0
                if self.draw:
                    self.plot.instantiate_attrs(node)

    def addWlans(self, node):
        node.params['wlan'] = []
        wlans = node.params.get('wlans', 1)
        for wlan in range(wlans):
            wlan_id = wlan
            if isinstance(node, AP):
                wlan_id += 1
            node.params['wlan'].append(node.name + '-wlan' + str(wlan_id))
        node.params.pop("wlans", None)

        # creates hwsim interfaces on the fly
        if Mac80211Hwsim.hwsim_ids:
            Mac80211Hwsim(node=node, on_the_fly=True)
            self.config_runtime_node(node)

    def addStation(self, name, cls=None, **params):
        """Add Station.
           name: name of station to add
           cls: custom host class/constructor (optional)
           params: parameters for station
           returns: added station"""
        # Default IP and MAC addresses
        defaults = {'ip': ipAdd(self.nextIP,
                                ipBaseNum=self.ipBaseNum,
                                prefixLen=self.prefixLen) +
                          '/{}'.format(self.prefixLen),
                    'ip6': ipAdd6(self.nextIP6,
                                  ipBaseNum=self.ip6BaseNum,
                                  prefixLen=self.prefixLen6) +
                          '/{}'.format(self.prefixLen6),
                    'channel': self.channel,
                    'band': self.band,
                    'freq': self.freq,
                    'mode': self.mode,
                    'encrypt': self.encrypt,
                    'passwd': self.passwd,
                    'ieee80211w': self.ieee80211w
                   }
        defaults.update(params)

        if self.autoSetPositions and 'position' not in params:
            defaults['position'] = [round(self.nextPos_sta, 2), 0, 0]
        if self.autoSetMacs:
            defaults['mac'] = macColonHex(self.nextIP)
        if self.autoPinCpus:
            defaults['cores'] = self.nextCore
            self.nextCore = (self.nextCore + 1) % self.numCores
        self.nextIP += 1
        self.nextIP6 += 1
        self.nextPos_sta += 2

        if not cls:
            cls = self.station
        sta = cls(name, **defaults)

        if 'position' in params or self.autoSetPositions:
            self.pos_to_array(sta)

        self.addWlans(sta)
        self.stations.append(sta)
        self.nameToNode[name] = sta
        return sta

    def addCar(self, name, cls=None, **params):
        """Add Car.
           name: name of vehicle to add
           cls: custom host class/constructor
           params: parameters for car
           returns: added car"""
        # Default IP and MAC addresses
        defaults = {'ip': ipAdd(self.nextIP,
                                ipBaseNum=self.ipBaseNum,
                                prefixLen=self.prefixLen) +
                          '/{}'.format(self.prefixLen),
                    'ip6': ipAdd6(self.nextIP6,
                                  ipBaseNum=self.ip6BaseNum,
                                  prefixLen=self.prefixLen6) +
                          '/{}'.format(self.prefixLen6),
                    }

        if self.autoSetMacs:
            defaults['mac'] = macColonHex(self.nextIP)
        if self.autoPinCpus:
            defaults['cores'] = self.nextCore
            self.nextCore = (self.nextCore + 1) % self.numCores
        defaults.update(params)

        self.nextIP += 1
        self.nextIP6 += 1
        if not cls:
            cls = self.car
        car = cls(name, **defaults)

        if 'position' in params:
            self.pos_to_array(car)

        self.addWlans(car)
        self.cars.append(car)
        self.nameToNode[name] = car

        return car

    def addAccessPoint(self, name, cls=None, **params):
        """Add AccessPoint.
           name: name of accesspoint to add
           cls: custom switch class/constructor (optional)
           returns: added accesspoint
           side effect: increments listenPort var ."""
        defaults = {'listenPort': self.listenPort,
                    'inNamespace': self.inNamespace,
                    'ssid': self.ssid,
                    'channel': self.channel,
                    'band': self.band,
                    'freq': self.freq,
                    'mode': self.mode,
                    'encrypt': self.encrypt,
                    'passwd': self.passwd,
                    'ieee80211w': self.ieee80211w
                    }
        if self.client_isolation:
            defaults['client_isolation'] = True
        if self.json_file:
            defaults['json'] = self.json_file
        defaults.update(params)
        if self.autoSetMacs:
            defaults['mac'] = macColonHex(self.nextIP)
            self.nextIP += 1
        if self.autoSetPositions:
            defaults['position'] = [round(self.nextPos_ap, 2), 50, 0]
            self.nextPos_ap += 100
        wlan = None
        if cls and isinstance(cls, physicalAP):
            wlan = params.pop('phywlan', {})
            cls = self.accessPoint
        if not cls:
            cls = self.accessPoint
        ap = cls(name, **defaults)
        if not self.inNamespace and self.listenPort:
            self.listenPort += 1
        self.nameToNode[name] = ap
        if wlan:
            ap.params['phywlan'] = wlan
        if 'position' in params or self.autoSetPositions:
            self.pos_to_array(ap)
        self.addWlans(ap)
        self.aps.append(ap)
        return ap

    def setStaticRoute(self, node, ip=None, **params):
        """Set the static route to go through intf.
           net: subnet address"""
        # Note setParam won't call us if intf is none
        if isinstance(ip, BaseString) and ' ' in ip:
            params = ip
        else:
            natIP = ip.split('/')[0]
            params = '{} via {}'.format(params['net'], natIP)
        # Do this in one line in case we're messing with the root namespace
        node.cmd('ip route add', params)

    def addNAT(self, name='nat0', connect=True, inNamespace=False,
               linkTo=None, **params):
        """Add a NAT to the Mininet network
           name: name of NAT node
           connect: switch to connect to | True (s1) | None
           inNamespace: create in a network namespace
           params: other NAT node params, notably:
               ip: used as default gateway address"""
        nat = self.addHost(name, cls=NAT, inNamespace=inNamespace,
                           subnet=self.ipBase, **params)
        # find first ap and create link
        if connect:
            if not isinstance(connect, Node):
                if linkTo:
                    nodes = self.switches + self.aps + self.apsensors + self.modems
                    for node in nodes:
                        if linkTo == node.name:
                            connect = node
                else:
                    if self.switches:
                        connect = self.switches[0]
                    elif self.aps:
                        connect = self.aps[0]
            # Connect the nat to the ap
            self.addLink(nat, connect)
            # Set the default route on stations
            natIP = nat.params['ip'].split('/')[0]
            nodes = self.stations + self.hosts + self.cars + self.sensors + self.modems
            if 'net' in params:
                for node in nodes:
                    if node.inNamespace:
                        self.setStaticRoute(node, '{} via {}'.format(params['net'], natIP))
            else:
                for node in nodes:
                    if node.inNamespace:
                        if isinstance(node, self.sensor) or isinstance(node, self.apsensor):
                            node.setDefault6Route('via {}'.format(natIP))
                        else:
                            node.setDefaultRoute('via {}'.format(natIP))
        return nat

    def __iter__(self):
        "return iterator over node names"
        for node in chain(self.hosts, self.switches, self.controllers,
                          self.stations, self.cars, self.aps, self.sensors,
                          self.apsensors, self.modems):
            yield node.name

    def __len__(self):
        "returns number of nodes in net"
        return (len(self.hosts) + len(self.switches) +
                len(self.controllers) + len(self.stations) +
                len(self.cars) + len(self.aps) + len(self.sensors) +
                len(self.apsensors) + len(self.modems))

    def setModule(self, moduleDir):
        "set an alternative module rather than mac80211_hwsim"
        self.alt_module = moduleDir

    def do_association(self, intf, ap_intf):
        dist = intf.node.get_distance_to(ap_intf.node)
        if dist > ap_intf.range:
            return False
        return True

    def get_intf(self, node1, node2, port1=None, port2=None):
        wlan1, wlan2 = 0, 0

        if node1 in self.stations and node2 in self.stations:
            n1 = node1
            n2 = node2
        else:
            n1 = node1 if node2 in self.aps else node2
            n2 = node1 if node1 in self.aps else node2

            if port1 is not None and port2 is not None:
                wlan1 = port1 if node2 in self.aps else port2
                wlan2 = port1 if node1 in self.aps else port2

        intf1 = n1.wintfs[wlan1]
        intf2 = n2.wintfs[wlan2]

        return intf1, intf2

    def infra_wmediumd_link(self, node1, node2, port1=None, port2=None,
                            **params):
        intf1, intf2 = self.get_intf(node1, node2, port1, port2)

        if 'error_prob' not in params:
            intf1.associate(intf2)

        if self.wmediumd_mode == error_prob:
            self.wlinks.append([intf1, intf2, params['error_prob']])
        elif self.wmediumd_mode != interference:
            self.wlinks.append([intf1, intf2])

    def infra_tc(self, node1, node2, port1=None, port2=None,
                 cls=None, **params):
        intf, ap_intf = self.get_intf(node1, node2, port1, port2)
        do_association = True
        if hasattr(intf.node, 'position') and hasattr(ap_intf.node, 'position'):
            do_association = self.do_association(intf, ap_intf)
        if do_association:
            if 'bw' not in params and 'bw' not in str(cls):
                params['bw'] = intf.getCustomRate() if hasattr(intf.node, 'position') else intf.getCustomRate()
            # tc = True, this is useful for tc configuration
            TCWirelessLink(node=intf.node, intfName=intf.name,
                           port=intf.id, cls=cls, **params)
            intf.associate(ap_intf)

    def addLink(self, node1, node2=None, port1=None, port2=None,
                cls=None, **params):
        """"Add a link from node1 to node2
            node1: source node (or name)
            node2: dest node (or name)
            port1: source port (optional)
            port2: dest port (optional)
            cls: link class (optional)
            params: additional link params (optional)
            returns: link object"""

        # Accept node objects or names
        node1 = node1 if not isinstance(node1, string_types) else self[node1]
        node2 = node2 if not isinstance(node2, string_types) else self[node2]
        cls = self.link if cls is None else cls

        modes = [mesh, adhoc, ITSLink, WifiDirectLink, PhysicalWifiDirectLink]
        if cls in modes:
            link = cls(node=node1, **params)
            self.links.append(link)
            if node2 and self.wmediumd_mode == error_prob:
                self.infra_wmediumd_link(node1, node2, **params)
            return link
        elif cls == physicalMesh:
            cls(node=node1, **params)
        elif cls == LowPANLink:
            link = cls(node=node1, port=port1, **params)
            self.links.append(link)
            return link
        elif cls == LoWPAN:
            cls(node1=node1, node2=node2, **params)
        elif cls == WWANLink:
            link = cls(node=node1, port=port1, **params)
            self.links.append(link)
            return link
        elif cls == _4address:
            if self.wmediumd_mode == interference:
                link = cls(node1, node2, port1, port2, **params)
                self.links.append(link)
                return link

            if self.do_association(node1.wintfs[0], node2.wintfs[0]):
                link = cls(node1, node2, **params)
                self.links.append(link)
                return link
        elif ((node1 in self.stations and node2 in self.aps)
              or (node2 in self.stations and node1 in self.aps)) and cls != TCLink:
            if cls == wmediumd:
                self.infra_wmediumd_link(node1, node2, **params)
            else:
                self.infra_tc(node1, node2, port1, port2, cls, **params)
        else:
            if not cls or cls == wmediumd or cls == WirelessLink:
                cls = TCLink
            if self.disable_tcp_checksum:
                cls = TCULink

            Mininet.addLink(self, node1, node2, port1=port1, port2=port2,
                            cls=cls, **params)

    def configHosts(self):
        "Configure a set of nodes."
        nodes = self.hosts + self.sensors + self.modems
        for node in nodes:
            # info( host.name + ' ' )
            intf = node.defaultIntf()
            if intf:
                node.configDefault()
            else:
                # Don't configure nonexistent intf
                node.configDefault(ip=None, mac=None)
                # You're low priority, dude!
                # BL: do we want to do this here or not?
                # May not make sense if we have CPU lmiting...
                # quietRun( 'renice +18 -p ' + repr( host.pid ) )
                # This may not be the right place to do this, but
                # it needs to be done somewhere.
                # info( '\n' )

    def buildFromWirelessTopo(self, topo=None):
        """Build mininet from a topology object
           At the end of this function, everything should be connected
           and up."""
        info('*** Adding stations:\n')
        for staName in topo.stations():
            self.addStation(staName, **topo.nodeInfo(staName))
            info(staName + ' ')

        info('\n*** Adding access points:\n')
        for apName in topo.aps():
            # A bit ugly: add batch parameter if appropriate
            params = topo.nodeInfo(apName)
            cls = params.get('cls', self.accessPoint)
            if hasattr(cls, 'batchStartup'):
                params.setdefault('batch', True)
            self.addAccessPoint(apName, **params)
            info(apName + ' ')

        info('\n*** Configuring nodes...\n')
        self.configureNodes()

        super(Mininet_wifi, self).buildFromTopo(topo)

    def check_if_mob(self):
        if self.mob_model or self.mob_stop_time or self.roads:
            mob_params = self.get_mobility_params()
            stat_nodes, mob_nodes = self.get_mob_stat_nodes()
            method = TrackedMob
            if self.mob_model or self.cars or self.roads:
                method = self.start_mobility
            method(stat_nodes=stat_nodes, mob_nodes=mob_nodes, **mob_params)
            self.mob_check = True
        else:
            if self.draw and not self.isReplaying:
                self.check_dimension(self.get_mn_wifi_nodes())

    def staticArp(self):
        "Add all-pairs ARP entries to remove the need to handle broadcast."
        nodes = self.stations + self.hosts + self.cars
        for src in nodes:
            for dst in nodes:
                if src != dst:
                    src.setARP(ip=dst.IP(), mac=dst.MAC())

    def hasVoltageParam(self):
        nodes = self.get_mn_wifi_nodes()
        energy_nodes = []
        for node in nodes:
            if 'voltage' in node.params:
                energy_nodes.append(node)
        if energy_nodes:
            Energy(energy_nodes)

    def build(self):
        "Build mininet-wifi."
        if self.topo:
            self.buildFromWirelessTopo(self.topo)
            if self.init_plot or self.init_Plot3D:
                max_z = 0
                if self.init_Plot3D:
                    max_z = len(self.stations) * 100
                self.plotGraph(max_x=(len(self.stations) * 100),
                               max_y=(len(self.stations) * 100),
                               max_z=max_z)
        else:
            if not mob.stations:
                for node in self.stations:
                    if hasattr(node, 'position'):
                        mob.stations.append(node)

        if self.config4addr or self.configWiFiDirect or self.wmediumd_mode == error_prob:
            # sync with the current 2nd interface type
            for id, link in enumerate(self.wlinks):
                for node in self.stations:
                    for intf in node.wintfs.values():
                        if intf.name == link[1].name:
                            self.wlinks[id][1] = intf
            self.init_wmediumd()

        if self.inNamespace:
            self.configureControlNetwork()

        debug('*** Configuring nodes\n')
        self.configHosts()
        if self.xterms:
            self.startTerms()
        if self.autoStaticArp:
            self.staticArp()

        if not self.mob_check:
            self.check_if_mob()

        if self.allAutoAssociation:
            if self.autoAssociation and not self.configWiFiDirect:
                self.auto_association()

        self.hasVoltageParam()
        self.built = True

    def startTerms(self):
        "Start a terminal for each node."
        Mininet.startTerms(self)
        self.terms += makeTerms(self.stations, 'station')
        self.terms += makeTerms(self.aps, 'ap')
        self.terms += makeTerms(self.sensors, 'sensor')
        self.terms += makeTerms(self.apsensors, 'apsensor')
        self.terms += makeTerms(self.modems, 'modem')

    def telemetry(self, **kwargs):
        run_telemetry(**kwargs)

    def start(self):
        "Start controller and switches."
        if not self.built:
            self.build()

        if not self.mob_check:
            self.check_if_mob()

        info('*** Starting controller(s)\n')
        for controller in self.controllers:
            info(controller.name + ' ')
            controller.start()
        info('\n')

        info('*** Starting L2 nodes\n')
        nodesL2 = self.switches + self.aps + self.apsensors
        for nodeL2 in nodesL2:
            info(nodeL2.name + ' ')
            nodeL2.start(self.controllers)

        started = {}
        for swclass, switches in groupby(
                sorted(nodesL2, key=lambda x: str(type(x))), type):
            switches = tuple(switches)
            if hasattr(swclass, 'batchStartup'):
                success = swclass.batchStartup(switches)
                started.update({s: s for s in success})
        info('\n')
        if self.waitConn:
            self.waitConnected()

    def stop(self):
        'Stop Mininet-WiFi'
        self.stop_graph_params()
        info('*** Stopping %i controllers\n' % len(self.controllers))
        for controller in self.controllers:
            info(controller.name + ' ')
            controller.stop()
        info('\n')
        if self.terms:
            info('*** Stopping %i terms\n' % len(self.terms))
            self.stopXterms()
        info('*** Stopping %i links\n' % len(self.links))
        for link in self.links:
            info('.')
            link.stop()
        info('\n')
        info('*** Stopping switches/access points\n')
        stopped = {}
        nodesL2 = self.switches + self.aps + self.apsensors
        for swclass, switches in groupby(
                sorted(nodesL2, key=lambda x: str(type(x))), type):
            switches = tuple(switches)
            if hasattr(swclass, 'batchShutdown'):
                success = swclass.batchShutdown(switches)
                stopped.update({s: s for s in success})
        for switch in nodesL2:
            info(switch.name + ' ')
            if switch not in stopped:
                switch.stop()
            switch.terminate()
        info('\n')
        info('*** Stopping nodes\n')
        nodes = self.hosts + self.stations + self.sensors + self.modems
        for node in nodes:
            info(node.name + ' ')
            node.terminate()
        info('\n')
        self.closeMininetWiFi()
        info('\n*** Done\n')

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
            hosts = self.hosts + self.stations + self.sensors + self.modems
            output('*** Ping: testing ping reachability\n')
        for node in hosts:
            output('{} -> '.format(node.name))
            for dest in hosts:
                if node != dest:
                    opts = ''
                    if timeout:
                        opts = '-W {}'.format(timeout)
                    if dest.intfs:
                        cmd = 'ping -c1 {} {}'
                        if isinstance(node, LowPANNode):
                            result = node.cmdPrint(cmd.format(opts, dest.IP6()))
                        else:
                            result = node.cmdPrint(cmd.format(opts, dest.IP()))
                        sent, received = self._parsePing(result)
                    else:
                        sent, received = 0, 0
                    packets += sent
                    if received > sent:
                        error('*** Error: received too many packets')
                        error(result)
                        node.cmdPrint('route')
                        exit(1)
                    lost += sent - received
                    output(('{} '.format(dest.name)) if received else 'X ')
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

    def pingFull(self, hosts=None, timeout=None):
        """Ping between all specified hosts and return all data.
           hosts: list of hosts
           timeout: time to wait for a response, as string
           returns: all ping data; see function body."""
        # should we check if running?
        # Each value is a tuple: (src, dsd, [all ping outputs])
        all_outputs = []
        if not hosts:
            hosts = self.hosts + self.stations
            output('*** Ping: testing ping reachability\n')

        for node in hosts:
            output('{} -> '.format(node.name))
            for dest in hosts:
                if node != dest:
                    opts = ''
                    if timeout:
                        opts = '-W {}'.format(timeout)
                    result = node.cmd('ping -c1 {} {}'.format(opts, dest.IP()))
                    outputs = self._parsePingFull(result)
                    sent, received, rttmin, rttavg, rttmax, rttdev = outputs
                    all_outputs.append((node, dest, outputs))
                    output(dest.name if received else 'X ')
            output('\n')
        output("*** Results: \n")
        for outputs in all_outputs:
            src, dest, ping_outputs = outputs
            sent, received, rttmin, rttavg, rttmax, rttdev = ping_outputs
            output(" {}->{}: {}/{}, ".format(src, dest, sent, received))
            output("rtt min/avg/max/mdev %0.3f/%0.3f/%0.3f/%0.3f ms\n" %
                   (rttmin, rttavg, rttmax, rttdev))
        return all_outputs

    def pingAll(self, timeout=None):
        """Ping between all hosts.
           returns: ploss packet loss percentage"""
        sleep(3)
        return self.ping(timeout=timeout)

    def pingPair(self):
        """Ping between first two hosts, useful for testing.
           returns: ploss packet loss percentage"""
        sleep(3)
        nodes = self.hosts + self.stations
        hosts = [nodes[0], nodes[1]]
        return self.ping(hosts=hosts)

    def pingAllFull(self):
        """Ping between all hosts.
           returns: ploss packet loss percentage"""
        sleep(3)
        return self.pingFull()

    def pingPairFull(self):
        """Ping between first two hosts, useful for testing.
           returns: ploss packet loss percentage"""
        sleep(3)
        nodes = self.hosts + self.stations
        hosts = [nodes[0], nodes[1]]
        return self.pingFull(hosts=hosts)

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
        sleep(3)
        nodes = self.hosts + self.stations
        hosts = hosts or [nodes[0], nodes[-1]]
        assert len(hosts) == 2
        client, server = hosts

        conn1 = 0
        conn2 = 0
        if isinstance(client, Station) or isinstance(server, Station):
            cmd = 'iw dev {} link | grep -ic \'Connected\''
            if isinstance(client, Station):
                while conn1 == 0:
                    conn1 = int(client.cmd(cmd.format(client.wintfs[0].name)))
            if isinstance(server, Station):
                while conn2 == 0:
                    conn2 = int(server.cmd(cmd.format(server.wintfs[0].name)))
        output('*** Iperf: testing', l4Type, 'bandwidth between',
               client, 'and', server, '\n')
        server.cmd('killall -9 iperf')
        iperfArgs = 'iperf -p %d ' % port
        bwArgs = ''
        if l4Type == 'UDP':
            iperfArgs += '-u '
            bwArgs = '-b ' + udpBw + ' '
        elif l4Type != 'TCP':
            raise Exception('Unexpected l4 type: {}'.format(l4Type))
        if fmt:
            iperfArgs += '-f {} '.format(fmt)
        server.sendCmd(iperfArgs + '-s')
        if l4Type == 'TCP':
            if not waitListening(client, server.IP(), port):
                raise Exception('Could not connect to iperf on port %d'
                                % port)
        cliout = client.cmd(iperfArgs + '-t %d -c ' % seconds +
                            server.IP() + ' ' + bwArgs)
        debug('Client output: {}\n'.format(cliout))
        servout = ''
        # We want the last *b/sec from the iperf server output
        # for TCP, there are two of them because of waitListening
        count = 2 if l4Type == 'TCP' else 1
        while len(re.findall('/sec', servout)) < count:
            servout += server.monitor(timeoutms=5000)
        server.sendInt()
        servout += server.waitOutput()
        debug('Server output: {}\n'.format(servout))
        result = [self._parseIperf(servout), self._parseIperf(cliout)]
        if l4Type == 'UDP':
            result.insert(0, udpBw)
        output('*** Results: {}\n'.format(result))
        return result

    def get_mn_wifi_nodes(self):
        return self.stations + self.cars + self.aps + \
               self.sensors + self.apsensors + self.modems

    def get_distance(self, src, dst):
        """
        gets the distance between two nodes
        :params src: source node
        :params dst: destination node
        """
        nodes = self.get_mn_wifi_nodes()
        try:
            src = self.nameToNode[src]
            if src in nodes:
                dst = self.nameToNode[dst]
                if dst in nodes:
                    dist = src.get_distance_to(dst)
                    info("The distance between {} and "
                         "{} is {} meters\n".format(src, dst, dist))
        except KeyError:
            info("node {} or/and node {} does not exist or "
                 "there is no position defined\n".format(dst, src))

    def mobility(self, *args, **kwargs):
        "Configure mobility parameters"
        ConfigMobility(*args, **kwargs)

    def get_mob_stat_nodes(self):
        mob_nodes = []
        stat_nodes = []
        nodes = self.stations + self.aps + self.cars + \
                self.sensors + self.apsensors + self.modems
        for node in nodes:
            if hasattr(node, 'position') and 'initPos' not in node.params:
                stat_nodes.append(node)
            else:
                mob_nodes.append(node)
        return stat_nodes, mob_nodes

    def setPropagationModel(self, **kwargs):
        ppm.set_attr(self.noise_th, self.cca_th, **kwargs)

    def setInitialMediums(self, mediums):
        self.initial_mediums = mediums

    def configNodesStatus(self, src, dst, status):
        sta = self.nameToNode[dst]
        ap = self.nameToNode[src]
        if isinstance(self.nameToNode[src], Station):
            sta = self.nameToNode[src]
            ap = self.nameToNode[dst]

        if status == 'down':
            for intf in sta.wintfs.values():
                if intf.associatedTo:
                    intf.disconnect(ap.wintfs[0])
        else:
            for intf in sta.wintfs.values():
                if not intf.associatedTo:
                    intf.iw_connect(ap.wintfs[0])

    # BL: I think this can be rewritten now that we have
    # a real link class.
    def configLinkStatus(self, src, dst, status):
        """Change status of src <-> dst links.
           src: node name
           dst: node name
           status: string {up, down}"""
        if src not in self.nameToNode:
            error('src not in network: {}\n'.format(src))
        elif dst not in self.nameToNode:
            error('dst not in network: {}\n'.format(dst))

        condition1 = [isinstance(self.nameToNode[src], Station),
                      isinstance(self.nameToNode[dst], AP)]
        condition2 = [isinstance(self.nameToNode[src], AP),
                      isinstance(self.nameToNode[dst], Station)]

        if all(condition1) or all(condition2):
            self.configNodesStatus(src, dst, status)
        else:
            src = self.nameToNode[src]
            dst = self.nameToNode[dst]
            connections = src.connectionsTo(dst)
            if len(connections) == 0:
                error('src and dst not connected: {} {}\n'.format(src, dst))
            for srcIntf, dstIntf in connections:
                result = srcIntf.ifconfig(status)
                if result:
                    error('link src status change failed: {}\n'.format(result))
                result = dstIntf.ifconfig(status)
                if result:
                    error('link dst status change failed: {}\n'.format(result))

    def interact(self):
        "Start network and run our simple CLI."
        self.start()
        result = CLI(self)
        self.stop()
        return result

    inited = False

    def createVirtualIfaces(self, nodes):
        "Creates virtual wifi interfaces"
        for node in nodes:
            if 'nvif' in node.params:
                for vif_ in range(node.params['nvif']):
                    vif = node.params['wlan'][0] + str(vif_ + 1)
                    node.params['wlan'].append(vif)
                    mac = str(node.wintfs[0].mac)
                    new_mac = '{}{}{}'.format(mac[:4], vif_+1, mac[5:])
                    node.cmd('iw dev {} interface add {} '
                             'type station'.format(node.params['wlan'][0], vif))
                    TCWirelessLink(node, intfName=vif)
                    managed(node, wlan=vif_+1)

                    node.wintfs[vif_+1].mac = new_mac
                    for intf in node.wintfs.values():
                        intf.configureMacAddr()

    def configIFB(self, node):
        for wlan in range(len(node.params['wlan'])):
            if self.ifb:
                node.configIFB(wlan, self.ifbIntf)  # Adding Support to IFB
                node.wintfs[wlan].ifb = 'ifb' + str(wlan + 1)
                self.ifbIntf += 1

    def configNode(self, node):
        "Configure Wireless Link"
        for wlan in range(len(node.params['wlan'])):
            if not self.autoAssociation or self.roads:
                intf = node.params['wlan'][wlan]
                link = TCWirelessLink(node, intfName=intf)
                self.links.append(link)
            managed(node, wlan)
        for intf in node.wintfs.values():
            intf.configureMacAddr()
        node.configDefault()
        self.configIFB(node)

    def plotGraph(self, **kwargs):
        "Plots Graph"
        self.draw = True
        for key, value in kwargs.items():
            setattr(self, key, value)
        if kwargs.get('max_z', 0) != 0:
            self.plot = Plot3D
        CleanupWifi.plot = self.plot

    def check_dimension(self, nodes):
        try:
            for node in nodes:
                if hasattr(node, 'coord'):
                    node.position = node.coord[0].split(',')
            PlotGraph(min_x=self.min_x, min_y=self.min_y, min_z=self.min_z,
                      max_x=self.max_x, max_y=self.max_y, max_z=self.max_z,
                      nodes=nodes, links=self.links)
            if not issubclass(self.plot, Plot3D):
                PlotGraph.pause()
        except:
            info('Something went wrong with the GUI.\n')
            self.draw = False

    def start_mobility(self, **kwargs):
        "Starts Mobility"
        for node in kwargs.get('mob_nodes'):
            node.position, node.pos = (0, 0, 0), (0, 0, 0)
        if self.roads:
            vanet(**kwargs)
        else:
            MobModel(**kwargs)

    def setMobilityModel(self, **kwargs):
        for key in kwargs:
            if key == 'model':
                self.mob_model = kwargs.get(key)
            elif key == 'time':
                self.mob_start_time = kwargs.get(key)
            elif key in self.__dict__.keys():
                setattr(self, key, kwargs.get(key))

    def startMobility(self, **kwargs):
        for key in kwargs:
            if key == 'time':
                self.mob_start_time = kwargs.get(key)
            else:
                setattr(self, key, kwargs.get(key))

    def stopMobility(self, **kwargs):
        "Stops Mobility"
        if self.allAutoAssociation and \
                not self.configWiFiDirect and not self.config4addr:
            self.auto_association()
        for key in kwargs:
            if key == 'time':
                self.mob_stop_time = kwargs.get(key)
            else:
                setattr(self, key, kwargs.get(key))

    def get_mobility_params(self):
        "Set Mobility Parameters"
        mob_params = {}
        float_args = ['min_x', 'min_y', 'min_z',
                      'max_x', 'max_y', 'max_z',
                      'min_v', 'max_v', 'min_wt', 'max_wt']
        args = ['stations', 'cars', 'aps', 'draw', 'seed',
                'roads', 'mob_start_time', 'mob_stop_time',
                'links', 'mob_model', 'mob_rep', 'reverse',
                'ac_method', 'pointlist', 'n_groups']
        args += float_args
        for arg in args:
            if arg in float_args:
                mob_params.setdefault(arg, float(getattr(self, arg)))
            else:
                mob_params.setdefault(arg, getattr(self, arg))

        mob_params.setdefault('ppm', ppm.model)
        return mob_params

    def useExternalProgram(self, program, **kwargs):
        """Opens an external program
        :params program: only sumo is supported so far
        :params **params config_file: file configuration"""
        for car in self.cars:
            if not hasattr(car, 'position'):
                car.position = (0, 0, 0)
            car.pos = car.position
        program(self.cars, self.aps, **kwargs)

    def start_wmediumd(self):
        wmediumd(wlinks=self.wlinks, fading_cof=self.fading_cof,
                 noise_th=self.noise_th, stations=self.stations,
                 aps=self.aps, cars=self.cars, ppm=ppm, mediums=self.initial_mediums)

    def init_wmediumd(self):
        self.start_wmediumd()
        if self.wmediumd_mode != error_prob:
            for sta in self.stations:
                sta.set_pos_wmediumd(sta.position)
        for sta in self.stations:
            if sta in self.aps:
                self.stations.remove(sta)
        self.config_antenna()

    def addSensors(self, sensors):
        for sensor in sensors:
            self.nameToNode[sensor.name] = sensor

    def addModems(self):
        for modem in self.modems:
            self.nameToNode[modem.name] = modem

    def config_range(self):
        nodes = self.stations + self.cars + self.aps
        for node in nodes:
            for intf in node.wintfs.values():
                if int(intf.range) == 0:
                    intf.setDefaultRange()
                else:
                    # assign txpower according to the signal range
                    if 'model' not in node.params:
                        intf.getTxPowerGivenRange()

    def config_antenna(self):
        nodes = self.stations + self.cars + self.aps
        for node in nodes:
            for intf in node.wintfs.values():
                if not isinstance(intf, (_4addrAP, PhysicalWifiDirectLink, phyAP)):
                    intf.setTxPower(intf.txpower)
                    intf.setAntennaGain(intf.antennaGain)

    def configMasterIntf(self, node, wlan):
        TCWirelessLink(node)
        master(node, wlan, port=wlan)
        phy = node.params.get('phywlan', None)
        if phy:
            TCWirelessLink(node, intfName=phy)
            node.params['wlan'].append(phy)
            phyAP(node, wlan+1)

    def configureWifiNodes(self):
        "Keep backward compatibility"
        self.configureNodes()

    def configureNodes(self):
        "Configure WiFi Nodes"
        params = {}
        if self.docker:
            params['docker'] = self.docker
            params['container'] = self.container
            params['ssh_user'] = self.ssh_user
        params['rec_rssi'] = self.rec_rssi

        nodes, nradios = self.count_ifaces()
        if nodes:
            Mac80211Hwsim(nodes=nodes, nradios=nradios,
                          alt_module=self.alt_module, **params)

        if self.ifb: Mac80211Hwsim.load_ifb(nradios)

        if self.nwpans:
            self.sensors, self.apsensors = self.init_6lowpan_module(self.iot_module)
            sensors = self.sensors + self.apsensors
            self.addSensors(sensors)
            self.configure6LowPANLink()

        if self.nwwans:
            if self.alt_module: self.wwan_module = self.alt_module
            self.modems = self.init_wwan_module(self.wwan_module)
            self.addModems()
            self.configureWWANLink()

        nodes = self.stations + self.cars
        for node in nodes:
            self.configNode(node)
        self.createVirtualIfaces(self.stations)

        for ap in self.aps:
            for wlan in range(len(ap.params['wlan'])):
                self.configMasterIntf(ap, wlan)
                intf = ap.wintfs[wlan]
                if not intf.mac:
                    intf.mac = intf.getMAC()
                intf.setMAC(intf.mac)
            self.configIFB(ap)

        self.config_range()
        if self.link == wmediumd:
            self.wmediumd_mode()
            if not self.configWiFiDirect and not self.config4addr \
                    and self.wmediumd_mode != error_prob:
                self.start_wmediumd()

        for ap in self.aps:
            for intf in list(ap.wintfs.values()):
                HostapdConfig(intf)
                if self.link == wmediumd and 'vssids' in ap.params:
                    break

        if not self.config4addr and not self.configWiFiDirect:
            self.config_antenna()

    @staticmethod
    def wmediumd_workaround(node, value=1):
        # We need to set the position after starting wmediumd
        sleep(0.15)
        pos = node.position
        pos_x = float(pos[0]) + value
        pos = (pos_x, pos[1], pos[2])
        node.set_pos_wmediumd(pos)

    def restore_links(self):
        # restore link params when it is manually set
        for link in self.links:
            params = {}
            if 'bw' in link.intf1.params:
                params['bw'] = link.intf1.params['bw']
            if 'latency' in link.intf1.params:
                params['latency'] = link.intf1.params['latency']
            if 'loss' in link.intf1.params:
                params['loss'] = link.intf1.params['loss']
            if params and 'delay' not in link.intf1.params and hasattr(link.intf1, 'configWLink'):
                link.intf1.configWLink.set_tc(link.intf1.name, **params)

    def auto_association(self):
        "This is useful to make the users' life easier"
        isap = []
        for node in self.stations:
            for intf in node.wintfs.values():
                if isinstance(intf, master) or \
                        isinstance(intf, _4addrClient or isinstance(intf, _4addrAP)):
                    if node not in self.aps and node not in isap:
                        isap.append(node)

        for sta in isap:
            self.aps.append(sta)
            self.stations.remove(sta)
            if sta in mob.stations:
                mob.stations.remove(sta)

        mob.aps = self.aps
        nodes = self.aps + self.stations + self.cars
        for node in nodes:
            if hasattr(node, 'position'):
                if isinstance(node, Car) and node.position == (0, 0, 0):
                    pass
                else:
                    for intf in node.wintfs.values():
                        if isinstance(intf, adhoc):
                            info(node.name + ' ')
                            sleep(1)
                    node.pos = (0, 0, 0)
                    if not isinstance(node, AP):
                        ConfigMobLinks(node)
                    # we need this cause wmediumd is struggling
                    # with some associations e.g. wpa
                    if self.wmediumd_mode == interference:
                        self.wmediumd_workaround(node)
                        self.wmediumd_workaround(node, -1)

        self.restore_links()

        nodes = self.stations + self.cars
        for node in nodes:
            for wlan in range(len(node.params['wlan'])):
                intf = node.params['wlan'][wlan]
                link = TCWirelessLink(node, intfName=intf, port=wlan)
                self.links.append(link)
                # lets set ip/mac to intfs
                node.intfs[wlan].ip = node.wintfs[wlan].ip
                node.intfs[wlan].mac = node.wintfs[wlan].mac

    @staticmethod
    def stop_simulation():
        "Pause the simulation"
        mob.pause_simulation = True

    @staticmethod
    def start_simulation():
        "Start the simulation"
        mob.pause_simulation = False

    @staticmethod
    def setChannelEquation(**params):
        """Set Channel Equation
        :params bw: bandwidth (mbps)
        :params delay: delay (ms)
        :params latency: latency (ms)
        :params loss: loss (%)"""
        IntfWireless.eqBw = params.get('bw', IntfWireless.eqBw)
        IntfWireless.eqDelay = params.get('delay', IntfWireless.eqDelay)
        IntfWireless.eqLatency = params.get('latency', IntfWireless.eqLatency)
        IntfWireless.eqLoss = params.get('loss', IntfWireless.eqLoss)

    @staticmethod
    def stop_graph_params():
        "Stop the graph"
        if parseData.thread_:
            parseData.thread_._keep_alive = False
        if mob.thread_:
            mob.thread_._keep_alive = False
        if Energy.thread_:
            Energy.thread_._keep_alive = False
            sleep(1)
        sleep(0.5)

    @classmethod
    def closeMininetWiFi(self):
        "Close Mininet-WiFi"
        CleanupWifi.kill_mod_proc()


class MininetWithControlWNet(Mininet_wifi):
    """Control network support:
       Create an explicit control network. Currently this is only
       used/usable with the user datapath.
       Notes:
       1. If the controller and switches are in the same (e.g. root)
          namespace, they can just use the loopback connection.
       2. If we can get unix domain sockets to work, we can use them
          instead of an explicit control network.
       3. Instead of routing, we could bridge or use 'in-band' control.
       4. Even if we dispense with this in general, it could still be
          useful for people who wish to simulate a separate control
          network (since real networks may need one!)
       5. Basically nobody ever used this code, so it has been moved
          into its own class.
       6. Ultimately we may wish to extend this to allow us to create a
          control network which every node's control interface is
          attached to."""

    def configureControlNetwork(self):
        "Configure control network."
        self.configureRoutedControlNetwork()

    # We still need to figure out the right way to pass
    # in the control network location.

    def configureRoutedControlNetwork(self, ip='192.168.123.1',
                                      prefixLen=16):
        """Configure a routed control network on controller and switches.
           For use with the user datapath only right now."""
        controller = self.controllers[0]
        info(controller.name + ' <->')
        cip = ip
        snum = ipParse(ip)
        nodesL2 = self.switches + self.aps + self.apsensors
        for nodeL2 in nodesL2:
            info(' ' + nodeL2.name)
            if self.link == wmediumd:
                link = Link(nodeL2, controller, port1=0)
            else:
                self.link = Link
                link = self.link(nodeL2, controller, port1=0)
            sintf, cintf = link.intf1, link.intf2
            nodeL2.controlIntf = sintf
            snum += 1
            while snum & 0xff in [0, 255]:
                snum += 1
            sip = ipStr(snum)
            cintf.setIP(cip, prefixLen)
            sintf.setIP(sip, prefixLen)
            controller.setHostRoute(sip, cintf)
            nodeL2.setHostRoute(cip, sintf)
        info('\n')
        info('*** Testing control network\n')
        while not cintf.isUp():
            info('*** Waiting for', cintf, 'to come up\n')
            sleep(1)
        for nodeL2 in nodesL2:
            while not sintf.isUp():
                info('*** Waiting for', sintf, 'to come up\n')
                sleep(1)
            if self.ping(hosts=[nodeL2, controller]) != 0:
                error('*** Error: control network test failed\n')
                exit(1)
        info('\n')
