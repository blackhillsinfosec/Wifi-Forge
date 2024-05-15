"""
    Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)
"""

from mininet.util import BaseString, getincrementaldecoder, Python3, \
    errRun, quietRun
from mn_wifi.node import Node_wifi


class WWANNode(Node_wifi):
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
    def setIP(self, ip, prefixLen=64, intf=None, **kwargs):
        """Set the IP address for an interface.
           intf: intf or intf name
           ip: IP address as a string
           kwargs: any additional arguments for intf.setIP"""
        return self.intf(intf).setIP(ip, prefixLen, **kwargs)

    def IP(self, intf=None):
        "Return IP address of a node or specific interface."
        return self.intf(intf).IP()

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

    def config(self, mac=None, ip=None, defaultRoute=None, lo='up', **_params):
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

        self.setParam(r, 'setIP', ip=ip)
        self.setParam(r, 'setDefaultRoute', defaultRoute=defaultRoute)

        # This should be examined
        self.cmd('ip link set lo ' + lo)
        return r