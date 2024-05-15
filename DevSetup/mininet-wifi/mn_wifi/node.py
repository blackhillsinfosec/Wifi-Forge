"""
Node objects for Mininet-WiFi.
Nodes provide a simple abstraction for interacting with stations, aps
and controllers. Local nodes are simply one or more processes on the local
machine.
Node: superclass for all (primarily local) network nodes.
Station: a virtual station. By default, a station is simply a shell; commands
    may be sent using Cmd (which waits for output), or using sendCmd(),
    which returns immediately, allowing subsequent monitoring using
    monitor(). Examples of how to run experiments using this
    functionality are provided in the examples/ directory. By default,
    stations share the root file system, but they may also specify private
    directories.
CPULimitedStation: a virtual station whose CPU bandwidth is limited by
    RT or CFS bandwidth limiting.
UserAP: a AP using the user-space switch from the OpenFlow
    reference implementation.
OVSAP: a AP using the Open vSwitch OpenFlow-compatible switch
    implementation (openvswitch.org).
"""


import re
import math
import matplotlib.pyplot as plt

from time import sleep
from sys import exit
from os import system as sh, getpid

from mininet.log import info, debug, error
from mininet.util import (errRun, errFail, Python3, getincrementaldecoder,
                          quietRun, BaseString)
from mininet.node import Node, UserSwitch, OVSSwitch, CPULimitedHost
from mininet.moduledeps import pathCheck
from mininet.link import Intf
from mn_wifi.link import WirelessIntf, physicalMesh, ITSLink
from mn_wifi.wmediumdConnector import w_server, w_pos, w_cst, wmediumd_mode

from re import findall


class Node_wifi(Node):
    """A virtual network node is simply a shell in a network namespace.
       We communicate with it using pipes."""

    portBase = 0  # Nodes always start with eth0/port0, even in OF 1.0

    def __init__(self, name, inNamespace=True, **params):
        """name: name of node
           inNamespace: in network namespace?
           privateDirs: list of private directory strings or tuples
           params: Node parameters (see config() for details)"""

        # Make sure class actually works
        self.checkSetup()

        if 'position' in params:
            self.position = params.get('position')
        self.name = params.get('name', name)
        self.privateDirs = params.get('privateDirs', [])
        self.inNamespace = params.get('inNamespace', inNamespace)

        # Python 3 complains if we don't wait for shell exit
        self.waitExited = params.get('waitExited', Python3)

        # Stash configuration parameters for future reference
        self.params = params

        self.intfs = {}  # dict of port numbers to interfaces
        self.ports = {}  # dict of interfaces to port numbers
        self.wintfs = {}  # dict of wireless port numbers
        self.wports = {}  # dict of interfaces to port numbers
        self.nameToIntf = {}  # dict of interface names to Intfs

        # Make pylint happy
        (self.shell, self.execed, self.pid, self.stdin, self.stdout,
         self.lastPid, self.lastCmd, self.pollOut) = (
             None, None, None, None, None, None, None, None)
        self.waiting = False
        self.readbuf = ''

        # Incremental decoder for buffered reading
        self.decoder = getincrementaldecoder()

        # Start command interpreter shell
        self.master, self.slave = None, None  # pylint
        self.startShell()
        self.mountPrivateDirs()

    # File descriptor to node mapping support
    # Class variables and methods
    inToNode = {}  # mapping of input fds to nodes
    outToNode = {}  # mapping of output fds to nodes

    def get_wlan(self, intf):
        return self.params['wlan'].index(intf)

    def getNameToWintf(self, intf):
        wlan = self.get_wlan(intf) if isinstance(intf, BaseString) else 0
        return self.wintfs[wlan]

    def setPhysicalMeshMode(self, intf=None, **kwargs):
        if intf: kwargs['intf'] = intf
        physicalMesh(self, **kwargs)

    def setMeshMode(self, intf=None, **kwargs):
        self.getNameToWintf(intf).setMeshMode(**kwargs)

    def setAdhocMode(self, intf=None, **kwargs):
        self.getNameToWintf(intf).setAdhocMode(**kwargs)

    def setManagedMode(self, intf=None):
        self.getNameToWintf(intf).setManagedMode()

    def setMasterMode(self, intf=None, **kwargs):
        self.getNameToWintf(intf).setMasterMode(**kwargs)

    def setTC(self, intf=None, **kwargs):
        self.getNameToWintf(intf).config_tc(**kwargs)

    def setOCBMode(self, **params):
        ITSLink(self, **params)

    def setMaxVelocity(self, v=None):
        self.max_v = v

    def setMinVelocity(self, v=None):
        self.min_v = v

    def setIntfName(self, *args):
        self.wintfs[int(args[1])].setIntfName(*args)

    def roam(self, bssid, intf=None):
        self.getNameToWintf(intf).roam(bssid)

    def configLinks(self):
        "Applies channel params and handover"
        from mn_wifi.mobility import ConfigMobLinks
        ConfigMobLinks(self)

    def configIFB(self, wlan, ifbID):
        "Support to Intermediate Functional Block (IFB) Devices"
        intf = self.params['wlan'][wlan]
        sh('ip link set dev ifb%s netns %s' % (ifbID, self.pid))
        self.cmd('ip link set ifb%s name ifb%s' % (ifbID, wlan+1))
        self.cmd('ip link set ifb%s up' % (wlan+1))
        self.handle_ingress_data(intf, wlan)

    def handle_ingress_data(self, intf, wlan):
        self.cmd('tc qdisc add dev %s handle ffff: ingress' % intf)
        self.cmd('tc filter add dev %s parent ffff: protocol ip u32 '
                 'match u32 0 0 action mirred egress redirect dev ifb%s'
                 % (intf, (wlan+1)))

    def setDefaultRange(self, intf):
        "Set Default Signal Range"
        self.getNameToWintf(intf).setDefaultRange()

    def setRange(self, range, intf=None):
        self.getNameToWintf(intf).setRange(range)
        self.update_graph()

    def setAntennaGain(self, gain, intf=None):
        self.getNameToWintf(intf).setAntennaGain(gain)
        self.update_graph()

    def setAntennaHeight(self, height, intf=None):
        self.getNameToWintf(intf).setAntennaHeight(height)
        self.update_graph()
        
    def getAntennaHeight(self, intf=None):
        return self.getNameToWintf(intf).getAntennaHeight()

    def setChannel(self, channel, intf=None):
        self.getNameToWintf(intf).setChannel(channel)

    def setTxPower(self, txpower, intf=None):
        self.getNameToWintf(intf).setTxPower(txpower)
        self.update_graph()

    def setMediumId(self, medium_id, intf=None):
        """Set medium id to create isolated interface groups"""
        self.getNameToWintf(intf).setMediumId(medium_id)

    def get_txpower(self, intf):
        connected = self.cmd('iw dev %s link | awk \'{print $1}\'' % intf)
        cmd = 'iw dev %s info | grep txpower | awk \'{print $2}\'' % intf
        if connected != 'Not' or isinstance(self, AP):
            try:
                txpower = int(float(self.cmd(cmd)))
            except:
                txpower = 14 if isinstance(self, AP) else 20
            return txpower

    def set_text(self, text):
        self.plttxt.set_text(text)

    def set_text_pos(self, x, y):
        self.plttxt.xyann = (x, y)

    def set_circle_center(self, x, y):
        self.circle.center = x, y

    def set_circle_radius(self):
        self.circle.set_radius(self.get_max_radius())

    def set_pos_wmediumd(self, pos):
        "Set Position for wmediumd"
        if self.lastpos != pos:
            self.lastpos = pos
            for id, wmIface in enumerate(self.wmIfaces):
                w_server.update_pos(w_pos(wmIface,
                    [(float(pos[0])+id), float(pos[1]), float(pos[2])]))

    def setPosition(self, pos):
        "Set Position"
        self.position = [float(x) for x in pos.split(',')]
        self.update_graph()

        if wmediumd_mode.mode == w_cst.INTERFERENCE_MODE:
            self.set_pos_wmediumd(self.position)
        self.configLinks()

    def get_circle_color(self):
        if 'color' in self.params:
            color = self.params['color']
        else:
            color = 'b'
            if isinstance(self, Station):
                color = 'g'
            elif isinstance(self, Car):
                color = 'r'
        return color

    def updateLine(self):
        pos = [self.position[0], self.position[1]]
        if hasattr(self, 'lines'):
            for line in self.lines:
                for n in range(len(line)):
                    if '-' == line[n]: node = line[:n]
                pos_ = self.lines[line].get_data()
                if self.name == node:
                    self.lines[line].set_data([pos[0], pos_[0][1]], [pos[1], pos_[1][1]])
                else:
                    self.lines[line].set_data([pos_[0][0], pos[0]], [pos_[1][0], pos[1]])

    def getxyz(self): 
        pos = self.position 
        x, y = round(pos[0], 2), round(pos[1], 2)
        #only access third element if it exists 
        if len(pos) == 3:
            z = round(pos[2], 2) 
        #otherwise, set z to 0 
        else: 
            z = 0 
        return x, y, z

    def update_3d(self):
        from mn_wifi.plot import Plot3D
        self.plt_node.remove()
        self.circle.remove()
        self.plttxt.remove()
        Plot3D.instantiate_attrs(self)

    def update_2d(self):
        x, y, z = self.getxyz()
        self.set_text_pos(x, y)
        self.plt_node.set_data(x, y)
        self.circle.center = x, y
        # Enable the update of the wired links when the nodes have mobility
        self.updateLine()

    def get_max_radius(self):
        range_list = []
        for n in self.wintfs.values():
            range_list.append(n.range)
        return max(range_list)

    def update_graph(self):
        if plt.fignum_exists(1):
            if hasattr(self.circle, 'set_radius'):
                self.set_circle_radius()
                self.updateLine()
                self.update_2d()
            else:
                self.update_3d()

    def get_distance_to(self, dst):
        """Get the distance between two nodes
        :param self: source node
        :param dst: destination node"""
        pos_src = self.position
        pos_dst = dst.position
        x = (float(pos_src[0]) - float(pos_dst[0])) ** 2
        y = (float(pos_src[1]) - float(pos_dst[1])) ** 2
        z = (float(pos_src[2]) - float(pos_dst[2])) ** 2
        dist = math.sqrt(x + y + z)
        return round(dist, 2)

    # we actualy do not use this within the code. This can be only evoked manually.
    def setAssociation(self, ap, intf=None):
        "Force association to given AP"
        intf = self.getNameToWintf(intf)
        ap_intf = ap.wintfs[0]
        if hasattr(self, 'position') and hasattr(ap, 'position'):
            dist = self.get_distance_to(ap)
            if dist <= ap_intf.range:
                if intf.bgscan_module:
                    intf.roam(ap_intf.mac)
                    intf.update(ap_intf)
                elif intf.associatedTo != ap_intf:
                    if intf.associatedTo:
                        intf.disconnect(ap_intf)
                    intf.associate_infra(ap_intf)
                    intf.configWLink(dist)
                else:
                    info('%s is already connected!\n' % self)
                self.configLinks()
            else:
                info("%s is out of range!\n" % ap)
        else:
            intf.associate_infra(ap_intf)

    def newPort(self):
        "Return the next port number to allocate."
        if len(self.ports) > 0: return max(self.ports.values()) + 1
        return self.portBase

    def newWPort(self):
        "Return the next port number to allocate."
        if len(self.wports) > 0: return max(self.wports.values()) + 1
        return self.portBase

    def addWAttr(self, intf, port=None):
        """Add an wireless interface.
           intf: interface
           port: port number (optional, typically OpenFlow port number)
           moveIntfFn: function to move interface (optional)"""
        if port is None: port = self.newWPort()

        self.wintfs[port] = intf
        self.wports[intf] = port
        self.nameToIntf[intf.name] = intf

    def addWIntf(self, intf, port=None):
        """Add an interface.
           intf: interface
           port: port number (optional, typically OpenFlow port number)
           moveIntfFn: function to move interface (optional)"""
        if port is None: port = self.newPort()
        self.intfs[port] = intf
        self.ports[intf] = port
        self.nameToIntf[intf.name] = intf
        debug('\n')
        debug('added intf %s (%d) to node %s\n' % (intf, port, self.name))

    def connectionsTo(self, node):
        "Return [ intf1, intf2... ] for all intfs that connect self to node."
        # We could optimize this if it is important
        connections = []
        for intf in self.intfList():
            link = intf.link
            if link and link.intf2 is not None and 'wifi' not in str(link.intf2):
                node1, node2 = link.intf1.node, link.intf2.node
                if node1 == self and node2 == node:
                    connections += [ (intf, link.intf2) ]
                elif node1 == node and node2 == self:
                    connections += [ (intf, link.intf1) ]
        return connections

    # Convenience and configuration methods
    def setIP6(self, ip, prefixLen=64, intf=None, **kwargs):
        """Set the IP6 address for an interface.
           intf: intf or intf name
           ip: IP6 address as a string
           kwargs: any additional arguments for intf.setIP6"""
        return self.getNameToWintf(intf).setIP6(ip, prefixLen, **kwargs)

    def setIP(self, ip, prefixLen=8, intf=None, **kwargs):
        """Set the IP address for an interface.
           intf: intf or intf name
           ip: IP address as a string
           kwargs: any additional arguments for intf.setIP"""
        if intf in self.wintfs:
            return self.getNameToWintf(intf).setIP(ip, prefixLen, **kwargs)
        return self.intf(intf).setIP(ip, prefixLen, **kwargs)

    def setMode(self, mode, intf=None):
        return self.getNameToWintf(intf).setMode(mode)

    def config(self, mac=None, ip=None, ip6=None,
               defaultRoute=None, lo='up', **_params):
        """Configure Node according to (optional) parameters:
           mac: MAC address for default interface
           ip: IP address for default interface
           ip addr: arbitrary interface configuration
           Subclasses should override this method and call
           the parent class's config(**params)"""
        # If we were overriding this method, we would call
        # the superclass config method here as follows:
        # r = Parent.config( **_params )
        r = {}
        if not isinstance(self, Station) and not isinstance(self, Car):
            self.setParam(r, 'setMAC', mac=mac)
        self.setParam(r, 'setIP', ip=ip)
        self.setParam(r, 'setIP6', ip=ip6)
        self.setParam(r, 'setDefaultRoute', defaultRoute=defaultRoute)

        # This should be examined
        self.cmd('ip link set lo ' + lo)
        return r

    def configDefault(self, **moreParams):
        "Configure with default parameters"
        self.params.update(moreParams)
        self.config(**self.params)

    # Automatic class setup support
    isSetup = False

    @classmethod
    def setup(cls):
        "Make sure our class dependencies are available"
        pathCheck('mnexec', 'ip addr', moduleName='Mininet')

    def set_circle_color(self, color):
        for n in range(1, 3):
            if plt.fignum_exists(n):
                if hasattr(self, 'circle'):
                    self.circle.set_color(color)

    def showNode(self, show=True):
        self.circle.set_visible(show)
        self.plttxt.set_visible(show)
        self.plt_node.set_visible(show)

    def stop_(self):
        "Stops hostapd"
        process = 'mn%d_%s' % (getpid(), self.name)
        sh('pkill -f \'hostapd -B %s\'' % process)
        self.set_circle_color('w')

    def start_(self):
        "Starts hostapd"
        process = 'mn%d_%s' % (getpid(), self.name)
        sh('hostapd -B %s-wlan1.apconf' % process)
        color = self.get_circle_color()
        self.set_circle_color(color)

    def hide(self):
        for intf in self.wintfs.values():
            self.cmd('ip link set %s down' % intf.name)
        self.showNode(False)

    def show(self):
        for intf in self.wintfs.values():
            self.cmd('ip link set %s up' % intf.name)
        self.showNode()


class Station(Node_wifi):
    "A station is simply a Node"
    pass


class Car(Node_wifi):
    "A car is simply a Node"
    pass


class CPULimitedStation( Station, CPULimitedHost ):

    "CPU limited host"

    def __init__( self, name, sched='cfs', **kwargs ):
        Station.__init__( self, name, **kwargs )
        # Initialize class if necessary
        if not CPULimitedStation.inited: CPULimitedStation.init()
        # Create a cgroup and move shell into it
        self.cgroup = 'cpu,cpuacct,cpuset:/' + self.name
        errFail( 'cgcreate -g ' + self.cgroup )
        # We don't add ourselves to a cpuset because you must
        # specify the cpu and memory placement first
        errFail( 'cgclassify -g cpu,cpuacct:/%s %s' % ( self.name, self.pid ) )
        # BL: Setting the correct period/quota is tricky, particularly
        # for RT. RT allows very small quotas, but the overhead
        # seems to be high. CFS has a mininimum quota of 1 ms, but
        # still does better with larger period values.
        self.period_us = kwargs.get( 'period_us', 100000 )
        self.sched = sched
        if sched == 'rt':
            self.checkRtGroupSched()
            self.rtprio = 20

    _rtGroupSched = False   # internal class var: Is CONFIG_RT_GROUP_SCHED set?
    inited = False


class AP(Node_wifi):
    """A Switch is a Node that is running (or has execed?)
       an OpenFlow switch."""
    portBase = 1  # Switches start with port 1 in OpenFlow
    dpidLen = 16  # digits in dpid passed to switch

    def __init__(self, name, dpid=None, opts='', listenPort=None, **params):
        """dpid: dpid hex string (or None to derive from name, e.g. s1 -> 1)
           opts: additional switch options
           listenPort: port to listen on for dpctl connections"""
        Node_wifi.__init__(self, name, **params)
        self.dpid = self.defaultDpid(dpid)
        self.opts = opts
        self.listenPort = listenPort
        if not self.inNamespace: self.controlIntf = Intf('lo', self, port=0)

    def defaultDpid(self, dpid=None):
        "Return correctly formatted dpid from dpid or switch name (s1 -> 1)"
        if dpid:
            # Remove any colons and make sure it's a good hex number
            dpid = dpid.replace(':', '')
            assert len(dpid) <= self.dpidLen and int(dpid, 16) >= 0
            return '0' * (self.dpidLen - len(dpid)) + dpid

        # Use hex of the first number in the switch name
        nums = re.findall(r'\d+', self.name)
        if nums:
            dpid = hex(int(nums[ 0 ]))[ 2: ]
        else:
            raise Exception('Unable to derive default datapath ID - '
                            'please either specify a dpid or use a '
                            'canonical ap name such as ap23.')
        return '1' + '0' * (self.dpidLen -1 - len(dpid)) + dpid


class UserAP(AP, UserSwitch):
    "User-space AP."

    dpidLen = 12

    def __init__(self, name, dpopts='--no-slicing', **kwargs):
        """Init.
           name: name for the switch
           dpopts: additional arguments to ofdatapath (--no-slicing)"""
        AP.__init__(self, name, **kwargs)
        pathCheck('ofdatapath', 'ofprotocol',
                  moduleName='the OpenFlow reference user switch' +
                             '(openflow.org)')
        if self.listenPort:
            self.opts += ' --listen=ptcp:%i ' % self.listenPort
        else:
            self.opts += ' --listen=punix:/tmp/%s.listen' % self.name
        self.dpopts = dpopts

    @staticmethod
    def TCReapply(intf):
        """Unfortunately user switch and Mininet are fighting
           over tc queuing disciplines. To resolve the conflict,
           we re-create the user switch's configuration, but as a
           leaf of the TCIntf-created configuration."""
        if isinstance(intf, WirelessIntf):
            ifspeed = 10000000000  # 10 Gbps
            minspeed = ifspeed * 0.001

            res = intf.config(**intf.params)

            if res is None:  # link may not have TC parameters
                return

            # Re-add qdisc, root, and default classes user switch created, but
            # with new parent, as setup by Mininet's TCIntf
            parent = res['parent']
            intf.tc("%s qdisc add dev %s " + parent +
                    " handle 1: htb default 0xfffe")
            intf.tc("%s class add dev %s classid 1:0xffff parent 1: htb rate "
                    + str(ifspeed))
            intf.tc("%s class add dev %s classid 1:0xfffe parent 1:0xffff " +
                    "htb rate " + str(minspeed) + " ceil " + str(ifspeed))

    def start(self, controllers):
        """Start OpenFlow reference user datapath.
           Log to /tmp/sN-{ofd,ofp}.log.
           controllers: list of controller objects"""
        # Add controllers
        clist = ','.join(['tcp:%s:%d' % (c.IP(), c.port)
                          for c in controllers])
        ofdlog = '/tmp/' + self.name + '-ofd.log'
        ofplog = '/tmp/' + self.name + '-ofp.log'
        intfs = [str(i) for i in self.intfList() if not i.IP()]

        self.cmd('ofdatapath -i ' + ','.join(intfs) +
                 ' punix:/tmp/' + self.name + ' -d %s ' % self.dpid +
                 self.dpopts +
                 ' 1> ' + ofdlog + ' 2> ' + ofdlog + ' &')
        self.cmd('ofprotocol unix:/tmp/' + self.name +
                 ' ' + clist +
                 ' --fail=closed ' + self.opts +
                 ' 1> ' + ofplog + ' 2>' + ofplog + ' &')
        if "no-slicing" not in self.dpopts:
            # Only TCReapply if slicing is enable
            sleep(1)  # Allow ofdatapath to start before re-arranging qdisc's
            for intf in self.intfList():
                if not intf.IP():
                    self.TCReapply(intf)

    def stop(self, deleteIntfs=True):
        """Stop OpenFlow reference user datapath.
           deleteIntfs: delete interfaces? (True)"""
        # self.cmd('kill %ofdatapath')
        # self.cmd('kill %ofprotocol')
        # super(UserAP, self).stop(deleteIntfs)


class OVSAP(AP, OVSSwitch):
    "Open vSwitch AP. Depends on ovs-vsctl."

    def __init__(self, name, failMode='secure', datapath='kernel',
                 inband=False, protocols=None, reconnectms=1000,
                 stp=False, batch=False, **params):
        """name: name for switch
           failMode: controller loss behavior (secure|open)
           datapath: userspace or kernel mode (kernel|user)
           inband: use in-band control (False)
           protocols: use specific OpenFlow version(s) (e.g. OpenFlow13)
                      Unspecified (or old OVS version) uses OVS default
           reconnectms: max reconnect timeout in ms (0/None for default)
           stp: enable STP (False, requires failMode=standalone)
           batch: enable batch startup (False)"""
        AP.__init__(self, name, **params)
        self.failMode = failMode
        self.datapath = datapath
        self.inband = inband
        self.protocols = protocols
        self.reconnectms = reconnectms
        self.stp = stp
        self._uuids = []  # controller UUIDs
        self.batch = batch
        self.commands = []  # saved commands for batch startup

    @classmethod
    def setup(cls):
        "Make sure Open vSwitch is installed and working"
        pathCheck('ovs-vsctl', moduleName='Open vSwitch (openvswitch.org)')
        # This should no longer be needed, and it breaks
        # with OVS 1.7 which has renamed the kernel module:
        #  moduleDeps( subtract=OF_KMOD, add=OVS_KMOD )
        out, err, exitcode = errRun('ovs-vsctl -t 1 show')
        if exitcode:
            error(out + err +
                  'ovs-vsctl exited with code %d\n' % exitcode +
                  '*** Error connecting to ovs-db with ovs-vsctl\n'
                  'Make sure that Open vSwitch is installed, '
                  'that ovsdb-server is running, and that\n'
                  '"ovs-vsctl show" works correctly.\n'
                  'You may wish to try '
                  '"service openvswitch-switch start".\n')
            exit(1)
        version = quietRun('ovs-vsctl --version')
        cls.OVSVersion = findall(r'\d+\.\d+', version)[0]

    @staticmethod
    def TCReapply(intf):
        """Unfortunately OVS and Mininet are fighting
           over tc queuing disciplines. As a quick hack/
           workaround, we clear OVS's and reapply our own."""
        if isinstance(intf, WirelessIntf): intf.config(**intf.params)

    def start(self, controllers):
        "Start up a new OVS OpenFlow switch using ovs-vsctl"
        if self.inNamespace:
            raise Exception(
                'OVS kernel switch does not work in a namespace')
        int(self.dpid, 16)  # DPID must be a hex string
        # Command to add interfaces
        intfs = ''.join(' -- add-port %s %s' % (self, intf) +
                        self.intfOpts(intf)
                        for intf in self.intfList()
                        if self.ports[intf] and not intf.IP())
        # Command to create controller entries
        clist = [(self.name + c.name, '%s:%s:%d' %
                  (c.protocol, c.IP(), c.port))
                 for c in controllers]
        if self.listenPort:
            clist.append((self.name + '-listen',
                          'ptcp:%s' % self.listenPort))
        ccmd = '-- --id=@%s create Controller target=\\"%s\\"'
        if self.reconnectms:
            ccmd += ' max_backoff=%d' % self.reconnectms
        cargs = ' '.join(ccmd % (name, target)
                         for name, target in clist)
        # Controller ID list
        cids = ','.join('@%s' % name for name, _target in clist)
        # Try to delete any existing bridges with the same name
        if not self.isOldOVS():
            cargs += ' -- --if-exists del-br %s' % self
        # One ovs-vsctl command to rule them all!
        self.vsctl(cargs +
                   ' -- add-br %s' % self +
                   ' -- set bridge %s controller=[%s]' % (self, cids) +
                   self.bridgeOpts() +
                   intfs)
        # If necessary, restore TC config overwritten by OVS
        if not self.batch:
            for intf in self.intfList():
                self.TCReapply(intf)
        # we need to add the ifb interface at the end
        if self.wintfs[0].ifb: self.handle_ingress_data(self.wintfs[0], 0)

    @classmethod
    def batchStartup(cls, aps, run=errRun):
        """Batch startup for OVS
           aps: aps to start up
           run: function to run commands (errRun)"""
        info('...')
        cmds = 'ovs-vsctl'
        for ap in aps:
            if ap.isOldOVS():
                # Ideally we'd optimize this also
                run('ovs-vsctl del-br %s' % ap)
            for cmd in ap.commands:
                cmd = cmd.strip()
                # Don't exceed ARG_MAX
                if len(cmds) + len(cmd) >= cls.argmax:
                    run(cmds, shell=True)
                    cmds = 'ovs-vsctl'
                cmds += ' ' + cmd
                ap.cmds = []
                ap.batch = False
        if cmds:
            run(cmds, shell=True)
        # Reapply link config if necessary...
        for ap in aps:
            for intf in ap.intfs:
                if isinstance(intf, WirelessIntf): intf.config(**intf.params)
        return aps


OVSKernelAP = OVSAP
physicalAP = OVSAP


class OVSBridgeAP( OVSAP ):
    "OVSBridge is an OVSAP in standalone/bridge mode"

    def __init__( self, *args, **kwargs ):
        """stp: enable Spanning Tree Protocol (False)
           see OVSSwitch for other options"""
        kwargs.update( failMode='standalone' )
        OVSAP.__init__( self, *args, **kwargs )
