#!/usr/bin/env python

"""Package: mininet
   Test creation and all-pairs ping for each included mininet topo type."""

import unittest
import sys
#from time import sleep
from functools import partial

#from mininet.net import Mininet
#from mininet.node import Station, Controller
from mininet.node import UserSwitch, OVSSwitch, IVSSwitch
#from mininet.topo import SingleAPTopo, LinearWirelessTopo
from mininet.log import setLogLevel
from mininet.util import quietRun
from mininet.clean import cleanup

# Tell pylint not to complain about calls to other class
# pylint: disable=E1101

class testSingleSwitchCommon( object ):
    "Test ping with single ap topology (common code)."

    switchClass = None  # overridden in subclasses

    @staticmethod
    def tearDown():
        "Clean up if necessary"
        if sys.exc_info != ( None, None, None ):
            cleanup()

    #def testMinimal( self ):
    #    "Ping test on minimal topology"
    #    mn = Mininet( SingleAPTopo(), self.switchClass, Station, Controller,
    #                  waitConnected=True )
    #    sleep(2)
    #    dropped = mn.run( mn.ping )
    #    self.assertEqual( dropped, 0 )

    #def testSingle5( self ):
    #    "Ping test on 5-Station single-ap topology"
    #    mn = Mininet( SingleAPTopo( k=5 ), self.switchClass, Station, 
    #                  Controller, waitConnected=True )
    #    sleep(2)
    #    dropped = mn.run( mn.ping )
    #    self.assertEqual( dropped, 0 )

# pylint: enable=E1101

class testSingleSwitchOVSKernel( testSingleSwitchCommon, unittest.TestCase ):
    "Test ping with single ap topology (OVS kernel ap)."
    switchClass = OVSSwitch

class testSingleSwitchOVSUser( testSingleSwitchCommon, unittest.TestCase ):
    "Test ping with single ap topology (OVS user ap)."
    switchClass = partial( OVSSwitch, datapath='user' )

@unittest.skipUnless( quietRun( 'which ivs-ctl' ), 'IVS is not installed' )
class testSingleSwitchIVS( testSingleSwitchCommon, unittest.TestCase ):
    "Test ping with single ap topology (IVS switch)."
    switchClass = IVSSwitch

@unittest.skipUnless( quietRun( 'which ofprotocol' ),
                      'Reference user ap is not installed' )
class testSingleSwitchUserspace( testSingleSwitchCommon, unittest.TestCase ):
    "Test ping with single ap topology (Userspace ap)."
    switchClass = UserSwitch


# Tell pylint not to complain about calls to other class
# pylint: disable=E1101

class testLinearCommon( object ):
    "Test all-pairs ping with LinearNet (common code)."

    switchClass = None  # overridden in subclasses

    #def testLinear5( self ):
    #    "Ping test on a 5-ap topology"
    #    mn = Mininet( LinearWirelessTopo( k=5 ), self.switchClass, Station,
    #                  Controller, waitConnected=True )
    #    sleep(2)
    #    dropped = mn.run( mn.ping )
    #    self.assertEqual( dropped, 0 )

# pylint: enable=E1101


class testLinearOVSKernel( testLinearCommon, unittest.TestCase ):
    "Test all-pairs ping with LinearNet (OVS kernel ap)."
    switchClass = OVSSwitch

class testLinearOVSUser( testLinearCommon, unittest.TestCase ):
    "Test all-pairs ping with LinearNet (OVS user ap)."
    switchClass = partial( OVSSwitch, datapath='user' )

@unittest.skipUnless( quietRun( 'which ivs-ctl' ), 'IVS is not installed' )
class testLinearIVS( testLinearCommon, unittest.TestCase ):
    "Test all-pairs ping with LinearNet (IVS ap)."
    switchClass = IVSSwitch

@unittest.skipUnless( quietRun( 'which ofprotocol' ),
                      'Reference user ap is not installed' )
class testLinearUserspace( testLinearCommon, unittest.TestCase ):
    "Test all-pairs ping with LinearNet (Userspace ap)."
    switchClass = UserSwitch


if __name__ == '__main__':
    setLogLevel( 'warning' )
    unittest.main()
