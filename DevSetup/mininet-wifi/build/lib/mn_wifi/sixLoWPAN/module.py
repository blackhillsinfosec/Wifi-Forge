# author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)


import os
import subprocess
import logging
from mininet.log import debug, info


class module(object):
    "wireless module"

    externally_managed = False
    devices_created_dynamically = False

    def __init__(self, nodes, nwpan, iot_module):
        self.start(nodes, nwpan, iot_module)

    def start(self, nodes, nwpan, iot_module):
        """
        :param nodes: list of nodes
        :param nwpan: number of wifi radios
        :param iot_module: dir of a fakelb alternative module
        :param **params: ifb -  Intermediate Functional Block device"""
        wm = subprocess.call(['which', 'iwpan'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if wm == 0:
            self.load_module(nwpan, iot_module)  # Initatilize WiFi Module
            if iot_module == 'mac802154_hwsim':
                n = 0
                for sensor in nodes:
                    for _ in range(0, len(sensor.params['wpan'])):
                        n += 1
                        if n > 2:
                            os.system('wpan-hwsim add >/dev/null 2>&1')
            self.assign_iface(nodes)  # iface assign
        else:
            info('*** iwpan will be used, but it is not installed.\n' \
                 '*** Please install iwpan with sudo util/install.sh -6.\n')
            exit(1)

    def load_module(self, nwpan, iot_module):
        """ Load WiFi Module
        :param nwpan: number of radios
        :param iot_module: dir of a fakelb alternative module"""
        debug('Loading %s virtual interfaces\n' % nwpan)
        if iot_module == 'fakelb':
            os.system('modprobe fakelb numlbs=%s' % nwpan)
        elif iot_module == 'mac802154_hwsim':
            os.system('modprobe mac802154_hwsim')
        else:
            os.system('insmod %s' % iot_module)

    @classmethod
    def kill_mod(cls, module):
        if cls.module_loaded(module):
            info("*** Killing %s\n" % module)
            os.system('rmmod %s' % module)

    @classmethod
    def module_loaded(cls, module_name):
        "Checks whether module is running"
        lsmod_proc = subprocess.Popen(['lsmod'], stdout=subprocess.PIPE)
        grep_proc = subprocess.Popen(['grep', module_name],
                                     stdin=lsmod_proc.stdout, stdout=subprocess.PIPE)
        grep_proc.communicate()  # Block until finished
        return grep_proc.returncode == 0

    @classmethod
    def stop(cls):
        'Stop wireless Module'
        cls.kill_mod('fakelb')
        cls.kill_mod('mac802154_hwsim')

    def get_virtual_wpan(self):
        'Gets the list of virtual wlans that already exist'
        cmd = "iwpan dev 2>&1 | grep Interface " \
              "| awk '{print $2}'"

        wlans = subprocess.check_output\
            (cmd, shell=True).decode('utf-8').split("\n")

        wlans.pop()
        wlan_list = sorted(wlans)
        wlan_list.sort(key=len, reverse=False)
        return wlan_list

    def getPhy(self):
        'Gets the list of virtual wlans that already exist'
        cmd = "iwpan dev | grep phy | sed -ne 's/phy#\([0-9]\)/\\1/p'"

        phy = subprocess.check_output\
            (cmd, shell=True).decode('utf-8').split("\n")

        phy = sorted(phy)
        phy.pop(0)
        return phy

    def assign_iface(self, nodes):
        """Assign virtual interfaces for all nodes
        :param nodes: list of wireless nodes"""
        log_filename = '/tmp/mininetwifi-fakelb.log'
        self.logging_to_file(log_filename)
        debug("\n*** Configuring interfaces with appropriated network"
              "-namespaces...\n")
        phy = self.getPhy()
        wlan_list = self.get_virtual_wpan()
        for id, node in enumerate(nodes):
            node.id = id
            for wlan in range(0, len(node.params['wpan'])):
                os.system('iwpan phy phy{} set netns {}'.format(phy[0], node.pid))
                node.cmd('ip link set {} down'.format(wlan_list[0]))
                node.cmd('ip link set {} name {}'.format(wlan_list[0], node.params['wpan'][wlan]))
                wlan_list.pop(0)
                phy.pop(0)

    def logging_to_file(self, filename):
        logging.basicConfig(filename=filename,
                            filemode='a',
                            level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                           )
