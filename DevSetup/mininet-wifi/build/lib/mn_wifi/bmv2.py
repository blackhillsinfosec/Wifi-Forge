# coding=utf-8
"""
Copyright 2019-present Open Networking Foundation
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import json
import multiprocessing
import os
import random
import re
import socket
import sys
import threading
import time

Python3 = sys.version_info[0] == 3

if Python3:
    import urllib.request as urllib
else:
    import urllib2 as urllib
from contextlib import closing

from mininet.log import info, warn, debug
from mininet.link import Link
from mininet.node import Switch, Host
from mininet.util import netParse, ipAdd
from mn_wifi.node import AP, Station

SIMPLE_SWITCH_GRPC = 'simple_switch_grpc'
PKT_BYTES_TO_DUMP = 80
VALGRIND_PREFIX = 'valgrind --leak-check=yes'
SWITCH_START_TIMEOUT = 10  # seconds
BMV2_LOG_LINES = 5
BMV2_DEFAULT_DEVICE_ID = 1
DEFAULT_PIPECONF = "org.onosproject.pipelines.basic"

# Stratum paths relative to stratum repo root
STRATUM_BMV2 = 'stratum_bmv2'
STRATUM_BINARY = '/bazel-bin/stratum/hal/bin/bmv2/' + STRATUM_BMV2
STRATUM_INIT_PIPELINE = '/stratum/hal/bin/bmv2/dummy.json'

IPBASE = '192.168.123.0/24'
CONTROLLER = []


def getStratumRoot():
    if 'STRATUM_ROOT' not in os.environ:
        raise Exception("Env variable STRATUM_ROOT not set")
    return os.environ['STRATUM_ROOT']


def parseBoolean(value):
    if value in ['1', 1, 'true', 'True']:
        return True
    return False


def pickUnusedPort():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port


def writeToFile(path, value):
    with open(path, "w") as f:
        f.write(str(value))


def watchDog(sw):
    try:
        writeToFile(sw.keepaliveFile,
                    "Remove this file to terminate %s" % sw.name)
        while True:
            if P4Switch.mininet_exception == 1 \
                    or not os.path.isfile(sw.keepaliveFile):
                sw.killBmv2(log=False)
                return
            if sw.stopped:
                return
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                port = sw.grpcPortInternal if sw.grpcPortInternal else sw.grpcPort
                if s.connect_ex(('localhost', port)) == 0:
                    time.sleep(1)
                else:
                    warn("\n*** WARN: switch %s crashed ☠️, restarting... \n"
                         % sw.name)
                    sw.stop()
                    sw.start()
                    return
    except Exception as e:
        warn("*** ERROR: " + e.message)
        sw.killBmv2(log=True)


class P4Host(Host):
    def __init__(self, name, inNamespace=True, **params):
        Host.__init__(self, name, inNamespace=inNamespace, **params)

    def config(self, **params):
        r = super(Host, self).config(**params)
        for off in ["rx", "tx", "sg"]:
            cmd = "/sbin/ethtool --offload %s %s off" \
                  % (self.defaultIntf(), off)
            self.cmd(cmd)
        # disable IPv6
        self.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        self.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        self.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")
        return r


class P4Switch(Switch):
    """BMv2 software switch with gRPC server"""
    # Shared value used to notify to all instances of this class that a Mininet
    # exception occurred. Mininet exception handling doesn't call the stop()
    # method, so the mn process would hang after clean-up since Bmv2 would still
    # be running.
    mininet_exception = multiprocessing.Value('i', 0)

    def __init__(self, name, json=None, debugger=False, loglevel="info",
                 elogger=False, grpcport=None, cpuport=255, notifications=False,
                 thriftport=None, netcfg=False, dryrun=False, inNamespace=False,
                 inband=False, pipeconf=DEFAULT_PIPECONF, pktdump=False, valgrind=False,
                 gnmi=False, portcfg=True, onosdevid=None, adminstate=True, stratum=False,
                 switch_config=None, timeout=SWITCH_START_TIMEOUT, **kwargs):
        Switch.__init__(self, name, inNamespace=inNamespace, **kwargs)
        self.grpcPort = grpcport
        self.grpcPortInternal = None  # Needed for Stratum (local_hercules_url)
        self.thriftPort = thriftport
        self.cpuPort = cpuport
        self.inNamespace = inNamespace
        self.inband = inband
        self.useStratum = parseBoolean(stratum)
        self.debugger = parseBoolean(debugger)
        self.notifications = parseBoolean(notifications)
        self.loglevel = loglevel
        # Important: Mininet removes all /tmp/*.log files in case of exceptions.
        # We want to be able to see the bmv2 log if anything goes wrong, hence
        # avoid the .log extension.
        self.logfile = '/tmp/bmv2-%s-log' % self.name
        self.elogger = parseBoolean(elogger)
        self.pktdump = parseBoolean(pktdump)
        self.netcfg = parseBoolean(netcfg)
        self.dryrun = parseBoolean(dryrun)
        self.valgrind = parseBoolean(valgrind)
        self.netcfgfile = '/tmp/bmv2-%s-netcfg.json' % self.name
        self.chassisConfigFile = '/tmp/bmv2-%s-chassis-config.txt' % self.name
        self.pipeconfId = pipeconf
        self.injectPorts = parseBoolean(portcfg)
        self.withGnmi = parseBoolean(gnmi)
        self.longitude = kwargs['longitude'] if 'longitude' in kwargs else None
        self.latitude = kwargs['latitude'] if 'latitude' in kwargs else None
        if onosdevid is not None and len(onosdevid) > 0:
            self.onosDeviceId = onosdevid
        else:
            self.onosDeviceId = "device:bmv2:%s" % self.name
        nums = re.findall(r'\d+', name)
        self.p4DeviceId = int(nums[0])
        self.logfd = None
        self.bmv2popen = None
        self.stopped = True
        self.sip = None
        # In case of exceptions, mininet removes *.out files from /tmp. We use
        # this as a signal to terminate the switch instance (if active).
        self.keepaliveFile = '/tmp/bmv2-%s-watchdog.out' % self.name
        self.adminState = "ENABLED" if adminstate else "DISABLED"
        self.targetName = STRATUM_BMV2 if self.useStratum else SIMPLE_SWITCH_GRPC
        self.controllers = None
        self.switch_config = switch_config
        self.timeout = timeout

        path = os.path.dirname(os.path.abspath(__file__)) + '/examples/p4/ap-runtime.json'
        self.json = path if not json else json

        # Remove files from previous executions
        self.cleanupTmpFiles()

    def getSourceIp(self, dstIP):
        """
        Queries the Linux routing table to get the source IP that can talk with
        dstIP, and vice versa.
        """
        ipRouteOut = self.cmd('ip route get %s' % dstIP)
        r = re.search(r"src (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", ipRouteOut)
        return r.group(1) if r else None

    def getDeviceConfig(self, srcIP):

        basicCfg = {
            "managementAddress": "grpc://%s:%d?device_id=%d" % (
                srcIP, self.grpcPort, self.p4DeviceId),
            "driver": "stratum-bmv2" if self.useStratum else "bmv2",
            "pipeconf": self.pipeconfId
        }

        if self.longitude and self.latitude:
            basicCfg["longitude"] = self.longitude
            basicCfg["latitude"] = self.latitude

        cfgData = {
            "basic": basicCfg
        }

        if not self.useStratum and self.injectPorts:
            portData = {}
            portId = 1
            for intfName in self.intfNames():
                if intfName == 'lo':
                    continue
                portData[str(portId)] = {
                    "number": portId,
                    "name": intfName,
                    "enabled": True,
                    "removed": False,
                    "type": "copper",
                    "speed": 10000
                }
                portId += 1

            cfgData['ports'] = portData

        return cfgData

    def chassisConfig(self):
        config = """description: "BMv2 simple_switch {name}"
chassis {{
  platform: PLT_P4_SOFT_SWITCH
  name: "{name}"
}}
nodes {{
  id: {nodeId}
  name: "{name} node {nodeId}"
  slot: 1
  index: 1
}}\n""".format(name=self.name, nodeId=self.p4DeviceId)

        intfNumber = 1
        for intfName in self.intfNames():
            if intfName == 'lo':
                continue
            config = config + """singleton_ports {{
  id: {intfNumber}
  name: "{intfName}"
  slot: 1
  port: {intfNumber}
  channel: 1
  speed_bps: 10000000000
  config_params {{
    admin_state: ADMIN_STATE_{adminState}
  }}
  node: {nodeId}
}}\n""".format(intfName=intfName, intfNumber=intfNumber,
               nodeId=self.p4DeviceId, adminState=self.adminState)
            intfNumber += 1

        return config

    def doOnosNetcfg(self, controllerIP):
        """
        Notifies ONOS about the new device via Netcfg.
        """
        srcIP = self.getSourceIp(controllerIP)
        if not srcIP:
            warn("*** WARN: unable to get switch IP address, won't do netcfg\n")
            return

        cfgData = {
            "devices": {
                self.onosDeviceId: self.getDeviceConfig(srcIP)
            }
        }
        with open(self.netcfgfile, 'w') as fp:
            json.dump(cfgData, fp, indent=4)

        if not self.netcfg:
            # Do not push config to ONOS.
            info("\n")
            return

        # Build netcfg URL
        url = 'http://%s:8181/onos/v1/network/configuration/' % controllerIP
        # Instantiate password manager for HTTP auth
        pm = urllib.HTTPPasswordMgrWithDefaultRealm()

        if 'ONOS_WEB_USER' not in os.environ:
            os.environ['ONOS_WEB_USER'] = 'onos'
        if 'ONOS_WEB_PASS' not in os.environ:
            os.environ['ONOS_WEB_PASS'] = 'rocks'

        pm.add_password(None, url, os.environ['ONOS_WEB_USER'], os.environ['ONOS_WEB_PASS'])
        urllib.install_opener(urllib.build_opener(urllib.HTTPBasicAuthHandler(pm)))
        # Push config data to controller
        req = urllib.Request(url, json.dumps(cfgData).encode("utf-8"), {'Content-Type': 'application/json'})
        try:
            f = urllib.urlopen(req)
            info(f.read())
            f.close()
        except urllib.URLError as e:
            warn("*** WARN: unable to push config to ONOS (%s)\n" % e.reason)

    def start(self, controllers=None):

        if not self.stopped:
            warn("*** %s is already running!\n" % self.name)
            return

        if controllers is not None:
            #  If restarting after crash use same controllers as for first
            #  start.
            self.controllers = controllers

        if self.inNamespace and not self.inband:
            self.sip = self.getIP(self.p4DeviceId + 1)

        # Remove files from previous executions (if we are restarting)
        self.cleanupTmpFiles()

        if self.grpcPort is None:
            self.grpcPort = pickUnusedPort()
        writeToFile("/tmp/bmv2-%s-grpc-port" % self.name, self.grpcPort)
        if self.thriftPort is None:
            self.thriftPort = pickUnusedPort()
        writeToFile("/tmp/bmv2-%s-thrift-port" % self.name, self.thriftPort)

        if self.useStratum:
            config_dir = "/tmp/bmv2-%s-stratum" % self.name
            os.mkdir(config_dir)
            with open(self.chassisConfigFile, 'w') as fp:
                fp.write(self.chassisConfig())
            if self.grpcPortInternal is None:
                self.grpcPortInternal = pickUnusedPort()
            cmdString = self.getStratumCmdString(config_dir)
        else:
            cmdString = self.getBmv2CmdString()

        if self.dryrun:
            info("\n*** DRY RUN (not executing %s)\n" % self.targetName)

        debug("\n%s\n" % cmdString)

        try:
            if not self.dryrun:
                # Start the switch
                self.stopped = False
                self.logfd = open(self.logfile, "w")
                self.logfd.write(cmdString + "\n\n" + "-" * 80 + "\n\n")
                self.logfd.flush()
                self.bmv2popen = self.popen(cmdString,
                                            stdout=self.logfd,
                                            stderr=self.logfd)
                self.waitBmv2Start()

                # We want to be notified if BMv2/Stratum dies...
                if not self.inNamespace:
                    threading.Thread(target=watchDog, args=[self]).start()

                if self.json is not None:
                    if self.switch_config is not None:
                        # Switch initial configuration using Thrift CLI
                        try:
                            with open(self.switch_config, mode='r') as f:
                                # map(self.bmv2Thrift(), f.readlines())
                                for cmd_row in f:
                                    self.bmv2Thrift(cmd_row)
                            debug("\nSwitch has been configured with %s configuration file" % self.switch_config)
                        except IOError:
                            info("\nSwitch configuration file %s not found" % self.switch_config)

            if self.controllers:
                self.doOnosNetcfg(self.controllerIp(self.controllers))
        except Exception:
            P4Switch.mininet_exception = 1
            self.killBmv2()
            self.printBmv2Log()
            raise

    def bmv2Thrift(self, *args, **kwargs):
        "Run ovs-vsctl command (or queue for later execution)"
        cli_command = "simple_switch_CLI --thrift-port " + str(self.thriftPort) + " <<< "
        switch_cmd = ' '.join(map(str, filter(lambda ar: ar is not None, args)))
        command = cli_command + '"' + switch_cmd + '"'
        self.cmd(command)

    def attach(self, intf):
        """ Connect a new data port """
        # TODO: find a better way to add a port at runtime
        if self.pktdump:
            pcapFiles = ["./" + str(intf) + "_out.pcap", "./" + str(intf) + "_in.pcap"]
            self.bmv2Thrift('port_add', intf, next(key for key, value in self.intfs.items() if value == intf),
                            *pcapFiles)
        else:
            self.bmv2Thrift('port_add', intf, next(key for key, value in self.intfs.items() if value == intf))
        self.cmd('ifconfig', intf, 'up')
        # TODO: check if need to send a new netcfg
        # if self.controllers is not None and len(controllers) > 0 :
        #   self.doOnosNetcfg(self.controllerIp(controllers))
        # else:
        #    self.doOnosNetcfg(None)

    def getBmv2CmdString(self):
        bmv2Args = [SIMPLE_SWITCH_GRPC] + self.bmv2Args()
        if self.valgrind:
            bmv2Args = VALGRIND_PREFIX.split() + bmv2Args
        return " ".join(bmv2Args)

    def getStratumCmdString(self, config_dir):
        stratumRoot = getStratumRoot()
        args = [
            stratumRoot + STRATUM_BINARY,
            '-device_id=%d' % self.p4DeviceId,
            '-chassis_config_file=%s' % self.chassisConfigFile,
            '-forwarding_pipeline_configs_file=/dev/null',
            '-persistent_config_dir=' + config_dir,
            '-initial_pipeline=' + stratumRoot + STRATUM_INIT_PIPELINE,
            '-cpu_port=%s' % self.cpuPort,
            '-external_hercules_urls=0.0.0.0:%d' % self.grpcPort,
            '-local_hercules_url=localhost:%d' % self.grpcPortInternal,
            '-bmv2_thrift_port=%d' % self.thriftPort,
            '-bmv2_log_level=%s' % self.loglevel,
            '-max_num_controllers_per_node=10',
            '-write_req_log_file=/dev/null'
        ]
        return " ".join(args)

    def bmv2Args(self):
        args = ['--device-id %s' % str(self.p4DeviceId)]
        for port, intf in self.intfs.items():
            if not intf.IP():
                args.append('-i %d@%s' % (port, intf.name))
        args.append('--thrift-port %s' % self.thriftPort)
        if self.notifications:
            ntfaddr = 'ipc:///tmp/bmv2-%s-notifications.ipc' % self.name
            args.append('--notifications-addr %s' % ntfaddr)
        if self.elogger:
            nanologaddr = 'ipc:///tmp/bmv2-%s-nanolog.ipc' % self.name
            args.append('--nanolog %s' % nanologaddr)
        if self.debugger:
            dbgaddr = 'ipc:///tmp/bmv2-%s-debug.ipc' % self.name
            args.append('--debugger-addr %s' % dbgaddr)
        args.append('--log-console')
        if self.pktdump:
            args.append('--pcap --dump-packet-data %s' % PKT_BYTES_TO_DUMP)
        args.append('-L%s' % self.loglevel)
        if not self.json:
            args.append('--no-p4')
        else:
            args.append(self.json)
        # gRPC target-specific options
        args.append('--')
        args.append('--cpu-port %s' % self.cpuPort)
        args.append('--grpc-server-addr 0.0.0.0:%s' % self.grpcPort)
        return args

    def getIP(self, nextIP=1):
        ipBaseNum, prefixLen = netParse(IPBASE)
        return ipAdd(nextIP, ipBaseNum=ipBaseNum, prefixLen=prefixLen)

    def configNameSpace(self):
        global CONTROLLER
        if self.controllers:
            controller = self.controllers[0]
            self.sip = controller.IP()
        else:
            if not CONTROLLER:
                controller = P4Host('c0', inNamespace=False)
                CONTROLLER = controller
            else:
                controller = CONTROLLER

        self.cmd('ip link set lo up')
        if not self.inband:
            link = Link(self, controller, port1=0)
            sintf, cintf = link.intf1, link.intf2
            if controller.IP() == '127.0.0.1' or not controller.IP():
                cip = self.getIP()
            else:
                cip = controller.IP()
            controller.setIP(cip, intf='c0-eth%s' % (len(controller.intfs) - 1))
            self.setIP(intf='%s-eth0' % self.name, ip=self.sip)

            controller.setHostRoute('%s' % self.sip, cintf)
            self.setHostRoute(cip, sintf)

        return controller

    def waitBmv2Start(self):
        # Wait for switch to open gRPC port, before sending ONOS the netcfg.
        # Include time-out just in case something hangs.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        endtime = time.time() + self.timeout

        if self.inNamespace:
            self.configNameSpace()

        while True:
            port = self.grpcPortInternal if self.grpcPortInternal else self.grpcPort
            if self.inband:
                result = 0
            else:
                if self.inNamespace:
                    result = sock.connect_ex((self.sip, port))
                else:
                    result = sock.connect_ex(('localhost', port))

            if result == 0:
                # No new line
                sys.stdout.write("⚡️ %s @ %d thrift @ %s\n" % (self.targetName,
                                                              self.bmv2popen.pid,
                                                              self.thriftPort))
                sys.stdout.flush()
                # The port is open. Let's go! (Close socket first)
                sock.close()
                break
            # Port is not open yet. If there is time, we wait a bit.
            if endtime > time.time():
                sys.stdout.write('.')
                sys.stdout.flush()
                time.sleep(0.05)
            else:
                # Time's up.
                raise Exception("Switch did not start before timeout")

    def printBmv2Log(self):
        if os.path.isfile(self.logfile):
            info("\n-" * 80)
            info("\n%s log (from %s):" % (self.name, self.logfile))
            with open(self.logfile, 'r') as f:
                lines = f.readlines()
                if len(lines) > BMV2_LOG_LINES:
                    info("\n...")
                for line in lines[-BMV2_LOG_LINES:]:
                    info(line.rstrip())

    @staticmethod
    def controllerIp(controllers):
        try:
            # onos.py
            clist = controllers[0].nodes()
        except AttributeError:
            clist = controllers
        assert len(clist) > 0
        return random.choice(clist).IP()

    def killBmv2(self, log=False):
        self.stopped = True
        if self.bmv2popen is not None:
            self.bmv2popen.terminate()
            self.bmv2popen.wait()
            self.bmv2popen = None
        if self.logfd is not None:
            if log:
                self.logfd.write("*** PROCESS TERMINATED BY MININET ***\n")
            self.logfd.close()
            self.logfd = None

    def cleanupTmpFiles(self):
        self.cmd("rm -rf /tmp/bmv2-%s-*" % self.name)

    def stop(self, deleteIntfs=True):
        """Terminate switch."""
        self.killBmv2(log=True)
        Switch.stop(self, deleteIntfs)


class P4StratumSwitch(P4Switch):
    def __init__(self, name, **kwargs):
        kwargs["stratum"] = True
        super(P4StratumSwitch, self).__init__(name, **kwargs)


class P4Station(Station):
    def __init__(self, name, inNamespace=True, **params):
        Station.__init__(self, name, inNamespace=inNamespace, **params)

    def config(self, **params):
        #  offload does not work with wifi
        r = super(Station, self).config(**params)
        #for off in ["rx", "tx", "sg"]:
        #    cmd = "/sbin/ethtool --offload %s %s off" \
        #          % (self.defaultIntf(), off)
        #    self.cmd(cmd)
        # disable IPv6
        self.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        self.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        self.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")
        return r


class P4AP(P4Switch, AP):
    mininet_exception = multiprocessing.Value('i', 0)

    def __init__(self, name, **kwargs):
        P4Switch.__init__(self, name, **kwargs)
        self.wintfs = {}  # dict of wireless port numbers
        self.wports = {}  # dict of interfaces to port numbers


class P4StratumAP(P4AP):
    def __init__(self, name, **kwargs):
        kwargs["stratum"] = True
        super(P4StratumAP, self).__init__(name, **kwargs)


# Exports for bin/mn
switches = {
    'p4switch': P4Switch,
    'p4stratumswitch': P4StratumSwitch,
}
aps = {
    'p4ap': P4AP,
    'p4stratumap': P4StratumAP,
}
hosts = {'p4host': P4Host}
stations = {'p4station': P4Station}
