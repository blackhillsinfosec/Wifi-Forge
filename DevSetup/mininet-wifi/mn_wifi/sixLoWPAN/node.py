"""
    Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)
"""

import re
from time import sleep

from mininet.log import debug, error, info
from mininet.link import Intf
from mininet.node import OVSSwitch
from mininet.util import BaseString, getincrementaldecoder, Python3, \
    errRun, quietRun
from mininet.moduledeps import pathCheck
from mn_wifi.node import Node_wifi, UserAP
from mn_wifi.sixLoWPAN.link import IntfSixLoWPAN

from re import findall


class LowPANNode(Node_wifi):
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
        self.wintfs = {}  # dict of port numbers to interfaces
        self.ports = {}  # dict of interfaces to port numbers
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

    # Convenience and configuration methods
    def setIP6(self, ip, prefixLen=64, intf=None, **kwargs):
        """Set the IP address for an interface.
           intf: intf or intf name
           ip: IP address as a string
           kwargs: any additional arguments for intf.setIP"""
        return self.intf(intf).setIP6(ip, prefixLen, **kwargs)

    def IP6(self, intf=None):
        "Return IP address of a node or specific interface."
        return self.intf(intf).IP6()

    def configRPLD(self):
        cmd = 'ifaces = { {\n'
        cmd += '        ifname = \"{}-pan0\",\n'.format(self.name)
        if 'storing_mode' not in self.params:
            self.params['storing_mode'] = 2
        if 'dodag_root' in self.params and self.params['dodag_root']:
            cmd += '        dodag_root = true,\n'
            cmd += '        rpls = { {\n'
            cmd += '               instance = 1,\n'
            cmd += '               dags = { {\n'
            cmd += '                       mode_of_operation = {},\n'.format(self.params['storing_mode'])
            cmd += '                       dest_prefix = \"fd3c:be8a:173f:8e80::/64\",\n'
            cmd += '               }, }\n'
            cmd += '        }, }\n'
        else:
            cmd += '        dodag_root = false,\n'
        cmd += '}, }'
        self.cmd('echo \'{}\' > lowpan-{}.conf'.format(cmd, self.name))
        self.runRPLD()

    def runRPLD(self):
        self.cmd('rpld -C lowpan-{}.conf &'.format(self.name))

    def setDefault6Route(self, intf=None):
        """Set the default ipv6 route to go through intf.
           intf: Intf or {dev <intfname> via <gw-ip> ...}"""
        # Note setParam won't call us if intf is none
        if isinstance(intf, BaseString) and ' ' in intf:
            params = intf
        else:
            params = 'dev %s' % intf
        # Do this in one line in case we're messing with the root namespace
        self.cmd('ip -6 route del default; ip -6 route add default', params)

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

        self.setParam(r, 'setIP6', ip=ip6)
        self.setParam(r, 'setDefaultRoute', defaultRoute=defaultRoute)

        # This should be examined
        self.cmd('ip link set lo ' + lo)
        return r


class APSensor(LowPANNode):
    """A APSensor is a Node that is running (or has execed?)
       an OpenFlow switch."""
    portBase = 1  # Switches start with port 1 in OpenFlow
    dpidLen = 16  # digits in dpid passed to switch

    def __init__(self, name, dpid=None, opts='', listenPort=None, **params):
        """dpid: dpid hex string (or None to derive from name, e.g. s1 -> 1)
           opts: additional switch options
           listenPort: port to listen on for dpctl connections"""
        LowPANNode.__init__(self, name, **params)
        self.dpid = self.defaultDpid(dpid)
        self.opts = opts
        self.listenPort = listenPort
        if not self.inNamespace:
            self.controlIntf = Intf('lo', self, port=0)

    def defaultDpid(self, dpid=None):
        "Return correctly formatted dpid from dpid or switch name (s1 -> 1)"
        if dpid:
            # Remove any colons and make sure it's a good hex number
            dpid = dpid.replace(':', '')
            assert len(dpid) <= self.dpidLen and int(dpid, 16) >= 0
            return '0' * (self.dpidLen - len(dpid)) + dpid
        else:
            # Use hex of the first number in the switch name
            nums = re.findall(r'\d+', self.name)
            if nums:
                dpid = hex(int(nums[0]))[2:]
            else:
                raise Exception('Unable to derive default datapath ID - '
                                'please either specify a dpid or use a '
                                'canonical ap name such as ap23.')
            return '1' + '0' * (self.dpidLen - 1 - len(dpid)) + dpid

    def defaultIntf(self):
        "Return control interface"
        if self.controlIntf:
            return self.controlIntf
        else:
            return LowPANNode.defaultIntf(self)

    def sendCmd(self, *cmd, **kwargs):
        """Send command to Node.
           cmd: string"""
        kwargs.setdefault('printPid', False)
        if not self.execed:
            return LowPANNode.sendCmd(self, *cmd, **kwargs)
        else:
            error('*** Error: %s has execed and cannot accept commands' %
                  self.name)

    # Automatic class setup support
    isSetup = False

    def connected(self):
        "Is the switch connected to a controller? (override this method)"
        # Assume that we are connected by default to whatever we need to
        # be connected to. This should be overridden by any OpenFlow
        # switch, but not by a standalone bridge.
        debug('Assuming', repr(self), 'is connected to a controller\n')
        return True

    def stop(self, deleteIntfs=True):
        """Stop switch
           deleteIntfs: delete interfaces? (True)"""
        if deleteIntfs:
            self.deleteIntfs()

    def __repr__(self):
        "More informative string representation"
        intfs = (','.join(['%s:%s' % (i.name, i.IP())
                           for i in self.intfList()]))
        return '<%s %s: %s pid=%s> ' % (
            self.__class__.__name__, self.name, intfs, self.pid)


class UserSensor(APSensor):
    "User-space AP."

    dpidLen = 12

    def __init__(self, name, dpopts='--no-slicing', **kwargs):
        """Init.
           name: name for the switch
           dpopts: additional arguments to ofdatapath (--no-slicing)"""
        APSensor.__init__(self, name, **kwargs)
        super(UserAP, self).__init__(name, dpopts='--no-slicing', **kwargs)
        pathCheck('ofdatapath', 'ofprotocol',
                  moduleName='the OpenFlow reference user switch' +
                             '(openflow.org)')
        if self.listenPort:
            self.opts += ' --listen=ptcp:%i ' % self.listenPort
        else:
            self.opts += ' --listen=punix:/tmp/%s.listen' % self.name
        self.dpopts = dpopts

    def start(self, controllers):
        """Start OpenFlow reference user datapath.
           Log to /tmp/sN-{ofd,ofp}.log.
           controllers: list of controller objects"""
        # Add controllers
        clist = ','.join(['tcp:%s:%d' % (c.IP(), c.port)
                          for c in controllers])
        ofdlog = '/tmp/' + self.name + '-ofd.log'
        ofplog = '/tmp/' + self.name + '-ofp.log'
        intfs = [str(i) for i in self.intfList()
                 if (isinstance(i, IntfSixLoWPAN) and not i.IP6() or
                     (not isinstance(i, IntfSixLoWPAN) and not i.IP()))]

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


class OVSSensor(APSensor, OVSSwitch):
    "Open vSwitch Sensor. Depends on ovs-vsctl."

    def __init__(self, name, failMode='secure', datapath='kernel',
                 inband=False, protocols=None,
                 reconnectms=1000, stp=False, batch=False, **params):
        """name: name for switch
           failMode: controller loss behavior (secure|open)
           datapath: userspace or kernel mode (kernel|user)
           inband: use in-band control (False)
           protocols: use specific OpenFlow version(s) (e.g. OpenFlow13)
                      Unspecified (or old OVS version) uses OVS default
           reconnectms: max reconnect timeout in ms (0/None for default)
           stp: enable STP (False, requires failMode=standalone)
           batch: enable batch startup (False)"""
        APSensor.__init__(self, name, **params)
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
        pathCheck('ovs-vsctl',
                  moduleName='Open vSwitch (openvswitch.org)')
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

    def start(self, controllers):
        "Start up a new OVS OpenFlow switch using ovs-vsctl"
        if self.inNamespace:
            raise Exception(
                'OVS kernel AP does not work in a namespace')
        int(self.dpid, 16)  # DPID must be a hex string
        # Command to add interfaces
        intfs = ''.join(' -- add-port %s %s' % (self, intf) +
                        self.intfOpts(intf)
                        for intf in self.intfList()
                        if self.ports[intf] and
                        (isinstance(intf, IntfSixLoWPAN) and not intf.IP6() or
                         not isinstance(intf, IntfSixLoWPAN) and not intf.IP()))

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

    @classmethod
    def batchStartup(cls, aps, run=errRun):
        """Batch startup for OVS
           switches: switches to start up
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
        for switch in aps:
            for intf in switch.intfs.values():
                if isinstance(intf, IntfSixLoWPAN):
                    intf.config(**intf.params)
        return ap

    # This should be ~ int( quietRun( 'getconf ARG_MAX' ) ),
    # but the real limit seems to be much lower
    argmax = 128000
