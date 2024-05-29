# author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)


from os import system as sh
from subprocess import check_output as co, PIPE, Popen
import logging
from mininet.log import debug, info


class module(object):
    "wwan_hwsim module"

    externally_managed = False
    devices_created_dynamically = False

    def __init__(self, nodes, nwwan, wwan_module):
        self.start(nodes, nwwan, wwan_module)

    def start(self, nodes, nwwan, wwan_module):
        """
        :param nodes: list of nodes
        :param nwwan: number of wwan radios
        :param wwan_module: dir of a wwan_hwsim alternative module
        """

        self.load_module(nwwan, wwan_module)  # Initatilize wwan_hwsim module
        self.assign_iface(nodes)  # iface assign

    def load_module(self, nwwan, wwan_module):
        """ Load WiFi Module
        :param nwwan: number of radios
        :param wwan_module: dir of a wwan_hwsim alternative module"""
        debug('Loading %s virtual interfaces\n' % nwwan)
        if wwan_module == 'wwan_hwsim':
            sh('modprobe wwan_hwsim devices={}'.format(nwwan))
        else:
            sh('insmod %s devices={}'.format(wwan_module, nwwan))

    @classmethod
    def kill_mod(cls, module):
        if cls.module_loaded(module):
            info("*** Killing %s\n" % module)
            sh('rmmod %s' % module)

    @classmethod
    def module_loaded(cls, module_name):
        "Checks whether module is running"
        lsmod_proc = Popen(['lsmod'], stdout=PIPE)
        grep_proc = Popen(['grep', module_name], stdin=lsmod_proc.stdout, stdout=PIPE)
        grep_proc.communicate()  # Block until finished
        return grep_proc.returncode == 0

    @classmethod
    def stop(cls):
        'Stop wwan_hwsim module'
        cls.kill_mod('wwan_hwsim')

    def get_virtual_wwan(self):
        'Gets the list of virtual wlans that already exist'
        cmd = "ip link 2>&1 | grep POINTOPOINT | awk '{print $2}' | tr -d \':\'"
        wwans = co(cmd, shell=True).decode('utf-8').split("\n")

        wwans.pop()
        wwan_list = sorted(wwans)
        wwan_list.sort(key=len, reverse=False)
        return wwan_list

    def assign_iface(self, nodes):
        """Assign virtual interfaces for all nodes
        :param nodes: list of wireless nodes"""
        log_filename = '/tmp/mininetwifi-wwan_hwsim.log'
        self.logging_to_file(log_filename)
        debug("\n*** Configuring interfaces with appropriated network"
              "-namespaces...\n")
        wwan_list = self.get_virtual_wwan()
        for node in nodes:
            for wlan in range(0, len(node.params['wwan'])):
                sh('ip link set {} netns {}'.format(wwan_list[0], node.pid))
                node.cmd('ip link set {} down'.format(wwan_list[0]))
                node.cmd('ip link set {} name {}'.format(wwan_list[0], node.params['wwan'][wlan]))
                wwan_list.pop(0)

    def logging_to_file(self, filename):
        logging.basicConfig(filename=filename,
                            filemode='a',
                            level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                           )