#!/usr/bin/env python

"""Package: mininet
   Regression tests for ap dpid assignment."""

import unittest
import sys

from mininet.node import Controller, IVSSwitch
from mininet.log import setLogLevel
from mininet.util import quietRun
from mininet.clean import cleanup
from mn_wifi.node import Station, UserAP, OVSAP
from mn_wifi.topo import Topo
from mn_wifi.net import Mininet_wifi


class TestSwitchDpidAssignmentOVS(unittest.TestCase):
    "Verify Switch dpid assignment."

    accessPointClass = OVSAP  # overridden in subclasses

    def tearDown(self):
        "Clean up if necessary"
        # satisfy pylint
        assert self
        if sys.exc_info != (None, None, None):
            cleanup()

    def testDefaultDpid(self):
        """Verify that the default dpid is assigned using a valid provided
        canonical apname if no dpid is passed in ap creation."""
        ap = Mininet_wifi(topo=Topo(),
                          accessPoint=self.accessPointClass,
                          station=Station, controller=Controller,
                         ).addAccessPoint('ap1')
        self.assertEqual(ap.defaultDpid(), ap.dpid)

    def dpidFrom(self, num):
        "Compute default dpid from number"
        fmt = ('%0' + str(self.accessPointClass.dpidLen) + 'x')
        return fmt % num

    def testActualDpidAssignment(self):
        """Verify that AP dpid is the actual dpid assigned if dpid is
        passed in ap creation."""
        dpid = self.dpidFrom(0xABCD)
        ap = Mininet_wifi(topo=Topo(), accessPoint=self.accessPointClass,
                          station=Station, controller=Controller,
                         ).addAccessPoint('ap1', dpid=dpid)
        self.assertEqual(ap.dpid, dpid)

    def dpidFrom_(self, num):
        "Compute default dpid from number"
        fmt = ('1%0' + str(self.accessPointClass.dpidLen - 1) + 'x')
        return fmt % num

    def testDefaultDpidLen(self):
        """Verify that Default dpid length is 16 characters consisting of
        16 - len(hex of first string of contiguous digits passed in ap
        name) 0's followed by hex of first string of contiguous digits passed
        in ap name."""
        ap = Mininet_wifi(topo=Topo(), accessPoint=self.accessPointClass,
                          station=Station, controller=Controller,
                         ).addAccessPoint('ap123')

        self.assertEqual(ap.dpid, self.dpidFrom_(123))

class OVSUser(OVSAP):
    "OVS User AP convenience class"
    def __init__(self, *args, **kwargs):
        kwargs.update(datapath='user')
        OVSAP.__init__(self, *args, **kwargs)

class testSwitchOVSUser(TestSwitchDpidAssignmentOVS):
    "Test dpid assignnment of OVS User AP."
    accessPointClass = OVSUser

@unittest.skipUnless(quietRun('which ivs-ctl'),
                     'IVS ap is not installed')
class testSwitchIVS(TestSwitchDpidAssignmentOVS):
    "Test dpid assignment of IVS ap."
    accessPointClass = IVSSwitch

@unittest.skipUnless(quietRun('which ofprotocol'),
                     'Reference user ap is not installed')
class testSwitchUserspace(TestSwitchDpidAssignmentOVS):
    "Test dpid assignment of Userspace ap."
    accessPointClass = UserAP


if __name__ == '__main__':
    setLogLevel('warning')
    unittest.main()
