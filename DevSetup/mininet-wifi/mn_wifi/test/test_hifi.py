#!/usr/bin/env python

"""Package: mininet
   Test creation and pings for topologies with link and/or CPU options."""

import unittest
import sys
from functools import partial

from mininet.net import Mininet
from mininet.node import IVSSwitch
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.topo import Topo
from mininet.log import setLogLevel
from mininet.util import quietRun
from mininet.clean import cleanup
from mn_wifi.node import OVSAP, UserAP


# Number of stations for each test
N = 2

class SingleAPOptionsTopo(Topo):
    "Single switch connected to n hosts."
    def __init__(self, n=2, hopts=None, lopts=None):
        if not hopts:
            hopts = {}
        if not lopts:
            lopts = {}
        Topo.__init__(self, hopts=hopts, lopts=lopts)
        ap = self.addAccessPoint('ap1')
        for h in range(n):
            station = self.addStation('sta%s' % (h + 1))
            self.addLink(station, ap)

# Tell pylint not to complain about calls to other class
# pylint: disable=E1101

class testOptionsTopoCommon( object ):
    """Verify ability to create networks with host and link options
       (common code)."""

    apClass = None  # overridden in subclasses

    @staticmethod
    def tearDown():
        "Clean up if necessary"
        if sys.exc_info != ( None, None, None ):
            cleanup()

    def runOptionsTopoTest( self, n, msg, hopts=None, lopts=None ):
        "Generic topology-with-options test runner."
        mn = Mininet( topo=SingleAPOptionsTopo( n=n, hopts=hopts,
                                                lopts=lopts ),
                      host=CPULimitedHost, link=TCLink,
                      switch=self.apClass, waitConnected=True)
        dropped = mn.run( mn.ping )
        hoptsStr = ', '.join( '%s: %s' % ( opt, value )
                              for opt, value in hopts.items() )
        loptsStr = ', '.join( '%s: %s' % ( opt, value )
                              for opt, value in lopts.items() )
        msg += ( '%s%% of pings were dropped during mininet.ping().\n'
                 'Topo = SingleAPTopo, %s stations\n'
                 'hopts = %s\n'
                 'lopts = %s\n'
                 'host = CPULimitedHost\n'
                 'link = TCLink\n'
                 'Switch = %s\n'
                 % ( dropped, n, hoptsStr, loptsStr, self.switchClass ) )

        self.assertEqual( dropped, 0, msg=msg )

    def assertWithinTolerance( self, measured, expected, tolerance_frac, msg ):
        """Check that a given value is within a tolerance of expected
        tolerance_frac: less-than-1.0 value; 0.8 would yield 20% tolerance.
        """
        upperBound = ( float( expected ) + ( 1 - tolerance_frac ) *
                       float( expected ) )
        lowerBound = float( expected ) * tolerance_frac
        info = ( 'measured value is out of bounds\n'
                 'expected value: %s\n'
                 'measured value: %s\n'
                 'failure tolerance: %s\n'
                 'upper bound: %s\n'
                 'lower bound: %s\n'
                 % ( expected, measured, tolerance_frac,
                     upperBound, lowerBound ) )
        msg += info

        self.assertGreaterEqual( float( measured ), lowerBound, msg=msg )
        self.assertLessEqual( float( measured ), upperBound, msg=msg )

# pylint: enable=E1101

class testOptionsTopoOVSKernel( testOptionsTopoCommon, unittest.TestCase ):
    """Verify ability to create networks with host and link options
       (OVS kernel switch)."""
    longMessage = True
    switchClass = OVSAP

@unittest.skip( 'Skipping OVS user switch test for now' )
class testOptionsTopoOVSUser( testOptionsTopoCommon, unittest.TestCase ):
    """Verify ability to create networks with host and link options
       (OVS user switch)."""
    longMessage = True
    switchClass = partial( OVSAP, datapath='user' )

@unittest.skipUnless( quietRun( 'which ivs-ctl' ), 'IVS is not installed' )
class testOptionsTopoIVS( testOptionsTopoCommon, unittest.TestCase ):
    "Verify ability to create networks with host and link options (IVS)."
    longMessage = True
    switchClass = IVSSwitch

@unittest.skipUnless( quietRun( 'which ofprotocol' ),
                      'Reference user switch is not installed' )
class testOptionsTopoUserspace( testOptionsTopoCommon, unittest.TestCase ):
    """Verify ability to create networks with host and link options
     (UserSwitch)."""
    longMessage = True
    apClass = UserAP

if __name__ == '__main__':
    setLogLevel( 'warning' )
    unittest.main()
