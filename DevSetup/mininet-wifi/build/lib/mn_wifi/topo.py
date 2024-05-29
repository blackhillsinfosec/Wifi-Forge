#!/usr/bin/env python
"""@package topo

Wireless Network topology creation.

@author Ramon Fontes (ramonrf@dca.fee.unicamp.br)

This package includes code to represent network topologies.
"""

from mininet.util import irange
from mininet.topo import Topo as MN_TOPO, MultiGraph


class Topo(MN_TOPO):
    "Data center network representation for structured multi-trees."

    def __init__(self, *args, **params):
        """Topo object.
           Optional named parameters:
           hinfo: default host options
           sopts: default switch options
           lopts: default link options
           calls build()"""
        self.g = MultiGraph()
        self.hopts = params.pop('hopts', {})
        self.sopts = params.pop('sopts', {})
        self.lopts = params.pop('lopts', {})
        # ports[src][dst][sport] is port on dst that connects to src
        self.ports = {}
        self.build(*args, **params)

    def build(self, *args, **params):
        "Override this method to build your topology."
        pass

    def addStation(self, name, **opts):
        """Convenience method: Add station to graph.
           name: station name
           opts: station options
           returns: host name"""
        if not opts and self.hopts:
            opts = self.hopts
        return self.addNode(name, isStation=True, **opts)

    def addAccessPoint(self, name, **opts):
        """Convenience method: Add ap to graph.
           name: ap name
           opts: ap options
           returns: ap name"""

        if not opts and self.sopts:
            opts = self.sopts
        result = self.addNode(name, isAP=True, **opts)
        return result

    def addHost(self, name, **opts):
        """Convenience method: Add host to graph.
           name: host name
           opts: host options
           returns: host name"""
        if not opts and self.hopts:
            opts = self.hopts
        return self.addNode(name, isHost=True, **opts)

    # This legacy port management mechanism is clunky and will probably
    # be removed at some point.

    def addPort(self, src, dst, sport=None, dport=None):
        """Generate port mapping for new edge.
            src: source switch name
            dst: destination switch name"""
        # Initialize if necessary
        ports = self.ports
        ports.setdefault(src, {})
        ports.setdefault(dst, {})
        # New port: number of outlinks + base
        if sport is None:
            if 'isAP' in self.g.node[src] or 'isSwitch' in self.g.node[src]:
                src_base = 1
            else:
                src_base = 0
            if 'isAP' in self.g.node[src]:
                sport = None
            else:
                sport = len(ports[ src ]) + src_base
        if dport is None:
            if 'isAP' in self.g.node[dst] or 'isSwitch' in self.g.node[dst]:
                dst_base = 1
            else:
                dst_base = 0
            if 'isAP' in self.g.node[dst]:
                dport = None
            else:
                dport = len(ports[ dst ]) + dst_base
        ports[ src ][ sport ] = (dst, dport)
        ports[ dst ][ dport ] = (src, sport)
        return sport, dport

    def nodes( self, sort=True ):
        "Return nodes in graph"
        if sort:
            return self.sorted( self.g.nodes() )
        return self.g.nodes()

    def aps( self, sort=True ):
        """Return aps.
           sort: sort aps alphabetically
           returns: dpids list of dpids"""
        return [ n for n in self.nodes( sort ) if 'isAP' in self.g.node[ n ] ]

    def stations( self, sort=True ):
        """Return stations.
           sort: sort stations alphabetically
           returns: list of stations"""
        return [ n for n in self.nodes( sort ) if 'isStation' in self.g.node[ n ] ]

    def switches( self, sort=True ):
        """Return switches.
           sort: sort switches alphabetically
           returns: list of switches"""
        return [ n for n in self.nodes( sort ) if 'isSwitch' in self.g.node[ n ] ]

    def hosts( self, sort=True ):
        """Return hosts.
           sort: sort hosts alphabetically
           returns: list of hosts"""
        return [ n for n in self.nodes( sort ) if 'isHost' in self.g.node[ n ] ]


# Our idiom defines additional parameters in build(param...)
# pylint: disable=arguments-differ

class SingleAPTopo(Topo):
    "Single ap connected to k stations."
    def build(self, k=2, **_opts):
        "k: number of stations"
        self.k = k
        ap = self.addAccessPoint('ap1')
        for h in irange(1, k):
            sta = self.addStation('sta%s' % h)
            self.addLink(sta, ap)


class MinimalWirelessTopo(SingleAPTopo):
    "Minimal wireless topology with two stations and one ap"
    def build(self):
        return SingleAPTopo.build(self, k=2)

                
class LinearWirelessTopo(Topo):
    "Linear Wireless topology of k aps, with n stations per ap."

    def build(self, k=2, n=1, **_opts):
        """k: number of switches
           n: number of hosts per switch"""
        self.k = k
        self.n = n
        if n == 1:
            genStaName = lambda i, j: 'sta%s' % i
        else:
            genStaName = lambda i, j: 'sta%sap%d' % (j, i)

        lastAP = None
        for i in irange(1, k):
            # Add accessPoint
            ap = self.addAccessPoint('ap%s' % i, ssid='ssid_ap%s' % i)
            # Add hosts to accessPoint
            for j in irange(1, n):
                sta = self.addStation(genStaName(i, j))
                self.addLink(sta, ap)
            # Connect accessPoint to previous
            if lastAP:
                self.addLink(ap, lastAP)
            lastAP = ap

# pylint: enable=arguments-differ
