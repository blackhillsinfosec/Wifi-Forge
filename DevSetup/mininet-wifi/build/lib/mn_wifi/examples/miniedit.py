#!/usr/bin/env python

"""
MiniEdit: a simple network editor for Mininet

This is a simple demonstration of how one might build a
GUI application using Mininet as the network model.

Bob Lantz, April 2010
Gregory Gee, July 2013

Controller icon from http://semlabs.co.uk/
OpenFlow icon from https://www.opennetworking.org/
"""

# Miniedit needs some work in order to pass pylint...
# pylint: disable=line-too-long,too-many-branches
# pylint: disable=too-many-statements,attribute-defined-outside-init
# pylint: disable=missing-docstring

MINIEDIT_VERSION = '2.3'

from optparse import OptionParser
from subprocess import call

import re
import json
from packaging import version
#from distutils.version import StrictVersion
import os
import sys
from functools import partial

Python3 = sys.version_info[0] == 3

if Python3:
    from tkinter import (Frame, Label, LabelFrame, Entry, OptionMenu, Checkbutton,
                         Menu, Toplevel, Button, BitmapImage, PhotoImage, Canvas,
                         Scrollbar, Wm, TclError, StringVar, IntVar,
                         E, W, EW, NW, Y, VERTICAL, SOLID, CENTER, ttk,
                         messagebox, font, filedialog, simpledialog,
                         RIGHT, LEFT, BOTH, TRUE, FALSE)
else:
    from Tkinter import ( Frame, Label, LabelFrame, Entry, OptionMenu, Checkbutton,
                          Menu, Toplevel, Button, BitmapImage, PhotoImage, Canvas,
                          Scrollbar, Wm, TclError, StringVar, IntVar,
                          E, W, EW, NW, Y, VERTICAL, SOLID, CENTER,
                          RIGHT, LEFT, BOTH, TRUE, FALSE)
    import ttk
    import tkFont as font
    import tkFileDialog as filedialog
    import tkSimpleDialog as simpledialog


if 'PYTHONPATH' in os.environ:
    sys.path = os.environ[ 'PYTHONPATH' ].split( ':' ) + sys.path

# someday: from ttk import *

from mininet.log import info, debug, warn, setLogLevel
from mininet.net import VERSION
from mininet.util import netParse, ipAdd, quietRun
from mininet.util import buildTopo
from mininet.util import custom, customClass
from mininet.term import makeTerm, cleanUpScreens
from mininet.node import Controller, RemoteController, NOX, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSSwitch, UserSwitch
from mininet.link import TCLink, Intf, Link
from mininet.moduledeps import moduleDeps
from mininet.topo import SingleSwitchTopo, LinearTopo, SingleSwitchReversedTopo
from mininet.topolib import TreeTopo

from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.node import CPULimitedStation, Station, OVSAP, UserAP
from mn_wifi.bmv2 import P4Switch, P4AP
from mn_wifi.link import wmediumd, master
from mn_wifi.mobility import Mobility, ConfigMobLinks
from mn_wifi.module import Mac80211Hwsim
from mn_wifi.wmediumdConnector import interference


info( 'MiniEdit running against Mininet '+VERSION, '\n' )
MININET_VERSION = re.sub(r'[^\d\.]', '', VERSION)

TOPODEF = 'none'
TOPOS = { 'minimal': lambda: SingleSwitchTopo( k=2 ),
          'linear': LinearTopo,
          'reversed': SingleSwitchReversedTopo,
          'single': SingleSwitchTopo,
          'none': None,
          'tree': TreeTopo }
CONTROLLERDEF = 'ref'
CONTROLLERS = { 'ref': Controller,
                'ovsc': OVSController,
                'nox': NOX,
                'remote': RemoteController,
                'none': lambda name: None }
LINKDEF = 'default'
LINKS = { 'default': Link,
          'tc': TCLink }
HOSTDEF = 'proc'
HOSTS = { 'proc': Host,
          'rt': custom( CPULimitedHost, sched='rt' ),
          'cfs': custom( CPULimitedHost, sched='cfs' ) }


class InbandController( RemoteController ):
    "RemoteController that ignores checkListening"
    def checkListening( self ):
        "Overridden to do nothing."
        return


class CustomUserSwitch(UserSwitch):
    "Customized UserSwitch"
    def __init__( self, name, dpopts='--no-slicing', **kwargs ):
        UserSwitch.__init__( self, name, **kwargs )
        self.switchIP = None

    def getSwitchIP(self):
        "Return management IP address"
        return self.switchIP

    def setSwitchIP(self, ip):
        "Set management IP address"
        self.switchIP = ip

    def start( self, controllers ):
        "Start and set management IP address"
        # Call superclass constructor
        UserSwitch.start( self, controllers )
        # Set Switch IP address
        if self.switchIP is not None:
            if not self.inNamespace:
                self.cmd( 'ifconfig', self, self.switchIP )
            else:
                self.cmd( 'ifconfig lo', self.switchIP )


class CustomUserAP(UserAP):
    "Customized UserAP"
    def __init__( self, name, dpopts='--no-slicing', **kwargs ):
        UserAP.__init__( self, name, **kwargs )
        self.apIP = None

    def getAPIP(self):
        "Return management IP address"
        return self.apIP

    def setAPIP(self, ip):
        "Set management IP address"
        self.apIP = ip

    def start( self, controllers ):
        "Start and set management IP address"
        # Call superclass constructor
        UserAP.start( self, controllers )
        # Set AP IP address
        if self.apIP is not None:
            if not self.inNamespace:
                self.cmd( 'ifconfig', self, self.apIP )
            else:
                self.cmd( 'ifconfig lo', self.apIP )


class LegacyRouter( Node ):
    "Simple IP router"
    def __init__( self, name, inNamespace=True, **params ):
        Node.__init__( self, name, inNamespace, **params )

    def config( self, **_params ):
        if self.intfs:
            self.setParam( _params, 'setIP', ip='0.0.0.0' )
        r = Node.config( self, **_params )
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
        return r


class LegacySwitch(OVSSwitch):
    "OVS switch in standalone/bridge mode"
    def __init__( self, name, **params ):
        OVSSwitch.__init__( self, name, failMode='standalone', **params )
        self.switchIP = None


class customOvs(OVSSwitch):
    "Customized OVS switch"

    def __init__( self, name, failMode='secure', datapath='kernel', **params ):
        OVSSwitch.__init__( self, name, failMode=failMode, datapath=datapath, **params )
        self.switchIP = None

    def getSwitchIP(self):
        "Return management IP address"
        return self.switchIP

    def setSwitchIP(self, ip):
        "Set management IP address"
        self.switchIP = ip

    def start( self, controllers ):
        "Start and set management IP address"
        # Call superclass constructor
        OVSSwitch.start( self, controllers )
        # Set Switch IP address
        if self.switchIP is not None:
            self.cmd( 'ifconfig', self, self.switchIP )


class customOvsAP(OVSAP):
    "Customized OVS switch"

    def __init__( self, name, failMode='secure', datapath='kernel', **params ):
        OVSAP.__init__( self, name, failMode=failMode, datapath=datapath,**params )
        self.apIP = None

    def getAPIP(self):
        "Return management IP address"
        return self.apIP

    def setAPIP(self, ip):
        "Set management IP address"
        self.apIP = ip

    def start( self, controllers ):
        "Start and set management IP address"
        # Call superclass constructor
        OVSAP.start( self, controllers )
        # Set AP IP address
        if self.apIP is not None:
            self.cmd( 'ifconfig', self, self.apIP )


class customBmv2Switch(P4Switch):
    "Customized Bmv2 switch"

    def __init__(self, name, json=None, grpcport=None, thriftport=None, netcfg=False,
                 switch_config=None, **kwargs):
        P4Switch.__init__(self, name, json, grpcport, thriftport, netcfg,
                                switch_config, **kwargs)
        self.apIP = None

    def getAPIP(self):
        "Return management IP address"
        return self.apIP

    def setAPIP(self, ip):
        "Set management IP address"
        self.apIP = ip

    def start(self, controllers):
        "Start and set management IP address"
        # Call superclass constructor
        P4Switch.start(self, controllers)
        # Set AP IP address
        if self.apIP is not None:
            self.cmd('ifconfig', self, self.apIP)


class customBmv2AP(P4AP):
    "Customized Bmv2 AP"

    def __init__(self, name, json=None, grpcport=None, thriftport=None, netcfg=False,
                 switch_config=None, **kwargs):
        P4AP.__init__(self, name, json, grpcport, thriftport, netcfg,
                            switch_config, **kwargs)
        self.apIP = None

    def getAPIP(self):
        "Return management IP address"
        return self.apIP

    def setAPIP(self, ip):
        "Set management IP address"
        self.apIP = ip

    def start(self, controllers):
        "Start and set management IP address"
        # Call superclass constructor
        P4AP.start(self, controllers)
        # Set AP IP address
        if self.apIP is not None:
            self.cmd('ifconfig', self, self.apIP)


class PrefsDialog(simpledialog.Dialog):
    "Preferences dialog"

    def __init__(self, parent, title, prefDefaults):

        self.prefValues = prefDefaults

        simpledialog.Dialog.__init__(self, parent, title)

    def body(self, master):
        "Create dialog body"
        self.rootFrame = master
        self.leftfieldFrame = Frame(self.rootFrame, padx=5, pady=5)
        self.leftfieldFrame.grid(row=0, column=0, sticky='nswe', columnspan=2)
        self.rightfieldFrame = Frame(self.rootFrame, padx=5, pady=5)
        self.rightfieldFrame.grid(row=0, column=2, sticky='nswe', columnspan=2)

        # Field for Base IP
        Label(self.leftfieldFrame, text="IP Base:").grid(row=0, sticky=E)
        self.ipEntry = Entry(self.leftfieldFrame)
        self.ipEntry.grid(row=0, column=1)
        ipBase =  self.prefValues['ipBase']
        self.ipEntry.insert(0, ipBase)

        # Selection of terminal type
        row = 1
        Label(self.leftfieldFrame, text="Default Terminal:").grid(row=row, sticky=E)
        self.terminalVar = StringVar(self.leftfieldFrame)
        self.terminalOption = OptionMenu(self.leftfieldFrame, self.terminalVar, "xterm", "gterm")
        self.terminalOption.grid(row=row, column=1, sticky=W)
        terminalType = self.prefValues['terminalType']
        self.terminalVar.set(terminalType)

        # Field for CLI
        row += 1
        Label(self.leftfieldFrame, text="Start CLI:").grid(row=row, sticky=E)
        self.cliStart = IntVar()
        self.cliButton = Checkbutton(self.leftfieldFrame, variable=self.cliStart)
        self.cliButton.grid(row=row, column=1, sticky=W)
        if self.prefValues['startCLI'] == '0':
            self.cliButton.deselect()
        else:
            self.cliButton.select()

        # Field for Wmediumd
        row += 1
        Label(self.leftfieldFrame, text="Enable Wmediumd:").grid(row=row, sticky=E)
        self.enWmediumd = IntVar()
        self.cliButton = Checkbutton(self.leftfieldFrame, variable=self.enWmediumd)
        self.cliButton.grid(row=row, column=1, sticky=W)
        if self.prefValues['enableWmediumd'] == '0':
            self.cliButton.deselect()
        else:
            self.cliButton.select()

        # Selection of switch type
        row += 1
        Label(self.leftfieldFrame, text="Default Switch:").grid(row=row, sticky=E)
        self.switchType = StringVar(self.leftfieldFrame)
        self.switchTypeMenu = OptionMenu(self.leftfieldFrame, self.switchType, "P4Switch", "Open vSwitch Kernel Mode", "Userspace", "Userspace inNamespace")
        self.switchTypeMenu.grid(row=row, column=1, sticky=W)
        switchTypePref = self.prefValues['switchType']
        if switchTypePref == 'bmv2':
            self.switchType.set("P4Switch")
        elif switchTypePref == 'userns':
            self.switchType.set("Userspace inNamespace")
        elif switchTypePref == 'user':
            self.switchType.set("Userspace")
        else:
            self.switchType.set("Open vSwitch Kernel Mode")

        # Selection of ap type
        row += 1
        Label(self.leftfieldFrame, text="Default AP/Switch:").grid(row=row, sticky=E)
        self.apType = StringVar(self.leftfieldFrame)
        self.apTypeMenu = OptionMenu(self.leftfieldFrame, self.apType, "P4AP",
                                     "Open vSwitch Kernel Mode",
                                     "Userspace", "Userspace inNamespace")
        self.switchTypeMenu.grid(row=row, column=1, sticky=W)
        apTypePref = self.prefValues['apType']
        if apTypePref == 'userns':
            self.apType.set("Userspace inNamespace")
        elif apTypePref == 'user':
            self.apType.set("Userspace")
        elif apTypePref == 'bmv2':
            self.apType.set("P4AP")
        else:
            self.apType.set("Open vSwitch Kernel Mode")
        """
        # Selection of mode
        row += 1
        Label(self.leftfieldFrame, text="Mode:").grid(row=3, sticky=E)
        self.mode = StringVar(self.leftfieldFrame)
        self.modeMenu = OptionMenu(self.leftfieldFrame, self.mode, "g", "a",
                                   "b", "n")
        self.modeMenu.grid(row=3, column=1, sticky=W)
        modePref = self.prefValues['mode']
        if modePref == 'g':
            self.mode.set("g")
        elif modePref == 'a':
            self.mode.set("a")
        elif modePref == 'b':
            self.mode.set("b")
        elif modePref == 'n':
            self.mode.set("n")
        else:
            self.mode.set("g")

        # Selection of authentication type
        Label(self.leftfieldFrame, text="Authentication:").grid(row=3, sticky=E)
        self.authentication = StringVar(self.leftfieldFrame)
        self.authenticationMenu = OptionMenu(self.leftfieldFrame, self.authentication, "none", "WEP",
                                             "WPA", "WPA2", "8021x")
        self.authenticationMenu.grid(row=3, column=1, sticky=W)
        authenticationPref = self.prefValues['authentication']
        if authenticationPref == 'WEP':
            self.authentication.set("WEP")
        elif authenticationPref == 'WPA':
            self.authentication.set("WPA")
        elif authenticationPref == 'WPA2':
            self.authentication.set("WPA2")
        elif authenticationPref == '8021x':
            self.authentication.set("8021x")
        else:
            self.authentication.set("none")
        """

        # Fields for OVS OpenFlow version
        ovsFrame= LabelFrame(self.leftfieldFrame, text='Open vSwitch', padx=5, pady=5)
        ovsFrame.grid(row=4, column=0, columnspan=2, sticky=EW)
        Label(ovsFrame, text="OpenFlow 1.0:").grid(row=0, sticky=E)
        Label(ovsFrame, text="OpenFlow 1.1:").grid(row=1, sticky=E)
        Label(ovsFrame, text="OpenFlow 1.2:").grid(row=2, sticky=E)
        Label(ovsFrame, text="OpenFlow 1.3:").grid(row=3, sticky=E)

        self.ovsOf10 = IntVar()
        self.covsOf10 = Checkbutton(ovsFrame, variable=self.ovsOf10)
        self.covsOf10.grid(row=0, column=1, sticky=W)
        if self.prefValues['openFlowVersions']['ovsOf10'] == '0':
            self.covsOf10.deselect()
        else:
            self.covsOf10.select()

        self.ovsOf11 = IntVar()
        self.covsOf11 = Checkbutton(ovsFrame, variable=self.ovsOf11)
        self.covsOf11.grid(row=1, column=1, sticky=W)
        if self.prefValues['openFlowVersions']['ovsOf11'] == '0':
            self.covsOf11.deselect()
        else:
            self.covsOf11.select()

        self.ovsOf12 = IntVar()
        self.covsOf12 = Checkbutton(ovsFrame, variable=self.ovsOf12)
        self.covsOf12.grid(row=2, column=1, sticky=W)
        if self.prefValues['openFlowVersions']['ovsOf12'] == '0':
            self.covsOf12.deselect()
        else:
            self.covsOf12.select()

        self.ovsOf13 = IntVar()
        self.covsOf13 = Checkbutton(ovsFrame, variable=self.ovsOf13)
        self.covsOf13.grid(row=3, column=1, sticky=W)
        if self.prefValues['openFlowVersions']['ovsOf13'] == '0':
            self.covsOf13.deselect()
        else:
            self.covsOf13.select()

        # Field for DPCTL listen port
        row += 1
        Label(self.leftfieldFrame, text="dpctl port:").grid(row=row, sticky=E)
        self.dpctlEntry = Entry(self.leftfieldFrame)
        self.dpctlEntry.grid(row=row, column=1)
        if 'dpctl' in self.prefValues:
            self.dpctlEntry.insert(0, self.prefValues['dpctl'])

        # sFlow
        sflowValues = self.prefValues['sflow']
        self.sflowFrame= LabelFrame(self.rightfieldFrame, text='sFlow Profile for Open vSwitch', padx=5, pady=5)
        self.sflowFrame.grid(row=0, column=0, columnspan=2, sticky=EW)

        Label(self.sflowFrame, text="Target:").grid(row=0, sticky=E)
        self.sflowTarget = Entry(self.sflowFrame)
        self.sflowTarget.grid(row=0, column=1)
        self.sflowTarget.insert(0, sflowValues['sflowTarget'])

        Label(self.sflowFrame, text="Sampling:").grid(row=1, sticky=E)
        self.sflowSampling = Entry(self.sflowFrame)
        self.sflowSampling.grid(row=1, column=1)
        self.sflowSampling.insert(0, sflowValues['sflowSampling'])

        Label(self.sflowFrame, text="Header:").grid(row=2, sticky=E)
        self.sflowHeader = Entry(self.sflowFrame)
        self.sflowHeader.grid(row=2, column=1)
        self.sflowHeader.insert(0, sflowValues['sflowHeader'])

        Label(self.sflowFrame, text="Polling:").grid(row=3, sticky=E)
        self.sflowPolling = Entry(self.sflowFrame)
        self.sflowPolling.grid(row=3, column=1)
        self.sflowPolling.insert(0, sflowValues['sflowPolling'])

        # NetFlow
        nflowValues = self.prefValues['netflow']
        self.nFrame= LabelFrame(self.rightfieldFrame, text='NetFlow Profile for Open vSwitch', padx=5, pady=5)
        self.nFrame.grid(row=1, column=0, columnspan=2, sticky=EW)

        Label(self.nFrame, text="Target:").grid(row=0, sticky=E)
        self.nflowTarget = Entry(self.nFrame)
        self.nflowTarget.grid(row=0, column=1)
        self.nflowTarget.insert(0, nflowValues['nflowTarget'])

        Label(self.nFrame, text="Active Timeout:").grid(row=1, sticky=E)
        self.nflowTimeout = Entry(self.nFrame)
        self.nflowTimeout.grid(row=1, column=1)
        self.nflowTimeout.insert(0, nflowValues['nflowTimeout'])

        Label(self.nFrame, text="Add ID to Interface:").grid(row=2, sticky=E)
        self.nflowAddId = IntVar()
        self.nflowAddIdButton = Checkbutton(self.nFrame, variable=self.nflowAddId)
        self.nflowAddIdButton.grid(row=2, column=1, sticky=W)
        if nflowValues['nflowAddId'] == '0':
            self.nflowAddIdButton.deselect()
        else:
            self.nflowAddIdButton.select()

        # initial focus
        return self.ipEntry

    def apply(self):
        ipBase = self.ipEntry.get()
        terminalType = self.terminalVar.get()
        startCLI = str(self.cliStart.get())
        enableWmediumd = str(self.enWmediumd.get())
        sw = self.switchType.get()
        ap = self.apType.get()
        dpctl = self.dpctlEntry.get()

        ovsOf10 = str(self.ovsOf10.get())
        ovsOf11 = str(self.ovsOf11.get())
        ovsOf12 = str(self.ovsOf12.get())
        ovsOf13 = str(self.ovsOf13.get())

        sflowValues = {'sflowTarget':self.sflowTarget.get(),
                       'sflowSampling':self.sflowSampling.get(),
                       'sflowHeader':self.sflowHeader.get(),
                       'sflowPolling':self.sflowPolling.get()}
        nflowvalues = {'nflowTarget':self.nflowTarget.get(),
                       'nflowTimeout':self.nflowTimeout.get(),
                       'nflowAddId':str(self.nflowAddId.get())}
        self.result = {'ipBase':ipBase,
                       'terminalType':terminalType,
                       'dpctl':dpctl,
                       'sflow':sflowValues,
                       'netflow':nflowvalues,
                       'enableWmediumd': enableWmediumd,
                       'startCLI':startCLI}
        if sw == 'Userspace':
            self.result['switchType'] = 'user'
        elif sw == 'Userspace inNamespace':
            self.result['switchType'] = 'userns'
        elif sw == 'P4Switch':
            self.result['apType'] = 'bmv2'
        else:
            self.result['switchType'] = 'ovs'

        if ap == 'Userspace':
            self.result['apType'] = 'user'
        elif ap == 'Userspace inNamespace':
            self.result['apType'] = 'userns'
        elif ap == 'P4AP':
            self.result['apType'] = 'bmv2'
        else:
            self.result['apType'] = 'ovs'

        self.ovsOk = True
        if ovsOf11 == "1":
            ovsVer = self.getOvsVersion()
            if version.parse(ovsVer) < version.parse('2.0'):
                self.ovsOk = False
                messagebox.showerror(title="Error",
                          message='Open vSwitch version 2.0+ required. You have '+ovsVer+'.')
        if ovsOf12 == "1" or ovsOf13 == "1":
            ovsVer = self.getOvsVersion()
            if version.parse(ovsVer) < version.parse('1.10'):
                self.ovsOk = False
                messagebox.showerror(title="Error",
                          message='Open vSwitch version 1.10+ required. You have '+ovsVer+'.')

        if self.ovsOk:
            self.result['openFlowVersions']={'ovsOf10':ovsOf10,
                                             'ovsOf11':ovsOf11,
                                             'ovsOf12':ovsOf12,
                                             'ovsOf13':ovsOf13}
        else:
            self.result = None

    @staticmethod
    def getOvsVersion():
        "Return OVS version"
        outp = quietRun("ovs-vsctl --version")
        r = r'ovs-vsctl \(Open vSwitch\) (.*)'
        m = re.search(r, outp)
        if m is None:
            warn( 'Version check failed' )
            return None

        info( 'Open vSwitch version is '+m.group(1), '\n' )
        return m.group(1)


class CustomDialog(object):

    # TODO: Fix button placement and Title and window focus lock
    def __init__(self, master, _title):
        self.top=Toplevel(master)

        self.bodyFrame = Frame(self.top)
        self.bodyFrame.grid(row=0, column=0, sticky='nswe')
        self.body(self.bodyFrame)

        #return self.b # initial focus
        buttonFrame = Frame(self.top, relief='ridge', bd=3, bg='lightgrey')
        buttonFrame.grid(row=1 , column=0, sticky='nswe')

        okButton = Button(buttonFrame, width=8, text='OK', relief='groove',
                          bd=4, command=self.okAction)
        okButton.grid(row=0, column=0, sticky=E)

        canlceButton = Button(buttonFrame, width=8, text='Cancel', relief='groove',
                              bd=4, command=self.cancelAction)
        canlceButton.grid(row=0, column=1, sticky=W)

    def body(self, master):
        self.rootFrame = master

    def apply(self):
        self.top.destroy()

    def cancelAction(self):
        self.top.destroy()

    def okAction(self):
        self.apply()
        self.top.destroy()

class HostDialog(CustomDialog):

    def __init__(self, master, title, prefDefaults):

        self.prefValues = prefDefaults
        self.result = None

        CustomDialog.__init__(self, master, title)

    def body(self, master):
        self.rootFrame = master
        n = ttk.Notebook(self.rootFrame)
        self.propFrame = Frame(n)
        self.vlanFrame = Frame(n)
        self.interfaceFrame = Frame(n)
        self.mountFrame = Frame(n)
        n.add(self.propFrame, text='Properties')
        n.add(self.vlanFrame, text='VLAN Interfaces')
        n.add(self.interfaceFrame, text='External Interfaces')
        n.add(self.mountFrame, text='Private Directories')
        n.pack()

        ### TAB 1
        # Field for Hostname
        Label(self.propFrame, text="Hostname:").grid(row=0, sticky=E)
        self.hostnameEntry = Entry(self.propFrame)
        self.hostnameEntry.grid(row=0, column=1)
        if 'hostname' in self.prefValues:
            self.hostnameEntry.insert(0, self.prefValues['hostname'])

        # Field for Switch IP
        Label(self.propFrame, text="IP Address:").grid(row=1, sticky=E)
        self.ipEntry = Entry(self.propFrame)
        self.ipEntry.grid(row=1, column=1)
        if 'ip' in self.prefValues:
            self.ipEntry.insert(0, self.prefValues['ip'])

        # Field for default route
        Label(self.propFrame, text="Default Route:").grid(row=2, sticky=E)
        self.routeEntry = Entry(self.propFrame)
        self.routeEntry.grid(row=2, column=1)
        if 'defaultRoute' in self.prefValues:
            self.routeEntry.insert(0, self.prefValues['defaultRoute'])

        # Field for CPU
        Label(self.propFrame, text="Amount CPU:").grid(row=3, sticky=E)
        self.cpuEntry = Entry(self.propFrame)
        self.cpuEntry.grid(row=3, column=1)
        if 'cpu' in self.prefValues:
            self.cpuEntry.insert(0, str(self.prefValues['cpu']))
        # Selection of Scheduler
        if 'sched' in self.prefValues:
            sched =  self.prefValues['sched']
        else:
            sched = 'host'
        self.schedVar = StringVar(self.propFrame)
        self.schedOption = OptionMenu(self.propFrame, self.schedVar, "host", "cfs", "rt")
        self.schedOption.grid(row=3, column=2, sticky=W)
        self.schedVar.set(sched)

        # Selection of Cores
        Label(self.propFrame, text="Cores:").grid(row=4, sticky=E)
        self.coreEntry = Entry(self.propFrame)
        self.coreEntry.grid(row=4, column=1)
        if 'cores' in self.prefValues:
            self.coreEntry.insert(1, self.prefValues['cores'])

        # Start command
        Label(self.propFrame, text="Start Command:").grid(row=5, sticky=E)
        self.startEntry = Entry(self.propFrame)
        self.startEntry.grid(row=5, column=1, sticky='nswe', columnspan=3)
        if 'startCommand' in self.prefValues:
            self.startEntry.insert(0, str(self.prefValues['startCommand']))
        # Stop command
        Label(self.propFrame, text="Stop Command:").grid(row=6, sticky=E)
        self.stopEntry = Entry(self.propFrame)
        self.stopEntry.grid(row=6, column=1, sticky='nswe', columnspan=3)
        if 'stopCommand' in self.prefValues:
            self.stopEntry.insert(0, str(self.prefValues['stopCommand']))

        ### TAB 2
        # External Interfaces
        self.externalInterfaces = 0
        Label(self.interfaceFrame, text="External Interface:").grid(row=0, column=0, sticky=E)
        self.b = Button( self.interfaceFrame, text='Add', command=self.addInterface)
        self.b.grid(row=0, column=1)

        self.interfaceFrame = VerticalScrolledTable(self.interfaceFrame, rows=0, columns=1, title='External Interfaces')
        self.interfaceFrame.grid(row=1, column=0, sticky='nswe', columnspan=2)
        self.tableFrame = self.interfaceFrame.interior
        self.tableFrame.addRow(value=['Interface Name'], readonly=True)

        # Add defined interfaces
        externalInterfaces = []
        if 'externalInterfaces' in self.prefValues:
            externalInterfaces = self.prefValues['externalInterfaces']

        for externalInterface in externalInterfaces:
            self.tableFrame.addRow(value=[externalInterface])

        ### TAB 3
        # VLAN Interfaces
        self.vlanInterfaces = 0
        Label(self.vlanFrame, text="VLAN Interface:").grid(row=0, column=0, sticky=E)
        self.vlanButton = Button( self.vlanFrame, text='Add', command=self.addVlanInterface)
        self.vlanButton.grid(row=0, column=1)

        self.vlanFrame = VerticalScrolledTable(self.vlanFrame, rows=0, columns=2, title='VLAN Interfaces')
        self.vlanFrame.grid(row=1, column=0, sticky='nswe', columnspan=2)
        self.vlanTableFrame = self.vlanFrame.interior
        self.vlanTableFrame.addRow(value=['IP Address','VLAN ID'], readonly=True)

        vlanInterfaces = []
        if 'vlanInterfaces' in self.prefValues:
            vlanInterfaces = self.prefValues['vlanInterfaces']
        for vlanInterface in vlanInterfaces:
            self.vlanTableFrame.addRow(value=vlanInterface)

        ### TAB 4
        # Private Directories
        self.privateDirectories = 0
        Label(self.mountFrame, text="Private Directory:").grid(row=0, column=0, sticky=E)
        self.mountButton = Button( self.mountFrame, text='Add', command=self.addDirectory)
        self.mountButton.grid(row=0, column=1)

        self.mountFrame = VerticalScrolledTable(self.mountFrame, rows=0, columns=2, title='Directories')
        self.mountFrame.grid(row=1, column=0, sticky='nswe', columnspan=2)
        self.mountTableFrame = self.mountFrame.interior
        self.mountTableFrame.addRow(value=['Mount','Persistent Directory'], readonly=True)

        directoryList = []
        if 'privateDirectory' in self.prefValues:
            directoryList = self.prefValues['privateDirectory']
        for privateDir in directoryList:
            if isinstance( privateDir, tuple ):
                self.mountTableFrame.addRow(value=privateDir)
            else:
                self.mountTableFrame.addRow(value=[privateDir,''])


    def addDirectory( self ):
        self.mountTableFrame.addRow()

    def addVlanInterface( self ):
        self.vlanTableFrame.addRow()

    def addInterface( self ):
        self.tableFrame.addRow()

    def apply(self):
        externalInterfaces = []
        for row in range(self.tableFrame.rows):
            if (len(self.tableFrame.get(row, 0)) > 0 and row > 0):
                externalInterfaces.append(self.tableFrame.get(row, 0))
        vlanInterfaces = []
        for row in range(self.vlanTableFrame.rows):
            if (len(self.vlanTableFrame.get(row, 0)) > 0
                    and len(self.vlanTableFrame.get(row, 1)) > 0 and row > 0):
                vlanInterfaces.append([self.vlanTableFrame.get(row, 0), self.vlanTableFrame.get(row, 1)])
        privateDirectories = []
        for row in range(self.mountTableFrame.rows):
            if len(self.mountTableFrame.get(row, 0)) > 0 and row > 0:
                if len(self.mountTableFrame.get(row, 1)) > 0:
                    privateDirectories.append((self.mountTableFrame.get(row, 0), self.mountTableFrame.get(row, 1)))
                else:
                    privateDirectories.append(self.mountTableFrame.get(row, 0))

        results = {'cpu': self.cpuEntry.get(),
                   'cores':self.coreEntry.get(),
                   'sched':self.schedVar.get(),
                   'hostname':self.hostnameEntry.get(),
                   'ip':self.ipEntry.get(),
                   'defaultRoute':self.routeEntry.get(),
                   'startCommand':self.startEntry.get(),
                   'stopCommand':self.stopEntry.get(),
                   'privateDirectory':privateDirectories,
                   'externalInterfaces':externalInterfaces,
                   'vlanInterfaces':vlanInterfaces}
        self.result = results


class StationDialog(CustomDialog):

    def __init__(self, master, title, prefDefaults):

        self.prefValues = prefDefaults
        self.result = None

        CustomDialog.__init__(self, master, title)

    def body(self, master):
        self.rootFrame = master
        n = ttk.Notebook(self.rootFrame)
        self.propFrame = Frame(n)
        self.authFrame = Frame(n)
        self.vlanFrame = Frame(n)
        self.interfaceFrame = Frame(n)
        self.mountFrame = Frame(n)
        n.add(self.propFrame, text='Properties')
        n.add(self.authFrame, text='Authentication')
        n.add(self.vlanFrame, text='VLAN Interfaces')
        n.add(self.interfaceFrame, text='External Interfaces')
        n.add(self.mountFrame, text='Private Directories')
        n.pack()

        ### TAB 1
        # Field for Hostname
        rowCount = 0
        Label(self.propFrame, text="Name:").grid(row=rowCount, sticky=E)
        self.hostnameEntry = Entry(self.propFrame)
        self.hostnameEntry.grid(row=rowCount, column=1)
        if 'hostname' in self.prefValues:
            self.hostnameEntry.insert(0, self.prefValues['hostname'])

        # Field for SSID
        #rowCount += 1
        #Label(self.propFrame, text="SSID:").grid(row=rowCount, sticky=E)
        #self.ssidEntry = Entry(self.propFrame)
        #self.ssidEntry.grid(row=rowCount, column=1)
        #self.ssidEntry.insert(0, self.prefValues['ssid'])

        # Field for channel
        #rowCount += 1
        #Label(self.propFrame, text="Channel:").grid(row=rowCount, sticky=E)
        #self.channelEntry = Entry(self.propFrame)
        #self.channelEntry.grid(row=rowCount, column=1)
        #self.channelEntry.insert(0, self.prefValues['channel'])

        # Selection of mode
        #rowCount += 1
        #Label(self.propFrame, text="Mode:").grid(row=rowCount, sticky=E)
        #self.mode = StringVar(self.propFrame)
        #self.modeMenu = OptionMenu(self.propFrame, self.mode, "g", "a",
        #                           "b", "n")
        #self.modeMenu.grid(row=rowCount, column=1, sticky=W)
        #if 'mode' in self.prefValues:
        #    authPref = self.prefValues['mode']
        #    if authPref == 'g':
        #        self.mode.set("g")
        #    elif authPref == 'a':
        #        self.mode.set("a")
        #    elif authPref == 'b':
        #        self.mode.set("b")
        #    elif authPref == 'n':
        #        self.mode.set("n")
        #    else:
        #        self.mode.set("g")
        #else:
        #    self.mode.set("g")
        self.mode = 'g'

        # Field for Wlans
        rowCount += 1
        Label(self.propFrame, text="Wlans:").grid(row=rowCount, sticky=E)
        self.wlansEntry = Entry(self.propFrame)
        self.wlansEntry.grid(row=rowCount, column=1)
        self.wlansEntry.insert(0, self.prefValues['wlans'])

        # Field for Wpans
        rowCount += 1
        Label(self.propFrame, text="Wpans:").grid(row=rowCount, sticky=E)
        self.wpansEntry = Entry(self.propFrame)
        self.wpansEntry.grid(row=rowCount, column=1)
        self.wpansEntry.insert(0, self.prefValues['wpans'])

        # Field for signal range
        rowCount += 1
        Label(self.propFrame, text="Signal Range:").grid(row=rowCount, sticky=E)
        self.rangeEntry = Entry(self.propFrame)
        self.rangeEntry.grid(row=rowCount, column=1)
        self.rangeEntry.insert(0, self.prefValues['range'])

        # Field for Station IP
        rowCount += 1
        Label(self.propFrame, text="IP Address:").grid(row=rowCount, sticky=E)
        self.ipEntry = Entry(self.propFrame)
        self.ipEntry.grid(row=rowCount, column=1)
        if 'ip' in self.prefValues:
            self.ipEntry.insert(0, self.prefValues['ip'])

        # Field for default route
        rowCount += 1
        Label(self.propFrame, text="Default Route:").grid(row=rowCount, sticky=E)
        self.routeEntry = Entry(self.propFrame)
        self.routeEntry.grid(row=rowCount, column=1)
        if 'defaultRoute' in self.prefValues:
            self.routeEntry.insert(0, self.prefValues['defaultRoute'])

        # Field for CPU
        rowCount += 1
        Label(self.propFrame, text="Amount CPU:").grid(row=rowCount, sticky=E)
        self.cpuEntry = Entry(self.propFrame)
        self.cpuEntry.grid(row=rowCount, column=1)
        if 'cpu' in self.prefValues:
            self.cpuEntry.insert(0, str(self.prefValues['cpu']))
        # Selection of Scheduler
        if 'sched' in self.prefValues:
            sched =  self.prefValues['sched']
        else:
            sched = 'station'
        self.schedVar = StringVar(self.propFrame)
        self.schedOption = OptionMenu(self.propFrame, self.schedVar, "station", "cfs", "rt")
        self.schedOption.grid(row=rowCount, column=2, sticky=W)
        self.schedVar.set(sched)

        # Selection of Cores
        rowCount += 1
        Label(self.propFrame, text="Cores:").grid(row=rowCount, sticky=E)
        self.coreEntry = Entry(self.propFrame)
        self.coreEntry.grid(row=rowCount, column=1)
        if 'cores' in self.prefValues:
            self.coreEntry.insert(1, self.prefValues['cores'])

        # Start command
        rowCount += 1
        Label(self.propFrame, text="Start Command:").grid(row=rowCount, sticky=E)
        self.startEntry = Entry(self.propFrame)
        self.startEntry.grid(row=rowCount, column=1, sticky='nswe', columnspan=3)
        if 'startCommand' in self.prefValues:
            self.startEntry.insert(0, str(self.prefValues['startCommand']))
        # Stop command
        rowCount += 1
        Label(self.propFrame, text="Stop Command:").grid(row=rowCount, sticky=E)
        self.stopEntry = Entry(self.propFrame)
        self.stopEntry.grid(row=rowCount, column=1, sticky='nswe', columnspan=3)
        if 'stopCommand' in self.prefValues:
            self.stopEntry.insert(0, str(self.prefValues['stopCommand']))

        ### TAB Auth
        rowCount = 0
        # Selection of authentication
        Label(self.authFrame, text="Authentication:").grid(row=rowCount, sticky=E)
        self.authentication = StringVar(self.authFrame)
        self.authenticationMenu = OptionMenu(self.authFrame,
                                             self.authentication, "none", "WEP",
                                             "WPA", "WPA2", "8021x")
        self.authenticationMenu.grid(row=rowCount, column=1, sticky=W)
        if 'authentication' in self.prefValues:
            authPref = self.prefValues['authentication']
            if authPref == 'WEP':
                self.authentication.set("WEP")
            elif authPref == 'WPA':
                self.authentication.set("WPA")
            elif authPref == 'WPA2':
                self.authentication.set("WPA2")
            elif authPref == '8021x':
                self.authentication.set("8021x")
            else:
                self.authentication.set("none")
        else:
            self.authentication.set("none")
        rowCount += 1

        # Field for username
        Label(self.authFrame, text="Username:").grid(row=rowCount, sticky=E)
        self.userEntry = Entry(self.authFrame)
        self.userEntry.grid(row=rowCount, column=1)
        if 'user' in self.prefValues:
            self.userEntry.insert(0, self.prefValues['user'])

        # Field for passwd
        rowCount += 1
        Label(self.authFrame, text="Password:").grid(row=rowCount, sticky=E)
        self.passwdEntry = Entry(self.authFrame)
        self.passwdEntry.grid(row=rowCount, column=1)
        if 'passwd' in self.prefValues:
            self.passwdEntry.insert(0, self.prefValues['passwd'])

        ### TAB 2
        # External Interfaces
        self.externalInterfaces = 0
        Label(self.interfaceFrame, text="External Interface:").grid(row=0, column=0, sticky=E)
        self.b = Button( self.interfaceFrame, text='Add', command=self.addInterface)
        self.b.grid(row=0, column=1)

        self.interfaceFrame = VerticalScrolledTable(self.interfaceFrame, rows=0, columns=1, title='External Interfaces')
        self.interfaceFrame.grid(row=1, column=0, sticky='nswe', columnspan=2)
        self.tableFrame = self.interfaceFrame.interior
        self.tableFrame.addRow(value=['Interface Name'], readonly=True)

        # Add defined interfaces
        externalInterfaces = []
        if 'externalInterfaces' in self.prefValues:
            externalInterfaces = self.prefValues['externalInterfaces']

        for externalInterface in externalInterfaces:
            self.tableFrame.addRow(value=[externalInterface])

        ### TAB 3
        # VLAN Interfaces
        self.vlanInterfaces = 0
        Label(self.vlanFrame, text="VLAN Interface:").grid(row=0, column=0, sticky=E)
        self.vlanButton = Button( self.vlanFrame, text='Add', command=self.addVlanInterface)
        self.vlanButton.grid(row=0, column=1)

        self.vlanFrame = VerticalScrolledTable(self.vlanFrame, rows=0, columns=2, title='VLAN Interfaces')
        self.vlanFrame.grid(row=1, column=0, sticky='nswe', columnspan=2)
        self.vlanTableFrame = self.vlanFrame.interior
        self.vlanTableFrame.addRow(value=['IP Address','VLAN ID'], readonly=True)

        vlanInterfaces = []
        if 'vlanInterfaces' in self.prefValues:
            vlanInterfaces = self.prefValues['vlanInterfaces']
        for vlanInterface in vlanInterfaces:
            self.vlanTableFrame.addRow(value=vlanInterface)

        ### TAB 4
        # Private Directories
        self.privateDirectories = 0
        Label(self.mountFrame, text="Private Directory:").grid(row=0, column=0, sticky=E)
        self.mountButton = Button( self.mountFrame, text='Add', command=self.addDirectory)
        self.mountButton.grid(row=0, column=1)

        self.mountFrame = VerticalScrolledTable(self.mountFrame, rows=0, columns=2, title='Directories')
        self.mountFrame.grid(row=1, column=0, sticky='nswe', columnspan=2)
        self.mountTableFrame = self.mountFrame.interior
        self.mountTableFrame.addRow(value=['Mount','Persistent Directory'], readonly=True)

        directoryList = []
        if 'privateDirectory' in self.prefValues:
            directoryList = self.prefValues['privateDirectory']
        for privateDir in directoryList:
            if isinstance( privateDir, tuple ):
                self.mountTableFrame.addRow(value=privateDir)
            else:
                self.mountTableFrame.addRow(value=[privateDir,''])

    def addDirectory( self ):
        self.mountTableFrame.addRow()

    def addVlanInterface( self ):
        self.vlanTableFrame.addRow()

    def addInterface( self ):
        self.tableFrame.addRow()

    def apply(self):
        externalInterfaces = []
        for row in range(self.tableFrame.rows):
            if (len(self.tableFrame.get(row, 0)) > 0 and row > 0):
                externalInterfaces.append(self.tableFrame.get(row, 0))
        vlanInterfaces = []
        for row in range(self.vlanTableFrame.rows):
            if (len(self.vlanTableFrame.get(row, 0)) > 0 and
                    len(self.vlanTableFrame.get(row, 1)) > 0 and row > 0):
                vlanInterfaces.append([self.vlanTableFrame.get(row, 0), self.vlanTableFrame.get(row, 1)])
        privateDirectories = []
        for row in range(self.mountTableFrame.rows):
            if len(self.mountTableFrame.get(row, 0)) > 0 and row > 0:
                if len(self.mountTableFrame.get(row, 1)) > 0:
                    privateDirectories.append((self.mountTableFrame.get(row, 0), self.mountTableFrame.get(row, 1)))
                else:
                    privateDirectories.append(self.mountTableFrame.get(row, 0))

        results = {'cpu': self.cpuEntry.get(),
                   'cores':self.coreEntry.get(),
                   'sched':self.schedVar.get(),
                   'hostname':self.hostnameEntry.get(),
                   'ip':self.ipEntry.get(),
                   'defaultRoute':self.routeEntry.get(),
                   'startCommand':self.startEntry.get(),
                   'stopCommand':self.stopEntry.get(),
                   'privateDirectory':privateDirectories,
                   'externalInterfaces':externalInterfaces,
                   'vlanInterfaces':vlanInterfaces}
        #results['ssid'] = str(self.ssidEntry.get())
        results['passwd'] = str(self.passwdEntry.get())
        results['user'] = str(self.userEntry.get())
        results['wlans'] = self.wlansEntry.get()
        results['mode'] = 'g'
        results['wpans'] = self.wpansEntry.get()
        results['range'] = str(self.rangeEntry.get())
        self.result = results


class SwitchDialog(CustomDialog):

    def __init__(self, master, title, prefDefaults):

        self.prefValues = prefDefaults
        self.result = None
        CustomDialog.__init__(self, master, title)

    def body(self, master):
        self.rootFrame = master
        self.leftfieldFrame = Frame(self.rootFrame)
        self.rightfieldFrame = Frame(self.rootFrame)
        self.leftfieldFrame.grid(row=0, column=0, sticky='nswe')
        self.rightfieldFrame.grid(row=0, column=1, sticky='nswe')

        rowCount = 0
        externalInterfaces = []
        if 'externalInterfaces' in self.prefValues:
            externalInterfaces = self.prefValues['externalInterfaces']

        # Field for Hostname
        Label(self.leftfieldFrame, text="Hostname:").grid(row=rowCount, sticky=E)
        self.hostnameEntry = Entry(self.leftfieldFrame)
        self.hostnameEntry.grid(row=rowCount, column=1)
        self.hostnameEntry.insert(0, self.prefValues['hostname'])
        rowCount += 1

        # Field for DPID
        Label(self.leftfieldFrame, text="DPID:").grid(row=rowCount, sticky=E)
        self.dpidEntry = Entry(self.leftfieldFrame)
        self.dpidEntry.grid(row=rowCount, column=1)
        if 'dpid' in self.prefValues:
            self.dpidEntry.insert(0, self.prefValues['dpid'])
        rowCount += 1

        # Field for Netflow
        Label(self.leftfieldFrame, text="Enable NetFlow:").grid(row=rowCount, sticky=E)
        self.nflow = IntVar()
        self.nflowButton = Checkbutton(self.leftfieldFrame, variable=self.nflow)
        self.nflowButton.grid(row=rowCount, column=1, sticky=W)
        if 'netflow' in self.prefValues:
            if self.prefValues['netflow'] == '0':
                self.nflowButton.deselect()
            else:
                self.nflowButton.select()
        else:
            self.nflowButton.deselect()
        rowCount += 1

        # Field for sflow
        Label(self.leftfieldFrame, text="Enable sFlow:").grid(row=rowCount, sticky=E)
        self.sflow = IntVar()
        self.sflowButton = Checkbutton(self.leftfieldFrame, variable=self.sflow)
        self.sflowButton.grid(row=rowCount, column=1, sticky=W)
        if 'sflow' in self.prefValues:
            if self.prefValues['sflow'] == '0':
                self.sflowButton.deselect()
            else:
                self.sflowButton.select()
        else:
            self.sflowButton.deselect()
        rowCount += 1

        # Selection of switch type
        Label(self.leftfieldFrame, text="Switch Type:").grid(row=rowCount, sticky=E)
        self.switchType = StringVar(self.leftfieldFrame)
        self.switchTypeMenu = OptionMenu(self.leftfieldFrame, self.switchType, "Default", "P4Switch", "Open vSwitch Kernel Mode", "Userspace", "Userspace inNamespace")
        self.switchTypeMenu.grid(row=rowCount, column=1, sticky=W)
        if 'switchType' in self.prefValues:
            switchTypePref = self.prefValues['switchType']
            if switchTypePref == 'userns':
                self.switchType.set("Userspace inNamespace")
            elif switchTypePref == 'user':
                self.switchType.set("Userspace")
            elif switchTypePref == 'bmv2':
                self.switchType.set("P4AP")
            elif switchTypePref == 'ovs':
                self.switchType.set("Open vSwitch Kernel Mode")
            else:
                self.switchType.set("Default")
        else:
            self.switchType.set("Default")
        rowCount += 1

        # Field for Switch IP
        Label(self.leftfieldFrame, text="IP Address:").grid(row=rowCount, sticky=E)
        self.ipEntry = Entry(self.leftfieldFrame)
        self.ipEntry.grid(row=rowCount, column=1)
        if 'switchIP' in self.prefValues:
            self.ipEntry.insert(0, self.prefValues['switchIP'])
        rowCount += 1

        # Field for DPCTL port
        Label(self.leftfieldFrame, text="DPCTL port:").grid(row=rowCount, sticky=E)
        self.dpctlEntry = Entry(self.leftfieldFrame)
        self.dpctlEntry.grid(row=rowCount, column=1)
        if 'dpctl' in self.prefValues:
            self.dpctlEntry.insert(0, self.prefValues['dpctl'])
        rowCount+=1

        # External Interfaces
        Label(self.rightfieldFrame, text="External Interface:").grid(row=0, sticky=E)
        self.b = Button( self.rightfieldFrame, text='Add', command=self.addInterface)
        self.b.grid(row=0, column=1)

        self.interfaceFrame = VerticalScrolledTable(self.rightfieldFrame, rows=0, columns=1, title='External Interfaces')
        self.interfaceFrame.grid(row=1, column=0, sticky='nswe', columnspan=2)
        self.tableFrame = self.interfaceFrame.interior

        # Add defined interfaces
        for externalInterface in externalInterfaces:
            self.tableFrame.addRow(value=[externalInterface])

        self.commandFrame = Frame(self.rootFrame)
        self.commandFrame.grid(row=1, column=0, sticky='nswe', columnspan=2)
        self.commandFrame.columnconfigure(1, weight=1)
        # Start command
        Label(self.commandFrame, text="Start Command:").grid(row=0, column=0, sticky=W)
        self.startEntry = Entry(self.commandFrame)
        self.startEntry.grid(row=0, column=1,  sticky='nsew')
        if 'startCommand' in self.prefValues:
            self.startEntry.insert(0, str(self.prefValues['startCommand']))
        # Stop command
        Label(self.commandFrame, text="Stop Command:").grid(row=1, column=0, sticky=W)
        self.stopEntry = Entry(self.commandFrame)
        self.stopEntry.grid(row=1, column=1, sticky='nsew')
        if 'stopCommand' in self.prefValues:
            self.stopEntry.insert(0, str(self.prefValues['stopCommand']))

    def addInterface( self ):
        self.tableFrame.addRow()

    def defaultDpid( self, name):
        "Derive dpid from switch name, s1 -> 1"
        assert self  # satisfy pylint and allow contextual override
        try:
            dpid = int( re.findall( r'\d+', name )[ 0 ] )
            dpid = hex( dpid )[ 2: ]
            return dpid
        except IndexError:
            return None
            #raise Exception( 'Unable to derive default datapath ID - '
            #                 'please either specify a dpid or use a '
            #                 'canonical switch name such as s23.' )

    def apply(self):
        externalInterfaces = []
        for row in range(self.tableFrame.rows):
            # debug( 'Interface is ' + self.tableFrame.get(row, 0), '\n' )
            if len(self.tableFrame.get(row, 0)) > 0:
                externalInterfaces.append(self.tableFrame.get(row, 0))

        dpid = self.dpidEntry.get()
        if (self.defaultDpid(self.hostnameEntry.get()) is None
                and len(dpid) == 0):
            messagebox.showerror(title="Error",
                                 message= 'Unable to derive default datapath ID - '
                                 'please either specify a DPID or use a '
                                 'canonical switch name such as s23.' )

        results = {'externalInterfaces':externalInterfaces,
                   'hostname':self.hostnameEntry.get(),
                   'dpid':dpid,
                   'startCommand':self.startEntry.get(),
                   'stopCommand':self.stopEntry.get(),
                   'sflow':str(self.sflow.get()),
                   'netflow':str(self.nflow.get()),
                   'dpctl':self.dpctlEntry.get(),
                   'switchIP':self.ipEntry.get()}
        sw = self.switchType.get()
        if sw == 'Userspace inNamespace':
            results['switchType'] = 'userns'
        elif sw == 'Userspace':
            results['switchType'] = 'user'
        elif sw == 'Open vSwitch Kernel Mode':
            results['switchType'] = 'ovs'
        elif sw == 'P4AP':
            results['switchType'] = 'bmv2'
        else:
            results['switchType'] = 'default'
        self.result = results


class APDialog(CustomDialog):

    def __init__(self, master, title, prefDefaults):

        self.prefValues = prefDefaults
        self.result = None
        CustomDialog.__init__(self, master, title)

    def body(self, master):
        self.rootFrame = master
        n = ttk.Notebook(self.rootFrame)
        self.propFrame = Frame(n)
        self.authFrame = Frame(n)
        n.add(self.propFrame, text='Properties')
        n.add(self.authFrame, text='Authentication')
        n.pack()

        self.leftfieldFrame = Frame(self.propFrame)
        self.rightfieldFrame = Frame(self.propFrame)
        self.leftfieldFrame.grid(row=0, column=0, sticky='nswe')
        self.rightfieldFrame.grid(row=0, column=1, sticky='nswe')

        rowCount = 0
        externalInterfaces = []
        if 'externalInterfaces' in self.prefValues:
            externalInterfaces = self.prefValues['externalInterfaces']

        # Field for Hostname
        Label(self.leftfieldFrame, text="Hostname:").grid(row=rowCount, sticky=E)
        self.hostnameEntry = Entry(self.leftfieldFrame)
        self.hostnameEntry.grid(row=rowCount, column=1)
        self.hostnameEntry.insert(0, self.prefValues['hostname'])
        rowCount += 1

        # Field for wlans
        Label(self.leftfieldFrame, text="Wlans:").grid(row=rowCount, sticky=E)
        self.wlansEntry = Entry(self.leftfieldFrame)
        self.wlansEntry.grid(row=rowCount, column=1)
        self.wlansEntry.insert(0, self.prefValues['wlans'])
        rowCount += 1

        # Field for SSID
        Label(self.leftfieldFrame, text="SSID:").grid(row=rowCount, sticky=E)
        self.ssidEntry = Entry(self.leftfieldFrame)
        self.ssidEntry.grid(row=rowCount, column=1)
        self.ssidEntry.insert(0, self.prefValues['ssid'])
        rowCount += 1

        # Field for channel
        Label(self.leftfieldFrame, text="Channel:").grid(row=rowCount, sticky=E)
        self.channelEntry = Entry(self.leftfieldFrame)
        self.channelEntry.grid(row=rowCount, column=1)
        self.channelEntry.insert(0, self.prefValues['channel'])
        rowCount += 1

        # Selection of mode
        Label(self.leftfieldFrame, text="Mode:").grid(row=rowCount, sticky=E)
        self.mode = StringVar(self.leftfieldFrame)
        self.modeMenu = OptionMenu(self.leftfieldFrame, self.mode, "g", "a", "b", "n")
        self.modeMenu.grid(row=rowCount, column=1, sticky=W)
        if 'mode' in self.prefValues:
            modePref = self.prefValues['mode']
            if modePref == 'g':
                self.mode.set("g")
            elif modePref == 'a':
                self.mode.set("a")
            elif modePref == 'b':
                self.mode.set("b")
            elif modePref == 'n':
                self.mode.set("n")
            else:
                self.mode.set("g")
        else:
            self.mode.set("g")
        rowCount += 1

        # Field for signal range
        Label(self.leftfieldFrame, text="Signal Range:").grid(row=rowCount, sticky=E)
        self.rangeEntry = Entry(self.leftfieldFrame)
        self.rangeEntry.grid(row=rowCount, column=1)
        self.rangeEntry.insert(0, self.prefValues['range'])
        rowCount += 1

        # Selection of ap type
        Label(self.leftfieldFrame, text="AP Type:").grid(row=rowCount, sticky=E)
        self.apType = StringVar(self.leftfieldFrame)
        self.apTypeMenu = OptionMenu(self.leftfieldFrame, self.apType, "Default", "P4AP", "Open vSwitch Kernel Mode",
                                     "Userspace", "Userspace inNamespace")
        self.apTypeMenu.grid(row=rowCount, column=1, sticky=W)
        if 'apType' in self.prefValues:
            apTypePref = self.prefValues['apType']
            if apTypePref == 'userns':
                self.apType.set("Userspace inNamespace")
            elif apTypePref == 'user':
                self.apType.set("Userspace")
            elif apTypePref == 'bmv2':
                self.apType.set("P4AP")
            elif apTypePref == 'ovs':
                self.apType.set("Open vSwitch Kernel Mode")
            else:
                self.apType.set("Default")
        else:
            self.apType.set("Default")
        rowCount += 1

        # Field for DPID
        Label(self.leftfieldFrame, text="DPID:").grid(row=rowCount, sticky=E)
        self.dpidEntry = Entry(self.leftfieldFrame)
        self.dpidEntry.grid(row=rowCount, column=1)
        if 'dpid' in self.prefValues:
            self.dpidEntry.insert(0, self.prefValues['dpid'])
        rowCount+=1

        # Field for Netflow
        Label(self.leftfieldFrame, text="Enable NetFlow:").grid(row=rowCount, sticky=E)
        self.nflow = IntVar()
        self.nflowButton = Checkbutton(self.leftfieldFrame, variable=self.nflow)
        self.nflowButton.grid(row=rowCount, column=1, sticky=W)
        if 'netflow' in self.prefValues:
            if self.prefValues['netflow'] == '0':
                self.nflowButton.deselect()
            else:
                self.nflowButton.select()
        else:
            self.nflowButton.deselect()
        rowCount+=1

        # Field for sflow
        Label(self.leftfieldFrame, text="Enable sFlow:").grid(row=rowCount, sticky=E)
        self.sflow = IntVar()
        self.sflowButton = Checkbutton(self.leftfieldFrame, variable=self.sflow)
        self.sflowButton.grid(row=rowCount, column=1, sticky=W)
        if 'sflow' in self.prefValues:
            if self.prefValues['sflow'] == '0':
                self.sflowButton.deselect()
            else:
                self.sflowButton.select()
        else:
            self.sflowButton.deselect()
        rowCount += 1

        # Field for Switch IP
        Label(self.leftfieldFrame, text="IP Address:").grid(row=rowCount, sticky=E)
        self.ipEntry = Entry(self.leftfieldFrame)
        self.ipEntry.grid(row=rowCount, column=1)
        if 'apIP' in self.prefValues:
            self.ipEntry.insert(0, self.prefValues['apIP'])
        rowCount += 1

        # Field for DPCTL port
        Label(self.leftfieldFrame, text="DPCTL port:").grid(row=rowCount, sticky=E)
        self.dpctlEntry = Entry(self.leftfieldFrame)
        self.dpctlEntry.grid(row=rowCount, column=1)
        if 'dpctl' in self.prefValues:
            self.dpctlEntry.insert(0, self.prefValues['dpctl'])
        rowCount += 1

        # External Interfaces
        Label(self.rightfieldFrame, text="External Interface:").grid(row=0, sticky=E)
        self.b = Button( self.rightfieldFrame, text='Add', command=self.addInterface)
        self.b.grid(row=0, column=1)

        self.interfaceFrame = VerticalScrolledTable(self.rightfieldFrame, rows=0, columns=1, title='External Interfaces')
        self.interfaceFrame.grid(row=1, column=0, sticky='nswe', columnspan=2)
        self.tableFrame = self.interfaceFrame.interior

        # Add defined interfaces
        for externalInterface in externalInterfaces:
            self.tableFrame.addRow(value=[externalInterface])

        self.commandFrame = Frame(self.propFrame)
        self.commandFrame.grid(row=1, column=0, sticky='nswe', columnspan=2)
        self.commandFrame.columnconfigure(1, weight=1)
        # Start command
        Label(self.commandFrame, text="Start Command:").grid(row=0, column=0, sticky=W)
        self.startEntry = Entry(self.commandFrame)
        self.startEntry.grid(row=0, column=1,  sticky='nsew')
        if 'startCommand' in self.prefValues:
            self.startEntry.insert(0, str(self.prefValues['startCommand']))
        # Stop command
        Label(self.commandFrame, text="Stop Command:").grid(row=1, column=0, sticky=W)
        self.stopEntry = Entry(self.commandFrame)
        self.stopEntry.grid(row=1, column=1, sticky='nsew')
        if 'stopCommand' in self.prefValues:
            self.stopEntry.insert(0, str(self.prefValues['stopCommand']))

        rowCount = 0
        # Selection of authentication
        Label(self.authFrame, text="Authentication:").grid(row=rowCount, sticky=E)
        self.authentication = StringVar(self.authFrame)
        self.authenticationMenu = OptionMenu(self.authFrame,
                                             self.authentication, "none", "WEP",
                                             "WPA", "WPA2", "8021x")
        self.authenticationMenu.grid(row=rowCount, column=1, sticky=W)
        if 'authentication' in self.prefValues:
            authPref = self.prefValues['authentication']
            if authPref == 'WEP':
                self.authentication.set("WEP")
            elif authPref == 'WPA':
                self.authentication.set("WPA")
            elif authPref == 'WPA2':
                self.authentication.set("WPA2")
            elif authPref == '8021x':
                self.authentication.set("8021x")
            else:
                self.authentication.set("none")
        else:
            self.authentication.set("none")
        rowCount += 1

        # Field for passwd
        Label(self.authFrame, text="Password:").grid(row=rowCount, sticky=E)
        self.passwdEntry = Entry(self.authFrame)
        self.passwdEntry.grid(row=rowCount, column=1)
        self.passwdEntry.insert(0, self.prefValues['passwd'])
        rowCount += 1

    def addInterface(self):
        self.tableFrame.addRow()

    def defaultDpid( self, name):
        "Derive dpid from switch name, s1 -> 1"
        assert self  # satisfy pylint and allow contextual override
        try:
            dpid = int( re.findall( r'\d+', name )[ 0 ] )
            dpid = hex( dpid )[ 2: ]
            return dpid
        except IndexError:
            return None
            #raise Exception( 'Unable to derive default datapath ID - '
            #                 'please either specify a dpid or use a '
            #                 'canonical switch name such as s23.' )

    def apply(self):
        externalInterfaces = []
        for row in range(self.tableFrame.rows):
            # debug( 'Interface is ' + self.tableFrame.get(row, 0), '\n' )
            if len(self.tableFrame.get(row, 0)) > 0:
                externalInterfaces.append(self.tableFrame.get(row, 0))

        dpid = self.dpidEntry.get()
        if (self.defaultDpid(self.hostnameEntry.get()) is None
           and len(dpid) == 0):
            messagebox.showerror(title="Error",
                      message= 'Unable to derive default datapath ID - '
                      'please either specify a DPID or use a '
                      'canonical switch name such as s23.' )

        results = {'externalInterfaces': externalInterfaces,
                   'hostname': self.hostnameEntry.get(),
                   'dpid': dpid,
                   'startCommand':self.startEntry.get(),
                   'stopCommand': self.stopEntry.get(),
                   'sflow': str(self.sflow.get()),
                   'netflow': str(self.nflow.get()),
                   'dpctl': self.dpctlEntry.get(),
                   'apIP': self.ipEntry.get()}
        results['ssid'] = str(self.ssidEntry.get())
        results['channel'] = str(self.channelEntry.get())
        results['range'] = str(self.rangeEntry.get())
        results['wlans'] = self.wlansEntry.get()
        results['mode'] = str(self.mode.get())
        results['authentication'] = self.authentication.get()
        results['passwd'] = str(self.passwdEntry.get())
        ap = self.apType.get()
        if ap == 'Userspace inNamespace':
            results['apType'] = 'userns'
        elif ap == 'Userspace':
            results['apType'] = 'user'
        elif ap == 'Open vSwitch Kernel Mode':
            results['apType'] = 'ovs'
        elif ap == 'P4AP':
            results['apType'] = 'bmv2'
        else:
            results['apType'] = 'default'
        self.result = results


class VerticalScrolledTable(LabelFrame):
    """A pure Tkinter scrollable frame that actually works!

    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling

    """
    def __init__(self, parent, rows=2, columns=2, title=None, *args, **kw):
        LabelFrame.__init__(self, parent, text=title, padx=5, pady=5, *args, **kw)

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = TableFrame(canvas, rows=rows, columns=columns)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(_event):
        # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
            # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(_event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)

        return


class TableFrame(Frame):
    def __init__(self, parent, rows=2, columns=2):

        Frame.__init__(self, parent, background="black")
        self._widgets = []
        self.rows = rows
        self.columns = columns
        for row in range(rows):
            current_row = []
            for column in range(columns):
                label = Entry(self, borderwidth=0)
                label.grid(row=row, column=column, sticky="wens", padx=1, pady=1)
                current_row.append(label)
            self._widgets.append(current_row)

    def set(self, row, column, value):
        widget = self._widgets[row][column]
        widget.insert(0, value)

    def get(self, row, column):
        widget = self._widgets[row][column]
        return widget.get()

    def addRow( self, value=None, readonly=False ):
        # debug( "Adding row " + str(self.rows +1), '\n' )
        current_row = []
        for column in range(self.columns):
            label = Entry(self, borderwidth=0)
            label.grid(row=self.rows, column=column, sticky="wens", padx=1, pady=1)
            if value is not None:
                label.insert(0, value[column])
            if readonly == True:
                label.configure(state='readonly')
            current_row.append(label)
        self._widgets.append(current_row)
        self.update_idletasks()
        self.rows += 1


class LinkDialog(simpledialog.Dialog):

    def __init__(self, parent, title, linkDefaults, links, src, dest):

        self.linkValues = linkDefaults
        self.links = links
        self.src = src
        self.dest = dest
        simpledialog.Dialog.__init__(self, parent, title)

    def body(self, master):
        if 'link' not in self.linkValues:
            self.linkValues['channel'] = '1'
        if 'ssid' not in self.linkValues:
            self.linkValues['ssid'] = 'new-ssid'
        if 'mode' not in self.linkValues:
            self.linkValues['mode'] = 'g'

        rowCount = 0
        Label(master, text="Connection:").grid(row=rowCount, sticky=E)
        connectionOpt = None
        if 'connection' in self.linkValues:
            connectionOpt = self.linkValues['connection']
        self.e1 = StringVar(master)
        self.opt1 = OptionMenu(master, self.e1, "wired", "adhoc", "mesh", "wifi-direct", "6lowpan")
        self.opt1.grid(row=rowCount, column=1, sticky=W)
        if connectionOpt:
            if self.linkValues['connection'] == 'adhoc':
                self.e1.set("adhoc")
            elif self.linkValues['connection'] == 'wifi-direct':
                self.e1.set("wifi-direct")
            elif self.linkValues['connection'] == 'mesh':
                self.e1.set("mesh")
            elif self.linkValues['connection'] == '6lowpan':
                self.e1.set("6lowpan")
            else:
                self.e1.set("wired")
        else:
            self.e1.set("wired")

        rowCount += 1
        Label(master, text="SSID:").grid(row=rowCount, sticky=E)
        self.e2 = Entry(master)
        self.e2.grid(row=rowCount, column=1)
        self.e2.insert(0, str(self.linkValues['ssid']))

        rowCount += 1
        Label(master, text="Channel:").grid(row=rowCount, sticky=E)
        self.e3 = Entry(master)
        self.e3.grid(row=rowCount, column=1)
        self.e3.insert(0, str(self.linkValues['channel']))

        rowCount += 1
        Label(master, text="Mode:").grid(row=rowCount, sticky=E)
        modeOpt = None
        if 'mode' in self.linkValues:
            modeOpt = self.linkValues['mode']
        self.e4 = StringVar(master)
        self.opt1 = OptionMenu(master, self.e4, "a", "b", "g", "n")
        self.opt1.grid(row=rowCount, column=1, sticky=W)
        if modeOpt:
            if self.linkValues['mode'] == 'a':
                self.e4.set("a")
            elif self.linkValues['mode'] == 'b':
                self.e4.set("b")
            elif self.linkValues['mode'] == 'g':
                self.e4.set("g")
            elif self.linkValues['mode'] == 'n':
                self.e4.set("n")

        rowCount += 1
        Label(master, text="Bandwidth:").grid(row=rowCount, sticky=E)
        self.e5 = Entry(master)
        self.e5.grid(row=rowCount, column=1)
        Label(master, text="Mbit").grid(row=rowCount, column=2, sticky=W)
        if 'bw' in self.linkValues:
            self.e5.insert(0,str(self.linkValues['bw']))

        rowCount += 1
        Label(master, text="Delay:").grid(row=rowCount, sticky=E)
        self.e6 = Entry(master)
        self.e6.grid(row=rowCount, column=1)
        if 'delay' in self.linkValues:
            self.e6.insert(0, self.linkValues['delay'])

        rowCount += 1
        Label(master, text="Loss:").grid(row=rowCount, sticky=E)
        self.e7 = Entry(master)
        self.e7.grid(row=rowCount, column=1)
        Label(master, text="%").grid(row=rowCount, column=2, sticky=W)
        if 'loss' in self.linkValues:
            self.e7.insert(0, str(self.linkValues['loss']))

        rowCount += 1
        Label(master, text="Max Queue size:").grid(row=rowCount, sticky=E)
        self.e8 = Entry(master)
        self.e8.grid(row=rowCount, column=1)
        if 'max_queue_size' in self.linkValues:
            self.e8.insert(0, str(self.linkValues['max_queue_size']))

        rowCount += 1
        Label(master, text="Jitter:").grid(row=rowCount, sticky=E)
        self.e9 = Entry(master)
        self.e9.grid(row=rowCount, column=1)
        if 'jitter' in self.linkValues:
            self.e9.insert(0, self.linkValues['jitter'])

        rowCount += 1
        Label(master, text="Speedup:").grid(row=rowCount, sticky=E)
        self.e10 = Entry(master)
        self.e10.grid(row=rowCount, column=1)
        if 'speedup' in self.linkValues:
            self.e10.insert(0, str(self.linkValues['speedup']))

        if 'wlans' in self.src:
            rowCount += 1
            Label(master, text="Source:").grid(row=rowCount, sticky=E)
            srcOpt = None
            if 'src' in self.links:
                srcOpt = self.links['src']['text']
            wlans = []
            wlans.append('default')
            for wlan in range(int(self.src['wlans'])):
                if 'ap' in srcOpt:
                    wlan_ = wlan + 1
                else:
                    wlan_ = wlan
                wlans.append('%s-wlan%s' % (srcOpt, wlan_))
            self.e11 = StringVar(master)
            self.opt2 = OptionMenu(master, self.e11, *tuple(wlans))
            self.opt2.grid(row=rowCount, column=1, sticky=W)
            if srcOpt and 'src' in self.linkValues:
                for wlan in wlans:
                    if self.linkValues['src'] == wlan:
                        self.e11.set(wlan)
            else:
                self.e11.set('default')
        else:
            self.e11 = ''

        if 'wlans' in self.dest:
            rowCount += 1
            Label(master, text="Destination:").grid(row=rowCount, sticky=E)
            destOpt = None
            if 'dest' in self.links:
                destOpt = self.links['dest']['text']
            wlans = []
            wlans.append('default')
            for wlan in range(int(self.dest['wlans'])):
                if 'ap' in destOpt:
                    wlan_ = wlan+1
                else:
                    wlan_ = wlan
                wlans.append('%s-wlan%s' % (destOpt, wlan_))
            self.e12 = StringVar(master)
            self.opt3 = OptionMenu(master, self.e12, *tuple(wlans))
            self.opt3.grid(row=rowCount, column=1, sticky=W)
            if destOpt and 'dest' in self.linkValues:
                for wlan in wlans:
                    if self.linkValues['dest'] == wlan:
                        self.e12.set(wlan)
            else:
                self.e12.set('default')
        else:
            self.e12 = ''

        return self.e2 # initial focus

    def apply(self):
        self.result = {}
        if len(self.e1.get()) > 0:
            self.result['connection'] = (self.e1.get())
        if len(self.e2.get()) > 0:
            self.result['ssid'] = (self.e2.get())
        if len(self.e3.get()) > 0:
            self.result['channel'] = (self.e3.get())
        if len(self.e4.get()) > 0:
            self.result['mode'] = (self.e4.get())
        if len(self.e5.get()) > 0:
            self.result['bw'] = int(self.e5.get())
        if len(self.e6.get()) > 0:
            self.result['delay'] = self.e6.get()
        if len(self.e7.get()) > 0:
            self.result['loss'] = int(self.e7.get())
        if len(self.e8.get()) > 0:
            self.result['max_queue_size'] = int(self.e8.get())
        if len(self.e9.get()) > 0:
            self.result['jitter'] = self.e9.get()
        if len(self.e10.get()) > 0:
            self.result['speedup'] = int(self.e10.get())
        if self.e11 != '' and len(self.e11.get()) > 0:
            self.result['src'] = self.e11.get()
        if self.e12 != '' and len(self.e12.get()) > 0:
            self.result['dest'] = self.e12.get()


class ControllerDialog(simpledialog.Dialog):

    def __init__(self, parent, title, ctrlrDefaults=None):

        if ctrlrDefaults:
            self.ctrlrValues = ctrlrDefaults

        simpledialog.Dialog.__init__(self, parent, title)

    def body(self, master):

        self.var = StringVar(master)
        self.protcolvar = StringVar(master)

        rowCount=0
        # Field for Hostname
        Label(master, text="Name:").grid(row=rowCount, sticky=E)
        self.hostnameEntry = Entry(master)
        self.hostnameEntry.grid(row=rowCount, column=1)
        self.hostnameEntry.insert(0, self.ctrlrValues['hostname'])
        rowCount+=1

        # Field for Remove Controller Port
        Label(master, text="Controller Port:").grid(row=rowCount, sticky=E)
        self.e2 = Entry(master)
        self.e2.grid(row=rowCount, column=1)
        self.e2.insert(0, self.ctrlrValues['remotePort'])
        rowCount+=1

        # Field for Controller Type
        Label(master, text="Controller Type:").grid(row=rowCount, sticky=E)
        controllerType = self.ctrlrValues['controllerType']
        self.o1 = OptionMenu(master, self.var, "Remote Controller", "In-Band Controller", "OpenFlow Reference", "OVS Controller")
        self.o1.grid(row=rowCount, column=1, sticky=W)
        if controllerType == 'ref':
            self.var.set("OpenFlow Reference")
        elif controllerType == 'inband':
            self.var.set("In-Band Controller")
        elif controllerType == 'remote':
            self.var.set("Remote Controller")
        else:
            self.var.set("OVS Controller")
        rowCount+=1

        # Field for Controller Protcol
        Label(master, text="Protocol:").grid(row=rowCount, sticky=E)
        if 'controllerProtocol' in self.ctrlrValues:
            controllerProtocol = self.ctrlrValues['controllerProtocol']
        else:
            controllerProtocol = 'tcp'
        self.protcol = OptionMenu(master, self.protcolvar, "TCP", "SSL")
        self.protcol.grid(row=rowCount, column=1, sticky=W)
        if controllerProtocol == 'ssl':
            self.protcolvar.set("SSL")
        else:
            self.protcolvar.set("TCP")
        rowCount+=1

        # Field for Remove Controller IP
        remoteFrame= LabelFrame(master, text='Remote/In-Band Controller', padx=5, pady=5)
        remoteFrame.grid(row=rowCount, column=0, columnspan=2, sticky=W)

        Label(remoteFrame, text="IP Address:").grid(row=0, sticky=E)
        self.e1 = Entry(remoteFrame)
        self.e1.grid(row=0, column=1)
        self.e1.insert(0, self.ctrlrValues['remoteIP'])
        rowCount+=1

        return self.hostnameEntry # initial focus

    def apply(self):
        self.result = { 'hostname': self.hostnameEntry.get(),
                        'remoteIP': self.e1.get(),
                        'remotePort': int(self.e2.get())}

        controllerType = self.var.get()
        if controllerType == 'Remote Controller':
            self.result['controllerType'] = 'remote'
        elif controllerType == 'In-Band Controller':
            self.result['controllerType'] = 'inband'
        elif controllerType == 'OpenFlow Reference':
            self.result['controllerType'] = 'ref'
        else:
            self.result['controllerType'] = 'ovsc'
        controllerProtocol = self.protcolvar.get()
        if controllerProtocol == 'SSL':
            self.result['controllerProtocol'] = 'ssl'
        else:
            self.result['controllerProtocol'] = 'tcp'


class ToolTip(object):

    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, _cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 27
        y = y + cy + self.widget.winfo_rooty() +27
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        try:
            # For Mac OS
            # pylint: disable=protected-access
            tw.tk.call("::tk::unsupported::MacWindowStyle",
                       "style", tw._w,
                       "help", "noActivates")
            # pylint: enable=protected-access
        except TclError:
            pass
        label = Label(tw, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class MiniEdit(Frame):
    "A simple network editor for Mininet."

    def __init__(self, parent=None, cheight=600, cwidth=1000):

        self.defaultIpBase = '10.0.0.0/8'

        self.nflowDefaults = {'nflowTarget': '',
                              'nflowTimeout': '600',
                              'nflowAddId': '0'}
        self.sflowDefaults = {'sflowTarget': '',
                              'sflowSampling': '400',
                              'sflowHeader': '128',
                              'sflowPolling': '30'}

        self.appPrefs={
            "ipBase": self.defaultIpBase,
            "startCLI": "0",
            "enableWmediumd": "0",
            "terminalType": 'xterm',
            "switchType": 'ovs',
            "apType": 'ovs',
            "authentication": 'none',
            "passwd": '',
            "mode": 'g',
            "dpctl": '',
            'sflow': self.sflowDefaults,
            'netflow': self.nflowDefaults,
            'openFlowVersions': {'ovsOf10': '1',
                                 'ovsOf11': '0',
                                 'ovsOf12': '0',
                                 'ovsOf13': '0'}
        }

        Frame.__init__(self, parent)
        self.action = None
        self.appName = 'MiniEdit'
        self.fixedFont = font.Font ( family="DejaVu Sans Mono", size="14" )

        # Style
        self.font = ( 'Geneva', 9 )
        self.smallFont = ( 'Geneva', 7 )
        self.bg = 'white'

        # Title
        self.top = self.winfo_toplevel()
        self.top.title( self.appName )

        # Menu bar
        self.createMenubar()

        # Editing canvas
        self.cheight, self.cwidth = cheight, cwidth
        self.cframe, self.canvas = self.createCanvas()

        # Toolbar
        self.controllers = {}

        # Toolbar
        self.images = miniEditImages()
        self.buttons = {}
        self.active = None
        self.tools = ('Select', 'Host', 'Station', 'Switch', 'AP',
                      'LegacySwitch', 'LegacyRouter', 'NetLink', 'Controller')
        self.customColors = {'Switch': 'darkGreen', 'Host': 'blue'}
        self.toolbar = self.createToolbar()

        # Layout
        self.toolbar.grid(column=0, row=0, sticky='nsew')
        self.cframe.grid(column=1, row=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.pack(expand=True, fill='both')

        # About box
        self.aboutBox = None

        # Initialize node data
        self.nodeBindings = self.createNodeBindings()
        self.nodePrefixes = {'LegacyRouter': 'r', 'LegacySwitch': 's', 'Switch': 's',
                             'AP': 'ap', 'Host': 'h', 'Station': 'sta', 'Controller': 'c'}
        self.widgetToItem = {}
        self.itemToWidget = {}

        # Initialize link tool
        self.link = self.linkWidget = None

        # Selection support
        self.selection = None

        # Keyboard bindings
        self.bind('<Control-q>', lambda event: self.quit())
        self.bind('<KeyPress-Delete>', self.deleteSelection)
        self.bind('<KeyPress-BackSpace>', self.deleteSelection)
        self.focus()

        self.hostPopup = Menu(self.top, tearoff=0)
        self.hostPopup.add_command(label='Host Options', font=self.font)
        self.hostPopup.add_separator()
        self.hostPopup.add_command(label='Properties', font=self.font, command=self.hostDetails)

        self.hostRunPopup = Menu(self.top, tearoff=0)
        self.hostRunPopup.add_command(label='Host Options', font=self.font)
        self.hostRunPopup.add_separator()
        self.hostRunPopup.add_command(label='Terminal', font=self.font, command=self.xterm)

        self.stationPopup = Menu(self.top, tearoff=0)
        self.stationPopup.add_command(label='Station Options', font=self.font)
        self.stationPopup.add_separator()
        self.stationPopup.add_command(label='Properties', font=self.font, command=self.stationDetails)

        self.stationRunPopup = Menu(self.top, tearoff=0)
        self.stationRunPopup.add_command(label='Station Options', font=self.font)
        self.stationRunPopup.add_separator()
        self.stationRunPopup.add_command(label='Terminal', font=self.font, command=self.xterm)

        self.legacyRouterRunPopup = Menu(self.top, tearoff=0)
        self.legacyRouterRunPopup.add_command(label='Router Options', font=self.font)
        self.legacyRouterRunPopup.add_separator()
        self.legacyRouterRunPopup.add_command(label='Terminal', font=self.font, command=self.xterm)

        self.switchPopup = Menu(self.top, tearoff=0)
        self.switchPopup.add_command(label='Switch Options', font=self.font)
        self.switchPopup.add_separator()
        self.switchPopup.add_command(label='Properties', font=self.font, command=self.switchDetails)

        self.switchRunPopup = Menu(self.top, tearoff=0)
        self.switchRunPopup.add_command(label='Switch Options', font=self.font)
        self.switchRunPopup.add_separator()
        self.switchRunPopup.add_command(label='List bridge details', font=self.font, command=self.listBridge)

        self.apPopup = Menu(self.top, tearoff=0)
        self.apPopup.add_command(label='AP Options', font=self.font)
        self.apPopup.add_separator()
        self.apPopup.add_command(label='Properties', font=self.font, command=self.apDetails)

        self.apRunPopup = Menu(self.top, tearoff=0)
        self.apRunPopup.add_command(label='AP Options', font=self.font)
        self.apRunPopup.add_separator()
        self.apRunPopup.add_command(label='List bridge details', font=self.font, command=self.listBridge)
        self.apRunPopup.add_command(label='Properties', font=self.font, command=self.apDetails)

        self.linkPopup = Menu(self.top, tearoff=0)
        self.linkPopup.add_command(label='Link Options', font=self.font)
        self.linkPopup.add_separator()
        self.linkPopup.add_command(label='Properties', font=self.font, command=self.linkDetails)

        self.linkRunPopup = Menu(self.top, tearoff=0)
        self.linkRunPopup.add_command(label='Link Options', font=self.font)
        self.linkRunPopup.add_separator()
        self.linkRunPopup.add_command(label='Link Up', font=self.font, command=self.linkUp)
        self.linkRunPopup.add_command(label='Link Down', font=self.font, command=self.linkDown)

        self.controllerPopup = Menu(self.top, tearoff=0)
        self.controllerPopup.add_command(label='Controller Options', font=self.font)
        self.controllerPopup.add_separator()
        self.controllerPopup.add_command(label='Properties', font=self.font, command=self.controllerDetails)

        # Event handling initalization
        self.linkx = self.linky = self.linkItem = None
        self.lastSelection = None

        # Model initialization
        self.links = {}
        self.hostOpts = {}
        self.stationOpts = {}
        self.switchOpts = {}
        self.apOpts = {}
        self.range = {}
        self.hostCount = 0
        self.stationCount = 0
        self.switchCount = 0
        self.apCount = 0
        self.controllerCount = 0
        self.net = None

        # Close window gracefully
        Wm.wm_protocol( self.top, name='WM_DELETE_WINDOW', func=self.quit )

    def quit( self ):
        "Stop our network, if any, then quit."
        self.stop()
        Frame.quit( self )

    def createMenubar( self ):
        "Create our menu bar."

        font = self.font

        mbar = Menu( self.top, font=font )
        self.top.configure( menu=mbar )

        fileMenu = Menu( mbar, tearoff=False )
        mbar.add_cascade( label="File", font=font, menu=fileMenu )
        fileMenu.add_command( label="New", font=font, command=self.newTopology )
        fileMenu.add_command( label="Open", font=font, command=self.loadTopology )
        fileMenu.add_command( label="Save", font=font, command=self.saveTopology )
        fileMenu.add_command( label="Export Level 2 Script", font=font, command=self.exportScript )
        fileMenu.add_separator()
        fileMenu.add_command( label='Quit', command=self.quit, font=font )

        editMenu = Menu( mbar, tearoff=False )
        mbar.add_cascade( label="Edit", font=font, menu=editMenu )
        editMenu.add_command( label="Cut", font=font,
                              command=lambda: self.deleteSelection( None ) )
        editMenu.add_command( label="Preferences", font=font, command=self.prefDetails)

        runMenu = Menu( mbar, tearoff=False )
        mbar.add_cascade( label="Run", font=font, menu=runMenu )
        runMenu.add_command( label="Run", font=font, command=self.doRun )
        runMenu.add_command( label="Stop", font=font, command=self.doStop )
        fileMenu.add_separator()
        runMenu.add_command( label='Show OVS Summary', font=font, command=self.ovsShow )
        runMenu.add_command( label='Root Terminal', font=font, command=self.rootTerminal )

        # Application menu
        appMenu = Menu( mbar, tearoff=False )
        mbar.add_cascade( label="Help", font=font, menu=appMenu )
        appMenu.add_command( label='About MiniEdit', command=self.about,
                             font=font)
    # Canvas

    def createCanvas( self ):
        "Create and return our scrolling canvas frame."
        f = Frame( self )

        canvas = Canvas( f, width=self.cwidth, height=self.cheight,
                         bg=self.bg )

        # Scroll bars
        xbar = Scrollbar( f, orient='horizontal', command=canvas.xview )
        ybar = Scrollbar( f, orient='vertical', command=canvas.yview )
        canvas.configure( xscrollcommand=xbar.set, yscrollcommand=ybar.set )

        # Resize box
        resize = Label( f, bg='white' )

        # Layout
        canvas.grid( row=0, column=1, sticky='nsew')
        ybar.grid( row=0, column=2, sticky='ns')
        xbar.grid( row=1, column=1, sticky='ew' )
        resize.grid( row=1, column=2, sticky='nsew' )

        # Resize behavior
        f.rowconfigure( 0, weight=1 )
        f.columnconfigure( 1, weight=1 )
        f.grid( row=0, column=0, sticky='nsew' )
        f.bind( '<Configure>', lambda event: self.updateScrollRegion() )

        # Mouse bindings
        canvas.bind( '<ButtonPress-1>', self.clickCanvas )
        canvas.bind( '<B1-Motion>', self.dragCanvas )
        canvas.bind( '<ButtonRelease-1>', self.releaseCanvas )

        return f, canvas

    def updateScrollRegion(self):
        "Update canvas scroll region to hold everything."
        bbox = self.canvas.bbox('all')
        if bbox is not None:
            self.canvas.configure(scrollregion=(0, 0, bbox[2], bbox[3]))

    def canvasx( self, x_root ):
        "Convert root x coordinate to canvas coordinate."
        c = self.canvas
        return c.canvasx( x_root ) - c.winfo_rootx()

    def canvasy( self, y_root ):
        "Convert root y coordinate to canvas coordinate."
        c = self.canvas
        return c.canvasy( y_root ) - c.winfo_rooty()

    # Toolbar

    def activate( self, toolName ):
        "Activate a tool and press its button."
        # Adjust button appearance
        if self.active:
            self.buttons[ self.active ].configure( relief='raised' )
        self.buttons[ toolName ].configure( relief='sunken' )
        # Activate dynamic bindings
        self.active = toolName


    @staticmethod
    def createToolTip(widget, text):
        toolTip = ToolTip(widget)
        def enter(_event):
            toolTip.showtip(text)
        def leave(_event):
            toolTip.hidetip()
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)

    def createToolbar( self ):
        "Create and return our toolbar frame."

        toolbar = Frame( self )

        # Tools
        for tool in self.tools:
            cmd = ( lambda t=tool: self.activate( t ) )
            b = Button( toolbar, text=tool, font=self.smallFont, command=cmd)
            if tool in self.images:
                b.config( height=35, image=self.images[ tool ] )
                self.createToolTip(b, str(tool))
                # b.config( compound='top' )
            b.pack( fill='x' )
            self.buttons[ tool ] = b
        self.activate( self.tools[ 0 ] )

        # Spacer
        Label( toolbar, text='' ).pack()

        # Commands
        for cmd, color in [ ( 'Stop', 'darkRed' ), ( 'Run', 'darkGreen' ) ]:
            doCmd = getattr( self, 'do' + cmd )
            b = Button( toolbar, text=cmd, font=self.smallFont,
                        fg=color, command=doCmd )
            b.pack( fill='x', side='bottom' )

        return toolbar

    def doRun( self ):
        "Run command."
        self.activate( 'Select' )
        for tool in self.tools:
            self.buttons[ tool ].config( state='disabled' )
        self.start()

    def doStop( self ):
        "Stop command."
        self.stop()
        for tool in self.tools:
            self.buttons[ tool ].config( state='normal' )

    def addNode( self, node, nodeNum, x, y, name=None):
        "Add a new node to our canvas."
        if 'Switch' == node:
            self.switchCount += 1
        if 'AP' == node:
            self.apCount += 1
        if 'Host' == node:
            self.hostCount += 1
        if 'Station' == node:
            self.stationCount += 1
        if 'Controller' == node:
            self.controllerCount += 1
        if name is None:
            name = self.nodePrefixes[ node ] + nodeNum

        self.addNamedNode(node, name, x, y)

    def addNamedNode( self, node, name, x, y):
        "Add a new node to our canvas."
        icon = self.nodeIcon( node, name )
        item = self.canvas.create_window( x, y, anchor='c', window=icon,
                                          tags=node )
        self.widgetToItem[ icon ] = item
        self.itemToWidget[ item ] = icon
        icon.links = {}

    def convertJsonUnicode(self, text):
        "Some part of Mininet don't like Unicode"
        unicode = type(u"")
        if Python3:
            unicode = str
        if isinstance(text, dict):
            return {self.convertJsonUnicode(key): self.convertJsonUnicode(value) for key, value in text.items()}
        elif isinstance(text, list):
            return [self.convertJsonUnicode(element) for element in text]
        elif isinstance(text, unicode):
            if Python3:
                return text
            return text.encode('utf-8')
        return text

    def loadTopology( self ):
        "Load command."
        c = self.canvas

        myFormats = [
            ('Mininet/Mininet-WiFi Topology','*.mn'),
            ('All Files','*'),
        ]
        f = filedialog.askopenfile(filetypes=myFormats, mode='rb')
        if f is None: return
        self.newTopology()
        loadedTopology = self.convertJsonUnicode(json.load(f))

        # Load application preferences
        if 'application' in loadedTopology:
            self.appPrefs = self.appPrefs.copy()
            self.appPrefs.update(loadedTopology['application'])
            if "ovsOf10" not in self.appPrefs["openFlowVersions"]:
                self.appPrefs["openFlowVersions"]["ovsOf10"] = '0'
            if "ovsOf11" not in self.appPrefs["openFlowVersions"]:
                self.appPrefs["openFlowVersions"]["ovsOf11"] = '0'
            if "ovsOf12" not in self.appPrefs["openFlowVersions"]:
                self.appPrefs["openFlowVersions"]["ovsOf12"] = '0'
            if "ovsOf13" not in self.appPrefs["openFlowVersions"]:
                self.appPrefs["openFlowVersions"]["ovsOf13"] = '0'
            if "sflow" not in self.appPrefs:
                self.appPrefs["sflow"] = self.sflowDefaults
            if "netflow" not in self.appPrefs:
                self.appPrefs["netflow"] = self.nflowDefaults

        # Load controllers
        if 'controllers' in loadedTopology:
            if loadedTopology['version'] == '1':
                # This is old location of controller info
                hostname = 'c0'
                self.controllers = {}
                self.controllers[hostname] = loadedTopology['controllers']['c0']
                self.controllers[hostname]['hostname'] = hostname
                self.addNode('Controller', 0, float(30), float(30), name=hostname)
                icon = self.findWidgetByName(hostname)
                icon.bind('<Button-3>', self.do_controllerPopup )
            else:
                controllers = loadedTopology['controllers']
                for controller in controllers:
                    hostname = controller['opts']['hostname']
                    x = controller['x']
                    y = controller['y']
                    self.addNode('Controller', 0, float(x), float(y), name=hostname)
                    self.controllers[hostname] = controller['opts']
                    icon = self.findWidgetByName(hostname)
                    icon.bind('<Button-3>', self.do_controllerPopup )

        # Load hosts
        if 'hosts' in loadedTopology:
            hosts = loadedTopology['hosts']
            for host in hosts:
                nodeNum = host['number']
                hostname = 'h'+nodeNum
                if 'hostname' in host['opts']:
                    hostname = host['opts']['hostname']
                else:
                    host['opts']['hostname'] = hostname
                if 'nodeNum' not in host['opts']:
                    host['opts']['nodeNum'] = int(nodeNum)
                x = host['x']
                y = host['y']
                self.addNode('Host', nodeNum, float(x), float(y), name=hostname)

                # Fix JSON converting tuple to list when saving
                if 'privateDirectory' in host['opts']:
                    newDirList = []
                    for privateDir in host['opts']['privateDirectory']:
                        if isinstance( privateDir, list ):
                            newDirList.append((privateDir[0],privateDir[1]))
                        else:
                            newDirList.append(privateDir)
                    host['opts']['privateDirectory'] = newDirList
                self.hostOpts[hostname] = host['opts']
                icon = self.findWidgetByName(hostname)
                icon.bind('<Button-3>', self.do_hostPopup)

        # Load stations
        if 'stations' in loadedTopology:
            stations = loadedTopology['stations']
            for station in stations:
                nodeNum = station['number']
                hostname = 'sta' + nodeNum
                if 'hostname' in station['opts']:
                    hostname = station['opts']['hostname']
                else:
                    station['opts']['hostname'] = hostname
                if 'nodeNum' not in station['opts']:
                    station['opts']['nodeNum'] = int(nodeNum)
                if 'mode' not in station['opts']:
                    station['opts']['mode'] = 'g'
                x = float(station['x'])
                y = float(station['y'])
                self.addNode('Station', nodeNum, float(x), float(y), name=hostname)

                # Fix JSON converting tuple to list when saving
                if 'privateDirectory' in station['opts']:
                    newDirList = []
                    for privateDir in station['opts']['privateDirectory']:
                        if isinstance(privateDir, list):
                            newDirList.append((privateDir[0], privateDir[1]))
                        else:
                            newDirList.append(privateDir)
                    station['opts']['privateDirectory'] = newDirList
                self.stationOpts[hostname] = station['opts']
                icon = self.findWidgetByName(hostname)
                icon.bind('<Button-3>', self.do_stationPopup)

                name = self.stationOpts[hostname]
                range = self.getRange(name, 'Station')
                self.range[hostname] = self.createCircle(x, y, range, c)

        # Load switches
        if 'switches' in loadedTopology:
            switches = loadedTopology['switches']
            for switch in switches:
                nodeNum = switch['number']
                hostname = 's'+nodeNum
                if 'controllers' not in switch['opts']:
                    switch['opts']['controllers'] = []
                if 'switchType' not in switch['opts']:
                    switch['opts']['switchType'] = 'default'
                if 'hostname' in switch['opts']:
                    hostname = switch['opts']['hostname']
                else:
                    switch['opts']['hostname'] = hostname
                if 'nodeNum' not in switch['opts']:
                    switch['opts']['nodeNum'] = int(nodeNum)
                x = switch['x']
                y = switch['y']
                if switch['opts']['switchType'] == "legacyRouter":
                    self.addNode('LegacyRouter', nodeNum, float(x), float(y), name=hostname)
                    icon = self.findWidgetByName(hostname)
                    icon.bind('<Button-3>', self.do_legacyRouterPopup )
                elif switch['opts']['switchType'] == "legacySwitch":
                    self.addNode('LegacySwitch', nodeNum, float(x), float(y), name=hostname)
                    icon = self.findWidgetByName(hostname)
                    icon.bind('<Button-3>', self.do_legacySwitchPopup )
                else:
                    self.addNode('Switch', nodeNum, float(x), float(y), name=hostname)
                    icon = self.findWidgetByName(hostname)
                    icon.bind('<Button-3>', self.do_switchPopup )
                self.switchOpts[hostname] = switch['opts']

                # create links to controllers
                if int(loadedTopology['version']) > 1:
                    controllers = self.switchOpts[hostname]['controllers']
                    for controller in controllers:
                        dest = self.findWidgetByName(controller)
                        dx, dy = self.canvas.coords( self.widgetToItem[ dest ] )
                        self.link = self.canvas.create_line(float(x),
                                                            float(y),
                                                            dx,
                                                            dy,
                                                            width=4,
                                                            fill='red',
                                                            dash=(6, 4, 2, 4),
                                                            tag='link' )
                        c.itemconfig(self.link, tags=c.gettags(self.link)+('control',))
                        self.addLink(icon, dest, linktype='control')
                        self.createControlLinkBindings()
                        self.link = self.linkWidget = None
                else:
                    dest = self.findWidgetByName('c0')
                    dx, dy = self.canvas.coords( self.widgetToItem[ dest ] )
                    self.link = self.canvas.create_line(float(x),
                                                        float(y),
                                                        dx,
                                                        dy,
                                                        width=4,
                                                        fill='red',
                                                        dash=(6, 4, 2, 4),
                                                        tag='link' )
                    c.itemconfig(self.link, tags=c.gettags(self.link)+('control',))
                    self.addLink(icon, dest, linktype='control')
                    self.createControlLinkBindings()
                    self.link = self.linkWidget = None

        # Load aps
        if 'aps' in loadedTopology:
            aps = loadedTopology['aps']
            for ap in aps:
                nodeNum = ap['number']
                hostname = 'ap' + nodeNum
                ssid = hostname + '-ssid'
                if 'ssid' not in ap['opts']:
                    ap['opts']['ssid'] = ssid
                if 'channel' not in ap['opts']:
                    ap['opts']['channel'] = 1
                if 'controllers' not in ap['opts']:
                    ap['opts']['controllers'] = []
                if 'apType' not in ap['opts']:
                    ap['opts']['apType'] = 'default'
                if 'authentication' not in ap['opts']:
                    ap['opts']['authentication'] = 'none'
                if 'passwd' not in ap['opts']:
                    ap['opts']['passwd'] = ''
                if 'mode' not in ap['opts']:
                    ap['opts']['mode'] = 'g'
                if 'range' not in ap['opts']:
                    ap['opts']['range'] = 'default'
                if 'wlans' not in ap['opts']:
                    ap['opts']['wlans'] = 1
                if 'ap' in ap['opts']:
                    hostname = ap['opts']['hostname']
                else:
                    ap['opts']['hostname'] = hostname
                if 'nodeNum' not in ap['opts']:
                    ap['opts']['nodeNum'] = int(nodeNum)
                x = float(ap['x'])
                y = float(ap['y'])
                if ap['opts']['apType'] == "legacyAP":
                    self.addNode('LegacyAP', nodeNum, float(x), float(y), name=hostname)
                    icon = self.findWidgetByName(hostname)
                    icon.bind('<Button-3>', self.do_legacyAPPopup)
                else:
                    self.addNode('AP', nodeNum, float(x), float(y), name=hostname)
                    icon = self.findWidgetByName(hostname)
                    icon.bind('<Button-3>', self.do_apPopup)
                self.apOpts[hostname] = ap['opts']

                name = self.apOpts[hostname]
                range = self.getRange(name, 'AP')
                self.range[hostname] = self.createCircle(x, y, range, c)

                # create links to controllers
                if int(loadedTopology['version']) > 1:
                    controllers = self.apOpts[hostname]['controllers']
                    for controller in controllers:
                        dest = self.findWidgetByName(controller)
                        dx, dy = self.canvas.coords(self.widgetToItem[dest])
                        self.link = self.canvas.create_line(float(x),
                                                            float(y),
                                                            dx,
                                                            dy,
                                                            width=4,
                                                            fill='red',
                                                            dash=(6, 4, 2, 4),
                                                            tag='link')
                        c.itemconfig(self.link, tags=c.gettags(self.link) + ('control',))
                        self.addLink(icon, dest, linktype='control')
                        self.createControlLinkBindings()
                        self.link = self.linkWidget = None
                else:
                    dest = self.findWidgetByName('c0')
                    dx, dy = self.canvas.coords(self.widgetToItem[dest])
                    self.link = self.canvas.create_line(float(x),
                                                        float(y),
                                                        dx,
                                                        dy,
                                                        width=4,
                                                        fill='red',
                                                        dash=(6, 4, 2, 4),
                                                        tag='link')
                    c.itemconfig(self.link, tags=c.gettags(self.link) + ('control',))
                    self.addLink(icon, dest, linktype='control')
                    self.createControlLinkBindings()
                    self.link = self.linkWidget = None

        # Load links
        if 'links' in loadedTopology:
            links = loadedTopology['links']
            for link in links:
                srcNode = link['src']
                src = self.findWidgetByName(srcNode)
                sx, sy = self.canvas.coords(self.widgetToItem[src])

                destNode = link['dest']
                dest = self.findWidgetByName(destNode)
                dx, dy = self.canvas.coords(self.widgetToItem[dest])

                self.link = self.canvas.create_line(sx, sy, dx, dy, width=4,
                                                    fill='blue', tag='link')
                c.itemconfig(self.link, tags=c.gettags(self.link)+('data',))
                self.addLink(src, dest, linkopts=link['opts'])
                self.createDataLinkBindings()
                self.link = self.linkWidget = None

        f.close()

    def findWidgetByName( self, name ):
        for widget in self.widgetToItem:
            if name ==  widget['text']:
                return widget

    def newTopology( self ):
        "New command."
        for widget in self.widgetToItem.keys():
            self.deleteItem( self.widgetToItem[ widget ] )
        for range_ in self.range.keys():
            self.deleteItem(self.range[range_])
        self.hostCount = 0
        self.stationCount = 0
        self.switchCount = 0
        self.apCount = 0
        self.controllerCount = 0
        self.links = {}
        self.hostOpts = {}
        self.stationOpts = {}
        self.switchOpts = {}
        self.apOpts = {}
        self.controllers = {}
        self.appPrefs["ipBase"]= self.defaultIpBase

    def saveTopology( self ):
        "Save command."
        myFormats = [
            ('Mininet Topology','*.mn'),
            ('All Files','*'),
        ]

        savingDictionary = {}
        fileName = filedialog.asksaveasfilename(filetypes=myFormats ,title="Save the topology as...")
        if len(fileName ) > 0:
            # Save Application preferences
            savingDictionary['version'] = '2'

            # Save Switches and Hosts
            hostsToSave = []
            stationsToSave = []
            switchesToSave = []
            apsToSave = []
            controllersToSave = []
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                x1, y1 = self.canvas.coords( self.widgetToItem[ widget ] )
                if 'Switch' in tags or 'LegacySwitch' in tags or 'LegacyRouter' in tags:
                    nodeNum = self.switchOpts[name]['nodeNum']
                    nodeToSave = {'number':str(nodeNum),
                                  'x':str(x1),
                                  'y':str(y1),
                                  'opts':self.switchOpts[name] }
                    switchesToSave.append(nodeToSave)
                elif 'AP' in tags:
                    nodeNum = self.apOpts[name]['nodeNum']
                    nodeToSave = {'number':str(nodeNum),
                                  'x':str(x1),
                                  'y':str(y1),
                                  'opts':self.apOpts[name] }
                    apsToSave.append(nodeToSave)
                elif 'Host' in tags:
                    nodeNum = self.hostOpts[name]['nodeNum']
                    nodeToSave = {'number':str(nodeNum),
                                  'x':str(x1),
                                  'y':str(y1),
                                  'opts':self.hostOpts[name] }
                    hostsToSave.append(nodeToSave)
                elif 'Station' in tags:
                    nodeNum = self.stationOpts[name]['nodeNum']
                    nodeToSave = {'number':str(nodeNum),
                                  'x':str(x1),
                                  'y':str(y1),
                                  'opts':self.stationOpts[name] }
                    stationsToSave.append(nodeToSave)
                elif 'Controller' in tags:
                    nodeToSave = {'x':str(x1),
                                  'y':str(y1),
                                  'opts':self.controllers[name] }
                    controllersToSave.append(nodeToSave)
                else:
                    raise Exception( "Cannot create mystery node: " + name )
            savingDictionary['hosts'] = hostsToSave
            savingDictionary['stations'] = stationsToSave
            savingDictionary['switches'] = switchesToSave
            savingDictionary['aps'] = apsToSave
            savingDictionary['controllers'] = controllersToSave

            # Save Links
            linksToSave = []
            for link in self.links.values():
                src = link['src']
                dst = link['dest']
                linkopts = link['linkOpts']

                srcName, dstName = src[ 'text' ], dst[ 'text' ]
                linkToSave = {'src':srcName,
                              'dest':dstName,
                              'opts':linkopts}
                if link['type'] == 'data':
                    linksToSave.append(linkToSave)
            savingDictionary['links'] = linksToSave

            # Save Application preferences
            savingDictionary['application'] = self.appPrefs

            try:
                f = open(fileName, 'wb')
                f.write(json.dumps(savingDictionary, sort_keys=True, indent=4, separators=(',', ': ')).encode())
            # pylint: disable=broad-except
            except Exception as er:
                warn( er, '\n' )
            # pylint: enable=broad-except
            finally:
                f.close()

    def exportScript( self ):
        "Export command."
        myFormats = [
            ('Mininet Custom Topology', '*.py'),
            ('All Files', '*'),
        ]

        isWiFi = False
        controllerType_ = ''
        apType_ = ''
        switchType_ = ''
        hasSwitch = False
        hasAP = False
        hasController = False
        hasStation = False
        hasLegacyRouter = False
        hasLegacySwitch = False
        hasHost = False
        isCPU = False
        for widget in self.widgetToItem:
            tags = self.canvas.gettags(self.widgetToItem[widget])
            name = widget['text']
            if 'Station' in tags or 'AP' in tags:
                isWiFi = True
                hasAP = True
                hasStation = True
            if 'Controller' in tags:
                hasController = True
                opts = self.controllers[name]
                controllerType = opts['controllerType']
                if controllerType == 'ref':
                    if ' Controller' not in controllerType_:
                        controllerType_ += ' Controller,'
                elif controllerType == 'remote':
                    if ' RemoteController' not in controllerType_:
                        controllerType_ += ' RemoteController,'
            elif 'AP' in tags:
                opts = self.apOpts[name]
                apType = opts['apType']
                if apType == 'user':
                    if ' UserAP' not in apType_:
                        apType_ += ' UserAP,'
                elif apType == 'bmv2':
                    if ' P4AP' not in apType_:
                        apType_ += ' P4AP,'
                elif apType == 'default':
                    if ' OVSKernelAP' not in apType_:
                        apType_ += ' OVSKernelAP,'
            elif 'Switch' in tags:
                hasSwitch = True
                opts = self.switchOpts[name]
                switchType = opts['switchType']
                if switchType == 'user':
                    if ' UserSwitch' not in switchType_:
                        switchType_ += ' UserSwitch,'
                elif switchType == 'bmv2':
                    if ' P4Switch' not in switchType_:
                        switchType_ += ' P4Switch,'
                elif switchType == 'default':
                    if ' OVSKernelSwitch' not in switchType_:
                        switchType_ += ' OVSKernelSwitch,'
            elif 'Host' in tags:
                hasHost = True
                opts = self.hostOpts[name]
                if 'cores' in opts or 'cpu' in opts:
                    isCPU = True
            elif 'LegacyRouter' in tags:
                hasLegacyRouter = True
            elif 'LegacySwitch' in tags:
                hasLegacySwitch = True

        links_ = ''
        sixLinks_ = ''
        for key, linkDetail in self.links.items():
            tags = self.canvas.gettags(key)
            if 'data' in tags:
                linkopts = linkDetail['linkOpts']
                if 'connection' in linkopts:
                    if 'adhoc' in linkopts['connection'] and ', adhoc' not in links_:
                        links_ += ', adhoc'
                    elif 'mesh' in linkopts['connection'] and ', mesh' not in links_:
                        links_ += ', mesh'
                    elif 'wifi-direct' in linkopts['connection'] and ', wifi-direct' not in links_:
                        links_ += ', wifiDirectLink'
                    elif '6lowpan' in linkopts['connection'] and 'sixLoWPANLink' not in sixLinks_:
                        sixLinks_ += ' sixLoWPANLink'

        fileName = filedialog.asksaveasfilename(filetypes=myFormats, title="Export the topology as...")
        if len(fileName) > 0:
            # debug( "Now saving under %s\n" % fileName )
            f = open(fileName, 'wb')

            f.write(b"#!/usr/bin/python\n")
            f.write(b"\n")
            if not isWiFi:
                f.write(b"from mininet.net import Mininet\n")
            args = ''
            if hasController:
                if not controllerType_:
                    controllerType_ = ' Controller'
                else:
                    controllerType_ = controllerType_[:-1]
                args += controllerType_
            if hasSwitch:
                if not switchType_:
                    switchType_ = ' OVSKernelSwitch'
                else:
                    switchType_ = switchType_[:-1]
                if args:
                    args += ',' + switchType_
                else:
                    args += switchType_
            if hasHost:
                if args:
                    args += ', '
                args += ' Host'
                if isCPU:
                    if args:
                        args += ', '
                    args += 'CPULimitedHost'
            if hasLegacyRouter:
                if args:
                    args += ', '
                args += ' Node'
            if hasLegacySwitch:
                if args:
                    args += ', '
                args += ' OVSKernelSwitch'

            if args:
                f.write(b"from mininet.node import" + args.encode() + b"\n")

            if not isWiFi:
                f.write(b"from mininet.cli import CLI\n")
                f.write(b"from mininet.link import TCLink, Intf\n")
            f.write(b"from mininet.log import setLogLevel, info\n")

            if isWiFi:
                f.write(b"from mn_wifi.net import Mininet_wifi\n")
                args = b''
                if hasStation:
                    args += b' Station'
                if hasAP:
                    if not apType_:
                        apType_ = ' OVSKernelAP'
                    else:
                        apType_ = apType_[:-1]
                    if args:
                        args += b',' + apType_.encode()
                    else:
                        args += apType_.encode()
                if args:
                    f.write(b"from mn_wifi.node import" + args + b"\n")
                f.write(b"from mn_wifi.cli import CLI\n")
                if not links_:
                    links_= ''
                f.write(b"from mn_wifi.link import wmediumd" + links_.encode() + b"\n")
                if sixLinks_:
                    f.write(b"from mn_wifi.sixLoWPAN.link import" + sixLinks_.encode() + b"\n")
                f.write(b"from mn_wifi.wmediumdConnector import interference\n")
            f.write(b"from subprocess import call\n")

            inBandCtrl = False
            for widget in self.widgetToItem:
                name = widget['text']
                tags = self.canvas.gettags(self.widgetToItem[widget])

                if 'Controller' in tags:
                    opts = self.controllers[name]
                    controllerType = opts['controllerType']
                    if controllerType == 'inband':
                        inBandCtrl = True

            if inBandCtrl:
                f.write(b"\n")
                f.write(b"class InbandController( RemoteController ):\n")
                f.write(b"\n")
                f.write(b"    def checkListening( self ):\n")
                f.write(b"        \"Overridden to do nothing.\"\n")
                f.write(b"        return\n")

            f.write(b"\n")
            f.write(b"\n")
            f.write(b"def myNetwork():\n")
            f.write(b"\n")
            if not isWiFi:
                f.write(b"    net = Mininet(topo=None,\n")
            else:
                f.write(b"    net = Mininet_wifi(topo=None,\n")
            if len(self.appPrefs['dpctl']) > 0:
                f.write(b"                       listenPort=" + self.appPrefs['dpctl'].encode() + b",\n")
            f.write(b"                       build=False,\n")
            if isWiFi:
                f.write(b"                       link=wmediumd,\n")
                f.write(b"                       wmediumd_mode=interference,\n")
            f.write(b"                       ipBase='" + self.appPrefs['ipBase'].encode() + b"')\n")
            f.write(b"\n")
            f.write(b"    info( '*** Adding controller\\n' )\n")
            for widget in self.widgetToItem:
                name = widget['text']
                tags = self.canvas.gettags( self.widgetToItem[widget])

                if 'Controller' in tags:
                    opts = self.controllers[name]
                    controllerType = opts['controllerType']
                    if 'controllerProtocol' in opts:
                        controllerProtocol = opts['controllerProtocol']
                    else:
                        controllerProtocol = b'tcp'
                    controllerIP = opts['remoteIP']
                    controllerPort = str(opts['remotePort'])

                    f.write(b"    " + name.encode() + b" = net.addController(name='" + name.encode() + b"',\n")

                    if controllerType == b'remote':
                        f.write(b"                           controller=RemoteController,\n")
                        f.write(b"                           ip='" + controllerIP.encode() + b"',\n")
                    elif controllerType == b'inband':
                        f.write(b"                           controller=InbandController,\n")
                        f.write(b"                           ip='" + controllerIP.encode() + b"',\n")
                    elif controllerType == b'ovsc':
                        f.write(b"                           controller=OVSController,\n")
                    else:
                        f.write(b"                           controller=Controller,\n")

                    f.write(b"                           protocol='" + controllerProtocol.encode() + b"',\n")
                    f.write(b"                           port=" + controllerPort.encode() + b")\n")
                    f.write(b"\n")

            # Save Switches and Hosts
            f.write(b"    info( '*** Add switches/APs\\n')\n")
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[widget])
                x1, y1 = self.canvas.coords(self.widgetToItem[widget])
                if 'LegacyRouter' in tags:
                    f.write(b"    " + name.encode() + b" = net.addHost('" + name.encode() + b"', cls=Node, ip='0.0.0.0')\n")
                    f.write(b"    " + name.encode() + b".cmd('sysctl -w net.ipv4.ip_forward=1')\n")
                if 'LegacySwitch' in tags:
                    f.write(b"    " + name.encode() + b"  = net.addSwitch('" + name.encode() + b"', cls=OVSKernelSwitch, failMode='standalone')\n")
                if 'Switch' in tags:
                    opts = self.switchOpts[name]
                    nodeNum = opts['nodeNum']
                    f.write(b"    " + name.encode() + b" = net.addSwitch('" + name.encode() + b"'")
                    if opts['switchType'] == 'default':
                        if self.appPrefs['switchType'] == 'user':
                            f.write(b", cls=UserSwitch")
                        elif self.appPrefs['switchType'] == 'userns':
                            f.write(b", cls=UserSwitch, inNamespace=True")
                        elif self.appPrefs['switchType'] == 'bmv2':
                            f.write(b", cls=P4Switch")
                        else:
                            f.write(b", cls=OVSKernelSwitch")
                    elif opts['switchType'] == 'user':
                        f.write(b", cls=UserSwitch")
                    elif opts['switchType'] == 'userns':
                        f.write(b", cls=UserSwitch, inNamespace=True")
                    elif opts['switchType'] == 'bmv2':
                        f.write(b", cls=P4Switch")
                    else:
                        f.write(b", cls=OVSKernelSwitch")
                    if 'dpctl' in opts:
                        f.write(b", listenPort=" + opts['dpctl'].encode())
                    if 'dpid' in opts:
                        f.write(b", dpid='" + opts['dpid'].encode() + b"'")
                    f.write(b")\n")
                    if 'externalInterfaces' in opts:
                        for extInterface in opts['externalInterfaces']:
                            f.write(b"    Intf( '" + extInterface.encode() + b"', node=" + name.encode() + b" )\n")
                if 'AP' in tags:
                    opts = self.apOpts[name]
                    nodeNum = opts['nodeNum']
                    f.write(b"    " + name.encode() + b" = net.addAccessPoint('" + name.encode() + b"'")
                    if opts['apType'] == 'default':
                        if self.appPrefs['apType'] == 'user':
                            f.write(b", cls=UserAP")
                        elif self.appPrefs['apType'] == 'userns':
                            f.write(b", cls=UserAP, inNamespace=True")
                        elif self.appPrefs['apType'] == 'bmv2':
                            f.write(b", cls=P4AP")
                        else:
                            f.write(b", cls=OVSKernelAP")
                    elif opts['apType'] == 'user':
                        f.write(b", cls=UserAP")
                    elif opts['apType'] == 'userns':
                        f.write(b", cls=UserAP, inNamespace=True")
                    elif opts['apType'] == 'bmv2':
                        f.write(b", cls=P4AP")
                    else:
                        f.write(b", cls=OVSKernelAP")
                    if 'dpctl' in opts:
                        f.write(b", listenPort=" + opts['dpctl'].encode())
                    if 'dpid' in opts:
                        f.write(b", dpid='" + opts['dpid'].encode() + b"'")
                    if 'ssid' in opts:
                        f.write(b", ssid='" + opts['ssid'].encode() + b"'")
                    if 'channel' in opts:
                        f.write(b",\n                             channel='" + opts['channel'].encode() + b"'")
                    if 'mode' in opts:
                        f.write(b", mode='" + opts['mode'].encode() + b"'")
                    if 'apIP' in opts and opts['apIP']:
                        f.write(b", ip='" + opts['apIP'].encode() + b"'")
                    if 'authentication' in opts and opts['authentication'] != 'none':
                        if opts['authentication'] == '8021x':
                            f.write(b", encrypt='wpa2', authmode='8021x'")
                        else:
                            f.write(b", encrypt='" + opts['authentication'].encode() +
                                    b"',\n                             passwd='" + opts['passwd'].encode() + b"'")
                    f.write(b", position='" + str(x1).encode() + b"," + str(y1).encode() + b",0'")
                    if opts['range'] != 'default':
                        f.write(b", range=" + str(opts['range']).encode() + b"")
                    f.write(b")\n")
                    if 'externalInterfaces' in opts:
                        for extInterface in opts['externalInterfaces']:
                            f.write(b"    Intf( '" + extInterface.encode() + b"', node=" + name.encode() + b" )\n")

            f.write(b"\n")
            f.write(b"    info( '*** Add hosts/stations\\n')\n")
            for widget in self.widgetToItem:
                name = widget['text']
                tags = self.canvas.gettags( self.widgetToItem[widget])
                x1, y1 = self.canvas.coords(self.widgetToItem[widget])
                if 'Host' in tags:
                    opts = self.hostOpts[name]
                    ip = None
                    defaultRoute = None
                    if 'defaultRoute' in opts and len(opts['defaultRoute']) > 0:
                        defaultRoute = "'via "+opts['defaultRoute']+"'"
                    else:
                        defaultRoute = 'None'
                    if 'ip' in opts and len(opts['ip']) > 0:
                        ip = opts['ip']
                    else:
                        nodeNum = self.hostOpts[name]['nodeNum']
                        ipBaseNum, prefixLen = netParse( self.appPrefs['ipBase'] )
                        ip = ipAdd(i=nodeNum, prefixLen=prefixLen, ipBaseNum=ipBaseNum)

                    if 'cores' in opts or 'cpu' in opts:
                        f.write(b"    "+name.encode() + b" = net.addHost('" + name.encode() + b"', cls=CPULimitedHost, ip='" + ip.encode() + b"', defaultRoute=" + defaultRoute.encode() + b")\n")
                        if 'cores' in opts:
                            f.write(b"    " + name.encode() + b".setCPUs(cores='" + opts['cores'].encode() + b"')\n")
                        if 'cpu' in opts:
                            f.write(b"    " + name.encode() + b".setCPUFrac(f=" + str(opts['cpu']).encode() + b", sched='" + opts['sched'].encode() + b"')\n")
                    else:
                        f.write(b"    " + name.encode() + b" = net.addHost('" + name.encode() + b"', cls=Host, ip='" + ip.encode() + b"', defaultRoute=" + defaultRoute.encode() + b")\n")
                    if 'externalInterfaces' in opts:
                        for extInterface in opts['externalInterfaces']:
                            f.write(b"    Intf( '" + extInterface.encode() + b"', node=" + name.encode() + b" )\n")
                if 'Station' in tags:
                    opts = self.stationOpts[name]
                    ip = None
                    defaultRoute = None
                    wlans = opts['wlans']
                    wpans = opts['wpans']
                    if 'defaultRoute' in opts and len(opts['defaultRoute']) > 0:
                        defaultRoute = "'via "+opts['defaultRoute']+"'"
                    else:
                        defaultRoute = 'None'
                    nodeNum = self.stationOpts[name]['nodeNum']
                    if 'ip' in opts and len(opts['ip']) > 0:
                        ip = opts['ip']
                    else:
                        ipBaseNum, prefixLen = netParse( self.appPrefs['ipBase'] )
                        ip = ipAdd(i=nodeNum, prefixLen=prefixLen, ipBaseNum=ipBaseNum)
                    args = ''
                    if int(wlans) > 1:
                        args += ', wlans=%s' % wlans
                    if int(wpans) > 0:
                        args += ', sixlowpan=%s' % wpans
                        wpanip = ", wpan_ip='2001::%s/64'" % nodeNum
                        args += wpanip
                    if 'authentication' in opts and opts['authentication']:
                        args_ = ['wpa', 'wpa2', 'wep']
                        if opts['authentication'] in args_:
                            args += ", encrypt='%s'" % opts['authentication']
                    if 'passwd' in opts and opts['passwd']:
                        if opts['passwd'] != '':
                            args += ", passwd='%s'" % opts['passwd']
                    if 'user' in opts and opts['user']:
                        if opts['user'] != '':
                            args += ", radius_identity='%s'" % opts['user']
                    if 'defaultRoute' in opts:
                        args += ", defaultRoute='%s'" % defaultRoute
                    if opts['range'] != 'default':
                        args += ", range=%s" % opts['range']
                    if 'cores' in opts or 'cpu' in opts:
                        f.write(b"    " + name.encode() + b" = net.addStation('" + name.encode() + b"', cls=CPULimitedHost, ip='" + ip.encode() + b"', defaultRoute=" + defaultRoute.encode() + b", position='" + str(x1).encode() + b"," + str(y1).encode() + b",0'"+ args.encode() + b")\n")
                        if 'cores' in opts:
                            f.write(b"    " + name.encode() + b".setCPUs(cores='" + opts['cores'].encode() + b"')\n")
                        if 'cpu' in opts:
                            f.write(b"    " + name.encode() + b".setCPUFrac(f=" + str(opts['cpu']).encode() + b", sched='" + opts['sched'].encode() + b"')\n")
                    else:
                        f.write(b"    " + name.encode() + b" = net.addStation('" + name.encode() + b"', ip='" + ip.encode() + b"',\n                           position='" + str(x1).encode() + b"," + str(y1).encode() + b",0'" + args.encode() + b")\n")
                    if 'externalInterfaces' in opts:
                        for extInterface in opts['externalInterfaces']:
                            f.write(b"    Intf( '" + extInterface.encode() + b"', node=" + name.encode() + b" )\n")
            f.write(b"\n")

            if isWiFi:
                f.write(b"    info(\"*** Configuring Propagation Model\\n\")\n")
                f.write(b"    net.setPropagationModel(model=\"logDistance\", exp=3)\n")
                f.write(b"\n")
                f.write(b"    info(\"*** Configuring wifi nodes\\n\")\n")
                f.write(b"    net.configureWifiNodes()\n")
                f.write(b"\n")

            # Save Links
            lowpan = []
            if self.links:
                f.write(b"    info( '*** Add links\\n')\n")
            for key,linkDetail in self.links.items():
                tags = self.canvas.gettags(key)
                if 'data' in tags:
                    optsExist = False
                    src = linkDetail['src']
                    dst = linkDetail['dest']
                    linkopts = linkDetail['linkOpts']
                    srcName, dstName = src['text'], dst['text']
                    bw = ''
                    # delay = ''
                    # loss = ''
                    # max_queue_size = ''
                    linkOpts = "{"
                    if 'bw' in linkopts:
                        bw =  linkopts['bw']
                        linkOpts = linkOpts + "'bw':" + str(bw)
                        optsExist = True
                    if 'delay' in linkopts:
                        # delay =  linkopts['delay']
                        if optsExist:
                            linkOpts = linkOpts + ","
                        linkOpts = linkOpts + "'delay':'"+linkopts['delay']+"'"
                        optsExist = True
                    if 'loss' in linkopts:
                        if optsExist:
                            linkOpts = linkOpts + ","
                        linkOpts = linkOpts + "'loss':" + str(linkopts['loss'])
                        optsExist = True
                    if 'max_queue_size' in linkopts:
                        if optsExist:
                            linkOpts = linkOpts + ","
                        linkOpts = linkOpts + "'max_queue_size':" + str(linkopts['max_queue_size'])
                        optsExist = True
                    if 'jitter' in linkopts:
                        if optsExist:
                            linkOpts = linkOpts + ","
                        linkOpts = linkOpts + "'jitter':'" + linkopts['jitter']+"'"
                        optsExist = True
                    if 'speedup' in linkopts:
                        if optsExist:
                            linkOpts = linkOpts + ","
                        linkOpts = linkOpts + "'speedup':" + str(linkopts['speedup'])
                        optsExist = True

                    linkOpts = linkOpts + "}"
                    args_ = ['adhoc', 'mesh', 'wifiDirect']
                    if optsExist:
                        f.write(b"    " + srcName.encode() + dstName.encode() + b" = " + linkOpts.encode() + b"\n")
                    if 'connection' in linkopts and '6lowpan' in linkopts['connection']:
                        if srcName not in lowpan:
                            f.write(b"    net.addLink(" + srcName.encode() + b", cls=sixLoWPANLink, panid='0xbeef')\n")
                            lowpan.append(srcName)
                        if dstName not in lowpan:
                            f.write(b"    net.addLink(" + dstName.encode() + b", cls=sixLoWPANLink, panid='0xbeef')\n")
                            lowpan.append(dstName)
                    elif 'connection' in linkopts and linkopts['connection'] in args_:
                        nodes = []
                        nodes.append(srcName)
                        nodes.append(dstName)
                        for node in nodes:
                            f.write(b"    net.addLink(" + node.encode())
                            if 'adhoc' in linkopts['connection'] or 'mesh' in linkopts['connection']:
                                link = ", cls={}, ssid=\'{}\', mode=\'{}\', channel={}".format(linkopts['connection'],
                                                                                                linkopts['ssid'],
                                                                                                linkopts['mode'],
                                                                                                linkopts['channel'])
                                f.write(link.encode())
                            elif 'wifiDirect' in linkopts['connection']:
                                f.write(b", cls=wifiDirectLink")
                            intf = None

                            if 'src' in linkopts and nodes.index(node) == 0:
                                intf = linkopts['src']
                            elif 'dest' in linkopts and nodes.index(node) == 1:
                                intf = linkopts['dest']
                            if intf and intf != 'default':
                                f.write(b", intf=\'%s\'" % intf)
                            f.write(b")\n")
                    else:
                        f.write(b"    net.addLink(" + srcName.encode() + b", " + dstName.encode())
                        if optsExist:
                            f.write(b", cls=TCLink , **" + srcName.encode() + dstName.encode())
                        if ('connection' in linkopts and '6lowpan' not in linkopts['connection']) \
                                or 'connection' not in linkopts:
                            f.write(b")\n")
            if self.links:
                f.write(b"\n")
            if isWiFi:
                f.write(b"    net.plotGraph(max_x=1000, max_y=1000)\n")
                f.write(b"\n")

            f.write(b"    info( '*** Starting network\\n')\n")
            f.write(b"    net.build()\n")

            f.write(b"    info( '*** Starting controllers\\n')\n")
            f.write(b"    for controller in net.controllers:\n")
            f.write(b"        controller.start()\n")
            f.write(b"\n")

            f.write(b"    info( '*** Starting switches/APs\\n')\n")
            for widget in self.widgetToItem:
                name = widget['text']
                tags = self.canvas.gettags( self.widgetToItem[widget])
                if 'Switch' in tags or 'LegacySwitch' in tags or 'AP' in tags:
                    if 'AP' in tags:
                        opts = self.apOpts[name]
                    else:
                        opts = self.switchOpts[name]
                    ctrlList = ",".join(opts['controllers'])
                    f.write(b"    net.get('" + name.encode() + b"').start([" + ctrlList.encode() + b"])\n")

            f.write(b"\n")

            f.write(b"    info( '*** Post configure nodes\\n')\n")
            for widget in self.widgetToItem:
                name = widget['text']
                tags = self.canvas.gettags(self.widgetToItem[widget])
                if 'Switch' in tags:
                    opts = self.switchOpts[name]
                    if opts['switchType'] == 'default':
                        if self.appPrefs['switchType'] == 'user':
                            if 'switchIP' in opts:
                                if len(opts['switchIP']) > 0:
                                    f.write(b"    "+ name.encode() + b".cmd('ifconfig " + name.encode() + b" " + opts['switchIP'].encode() + b"')\n")
                        elif self.appPrefs['switchType'] == 'userns':
                            if 'switchIP' in opts:
                                if len(opts['switchIP']) > 0:
                                    f.write(b"    "+ name.encode() + b".cmd('ifconfig lo " + opts['switchIP'].encode() + b"')\n")
                        elif self.appPrefs['switchType'] == 'ovs':
                            if 'switchIP' in opts:
                                if len(opts['switchIP']) > 0:
                                    f.write(b"    "+ name.encode() + b".cmd('ifconfig " + name.encode() + b" " + opts['switchIP'].encode() + b"')\n")
                    elif opts['switchType'] == 'user':
                        if 'switchIP' in opts:
                            if len(opts['switchIP']) > 0:
                                f.write(b"    " + name.encode() + b".cmd('ifconfig " + name.encode() + b" " + opts['switchIP'].encode() + b"')\n")
                    elif opts['switchType'] == 'userns':
                        if 'switchIP' in opts:
                            if len(opts['switchIP']) > 0:
                                f.write(b"    " + name.encode() + b".cmd('ifconfig lo " + opts['switchIP'].encode() + b"')\n")
                    elif opts['switchType'] == 'ovs':
                        if 'switchIP' in opts:
                            if len(opts['switchIP']) > 0:
                                f.write(b"    " + name.encode() + b".cmd('ifconfig " + name.encode() + b" " + opts['switchIP'].encode() + b"')\n")
                elif 'AP' in tags:
                    opts = self.apOpts[name]
                    if opts['apType'] == 'default' or opts['apType'] == 'ovs':
                        if 'apIP' in opts:
                            if len(opts['apIP']) > 0:
                                f.write(b"    " + name.encode() + b".cmd('ifconfig " + name.encode() + b" " + opts['apIP'].encode() + b"')\n")
            for widget in self.widgetToItem:
                name = widget['text']
                tags = self.canvas.gettags( self.widgetToItem[widget])
                if 'Host' in tags:
                    opts = self.hostOpts[name]
                    # Attach vlan interfaces
                    if 'vlanInterfaces' in opts:
                        for vlanInterface in opts['vlanInterfaces']:
                            f.write(b"    " + name.encode() + b".cmd('vconfig add " + name.encode() + b"-eth0 " + vlanInterface[1].encode() + b"')\n")
                            f.write(b"    " + name.encode() + b".cmd('ifconfig " + name.encode() + b"-eth0." + vlanInterface[1].encode() + b" " + vlanInterface[0].encode() + b"')\n")
                    # Run User Defined Start Command
                    if 'startCommand' in opts:
                        f.write(b"    " + name.encode() + b".cmdPrint('" + opts['startCommand'].encode() + b"')\n")
                elif 'Station' in tags:
                    opts = self.stationOpts[name]
                    # Attach vlan interfaces
                    if 'vlanInterfaces' in opts:
                        for vlanInterface in opts['vlanInterfaces']:
                            f.write(b"    " + name.encode() + b".cmd('vconfig add " + name.encode() + b"-wlan0 " + vlanInterface[1].encode() + b"')\n")
                            f.write(b"    " + name.encode() + b".cmd('ifconfig " + name.encode() + b"-wlan0." + vlanInterface[1].encode() + b" " + vlanInterface[0].encode() + b"')\n")
                    # Run User Defined Start Command
                    if 'startCommand' in opts:
                        f.write(b"    " + name.encode()+ b".cmdPrint('" + opts['startCommand'].encode() + b"')\n")
                if 'Switch' in tags or 'AP' in tags:
                    if 'Switch' in tags:
                        opts = self.switchOpts[name]
                    else:
                        opts = self.apOpts[name]
                    # Run User Defined Start Command
                    if 'startCommand' in opts:
                        f.write(b"    " + name.encode() + b".cmdPrint('" + opts['startCommand'].encode() + b"')\n")

            # Configure NetFlow
            nflowValues = self.appPrefs['netflow']
            if len(nflowValues['nflowTarget']) > 0:
                nflowEnabled = False
                nflowSwitches = ''
                nflowAPs = ''
                for widget in self.widgetToItem:
                    name = widget['text']
                    tags = self.canvas.gettags( self.widgetToItem[ widget ] )

                    if 'Switch' in tags:
                        opts = self.switchOpts[name]
                        if 'netflow' in opts:
                            if opts['netflow'] == '1':
                                nflowSwitches = nflowSwitches+' -- set Bridge '+name+' netflow=@MiniEditNF'
                                nflowEnabled=True
                    elif 'AP' in tags:
                        opts = self.apOpts[name]
                        if 'netflow' in opts:
                            if opts['netflow'] == '1':
                                nflowAPs = nflowAPs+' -- set Bridge '+name+' netflow=@MiniEditNF'
                                nflowEnabled=True
                if nflowEnabled:
                    nflowCmd = 'ovs-vsctl -- --id=@MiniEditNF create NetFlow '+ 'target=\\\"'+nflowValues['nflowTarget']+'\\\" '+ 'active-timeout='+nflowValues['nflowTimeout']
                    if nflowValues['nflowAddId'] == '1':
                        nflowCmd = nflowCmd + ' add_id_to_interface=true'
                    else:
                        nflowCmd = nflowCmd + ' add_id_to_interface=false'
                    f.write(b"    \n")
                    f.write(b"    call('" + nflowCmd.encode() + nflowSwitches.encode() + b"', shell=True)\n")

            # Configure sFlow
            sflowValues = self.appPrefs['sflow']
            if len(sflowValues['sflowTarget']) > 0:
                sflowEnabled = False
                sflowSwitches = ''
                sflowAPs = ''
                for widget in self.widgetToItem:
                    name = widget[ 'text' ]
                    tags = self.canvas.gettags( self.widgetToItem[ widget ] )

                    if 'Switch' in tags:
                        opts = self.switchOpts[name]
                        if 'sflow' in opts:
                            if opts['sflow'] == '1':
                                sflowSwitches = sflowSwitches+' -- set Bridge ' + name + ' sflow=@MiniEditSF'
                                sflowEnabled=True
                    elif 'AP' in tags:
                        opts = self.apOpts[name]
                        if 'sflow' in opts:
                            if opts['sflow'] == '1':
                                sflowAPs = sflowAPs+' -- set Bridge ' + name + ' sflow=@MiniEditSF'
                                sflowEnabled=True
                if sflowEnabled:
                    sflowCmd = 'ovs-vsctl -- --id=@MiniEditSF create sFlow ' + 'target=\\\"' + sflowValues['sflowTarget'] + '\\\" ' + 'header=' + sflowValues['sflowHeader']+' '+ 'sampling='+sflowValues['sflowSampling']+' '+ 'polling='+sflowValues['sflowPolling']
                    f.write(b"    \n")
                    f.write(b"    call('" + sflowCmd.encode() + sflowSwitches.encode() + b"', shell=True)\n")

            f.write(b"\n")
            f.write(b"    CLI(net)\n")
            for widget in self.widgetToItem:
                name = widget['text']
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                if 'Host' in tags or 'Station' in tags:
                    if 'Host' in tags:
                        opts = self.hostOpts[name]
                    else:
                        opts = self.stationOpts[name]
                    # Run User Defined Stop Command
                    if 'stopCommand' in opts:
                        f.write(b"    " + name.encode() + b".cmdPrint('" + opts['stopCommand'].encode() + b"')\n")
                if 'Switch' in tags or 'AP' in tags:
                    if 'Switch' in tags:
                        opts = self.switchOpts[name]
                    else:
                        opts = self.apOpts[name]
                    # Run User Defined Stop Command
                    if 'stopCommand' in opts:
                        f.write(b"    " + name.encode() + b".cmdPrint('" + opts['stopCommand'].encode() + b"')\n")

            f.write(b"    net.stop()\n")
            f.write(b"\n")
            f.write(b"\n")
            f.write(b"if __name__ == '__main__':\n")
            f.write(b"    setLogLevel( 'info' )\n")
            f.write(b"    myNetwork()\n")
            f.write(b"\n")
            f.close()

    # Generic canvas handler
    #
    # We could have used bindtags, as in nodeIcon, but
    # the dynamic approach used here
    # may actually require less code. In any case, it's an
    # interesting introspection-based alternative to bindtags.

    def canvasHandle(self, eventName, event):
        "Generic canvas event handler"
        if self.active is None:
            return
        toolName = self.active
        handler = getattr( self, eventName + toolName, None )
        if handler is not None:
            handler(event)

    def clickCanvas( self, event ):
        "Canvas click handler."
        self.canvasHandle( 'click', event )

    def dragCanvas( self, event ):
        "Canvas drag handler."
        self.canvasHandle( 'drag', event )

    def releaseCanvas( self, event ):
        "Canvas mouse up handler."
        self.canvasHandle( 'release', event )

    # Currently the only items we can select directly are
    # links. Nodes are handled by bindings in the node icon.

    def findItem( self, x, y ):
        "Find items at a location in our canvas."
        items = self.canvas.find_overlapping( x, y, x, y )
        if len( items ) == 0:
            return None
        return items[ 0 ]

    # Canvas bindings for Select, Host, Switch and Link tools

    def clickSelect( self, event ):
        "Select an item."
        self.selectItem( self.findItem( event.x, event.y ) )

    def deleteItem( self, item ):
        "Delete an item."
        # Don't delete while network is running
        if self.buttons[ 'Select' ][ 'state' ] == 'disabled':
            return
        # Delete from model
        if item in self.links:
            self.deleteLink( item )
        if item in self.itemToWidget:
            self.deleteNode( item )
        # Delete from view
        self.canvas.delete( item )

    def deleteSelection( self, _event ):
        "Delete the selected item."
        if self.selection is not None:
            self.deleteItem( self.selection )
        self.selectItem(None)

    def nodeIcon( self, node, name ):
        "Create a new node icon."
        icon = Button(self.canvas, image=self.images[node],
                      text=name, compound='top')
        # Unfortunately bindtags wants a tuple
        bindtags = [ str( self.nodeBindings ) ]
        bindtags += list( icon.bindtags() )
        icon.bindtags( tuple( bindtags ) )
        return icon

    def newNode( self, node, event ):
        "Add a new node to our canvas."
        c = self.canvas
        x, y = c.canvasx(event.x), c.canvasy(event.y)
        name = self.nodePrefixes[ node ]
        if 'Switch' == node:
            self.switchCount += 1
            name = self.nodePrefixes[ node ] + str( self.switchCount )
            self.switchOpts[name] = {}
            self.switchOpts[name]['nodeNum'] = self.switchCount
            self.switchOpts[name]['hostname'] = name
            self.switchOpts[name]['switchType'] = 'default'
            self.switchOpts[name]['controllers'] = []
        if 'AP' == node:
            self.apCount += 1
            name = self.nodePrefixes[ node ] + str( self.apCount )
            self.apOpts[name] = {}
            self.apOpts[name]['nodeNum'] = self.apCount
            self.apOpts[name]['hostname'] = name
            self.apOpts[name]['apType'] = 'default'
            self.apOpts[name]['ssid'] = name + '-ssid'
            self.apOpts[name]['channel'] = '1'
            self.apOpts[name]['mode'] = 'g'
            self.apOpts[name]['range'] = 'default'
            self.apOpts[name]['authentication'] = 'none'
            self.apOpts[name]['passwd'] = ''
            self.apOpts[name]['controllers'] = []
            self.apOpts[name]['wlans'] = 1
        if 'LegacyRouter' == node:
            self.switchCount += 1
            name = self.nodePrefixes[ node ] + str( self.switchCount )
            self.switchOpts[name] = {}
            self.switchOpts[name]['nodeNum'] = self.switchCount
            self.switchOpts[name]['hostname'] = name
            self.switchOpts[name]['switchType'] = 'legacyRouter'
        if 'LegacySwitch' == node:
            self.switchCount += 1
            name = self.nodePrefixes[ node ] + str( self.switchCount )
            self.switchOpts[name] = {}
            self.switchOpts[name]['nodeNum'] = self.switchCount
            self.switchOpts[name]['hostname'] = name
            self.switchOpts[name]['switchType'] = 'legacySwitch'
            self.switchOpts[name]['controllers'] = []
        if 'Host' == node:
            self.hostCount += 1
            name = self.nodePrefixes[ node ] + str( self.hostCount )
            self.hostOpts[name] = {'sched': 'host'}
            self.hostOpts[name]['nodeNum'] = self.hostCount
            self.hostOpts[name]['hostname'] = name
        if 'Station' == node:
            self.stationCount += 1
            name = self.nodePrefixes[ node ] + str( self.stationCount )
            self.stationOpts[name] = {'sched':'station'}
            self.stationOpts[name]['nodeNum'] = self.stationCount
            self.stationOpts[name]['hostname'] = name
            self.stationOpts[name]['ssid'] = name + '-ssid'
            self.stationOpts[name]['channel'] = '1'
            self.stationOpts[name]['mode'] = 'g'
            self.stationOpts[name]['range'] = 'default'
            self.stationOpts[name]['passwd'] = ''
            self.stationOpts[name]['user'] = ''
            self.stationOpts[name]['wpans'] = 0
            self.stationOpts[name]['wlans'] = 1
        if 'Controller' == node:
            name = self.nodePrefixes[ node ] + str( self.controllerCount )
            ctrlr = { 'controllerType': 'ref',
                      'hostname': name,
                      'controllerProtocol': 'tcp',
                      'remoteIP': '127.0.0.1',
                      'remotePort': 6653}
            self.controllers[name] = ctrlr
            # We want to start controller count at 0
            self.controllerCount += 1
        if node == 'AP' or node == 'Station':
            c = self.canvas
            if node == 'AP':
                node_ = self.apOpts[name]
                type = 'AP'
            else:
                node_ = self.stationOpts[name]
                type = 'Station'
            range = self.getRange(node_, type)

            self.range[name] = self.createCircle(x, y, range, c)

        icon = self.nodeIcon( node, name )
        item = self.canvas.create_window(x, y, anchor='c', window=icon, tags=node)
        self.widgetToItem[ icon ] = item
        self.itemToWidget[ item ] = icon
        self.selectItem( item )
        icon.links = {}
        if 'Switch' == node:
            icon.bind('<Button-3>', self.do_switchPopup )
        if 'AP' == node:
            icon.bind('<Button-3>', self.do_apPopup)
        if 'LegacyRouter' == node:
            icon.bind('<Button-3>', self.do_legacyRouterPopup )
        if 'LegacySwitch' == node:
            icon.bind('<Button-3>', self.do_legacySwitchPopup )
        if 'Host' == node:
            icon.bind('<Button-3>', self.do_hostPopup )
        if 'Station' == node:
            icon.bind('<Button-3>', self.do_stationPopup)
        if 'Controller' == node:
            icon.bind('<Button-3>', self.do_controllerPopup )

    def createCircle(self, x, y, range, c):
        return c.create_oval(x - range, y - range,
                             x + range, y + range,
                             outline="#0000ff", width=2)

    def clickController( self, event ):
        "Add a new Controller to our canvas."
        self.newNode( 'Controller', event )

    def clickHost( self, event ):
        "Add a new host to our canvas."
        self.newNode( 'Host', event )

    def clickStation( self, event ):
        "Add a new station to our canvas."
        self.newNode( 'Station', event )

    def clickLegacyRouter( self, event ):
        "Add a new switch to our canvas."
        self.newNode( 'LegacyRouter', event )

    def clickLegacySwitch( self, event ):
        "Add a new switch to our canvas."
        self.newNode( 'LegacySwitch', event )

    def clickSwitch( self, event ):
        "Add a new switch to our canvas."
        self.newNode( 'Switch', event )

    def clickAP( self, event ):
        "Add a new ap to our canvas."
        self.newNode( 'AP', event )

    def getRange(self, node, type):
        if node['range'] == 'default':
            range = 188 if node['mode'] == 'a' else 313
        else:
            range = node['range']

        return int(range)

    def dragNetLink( self, event ):
        "Drag a link's endpoint to another node."
        if self.link is None:
            return
        # Since drag starts in widget, we use root coords
        x = self.canvasx( event.x_root )
        y = self.canvasy( event.y_root )
        c = self.canvas
        c.coords( self.link, self.linkx, self.linky, x, y )

    def releaseNetLink( self, _event ):
        "Give up on the current link."
        if self.link is not None:
            self.canvas.delete( self.link )
        self.linkWidget = self.linkItem = self.link = None

    # Generic node handlers

    def createNodeBindings( self ):
        "Create a set of bindings for nodes."
        bindings = {
            '<ButtonPress-1>': self.clickNode,
            '<B1-Motion>': self.dragNode,
            '<ButtonRelease-1>': self.releaseNode,
            '<Enter>': self.enterNode,
            '<Leave>': self.leaveNode
        }
        l = Label()  # lightweight-ish owner for bindings
        for event, binding in bindings.items():
            l.bind( event, binding )
        return l

    def selectItem( self, item ):
        "Select an item and remember old selection."
        self.lastSelection = self.selection
        self.selection = item

    def enterNode( self, event ):
        "Select node on entry."
        self.selectNode( event )

    def leaveNode( self, _event ):
        "Restore old selection on exit."
        self.selectItem( self.lastSelection )

    def clickNode( self, event ):
        "Node click handler."
        if self.active == 'NetLink':
            self.startLink( event )
        else:
            self.selectNode( event )
        return 'break'

    def dragNode( self, event ):
        "Node drag handler."
        if self.active == 'NetLink':
            self.dragNetLink( event )
        else:
            self.dragNodeAround( event )

    def releaseNode( self, event ):
        "Node release handler."
        if self.active == 'NetLink':
            self.finishLink( event )

    # Specific node handlers

    def selectNode( self, event ):
        "Select the node that was clicked on."
        item = self.widgetToItem.get( event.widget, None )
        self.selectItem( item )

    def setPosition(self, node, x, y):
        node.setPosition('%s,%s,0' % (x, y))

    def dragNodeAround( self, event ):
        "Drag a node around on the canvas."
        c = self.canvas
        # Convert global to local coordinates;
        # Necessary since x, y are widget-relative
        x = self.canvasx( event.x_root )
        y = self.canvasy( event.y_root )
        w = event.widget
        # Adjust node position
        item = self.widgetToItem[ w ]
        c.coords( item, x, y )

        tags = self.canvas.gettags(item)
        if 'Station' in tags or 'AP' in tags:
            widget = self.itemToWidget[item]
            name = widget['text']
            if 'AP' in tags:
                node = self.apOpts[name]
                type = 'AP'
            else:
                node = self.stationOpts[name]
                type = 'Station'
            range = self.getRange(node, type)
            c.coords(self.range[name],
                     x - range, y - range,
                     x + range, y + range)
        # Adjust link positions
        for dest in w.links:
            link = w.links[dest]
            item = self.widgetToItem[dest]
            x1, y1 = c.coords(item)
            c.coords(link, x, y, x1, y1)

        if self.net and ('Station' in tags or 'AP' in tags):
            self.setPosition(self.net.getNodeByName(name), x, y)
        self.updateScrollRegion()

    def createControlLinkBindings( self ):
        "Create a set of bindings for nodes."
        # Link bindings
        # Selection still needs a bit of work overall
        # Callbacks ignore event

        def select( _event, link=self.link ):
            "Select item on mouse entry."
            self.selectItem( link )

        def highlight( _event, link=self.link ):
            "Highlight item on mouse entry."
            self.selectItem( link )
            self.canvas.itemconfig( link, fill='green' )

        def unhighlight( _event, link=self.link ):
            "Unhighlight item on mouse exit."
            self.canvas.itemconfig( link, fill='red' )
            #self.selectItem( None )

        self.canvas.tag_bind( self.link, '<Enter>', highlight )
        self.canvas.tag_bind( self.link, '<Leave>', unhighlight )
        self.canvas.tag_bind( self.link, '<ButtonPress-1>', select )

    def createDataLinkBindings( self ):
        "Create a set of bindings for nodes."
        # Link bindings
        # Selection still needs a bit of work overall
        # Callbacks ignore event

        def select( _event, link=self.link ):
            "Select item on mouse entry."
            self.selectItem( link )

        def highlight( _event, link=self.link ):
            "Highlight item on mouse entry."
            self.selectItem( link )
            self.canvas.itemconfig( link, fill='green' )

        def unhighlight( _event, link=self.link ):
            "Unhighlight item on mouse exit."
            self.canvas.itemconfig( link, fill='blue' )
            #self.selectItem( None )

        self.canvas.tag_bind( self.link, '<Enter>', highlight )
        self.canvas.tag_bind( self.link, '<Leave>', unhighlight )
        self.canvas.tag_bind( self.link, '<ButtonPress-1>', select )
        self.canvas.tag_bind( self.link, '<Button-3>', self.do_linkPopup )

    def startLink( self, event ):
        "Start a new link."
        if event.widget not in self.widgetToItem:
            # Didn't click on a node
            return

        w = event.widget
        item = self.widgetToItem[ w ]
        x, y = self.canvas.coords( item )
        self.link = self.canvas.create_line( x, y, x, y, width=4,
                                             fill='blue', tag='link' )
        self.linkx, self.linky = x, y
        self.linkWidget = w
        self.linkItem = item

    def finishLink( self, event ):
        "Finish creating a link"
        if self.link is None:
            return
        source = self.linkWidget
        c = self.canvas
        # Since we dragged from the widget, use root coords
        x, y = self.canvasx( event.x_root ), self.canvasy( event.y_root )
        target = self.findItem( x, y )
        dest = self.itemToWidget.get( target, None )
        if ( source is None or dest is None or source == dest
             or dest in source.links or source in dest.links ):
            self.releaseNetLink( event )
            return
        # For now, don't allow hosts to be directly linked
        stags = self.canvas.gettags( self.widgetToItem[ source ] )
        dtags = self.canvas.gettags( target )
        if (('Controller' in dtags and 'LegacyRouter' in stags) or
                ('Controller' in stags and 'LegacyRouter' in dtags) or
                ('Controller' in dtags and 'LegacySwitch' in stags) or
                ('Controller' in stags and 'LegacySwitch' in dtags) or
                ('Controller' in dtags and 'Host' in stags) or
                ('Controller' in stags and 'Host' in dtags) or
                ('Controller' in stags and 'Controller' in dtags)):
            self.releaseNetLink( event )
            return

        # Set link type
        linkType='data'
        if 'Controller' in stags or 'Controller' in dtags:
            linkType='control'
            c.itemconfig(self.link, dash=(6, 4, 2, 4), fill='red')
            self.createControlLinkBindings()
        elif 'Station' in stags and 'AP' in dtags:
            linkType='data'
            c.itemconfig(self.link, dash=(4, 2, 4, 2), fill='blue')
            self.createDataLinkBindings()
        elif 'AP' in stags and 'Station' in dtags:
            linkType='data'
            c.itemconfig(self.link, dash=(4, 2, 4, 2), fill='blue')
            self.createDataLinkBindings()
        else:
            linkType='data'
            self.createDataLinkBindings()
        c.itemconfig(self.link, tags=c.gettags(self.link)+(linkType,))

        x, y = c.coords( target )
        c.coords( self.link, self.linkx, self.linky, x, y )
        self.addLink( source, dest, linktype=linkType )
        if linkType == 'control':
            controllerName = ''
            switchName = ''
            if 'Controller' in stags:
                controllerName = source[ 'text' ]
                switchName = dest[ 'text' ]
            else:
                controllerName = dest[ 'text' ]
                switchName = source[ 'text' ]

            try:
                self.switchOpts[switchName]['controllers'].append(controllerName)
            except:
                self.apOpts[switchName]['controllers'].append(controllerName)

        # We're done
        self.link = self.linkWidget = None

    # Menu handlers

    def about( self ):
        "Display about box."
        about = self.aboutBox
        if about is None:
            bg = 'white'
            about = Toplevel( bg='white' )
            about.title( 'About' )
            desc = self.appName + ': a simple network editor for MiniNet'
            version = 'MiniEdit ' + MINIEDIT_VERSION
            author = 'Originally by: Bob Lantz <rlantz@cs>, April 2010'
            enhancements = 'Enhancements by: Ramon Fontes, Since October 2018'
            www = 'http://github.com/ramonfontes'
            line1 = Label( about, text=desc, font='Helvetica 10 bold', bg=bg )
            line2 = Label( about, text=version, font='Helvetica 9', bg=bg )
            line3 = Label( about, text=author, font='Helvetica 9', bg=bg )
            line4 = Label( about, text=enhancements, font='Helvetica 9', bg=bg )
            line5 = Entry( about, font='Helvetica 9', bg=bg, width=len(www), justify=CENTER )
            line5.insert(0, www)
            line5.configure(state='readonly')
            line1.pack( padx=20, pady=10 )
            line2.pack(pady=10 )
            line3.pack(pady=10 )
            line4.pack(pady=10 )
            line5.pack(pady=10 )
            hide = ( lambda about=about: about.withdraw() )
            self.aboutBox = about
            # Hide on close rather than destroying window
            Wm.wm_protocol( about, name='WM_DELETE_WINDOW', func=hide )
        # Show (existing) window
        about.deiconify()

    def createToolImages( self ):
        "Create toolbar (and icon) images."

    @staticmethod
    def checkIntf( intf ):
        "Make sure intf exists and is not configured."
        if ( ' %s:' % intf ) not in quietRun( 'ip link show' ):
            messagebox.showerror(title="Error",
                      message='External interface ' +intf + ' does not exist! Skipping.')
            return False
        ips = re.findall( r'\d+\.\d+\.\d+\.\d+', quietRun( 'ifconfig ' + intf ) )
        if ips:
            messagebox.showerror(title="Error",
                      message= intf + ' has an IP address and is probably in use! Skipping.' )
            return False
        return True

    def hostDetails( self, _ignore=None ):
        if ( self.selection is None or
             self.net is not None or
             self.selection not in self.itemToWidget ):
            return
        widget = self.itemToWidget[ self.selection ]
        name = widget[ 'text' ]
        tags = self.canvas.gettags( self.selection )
        if 'Host' not in tags:
            return

        prefDefaults = self.hostOpts[name]
        hostBox = HostDialog(self, title='Host Details', prefDefaults=prefDefaults)
        self.master.wait_window(hostBox.top)
        if hostBox.result:
            newHostOpts = {'nodeNum':self.hostOpts[name]['nodeNum']}
            newHostOpts['sched'] = hostBox.result['sched']
            if len(hostBox.result['startCommand']) > 0:
                newHostOpts['startCommand'] = hostBox.result['startCommand']
            if len(hostBox.result['stopCommand']) > 0:
                newHostOpts['stopCommand'] = hostBox.result['stopCommand']
            if len(hostBox.result['cpu']) > 0:
                newHostOpts['cpu'] = float(hostBox.result['cpu'])
            if len(hostBox.result['cores']) > 0:
                newHostOpts['cores'] = hostBox.result['cores']
            if len(hostBox.result['hostname']) > 0:
                newHostOpts['hostname'] = hostBox.result['hostname']
                name = hostBox.result['hostname']
                widget[ 'text' ] = name
            if len(hostBox.result['defaultRoute']) > 0:
                newHostOpts['defaultRoute'] = hostBox.result['defaultRoute']
            if len(hostBox.result['ip']) > 0:
                newHostOpts['ip'] = hostBox.result['ip']
            if len(hostBox.result['externalInterfaces']) > 0:
                newHostOpts['externalInterfaces'] = hostBox.result['externalInterfaces']
            if len(hostBox.result['vlanInterfaces']) > 0:
                newHostOpts['vlanInterfaces'] = hostBox.result['vlanInterfaces']
            if len(hostBox.result['privateDirectory']) > 0:
                newHostOpts['privateDirectory'] = hostBox.result['privateDirectory']
            self.hostOpts[name] = newHostOpts
            info( 'New host details for ' + name + ' = ' + str(newHostOpts), '\n' )

    def stationDetails( self, _ignore=None ):
        if ( self.selection is None or
             self.net is not None or
             self.selection not in self.itemToWidget ):
            return
        widget = self.itemToWidget[ self.selection ]
        name = widget[ 'text' ]
        tags = self.canvas.gettags( self.selection )
        if 'Station' not in tags:
            return

        prefDefaults = self.stationOpts[name]
        stationBox = StationDialog(self, title='Station Details', prefDefaults=prefDefaults)
        self.master.wait_window(stationBox.top)
        if stationBox.result:
            newStationOpts = {'nodeNum':self.stationOpts[name]['nodeNum']}
            newStationOpts['mode'] = stationBox.result['mode']
            newStationOpts['sched'] = stationBox.result['sched']
            newStationOpts['range'] = stationBox.result['range']
            if len(stationBox.result['startCommand']) > 0:
                newStationOpts['startCommand'] = stationBox.result['startCommand']
            if len(stationBox.result['stopCommand']) > 0:
                newStationOpts['stopCommand'] = stationBox.result['stopCommand']
            if len(stationBox.result['cpu']) > 0:
                newStationOpts['cpu'] = float(stationBox.result['cpu'])
            if len(stationBox.result['cores']) > 0:
                newStationOpts['cores'] = stationBox.result['cores']
            if len(stationBox.result['hostname']) > 0:
                newStationOpts['hostname'] = stationBox.result['hostname']
                name = stationBox.result['hostname']
                widget[ 'text' ] = name
            if len(stationBox.result['passwd']) > 0:
                newStationOpts['passwd'] = stationBox.result['passwd']
            if len(stationBox.result['user']) > 0:
                newStationOpts['user'] = stationBox.result['user']
            if len(stationBox.result['wpans']) > 0:
                newStationOpts['wpans'] = int(stationBox.result['wpans'])
            if len(stationBox.result['wlans']) > 0:
                newStationOpts['wlans'] = int(stationBox.result['wlans'])
            if len(stationBox.result['defaultRoute']) > 0:
                newStationOpts['defaultRoute'] = stationBox.result['defaultRoute']
            if len(stationBox.result['ip']) > 0:
                newStationOpts['ip'] = stationBox.result['ip']
            if len(stationBox.result['externalInterfaces']) > 0:
                newStationOpts['externalInterfaces'] = stationBox.result['externalInterfaces']
            if len(stationBox.result['vlanInterfaces']) > 0:
                newStationOpts['vlanInterfaces'] = stationBox.result['vlanInterfaces']
            if len(stationBox.result['privateDirectory']) > 0:
                newStationOpts['privateDirectory'] = stationBox.result['privateDirectory']
            name = widget['text']
            x, y = self.canvas.coords(self.selection)
            range = self.getRange(newStationOpts, 'Station')
            self.canvas.coords(self.range[name],
                               x - range, y - range,
                               x + range, y + range)
            self.stationOpts[name] = newStationOpts
            info( 'New station details for ' + name + ' = ' + str(newStationOpts), '\n' )

    def switchDetails( self, _ignore=None ):
        if ( self.selection is None or
             self.net is not None or
             self.selection not in self.itemToWidget ):
            return
        widget = self.itemToWidget[ self.selection ]
        name = widget[ 'text' ]
        tags = self.canvas.gettags( self.selection )
        if 'Switch' not in tags:
            return

        prefDefaults = self.switchOpts[name]
        switchBox = SwitchDialog(self, title='Switch Details', prefDefaults=prefDefaults)
        self.master.wait_window(switchBox.top)
        if switchBox.result:
            newSwitchOpts = {'nodeNum':self.switchOpts[name]['nodeNum']}
            newSwitchOpts['switchType'] = switchBox.result['switchType']
            newSwitchOpts['controllers'] = self.switchOpts[name]['controllers']
            if len(switchBox.result['startCommand']) > 0:
                newSwitchOpts['startCommand'] = switchBox.result['startCommand']
            if len(switchBox.result['stopCommand']) > 0:
                newSwitchOpts['stopCommand'] = switchBox.result['stopCommand']
            if len(switchBox.result['dpctl']) > 0:
                newSwitchOpts['dpctl'] = switchBox.result['dpctl']
            if len(switchBox.result['dpid']) > 0:
                newSwitchOpts['dpid'] = switchBox.result['dpid']
            if len(switchBox.result['hostname']) > 0:
                newSwitchOpts['hostname'] = switchBox.result['hostname']
                name = switchBox.result['hostname']
                widget[ 'text' ] = name
            if len(switchBox.result['externalInterfaces']) > 0:
                newSwitchOpts['externalInterfaces'] = switchBox.result['externalInterfaces']
            newSwitchOpts['switchIP'] = switchBox.result['switchIP']
            newSwitchOpts['sflow'] = switchBox.result['sflow']
            newSwitchOpts['netflow'] = switchBox.result['netflow']
            self.switchOpts[name] = newSwitchOpts
            info( 'New switch details for ' + name + ' = ' + str(newSwitchOpts), '\n' )

    def apDetails(self, _ignore=None):
        if (self.selection is None or
            #self.net is not None or
            self.selection not in self.itemToWidget):
            return
        widget = self.itemToWidget[self.selection]
        name = widget['text']
        tags = self.canvas.gettags(self.selection)
        if 'AP' not in tags:
            return

        prefDefaults = self.apOpts[name]
        apBox = APDialog(self, title='Access Point Details', prefDefaults=prefDefaults)
        self.master.wait_window(apBox.top)
        if apBox.result:
            newAPOpts = {'nodeNum':self.apOpts[name]['nodeNum']}
            newAPOpts['apType'] = apBox.result['apType']
            newAPOpts['authentication'] = apBox.result['authentication']
            newAPOpts['passwd'] = apBox.result['passwd']
            newAPOpts['mode'] = apBox.result['mode']
            newAPOpts['range'] = apBox.result['range']
            newAPOpts['wlans'] = int(apBox.result['wlans'])
            newAPOpts['controllers'] = self.apOpts[name]['controllers']
            if len(apBox.result['startCommand']) > 0:
                newAPOpts['startCommand'] = apBox.result['startCommand']
            if len(apBox.result['stopCommand']) > 0:
                newAPOpts['stopCommand'] = apBox.result['stopCommand']
            if len(apBox.result['dpctl']) > 0:
                newAPOpts['dpctl'] = apBox.result['dpctl']
            if len(apBox.result['dpid']) > 0:
                newAPOpts['dpid'] = apBox.result['dpid']
            if len(apBox.result['ssid']) > 0:
                newAPOpts['ssid'] = apBox.result['ssid']
            if len(apBox.result['channel']) > 0:
                newAPOpts['channel'] = apBox.result['channel']
            if len(apBox.result['hostname']) > 0:
                newAPOpts['hostname'] = apBox.result['hostname']
                name = apBox.result['hostname']
                widget[ 'text' ] = name
            if len(apBox.result['externalInterfaces']) > 0:
                newAPOpts['externalInterfaces'] = apBox.result['externalInterfaces']
            newAPOpts['apIP'] = apBox.result['apIP']
            newAPOpts['sflow'] = apBox.result['sflow']
            newAPOpts['netflow'] = apBox.result['netflow']
            self.apOpts[name] = newAPOpts
            name = widget['text']
            x, y = self.canvas.coords(self.selection)
            range = self.getRange(newAPOpts, 'AP')
            self.canvas.coords(self.range[name],
                               x - range, y - range,
                               x + range, y + range)

            if self.net:
                node = self.net.getNodeByName(newAPOpts['hostname'])
                self.setMode(node, newAPOpts['mode'])
                self.setChannel(node, newAPOpts['channel'])

            info( 'New access point details for ' + name + ' = ' + str(newAPOpts), '\n' )

    def setChannel(self, node, channel):
        node.wintfs[0].setAPChannel(int(channel))
        if isinstance(node.wintfs[0], master):
            node.wintfs[0].set_tc_ap()
        ConfigMobLinks()

    def setMode(self, node, mode):
        node.wintfs[0].setMode(mode)

    def linkUp( self ):
        if ( self.selection is None or
             self.net is None):
            return
        link = self.selection
        linkDetail =  self.links[link]
        src = linkDetail['src']
        dst = linkDetail['dest']
        srcName, dstName = src['text'], dst['text']
        self.net.configLinkStatus(srcName, dstName, 'up')
        self.canvas.itemconfig(link, dash=())

    def linkDown( self ):
        if ( self.selection is None or
             self.net is None):
            return
        link = self.selection
        linkDetail =  self.links[link]
        src = linkDetail['src']
        dst = linkDetail['dest']
        srcName, dstName = src[ 'text' ], dst[ 'text' ]
        self.net.configLinkStatus(srcName, dstName, 'down')
        self.canvas.itemconfig(link, dash=(4, 4))

    def linkDetails( self, _ignore=None ):
        if ( self.selection is None or
             self.net is not None):
            return
        link = self.selection
        linkDetail = self.links[link]
        nodeSrc = ''
        nodeDest = ''

        for widget in self.widgetToItem:
            nodeName = widget['text']
            if nodeName == linkDetail['src']['text']:
                tags = self.canvas.gettags(self.widgetToItem[widget])
                if 'AP' in tags:
                    nodeSrc = self.apOpts[nodeName]
                elif 'Station' in tags:
                    nodeSrc = self.stationOpts[nodeName]
            else:
                tags = self.canvas.gettags(self.widgetToItem[widget])
                if 'AP' in tags:
                    nodeDest = self.apOpts[nodeName]
                elif 'Station' in tags:
                    nodeDest = self.stationOpts[nodeName]

        linkopts = linkDetail['linkOpts']
        linkBox = LinkDialog(self, title='Link Details',
                             linkDefaults=linkopts, links=linkDetail,
                             src=nodeSrc, dest=nodeDest)
        if linkBox.result is not None:
            linkDetail['linkOpts'] = linkBox.result
            info( 'New link details = ' + str(linkBox.result), '\n' )

    def prefDetails( self ):
        prefDefaults = self.appPrefs
        prefBox = PrefsDialog(self, title='Preferences', prefDefaults=prefDefaults)
        info( 'New Prefs = ' + str(prefBox.result), '\n' )
        if prefBox.result:
            self.appPrefs = prefBox.result

    def controllerDetails( self ):
        if ( self.selection is None or
             self.net is not None or
             self.selection not in self.itemToWidget ):
            return
        widget = self.itemToWidget[ self.selection ]
        name = widget[ 'text' ]
        tags = self.canvas.gettags( self.selection )
        oldName = name
        if 'Controller' not in tags:
            return

        ctrlrBox = ControllerDialog(self, title='Controller Details', ctrlrDefaults=self.controllers[name])
        if ctrlrBox.result:
            # debug( 'Controller is ' + ctrlrBox.result[0], '\n' )
            if len(ctrlrBox.result['hostname']) > 0:
                name = ctrlrBox.result['hostname']
                widget[ 'text' ] = name
            else:
                ctrlrBox.result['hostname'] = name
            self.controllers[name] = ctrlrBox.result
            info( 'New controller details for ' + name + ' = ' + str(self.controllers[name]), '\n' )
            # Find references to controller and change name
            if oldName != name:
                for widget in self.widgetToItem:
                    switchName = widget[ 'text' ]
                    tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                    if 'Switch' in tags:
                        switch = self.switchOpts[switchName]
                        if oldName in switch['controllers']:
                            switch['controllers'].remove(oldName)
                            switch['controllers'].append(name)

    def listBridge( self, _ignore=None ):
        if ( self.selection is None or
             self.net is None or
             self.selection not in self.itemToWidget ):
            return
        name = self.itemToWidget[ self.selection ][ 'text' ]
        tags = self.canvas.gettags( self.selection )

        if name not in self.net.nameToNode:
            return
        if 'Switch' in tags or 'LegacySwitch' in tags:
            call(["xterm -T 'Bridge Details' -sb -sl 2000 -e 'ovs-vsctl list bridge " + name + "; read -p \"Press Enter to close\"' &"], shell=True)

    @staticmethod
    def ovsShow( _ignore=None ):
        call(["xterm -T 'OVS Summary' -sb -sl 2000 -e 'ovs-vsctl show; read -p \"Press Enter to close\"' &"], shell=True)

    @staticmethod
    def rootTerminal( _ignore=None ):
        call(["xterm -T 'Root Terminal' -sb -sl 2000 &"], shell=True)

    # Model interface
    #
    # Ultimately we will either want to use a topo or
    # mininet object here, probably.

    def addLink( self, source, dest, linktype='data', linkopts=None ):
        "Add link to model."
        if linkopts is None:
            linkopts = {}
        source.links[ dest ] = self.link
        dest.links[ source ] = self.link
        self.links[ self.link ] = {'type' :linktype,
                                   'src':source,
                                   'dest':dest,
                                   'linkOpts':linkopts}

    def deleteLink( self, link ):
        "Delete link from model."
        pair = self.links.get( link, None )
        if pair is not None:
            source=pair['src']
            dest=pair['dest']
            del source.links[ dest ]
            del dest.links[ source ]
            stags = self.canvas.gettags( self.widgetToItem[ source ] )
            # dtags = self.canvas.gettags( self.widgetToItem[ dest ] )
            ltags = self.canvas.gettags( link )

            if 'control' in ltags:
                controllerName = ''
                switchName = ''
                if 'Controller' in stags:
                    controllerName = source[ 'text' ]
                    switchName = dest[ 'text' ]
                else:
                    controllerName = dest[ 'text' ]
                    switchName = source[ 'text' ]

                if controllerName in self.switchOpts[switchName]['controllers']:
                    self.switchOpts[switchName]['controllers'].remove(controllerName)

        if link is not None:
            del self.links[ link ]

    def deleteNode( self, item ):
        "Delete node (and its links) from model."

        widget = self.itemToWidget[item]
        tags = self.canvas.gettags(item)

        if 'Controller' in tags:
            # remove from switch controller lists
            for serachwidget in self.widgetToItem:
                name = serachwidget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ serachwidget ] )
                if 'Switch' in tags:
                    if widget['text'] in self.switchOpts[name]['controllers']:
                        self.switchOpts[name]['controllers'].remove(widget['text'])
                tags = []

        if 'AP' in tags:
            self.deleteItem(self.range[widget['text']])

        for link in widget.links.values():
            # Delete from view and model
            self.deleteItem( link )
        del self.itemToWidget[ item ]
        del self.widgetToItem[ widget ]

    def buildNodes( self, net):
        # Make nodes
        info( "Getting Nodes.\n" )
        for widget in self.widgetToItem:
            name = widget['text']
            tags = self.canvas.gettags( self.widgetToItem[ widget ] )
            # debug( name+' has '+str(tags), '\n' )

            if 'Switch' in tags:
                opts = self.switchOpts[name]
                # debug( str(opts), '\n' )

                # Create the correct switch class
                switchParms = {}
                if 'dpctl' in opts:
                    switchParms['listenPort'] = int(opts['dpctl'])
                if 'dpid' in opts:
                    switchParms['dpid'] = opts['dpid']
                if opts['switchType'] == 'default':
                    if self.appPrefs['switchType'] == 'user':
                        switchClass = CustomUserSwitch
                    elif self.appPrefs['switchType'] == 'userns':
                        switchParms['inNamespace'] = True
                        switchClass = CustomUserSwitch
                    else:
                        switchClass = customOvs
                elif opts['switchType'] == 'user':
                    switchClass = CustomUserSwitch
                elif opts['switchType'] == 'userns':
                    switchClass = CustomUserSwitch
                    switchParms['inNamespace'] = True
                else:
                    switchClass = customOvs

                if switchClass == customOvs:
                    # Set OpenFlow versions
                    self.openFlowVersions = []
                    if self.appPrefs['openFlowVersions']['ovsOf10'] == '1':
                        self.openFlowVersions.append('OpenFlow10')
                    if self.appPrefs['openFlowVersions']['ovsOf11'] == '1':
                        self.openFlowVersions.append('OpenFlow11')
                    if self.appPrefs['openFlowVersions']['ovsOf12'] == '1':
                        self.openFlowVersions.append('OpenFlow12')
                    if self.appPrefs['openFlowVersions']['ovsOf13'] == '1':
                        self.openFlowVersions.append('OpenFlow13')
                    protoList = ",".join(self.openFlowVersions)
                    switchParms['protocols'] = protoList
                newSwitch = net.addSwitch( name , cls=switchClass, **switchParms)

                # Some post startup config
                if switchClass == CustomUserSwitch:
                    if 'switchIP' in opts:
                        if len(opts['switchIP']) > 0:
                            newSwitch.setSwitchIP(opts['switchIP'])
                if switchClass == customOvs:
                    if 'switchIP' in opts:
                        if len(opts['switchIP']) > 0:
                            newSwitch.setSwitchIP(opts['switchIP'])

                # Attach external interfaces
                if 'externalInterfaces' in opts:
                    for extInterface in opts['externalInterfaces']:
                        if self.checkIntf(extInterface):
                            Intf( extInterface, node=newSwitch )
            elif 'AP' in tags:
                opts = self.apOpts[name]
                # debug( str(opts), '\n' )

                # Create the correct switch class
                apParms = {}
                if 'dpctl' in opts:
                    apParms['listenPort'] = int(opts['dpctl'])
                if 'dpid' in opts:
                    apParms['dpid'] = opts['dpid']
                if 'ssid' in opts:
                    apParms['ssid'] = opts['ssid']
                if 'channel' in opts:
                    apParms['channel'] = opts['channel']
                if 'range' in opts:
                    node_ = self.apOpts[name]
                    range = self.getRange(node_, 'AP')
                    apParms['range'] = range
                if 'mode' in opts:
                    apParms['mode'] = opts['mode']
                if 'wlans' in opts:
                    apParms['wlans'] = opts['wlans']
                if 'authentication' in opts:
                    apParms['authentication'] = opts['authentication']
                if 'passwd' in opts:
                    apParms['passwd']=opts['passwd']
                if opts['apType'] == 'default':
                    if self.appPrefs['apType'] == 'user':
                        apClass = CustomUserAP
                    elif self.appPrefs['apType'] == 'userns':
                        apParms['inNamespace'] = True
                        apClass = CustomUserAP
                    else:
                        apClass = customOvsAP
                elif opts['apType'] == 'user':
                    apClass = CustomUserAP
                elif opts['apType'] == 'userns':
                    apClass = CustomUserAP
                    apParms['inNamespace'] = True
                else:
                    apClass = customOvsAP

                if apClass == customOvsAP:
                    # Set OpenFlow versions
                    self.openFlowVersions = []
                    if self.appPrefs['openFlowVersions']['ovsOf10'] == '1':
                        self.openFlowVersions.append('OpenFlow10')
                    if self.appPrefs['openFlowVersions']['ovsOf11'] == '1':
                        self.openFlowVersions.append('OpenFlow11')
                    if self.appPrefs['openFlowVersions']['ovsOf12'] == '1':
                        self.openFlowVersions.append('OpenFlow12')
                    if self.appPrefs['openFlowVersions']['ovsOf13'] == '1':
                        self.openFlowVersions.append('OpenFlow13')
                    protoList = ",".join(self.openFlowVersions)
                    apParms['protocols'] = protoList

                x1, y1 = self.canvas.coords(self.widgetToItem[widget])
                pos = x1, y1, 0

                newAP = net.addAccessPoint( name , cls=apClass,
                                            position=pos, **apParms)

                # Some post startup config
                if apClass == CustomUserAP:
                    if 'switchIP' in opts:
                        if len(opts['apIP']) > 0:
                            newAP.setAPIP(opts['switchIP'])
                if apClass == customOvsAP:
                    if 'apIP' in opts:
                        if len(opts['apIP']) > 0:
                            newAP.setAPIP(opts['apIP'])

                # Attach external interfaces
                if 'externalInterfaces' in opts:
                    for extInterface in opts['externalInterfaces']:
                        if self.checkIntf(extInterface):
                            Intf( extInterface, node=newAP )
            elif 'LegacySwitch' in tags:
                newSwitch = net.addSwitch( name , cls=LegacySwitch)
            elif 'LegacyRouter' in tags:
                newSwitch = net.addHost( name , cls=LegacyRouter)
            elif 'Host' in tags:
                opts = self.hostOpts[name]
                # debug( str(opts), '\n' )
                ip = None
                defaultRoute = None
                if 'defaultRoute' in opts and len(opts['defaultRoute']) > 0:
                    defaultRoute = 'via '+opts['defaultRoute']
                if 'ip' in opts and len(opts['ip']) > 0:
                    ip = opts['ip']
                else:
                    nodeNum = self.hostOpts[name]['nodeNum']
                    ipBaseNum, prefixLen = netParse( self.appPrefs['ipBase'] )
                    ip = ipAdd(i=nodeNum, prefixLen=prefixLen, ipBaseNum=ipBaseNum)

                # Create the correct host class
                if 'cores' in opts or 'cpu' in opts:
                    if 'privateDirectory' in opts:
                        hostCls = partial( CPULimitedHost,
                                           privateDirs=opts['privateDirectory'] )
                    else:
                        hostCls=CPULimitedHost
                else:
                    if 'privateDirectory' in opts:
                        hostCls = partial( Host,
                                           privateDirs=opts['privateDirectory'] )
                    else:
                        hostCls=Host
                debug( hostCls, '\n' )
                newHost = net.addHost( name, cls=hostCls, ip=ip,
                                       defaultRoute=defaultRoute )

                # Set the CPULimitedHost specific options
                if 'cores' in opts:
                    newHost.setCPUs(cores = opts['cores'])
                if 'cpu' in opts:
                    newHost.setCPUFrac(f=opts['cpu'], sched=opts['sched'])

                # Attach external interfaces
                if 'externalInterfaces' in opts:
                    for extInterface in opts['externalInterfaces']:
                        if self.checkIntf(extInterface):
                            Intf( extInterface, node=newHost )
                if 'vlanInterfaces' in opts:
                    if len(opts['vlanInterfaces']) > 0:
                        info( 'Checking that OS is VLAN prepared\n' )
                        self.pathCheck('vconfig', moduleName='vlan package')
                        moduleDeps( add='8021q' )
            elif 'Station' in tags:
                opts = self.stationOpts[name]
                # debug( str(opts), '\n' )
                ip = None
                defaultRoute = None
                if 'defaultRoute' in opts and len(opts['defaultRoute']) > 0:
                    defaultRoute = 'via '+opts['defaultRoute']
                if 'ip' in opts and len(opts['ip']) > 0:
                    ip = opts['ip']
                else:
                    nodeNum = self.stationOpts[name]['nodeNum']
                    ipBaseNum, prefixLen = netParse( self.appPrefs['ipBase'] )
                    ip = ipAdd(i=nodeNum, prefixLen=prefixLen, ipBaseNum=ipBaseNum)

                x1, y1 = self.canvas.coords(self.widgetToItem[widget])
                pos = x1, y1, 0

                # Create the correct host class
                if 'cores' in opts or 'cpu' in opts:
                    if 'privateDirectory' in opts:
                        staCls = partial( CPULimitedStation,
                                          privateDirs=opts['privateDirectory'] )
                    else:
                        staCls=CPULimitedStation
                else:
                    if 'privateDirectory' in opts:
                        staCls = partial( Station,
                                          privateDirs=opts['privateDirectory'] )
                    else:
                        staCls=Station
                debug( staCls, '\n' )
                newStation = net.addStation( name, cls=staCls, position=pos,
                                             ip=ip, defaultRoute=defaultRoute )
                # Set the CPULimitedHost specific options
                if 'cores' in opts:
                    newStation.setCPUs(cores = opts['cores'])
                if 'cpu' in opts:
                    newStation.setCPUFrac(f=opts['cpu'], sched=opts['sched'])

                # Attach external interfaces
                if 'externalInterfaces' in opts:
                    for extInterface in opts['externalInterfaces']:
                        if self.checkIntf(extInterface):
                            Intf( extInterface, node=newStation )
                if 'vlanInterfaces' in opts:
                    if len(opts['vlanInterfaces']) > 0:
                        info( 'Checking that OS is VLAN prepared\n' )
                        self.pathCheck('vconfig', moduleName='vlan package')
                        moduleDeps( add='8021q' )
            elif 'Controller' in tags:
                opts = self.controllers[name]

                # Get controller info from panel
                controllerType = opts['controllerType']
                if 'controllerProtocol' in opts:
                    controllerProtocol = opts['controllerProtocol']
                else:
                    controllerProtocol = 'tcp'
                    opts['controllerProtocol'] = 'tcp'
                controllerIP = opts['remoteIP']
                controllerPort = opts['remotePort']

                # Make controller
                info( 'Getting controller selection:'+controllerType, '\n' )
                if controllerType == 'remote':
                    net.addController(name=name,
                                      controller=RemoteController,
                                      ip=controllerIP,
                                      protocol=controllerProtocol,
                                      port=controllerPort)
                elif controllerType == 'inband':
                    net.addController(name=name,
                                      controller=InbandController,
                                      ip=controllerIP,
                                      protocol=controllerProtocol,
                                      port=controllerPort)
                elif controllerType == 'ovsc':
                    net.addController(name=name,
                                      controller=OVSController,
                                      protocol=controllerProtocol,
                                      port=controllerPort)
                else:
                    net.addController(name=name,
                                      controller=Controller,
                                      protocol=controllerProtocol,
                                      port=controllerPort)

            else:
                raise Exception( "Cannot create mystery node: " + name )

    @staticmethod
    def pathCheck( *args, **kwargs ):
        "Make sure each program in *args can be found in $PATH."
        moduleName = kwargs.get( 'moduleName', 'it' )
        for arg in args:
            if not quietRun( 'which ' + arg ):
                messagebox.showerror(title="Error",
                          message= 'Cannot find required executable %s.\n' % arg +
                          'Please make sure that %s is installed ' % moduleName +
                          'and available in your $PATH.' )

    def buildLinks( self, net):
        # Make links
        info( "Getting Links.\n" )
        for key,link in self.links.items():
            tags = self.canvas.gettags(key)
            if 'data' in tags:
                src=link['src']
                dst=link['dest']
                linkopts=link['linkOpts']
                srcName, dstName = src[ 'text' ], dst[ 'text' ]
                srcNode, dstNode = net.nameToNode[ srcName ], net.nameToNode[ dstName ]
                if linkopts:
                    net.addLink(srcNode, dstNode, cls=TCLink, **linkopts)
                else:
                    # debug( str(srcNode) )
                    # debug( str(dstNode), '\n' )
                    net.addLink(srcNode, dstNode)
                self.canvas.itemconfig(key, dash=())

    def build(self):
        "Build network based on our topology."
        dpctl = None

        if len(self.appPrefs['dpctl']) > 0:
            dpctl = int(self.appPrefs['dpctl'])
        link = TCLink

        wmediumd_mode = None
        if self.appPrefs['enableWmediumd'] == '1':
            link = wmediumd
            wmediumd_mode = interference

        net = Mininet_wifi(topo=None,
                           listenPort=dpctl,
                           build=False,
                           link=link,
                           wmediumd_mode=wmediumd_mode,
                           ipBase=self.appPrefs['ipBase'])

        self.buildNodes(net)
        net.configureNodes()
        self.buildLinks(net)

        # Build network (we have to do this separately at the moment )
        net.build()

        return net

    def postStartSetup(self):
        # Setup host details
        for widget in self.widgetToItem:
            name = widget[ 'text' ]
            tags = self.canvas.gettags( self.widgetToItem[ widget ] )
            if 'Host' in tags:
                newHost = self.net.get(name)
                opts = self.hostOpts[name]
                # Attach vlan interfaces
                if 'vlanInterfaces' in opts:
                    for vlanInterface in opts['vlanInterfaces']:
                        info( 'adding vlan interface '+vlanInterface[1], '\n' )
                        newHost.cmdPrint('ifconfig '+name+'-eth0.'+vlanInterface[1]+' '+vlanInterface[0])
                # Run User Defined Start Command
                if 'startCommand' in opts:
                    newHost.cmdPrint(opts['startCommand'])
            elif 'Station' in tags:
                newStation = self.net.get(name)
                opts = self.stationOpts[name]
                # Attach vlan interfaces
                if 'vlanInterfaces' in opts:
                    for vlanInterface in opts['vlanInterfaces']:
                        info( 'adding vlan interface '+vlanInterface[1], '\n' )
                        newStation.cmdPrint('ifconfig '+name+'-wlan0.'+vlanInterface[1]+' '+vlanInterface[0])
                # Run User Defined Start Command
                if 'startCommand' in opts:
                    newStation.cmdPrint(opts['startCommand'])
            if 'Switch' in tags:
                newNode = self.net.get(name)
                opts = self.switchOpts[name]
                # Run User Defined Start Command
                if 'startCommand' in opts:
                    newNode.cmdPrint(opts['startCommand'])
            elif 'AP' in tags:
                newNode = self.net.get(name)
                opts = self.apOpts[name]
                # Run User Defined Start Command
                if 'startCommand' in opts:
                    newNode.cmdPrint(opts['startCommand'])

        # Configure NetFlow
        nflowValues = self.appPrefs['netflow']
        if len(nflowValues['nflowTarget']) > 0:
            nflowEnabled = False
            nflowSwitches = ''
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )

                if 'Switch' in tags or 'AP' in tags:
                    opts = self.switchOpts[name]
                    if 'AP' in tags:
                        opts = self.apOpts[name]
                    if 'netflow' in opts:
                        if opts['netflow'] == '1':
                            info( name+' has Netflow enabled\n' )
                            nflowSwitches = nflowSwitches+' -- set Bridge '+name+' netflow=@MiniEditNF'
                            nflowEnabled=True
            if nflowEnabled:
                nflowCmd = 'ovs-vsctl -- --id=@MiniEditNF create NetFlow '+ 'target=\\\"'+nflowValues['nflowTarget']+'\\\" '+ 'active-timeout='+nflowValues['nflowTimeout']
                if nflowValues['nflowAddId'] == '1':
                    nflowCmd = nflowCmd + ' add_id_to_interface=true'
                else:
                    nflowCmd = nflowCmd + ' add_id_to_interface=false'
                info( 'cmd = '+nflowCmd+nflowSwitches, '\n' )
                call(nflowCmd+nflowSwitches, shell=True)

            else:
                info( 'No switches with Netflow\n' )
        else:
            info( 'No NetFlow targets specified.\n' )

        # Configure sFlow
        sflowValues = self.appPrefs['sflow']
        if len(sflowValues['sflowTarget']) > 0:
            sflowEnabled = False
            sflowSwitches = ''
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )

                if 'Switch' in tags or 'AP' in tags:
                    opts = self.switchOpts[name]
                    if 'AP' in tags:
                        opts = self.apOpts[name]
                    if 'sflow' in opts:
                        if opts['sflow'] == '1':
                            info( name+' has sflow enabled\n' )
                            sflowSwitches = sflowSwitches+' -- set Bridge '+name+' sflow=@MiniEditSF'
                            sflowEnabled=True
            if sflowEnabled:
                sflowCmd = 'ovs-vsctl -- --id=@MiniEditSF create sFlow '+ 'target=\\\"'+sflowValues['sflowTarget']+'\\\" '+ 'header='+sflowValues['sflowHeader']+' '+ 'sampling='+sflowValues['sflowSampling']+' '+ 'polling='+sflowValues['sflowPolling']
                info( 'cmd = '+sflowCmd+sflowSwitches, '\n' )
                call(sflowCmd+sflowSwitches, shell=True)

            else:
                info( 'No switches with sflow\n' )
        else:
            info( 'No sFlow targets specified.\n' )

        ## NOTE: MAKE SURE THIS IS LAST THING CALLED
        # Start the CLI if enabled
        if self.appPrefs['startCLI'] == '1':
            info( "\n\n NOTE: PLEASE REMEMBER TO EXIT THE CLI BEFORE YOU PRESS THE STOP BUTTON. Not exiting will prevent MiniEdit from quitting and will prevent you from starting the network again during this session.\n\n")
            CLI(self.net)

    def start( self ):
        "Start network."
        if self.net is None:
            self.net = self.build()

            # Since I am going to inject per switch controllers.
            # I can't call net.start().  I have to replicate what it
            # does and add the controller options.
            #self.net.start()
            info( '**** Starting %s controllers\n' % len( self.net.controllers ) )
            for controller in self.net.controllers:
                info( str(controller) + ' ')
                controller.start()
            info('\n')
            info( '**** Starting %s switches\n' % len( self.net.switches ) )
            for switch in self.net.switches:
                info( switch.name + ' ')
                switch.start( self.net.controllers )
            info('**** Starting %s aps\n' % len(self.net.aps))
            for ap in self.net.aps:
                info(ap.name + ' ')
                ap.start(self.net.controllers)
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                if 'Switch' in tags:
                    opts = self.switchOpts[name]
                    switchControllers = []
                    for ctrl in opts['controllers']:
                        switchControllers.append(self.net.get(ctrl))
                    info( name + ' ')
                    # Figure out what controllers will manage this switch
                    self.net.get(name).start( switchControllers )
                if 'LegacySwitch' in tags:
                    self.net.get(name).start( [] )
                    info( name + ' ')
            info('\n')

            self.postStartSetup()

    def stop( self ):
        "Stop network."
        if self.net is not None:
            # Stop host details
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                if 'Host' in tags:
                    newHost = self.net.get(name)
                    opts = self.hostOpts[name]
                    # Run User Defined Stop Command
                    if 'stopCommand' in opts:
                        newHost.cmdPrint(opts['stopCommand'])
                if 'Station' in tags:
                    newStation = self.net.get(name)
                    opts = self.stationOpts[name]
                    # Run User Defined Stop Command
                    if 'stopCommand' in opts:
                        newStation.cmdPrint(opts['stopCommand'])
                if 'Switch' in tags:
                    newNode = self.net.get(name)
                    opts = self.switchOpts[name]
                    # Run User Defined Stop Command
                    if 'stopCommand' in opts:
                        newNode.cmdPrint(opts['stopCommand'])

            self.net.stop()

        cleanUpScreens()

        Mac80211Hwsim.hwsim_ids = []
        Mobility.aps = []
        Mobility.stations = []
        Mobility.mobileNodes = []

        self.net = None

    def do_linkPopup(self, event):
        # display the popup menu
        if self.net is None:
            try:
                self.linkPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.linkPopup.grab_release()
        else:
            try:
                self.linkRunPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.linkRunPopup.grab_release()

    def do_controllerPopup(self, event):
        # display the popup menu
        if self.net is None:
            try:
                self.controllerPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.controllerPopup.grab_release()

    def do_legacyRouterPopup(self, event):
        # display the popup menu
        if self.net is not None:
            try:
                self.legacyRouterRunPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.legacyRouterRunPopup.grab_release()

    def do_hostPopup(self, event):
        # display the popup menu
        if self.net is None:
            try:
                self.hostPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.hostPopup.grab_release()
        else:
            try:
                self.hostRunPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.hostRunPopup.grab_release()

    def do_stationPopup(self, event):
        # display the popup menu
        if self.net is None:
            try:
                self.stationPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.stationPopup.grab_release()
        else:
            try:
                self.stationRunPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.stationRunPopup.grab_release()

    def do_legacySwitchPopup(self, event):
        # display the popup menu
        if self.net is not None:
            try:
                self.switchRunPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.switchRunPopup.grab_release()

    def do_switchPopup(self, event):
        # display the popup menu
        if self.net is None:
            try:
                self.switchPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.switchPopup.grab_release()
        else:
            try:
                self.switchRunPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.switchRunPopup.grab_release()

    def do_apPopup(self, event):
        # display the popup menu
        if self.net is None:
            try:
                self.apPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.apPopup.grab_release()
        else:
            try:
                self.apRunPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.apRunPopup.grab_release()

    def xterm( self, _ignore=None ):
        "Make an xterm when a button is pressed."
        if (self.selection is None or
            self.net is None or
            self.selection not in self.itemToWidget):
            return
        name = self.itemToWidget[ self.selection ][ 'text' ]
        if name not in self.net.nameToNode:
            return
        term = makeTerm( self.net.nameToNode[ name ], 'Host', term=self.appPrefs['terminalType'] )
        if version.parse(MININET_VERSION) > version.parse('2.0'):
            self.net.terms += term
        else:
            self.net.terms.append(term)

    def iperf( self, _ignore=None ):
        "Make an xterm when a button is pressed."
        if ( self.selection is None or
             self.net is None or
             self.selection not in self.itemToWidget ):
            return
        name = self.itemToWidget[ self.selection ][ 'text' ]
        if name not in self.net.nameToNode:
            return
        self.net.nameToNode[ name ].cmd( 'iperf -s -p 5001 &' )

    ### BELOW HERE IS THE TOPOLOGY IMPORT CODE ###

    def parseArgs( self ):
        """Parse command-line args and return options object.
           returns: opts parse options dict"""

        if '--custom' in sys.argv:
            index = sys.argv.index( '--custom' )
            if len( sys.argv ) > index + 1:
                filename = sys.argv[ index + 1 ]
                self.parseCustomFile( filename )
            else:
                raise Exception( 'Custom file name not found' )

        desc = ( "The %prog utility creates Mininet network from the\n"
                 "command line. It can create parametrized topologies,\n"
                 "invoke the Mininet CLI, and run tests." )

        usage = ( '%prog [options]\n'
                  '(type %prog -h for details)' )

        opts = OptionParser( description=desc, usage=usage )

        addDictOption( opts, TOPOS, TOPODEF, 'topo' )
        addDictOption( opts, LINKS, LINKDEF, 'link' )

        opts.add_option( '--custom', type='string', default=None,
                         help='read custom topo and node params from .py' +
                         'file' )

        self.options, self.args = opts.parse_args()
        # We don't accept extra arguments after the options
        if self.args:
            opts.print_help()
            sys.exit()

    def setCustom( self, name, value ):
        "Set custom parameters for MininetRunner."
        if name in ( 'topos', 'switches', 'aps', 'hosts', 'stations', 'controllers' ):
            # Update dictionaries
            param = name.upper()
            globals()[ param ].update( value )
        elif name == 'validate':
            # Add custom validate function
            self.validate = value
        else:
            # Add or modify global variable or class
            globals()[ name ] = value

    def parseCustomFile( self, fileName ):
        "Parse custom file and add params before parsing cmd-line options."
        customs = {}
        if os.path.isfile(fileName):
            with open(fileName, 'r') as f:
                exec(f.read())  # pylint: disable=exec-used
            for name, val in customs.items():
                self.setCustom(name, val)
        else:
            raise Exception('could not find custom file: %s' % fileName)

    def importTopo( self ):
        info( 'topo='+self.options.topo, '\n' )
        if self.options.topo == 'none':
            return
        self.newTopology()
        topo = buildTopo( TOPOS, self.options.topo )
        link = customClass( LINKS, self.options.link )
        importNet = Mininet_wifi(topo=topo, build=False, link=link)
        importNet.build()

        c = self.canvas
        rowIncrement = 100
        currentY = 100

        # Add Controllers
        info( 'controllers:'+str(len(importNet.controllers)), '\n' )
        for controller in importNet.controllers:
            name = controller.name
            x = self.controllerCount*100+100
            self.addNode('Controller', self.controllerCount,
                 float(x), float(currentY), name=name)
            icon = self.findWidgetByName(name)
            icon.bind('<Button-3>', self.do_controllerPopup )
            ctrlr = { 'controllerType': 'ref',
                      'hostname': name,
                      'controllerProtocol': controller.protocol,
                      'remoteIP': controller.ip,
                      'remotePort': controller.port}
            self.controllers[name] = ctrlr



        currentY = currentY + rowIncrement
        # Add switches
        info( 'switches:'+str(len(importNet.switches)), '\n' )
        columnCount = 0
        for switch in importNet.switches:
            name = switch.name
            self.switchOpts[name] = {}
            self.switchOpts[name]['nodeNum'] = self.switchCount
            self.switchOpts[name]['hostname'] = name
            self.switchOpts[name]['switchType'] = 'default'
            self.switchOpts[name]['controllers'] = []

            x = columnCount*100+100
            self.addNode('Switch', self.switchCount,
                 float(x), float(currentY), name=name)
            icon = self.findWidgetByName(name)
            icon.bind('<Button-3>', self.do_switchPopup )
            # Now link to controllers
            for controller in importNet.controllers:
                self.switchOpts[name]['controllers'].append(controller.name)
                dest = self.findWidgetByName(controller.name)
                dx, dy = c.coords( self.widgetToItem[ dest ] )
                self.link = c.create_line(float(x),
                                          float(currentY),
                                          dx,
                                          dy,
                                          width=4,
                                          fill='red',
                                          dash=(6, 4, 2, 4),
                                          tag='link' )
                c.itemconfig(self.link, tags=c.gettags(self.link)+('control',))
                self.addLink( icon, dest, linktype='control' )
                self.createControlLinkBindings()
                self.link = self.linkWidget = None
            if columnCount == 9:
                columnCount = 0
                currentY = currentY + rowIncrement
            else:
                columnCount =columnCount+1

        currentY = currentY + rowIncrement
        # Add switches
        info('aps:' + str(len(importNet.aps)), '\n')
        columnCount = 0
        for ap in importNet.aps:
            name = ap.name
            self.apOpts[name] = {}
            self.apOpts[name]['nodeNum'] = self.apCount
            self.apOpts[name]['hostname'] = name
            self.apOpts[name]['ssid'] = name + '-ssid'
            self.apOpts[name]['channel'] = '1'
            self.apOpts[name]['mode'] = 'g'
            self.apOpts[name]['range'] = 'default'
            self.apOpts[name]['authentication'] = 'none'
            self.apOpts[name]['passwd'] = ''
            self.apOpts[name]['apType'] = 'default'
            self.apOpts[name]['wlans'] = 1
            self.apOpts[name]['controllers'] = []

            x = columnCount * 100 + 100
            self.addNode('AP', self.apCount,
                         float(x), float(currentY), name=name)
            icon = self.findWidgetByName(name)
            icon.bind('<Button-3>', self.do_apPopup)
            # Now link to controllers
            for controller in importNet.controllers:
                self.switchOpts[name]['controllers'].append(controller.name)
                dest = self.findWidgetByName(controller.name)
                dx, dy = c.coords(self.widgetToItem[dest])
                self.link = c.create_line(float(x),
                                          float(currentY),
                                          dx,
                                          dy,
                                          width=4,
                                          fill='red',
                                          dash=(6, 4, 2, 4),
                                          tag='link')
                c.itemconfig(self.link, tags=c.gettags(self.link) + ('control',))
                self.addLink(icon, dest, linktype='control')
                self.createControlLinkBindings()
                self.link = self.linkWidget = None
            if columnCount == 9:
                columnCount = 0
                currentY = currentY + rowIncrement
            else:
                columnCount = columnCount + 1

        currentY = currentY + rowIncrement
        # Add hosts
        info( 'hosts:'+str(len(importNet.hosts)), '\n' )
        columnCount = 0
        for host in importNet.hosts:
            name = host.name
            self.hostOpts[name] = {'sched':'host'}
            self.hostOpts[name]['nodeNum']=self.hostCount
            self.hostOpts[name]['hostname']=name
            self.hostOpts[name]['ip']=host.IP()

            x = columnCount*100+100
            self.addNode('Host', self.hostCount,
                 float(x), float(currentY), name=name)
            icon = self.findWidgetByName(name)
            icon.bind('<Button-3>', self.do_hostPopup )
            if columnCount == 9:
                columnCount = 0
                currentY = currentY + rowIncrement
            else:
                columnCount =columnCount+1

        currentY = currentY + rowIncrement
        # Add hosts
        info('stations:' + str(len(importNet.stations)), '\n')
        columnCount = 0
        for station in importNet.stations:
            name = station.name
            self.stationOpts[name] = {'sched': 'station'}
            self.stationOpts[name]['nodeNum'] = self.stationCount
            self.stationOpts[name]['hostname'] = name
            self.stationOpts[name]['ip'] = station.IP()

            x = columnCount * 100 + 100
            self.addNode('Station', self.stationCount,
                         float(x), float(currentY), name=name)
            icon = self.findWidgetByName(name)
            icon.bind('<Button-3>', self.do_stationPopup)
            if columnCount == 9:
                columnCount = 0
                currentY = currentY + rowIncrement
            else:
                columnCount = columnCount + 1

        info( 'links:'+str(len(topo.links())), '\n' )
        #[('h1', 's3'), ('h2', 's4'), ('s3', 's4')]
        for link in topo.links():
            info( str(link), '\n' )
            srcNode = link[0]
            src = self.findWidgetByName(srcNode)
            sx, sy = self.canvas.coords( self.widgetToItem[ src ] )

            destNode = link[1]
            dest = self.findWidgetByName(destNode)
            dx, dy = self.canvas.coords( self.widgetToItem[ dest]  )

            params = topo.linkInfo( srcNode, destNode )
            info( 'Link Parameters='+str(params), '\n' )

            self.link = self.canvas.create_line( sx, sy, dx, dy, width=4,
                                             fill='blue', tag='link' )
            c.itemconfig(self.link, tags=c.gettags(self.link)+('data',))
            self.addLink( src, dest, linkopts=params )
            self.createDataLinkBindings()
            self.link = self.linkWidget = None

        importNet.stop()

def miniEditImages():
    "Create and return images for MiniEdit."

    # Image data. Git will be unhappy. However, the alternative
    # is to keep track of separate binary files, which is also
    # unappealing.

    return {
        'Select': BitmapImage(
            file='/usr/include/X11/bitmaps/left_ptr' ),

        'Switch': PhotoImage( data=r"""
R0lGODlhLgAgAPcAAB2ZxGq61imex4zH3RWWwmK41tzd3vn9/jCiyfX7/Q6SwFay0gBlmtnZ2snJ
yr+2tAuMu6rY6D6kyfHx8XO/2Uqszjmly6DU5uXz+JLN4uz3+kSrzlKx0ZeZm2K21BuYw67a6QB9
r+Xl5rW2uHW61On1+UGpzbrf6xiXwny9166vsMLCwgBdlAmHt8TFxgBwpNTs9C2hyO7t7ZnR5L/B
w0yv0NXV1gBimKGjpABtoQBuoqKkpiaUvqWmqHbB2/j4+Pf39729vgB/sN7w9obH3hSMugCAsonJ
4M/q8wBglgB6rCCaxLO0tX7C2wBqniGMuABzpuPl5f3+/v39/fr6+r7i7vP6/ABonV621LLc6zWk
yrq6uq6wskGlyUaszp6gohmYw8HDxKaoqn3E3LGztWGuzcnLzKmrrOnp6gB1qCaex1q001ewz+Dg
4QB3qrCxstHS09LR0dHR0s7Oz8zNzsfIyQaJuQB0pozL4YzI3re4uAGFtYDG3hOUwb+/wQB5rOvr
6wB2qdju9TWfxgBpniOcxeLj48vn8dvc3VKuzwB2qp6fos/Q0aXV6D+jxwB7rsXHyLu8vb27vCSc
xSGZwxyZxH3A2RuUv0+uzz+ozCedxgCDtABnnABroKutr/7+/n2/2LTd6wBvo9bX2OLo6lGv0C6d
xS6avjmmzLTR2uzr6m651RuXw4jF3CqfxySaxSadyAuRv9bd4cPExRiMuDKjyUWevNPS0sXl8BeY
xKytr8G/wABypXvC23vD3O73+3vE3cvU2PH5+7S1t7q7vCGVwO/v8JfM3zymyyyZwrWys+Hy90Ki
xK6qqg+TwBKXxMvMzaWtsK7U4jemzLXEygBxpW++2aCho97Z18bP0/T09fX29vb19ViuzdDR0crf
51qz01y00ujo6Onq6hCDs2Gpw3i71CqWv3S71nO92M/h52m207bJ0AN6rPPz9Nrh5Nvo7K/b6oTI
37Td7ABqneHi4yScxo/M4RiWwRqVwcro8n3B2lGoylStzszMzAAAACH5BAEAAP8ALAAAAAAuACAA
Bwj/AP8JHEjw3wEkEY74WOjrQhUNBSNKnCjRSoYKCOwJcKWpEAACBFBRGEKxZMkDjRAg2OBlQyYL
WhDEcOWxDwofv0zqHIhhDYIFC2p4MYFMS62ZaiYVWlJJAYIqO00KMlEjABYOQokaRbp0CYBKffpE
iDpxSKYC1gqswToUmYVaCFyp6QrgwwcCscaSJZhgQYBeAdRyqFBhgwWkGyct8WoXRZ8Ph/YOxMOB
CIUAHsBxwGQBAII1YwpMI5Brcd0PKFA4Q2ZFMgYteZqkwxyu1KQNJzQc+CdFCrxypyqdRoEPX6x7
ki/n2TfbAxtNRHYTVCWpWTRbuRoX7yMgZ9QSFQa0/7LU/BXygjIWXVOBTR2sxp7BxGpENgKbY+PR
reqyIOKnOh0M445AjTjDCgrPSBNFKt9w8wMVU5g0Bg8kDAAKOutQAkNEQNBwDRAEeVEcAV6w84Ay
KowQSRhmzNGAASIAYow2IP6DySPk8ANKCv1wINE2cpjxCUEgOIOPAKicQMMbKnhyhhg97HDNF4vs
IEYkNkzwjwSP/PHIE2VIgIdEnxjAiBwNGIKGDKS8I0sw2VAzApNOQimGLlyMAIkDw2yhZTF/KKGE
lxCEMtEPBtDhACQurLDCLkFIsoUeZLyRpx8OmEGHN3AEcU0HkFAhUDFulDroJvOU5M44iDjgDTQO
1P/hzRw2IFJPGw3AAY0LI/SAwxc7jEKQI2mkEUipRoxp0g821AMIGlG0McockMzihx5c1LkDDmSg
UVAiafACRbGPVKDTFG3MYUYdLoThRxDE6DEMGUww8eQONGwTER9piFINFOPasaFJVIjTwC1xzOGP
A3HUKoIMDTwJR4QRgdBOJzq8UM0Lj5QihU5ZdGMOCSSYUwYzAwwkDhNtUKTBOZ10koMOoohihDwm
HZKPEDwb4fMe9An0g5Yl+SDKFTHnkMMLLQAjXUTxUCLEIyH0bIQAwuxVQhEMcEIIIUmHUEsWGCQg
xQEaIFGAHV0+QnUIIWwyg2T/3MPLDQwwcAUhTjiswYsQl1SAxQKmbBJCIMe6ISjVmXwsWQKJEJJE
3l1/TY8O4wZyh8ZQ3IF4qX9cggTdAmEwCAMs3IB311fsDfbMGv97BxSBQBAP6QMN0QUhLCSRhOp5
e923zDpk/EIaRdyO+0C/eHBHEiz0vjrrfMfciSKD4LJ8RBEk88IN0ff+O/CEVEPLGK1tH1ECM7Dx
RDWdcMLJFTpUQ44jfCyjvlShZNDE/0QAgT6ypr6AAAA7
            """),

        'AP': PhotoImage(data=r"""
    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
+zfwyii1238UiwAAAABJRU5ErkJggg=="""),

        'LegacySwitch': PhotoImage( data=r"""
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
4BE2eIRYeHAEIBwBP0Y4Qn41YWRSCQgAOw==
            """),

        'LegacyRouter': PhotoImage( data=r"""
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
gGPLHwLwcMIo12Qxu0ABAQA7
            """),

        'Controller': PhotoImage( data=r"""
            R0lGODlhMAAwAPcAAAEBAWfNAYWFhcfHx+3t6/f390lJUaWlpfPz8/Hx72lpaZGRke/v77m5uc0B
            AeHh4e/v7WNjY3t7e5eXlyMjI4mJidPT0+3t7f///09PT7Ozs/X19fHx8ZWTk8HBwX9/fwAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAAAALAAAAAAwADAA
            Bwj/AAEIHEiwoMGDCBMqXMiwocOHECNKnEixosWLGAEIeMCxo8ePHwVkBGABg8mTKFOmtDByAIYN
            MGPCRCCzQIENNzEMGOkBAwIKQIMKpYCgKAIHCDB4GNkAA4OnUJ9++CDhQ1QGFzA0GKkBA4GvYMOK
            BYtBA1cNaNOqXcuWq8q3b81m7Cqzbk2bMMu6/Tl0qFEEAZLKxdj1KlSqVA3rnet1rOOwiwmznUzZ
            LdzLJgdfpIv3pmebN2Pm1GyRbocNp1PLNMDaAM3Im1/alQk4gO28pCt2RdCBt+/eRg8IP1AUdmmf
            f5MrL56bYlcOvaP7Xo6Ag3HdGDho3869u/YE1507t+3AgLz58ujPMwg/sTBUCAzgy49PH0LW5u0x
            XFiwvz////5dcJ9bjxVIAHsSdUXAAgs2yOCDDn6FYEQaFGDgYxNCpEFfHHKIX4IDhCjiiCSS+CGF
            FlCmogYpcnVABTDGKGOMAlRQYwUHnKjhAjX2aOOPN8LImgAL6PiQBhLMqCSNAThQgQRGOqRBBD1W
            aaOVAggnQARRNqRBBxmEKeaYZIrZQZcMKbDiigqM5OabcMYp55x01ilnQAA7
            """),

        'Host': PhotoImage( data=r"""
            R0lGODlhIAAYAPcAMf//////zP//mf//Zv//M///AP/M///MzP/M
            mf/MZv/MM//MAP+Z//+ZzP+Zmf+ZZv+ZM/+ZAP9m//9mzP9mmf9m
            Zv9mM/9mAP8z//8zzP8zmf8zZv8zM/8zAP8A//8AzP8Amf8AZv8A
            M/8AAMz//8z/zMz/mcz/Zsz/M8z/AMzM/8zMzMzMmczMZszMM8zM
            AMyZ/8yZzMyZmcyZZsyZM8yZAMxm/8xmzMxmmcxmZsxmM8xmAMwz
            /8wzzMwzmcwzZswzM8wzAMwA/8wAzMwAmcwAZswAM8wAAJn//5n/
            zJn/mZn/Zpn/M5n/AJnM/5nMzJnMmZnMZpnMM5nMAJmZ/5mZzJmZ
            mZmZZpmZM5mZAJlm/5lmzJlmmZlmZplmM5lmAJkz/5kzzJkzmZkz
            ZpkzM5kzAJkA/5kAzJkAmZkAZpkAM5kAAGb//2b/zGb/mWb/Zmb/
            M2b/AGbM/2bMzGbMmWbMZmbMM2bMAGaZ/2aZzGaZmWaZZmaZM2aZ
            AGZm/2ZmzGZmmWZmZmZmM2ZmAGYz/2YzzGYzmWYzZmYzM2YzAGYA
            /2YAzGYAmWYAZmYAM2YAADP//zP/zDP/mTP/ZjP/MzP/ADPM/zPM
            zDPMmTPMZjPMMzPMADOZ/zOZzDOZmTOZZjOZMzOZADNm/zNmzDNm
            mTNmZjNmMzNmADMz/zMzzDMzmTMzZjMzMzMzADMA/zMAzDMAmTMA
            ZjMAMzMAAAD//wD/zAD/mQD/ZgD/MwD/AADM/wDMzADMmQDMZgDM
            MwDMAACZ/wCZzACZmQCZZgCZMwCZAABm/wBmzABmmQBmZgBmMwBm
            AAAz/wAzzAAzmQAzZgAzMwAzAAAA/wAAzAAAmQAAZgAAM+4AAN0A
            ALsAAKoAAIgAAHcAAFUAAEQAACIAABEAAADuAADdAAC7AACqAACI
            AAB3AABVAABEAAAiAAARAAAA7gAA3QAAuwAAqgAAiAAAdwAAVQAA
            RAAAIgAAEe7u7t3d3bu7u6qqqoiIiHd3d1VVVURERCIiIhEREQAA
            ACH5BAEAAAAALAAAAAAgABgAAAiNAAH8G0iwoMGDCAcKTMiw4UBw
            BPXVm0ixosWLFvVBHFjPoUeC9Tb+6/jRY0iQ/8iVbHiS40CVKxG2
            HEkQZsyCM0mmvGkw50uePUV2tEnOZkyfQA8iTYpTKNOgKJ+C3AhO
            p9SWVaVOfWj1KdauTL9q5UgVbFKsEjGqXVtP40NwcBnCjXtw7tx/
            C8cSBBAQADs=
        """ ),

        'Station': PhotoImage(data=r"""
            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
            AXZBYRA4C/1iAAAAAElFTkSuQmCC
            """),

        'OldSwitch': PhotoImage( data=r"""
            R0lGODlhIAAYAPcAMf//////zP//mf//Zv//M///AP/M///MzP/M
            mf/MZv/MM//MAP+Z//+ZzP+Zmf+ZZv+ZM/+ZAP9m//9mzP9mmf9m
            Zv9mM/9mAP8z//8zzP8zmf8zZv8zM/8zAP8A//8AzP8Amf8AZv8A
            M/8AAMz//8z/zMz/mcz/Zsz/M8z/AMzM/8zMzMzMmczMZszMM8zM
            AMyZ/8yZzMyZmcyZZsyZM8yZAMxm/8xmzMxmmcxmZsxmM8xmAMwz
            /8wzzMwzmcwzZswzM8wzAMwA/8wAzMwAmcwAZswAM8wAAJn//5n/
            zJn/mZn/Zpn/M5n/AJnM/5nMzJnMmZnMZpnMM5nMAJmZ/5mZzJmZ
            mZmZZpmZM5mZAJlm/5lmzJlmmZlmZplmM5lmAJkz/5kzzJkzmZkz
            ZpkzM5kzAJkA/5kAzJkAmZkAZpkAM5kAAGb//2b/zGb/mWb/Zmb/
            M2b/AGbM/2bMzGbMmWbMZmbMM2bMAGaZ/2aZzGaZmWaZZmaZM2aZ
            AGZm/2ZmzGZmmWZmZmZmM2ZmAGYz/2YzzGYzmWYzZmYzM2YzAGYA
            /2YAzGYAmWYAZmYAM2YAADP//zP/zDP/mTP/ZjP/MzP/ADPM/zPM
            zDPMmTPMZjPMMzPMADOZ/zOZzDOZmTOZZjOZMzOZADNm/zNmzDNm
            mTNmZjNmMzNmADMz/zMzzDMzmTMzZjMzMzMzADMA/zMAzDMAmTMA
            ZjMAMzMAAAD//wD/zAD/mQD/ZgD/MwD/AADM/wDMzADMmQDMZgDM
            MwDMAACZ/wCZzACZmQCZZgCZMwCZAABm/wBmzABmmQBmZgBmMwBm
            AAAz/wAzzAAzmQAzZgAzMwAzAAAA/wAAzAAAmQAAZgAAM+4AAN0A
            ALsAAKoAAIgAAHcAAFUAAEQAACIAABEAAADuAADdAAC7AACqAACI
            AAB3AABVAABEAAAiAAARAAAA7gAA3QAAuwAAqgAAiAAAdwAAVQAA
            RAAAIgAAEe7u7t3d3bu7u6qqqoiIiHd3d1VVVURERCIiIhEREQAA
            ACH5BAEAAAAALAAAAAAgABgAAAhwAAEIHEiwoMGDCBMqXMiwocOH
            ECNKnEixosWB3zJq3Mixo0eNAL7xG0mypMmTKPl9Cznyn8uWL/m5
            /AeTpsyYI1eKlBnO5r+eLYHy9Ck0J8ubPmPOrMmUpM6UUKMa/Ui1
            6saLWLNq3cq1q9evYB0GBAA7
        """ ),

        'NetLink': PhotoImage( data=r"""
            R0lGODlhFgAWAPcAMf//////zP//mf//Zv//M///AP/M///MzP/M
            mf/MZv/MM//MAP+Z//+ZzP+Zmf+ZZv+ZM/+ZAP9m//9mzP9mmf9m
            Zv9mM/9mAP8z//8zzP8zmf8zZv8zM/8zAP8A//8AzP8Amf8AZv8A
            M/8AAMz//8z/zMz/mcz/Zsz/M8z/AMzM/8zMzMzMmczMZszMM8zM
            AMyZ/8yZzMyZmcyZZsyZM8yZAMxm/8xmzMxmmcxmZsxmM8xmAMwz
            /8wzzMwzmcwzZswzM8wzAMwA/8wAzMwAmcwAZswAM8wAAJn//5n/
            zJn/mZn/Zpn/M5n/AJnM/5nMzJnMmZnMZpnMM5nMAJmZ/5mZzJmZ
            mZmZZpmZM5mZAJlm/5lmzJlmmZlmZplmM5lmAJkz/5kzzJkzmZkz
            ZpkzM5kzAJkA/5kAzJkAmZkAZpkAM5kAAGb//2b/zGb/mWb/Zmb/
            M2b/AGbM/2bMzGbMmWbMZmbMM2bMAGaZ/2aZzGaZmWaZZmaZM2aZ
            AGZm/2ZmzGZmmWZmZmZmM2ZmAGYz/2YzzGYzmWYzZmYzM2YzAGYA
            /2YAzGYAmWYAZmYAM2YAADP//zP/zDP/mTP/ZjP/MzP/ADPM/zPM
            zDPMmTPMZjPMMzPMADOZ/zOZzDOZmTOZZjOZMzOZADNm/zNmzDNm
            mTNmZjNmMzNmADMz/zMzzDMzmTMzZjMzMzMzADMA/zMAzDMAmTMA
            ZjMAMzMAAAD//wD/zAD/mQD/ZgD/MwD/AADM/wDMzADMmQDMZgDM
            MwDMAACZ/wCZzACZmQCZZgCZMwCZAABm/wBmzABmmQBmZgBmMwBm
            AAAz/wAzzAAzmQAzZgAzMwAzAAAA/wAAzAAAmQAAZgAAM+4AAN0A
            ALsAAKoAAIgAAHcAAFUAAEQAACIAABEAAADuAADdAAC7AACqAACI
            AAB3AABVAABEAAAiAAARAAAA7gAA3QAAuwAAqgAAiAAAdwAAVQAA
            RAAAIgAAEe7u7t3d3bu7u6qqqoiIiHd3d1VVVURERCIiIhEREQAA
            ACH5BAEAAAAALAAAAAAWABYAAAhIAAEIHEiwoEGBrhIeXEgwoUKG
            Cx0+hGhQoiuKBy1irChxY0GNHgeCDAlgZEiTHlFuVImRJUWXEGEy
            lBmxI8mSNknm1Dnx5sCAADs=
        """ )
    }

def addDictOption( opts, choicesDict, default, name, helpStr=None ):
    """Convenience function to add choices dicts to OptionParser.
       opts: OptionParser instance
       choicesDict: dictionary of valid choices, must include default
       default: default choice key
       name: long option name
       help: string"""
    if default not in choicesDict:
        raise Exception( 'Invalid  default %s for choices dict: %s' %
                         ( default, name ) )
    if not helpStr:
        helpStr = ( '|'.join( sorted( choicesDict.keys() ) ) +
                    '[,param=value...]' )
    opts.add_option( '--' + name,
                     type='string',
                     default = default,
                     help = helpStr )

if __name__ == '__main__':
    setLogLevel( 'info' )
    app = MiniEdit()
    ### import topology if specified ###
    app.parseArgs()
    app.importTopo()

    app.mainloop()
