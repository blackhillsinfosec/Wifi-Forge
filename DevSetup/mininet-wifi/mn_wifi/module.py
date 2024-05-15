# author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)


from os import system as sh, path, getpid, devnull
from re import search
from time import sleep
from subprocess import check_output as co, PIPE, Popen, call, CalledProcessError
from logging import basicConfig, exception, DEBUG
from mininet.log import debug, info, error


class Mac80211Hwsim(object):
    "Loads mac80211_hwsim module"

    prefix = ""
    hwsim_ids = []
    externally_managed = False
    devices_created_dynamically = False
    phyWlans = None

    def __init__(self, on_the_fly=False, **params):
        if on_the_fly:
            self.configNodeOnTheFly(**params)
        else:
            self.start(**params)

    def get_wlan_list(self, phys, **params):
        if 'docker' in params:
            wlan_list = []
            for phy in range(len(phys)):
                wlan_list.append('wlan{}'.format(phy))
        else:
            wlan_list = self.get_wlan_iface()
        return wlan_list

    def get_hwsim_list(self):
        return 'find /sys/kernel/debug/ieee80211 -name hwsim | grep %05d ' \
               '| cut -d/ -f 6 | sort' % getpid()

    def configPhys(self, node, **params):
        phys = self.get_intf_list(self.get_hwsim_list())  # gets virtual and phy interfaces
        wlan_list = self.get_wlan_list(phys, **params)  # gets wlan list
        self.assign_iface(node, phys, wlan_list, (len(phys)-1), **params)

    def start(self, nodes, nradios, alt_module, rec_rssi, **params):
        """Starts environment
        :param nodes: list of wireless nodes
        :param nradios: number of wifi radios
        :param alt_module: dir of a mac80211_hwsim alternative module
        :params rec_rssi: if we set rssi to hwsim
        """
        if rec_rssi:
            self.add_phy_id(nodes)

        cmd = 'iw dev 2>&1 | grep Interface | awk \'{print $2}\''
        Mac80211Hwsim.phyWlans = self.get_intf_list(cmd)  # gets physical wlan(s)
        self.load_module(nradios, nodes, alt_module, **params)  # loads wifi module
        phys = self.get_intf_list(self.get_hwsim_list())  # gets virtual and phy interfaces
        wlan_list = self.get_wlan_list(phys, **params)  # gets wlan list
        for node in nodes:
            self.assign_iface(node, phys, wlan_list, **params)

    @staticmethod
    def create_static_radios(nradios, alt_module, modprobe):
        # Useful for kernel <= 3.13.x
        if nradios == 0: nradios = 1
        if alt_module:
            sh('insmod {} radios={}'.format(alt_module, nradios))
        else:
            sh('{}={}'.format(modprobe, nradios))

    def load_module(self, nradios, nodes, alt_module, **params):
        """Load WiFi Module
        nradios: number of wifi radios
        nodes: list of nodes
        alt_module: dir of a mac80211_hwsim alternative module
        """
        debug('Loading %s virtual wifi interfaces\n' % nradios)
        if not self.externally_managed:
            modprobe = 'modprobe mac80211_hwsim radios'
            if alt_module:
                output = sh('insmod {} radios=0 >/dev/null 2>&1'.format(alt_module))
            else:
                output = sh('{}=0 >/dev/null 2>&1'.format(modprobe))

            if output == 0:
                self.__create_hwsim_mgmt_devices(nradios, nodes, **params)
            else:
                self.create_static_radios(nradios, alt_module, modprobe)
        else:
            self.devices_created_dynamically = True
            self.__create_hwsim_mgmt_devices(nradios, nodes, **params)

    def configNodeOnTheFly(self, node):
        for _ in range(len(node.params['wlan'])):
            self.create_hwsim(len(Mac80211Hwsim.hwsim_ids))
        self.configPhys(node)

    def get_phys(self):
        # generate prefix
        num = 0
        numokay = False
        self.prefix = ""
        phys = co(self.get_hwsim_list(), shell=True).decode('utf-8').split("\n")

        while not numokay:
            self.prefix = "mn%05dp%02ds" % (getpid(), num)  # Add PID to mn-devicenames
            numokay = True
            for phy in phys:
                if phy.startswith(self.prefix):
                    num += 1
                    numokay = False
                    break
        return num

    def create_hwsim(self, n):
        self.get_phys()
        p = Popen(["hwsim_mgmt", "-c", "-n", self.prefix + ("%02d" % n)],
                  stdin=PIPE, stdout=PIPE, stderr=PIPE, bufsize=-1)
        output, err_out = p.communicate()
        if p.returncode == 0:
            m = search("ID (\d+)", output.decode())
            debug("Created mac80211_hwsim device with ID %s\n" % m.group(1))
            Mac80211Hwsim.hwsim_ids.append(m.group(1))
        else:
            error("\nError on creating mac80211_hwsim device "
                  "with name {}".format(self.prefix + ("%02d" % n)))
            error("\nOutput: {}".format(output))
            error("\nError: {}".format(err_out))

    def __create_hwsim_mgmt_devices(self, nradios, nodes, **params):
        if 'docker' in params:
            num = self.get_phys()
            self.docker_config(nradios=nradios, nodes=nodes, num=num, **params)
        else:
            try:
                for n in range(nradios):
                    self.create_hwsim(n)
            except:
                info("Warning! If you already had Mininet-WiFi installed "
                     "please run util/install.sh -W and then sudo make install.\n")

    @staticmethod
    def get_intf_list(cmd):
        'Gets all phys after starting the wireless module'
        phy = co(cmd, shell=True).decode('utf-8').split("\n")
        phy.pop()
        phy.sort(key=len, reverse=False)
        return phy

    @classmethod
    def load_ifb(cls, wlans):
        debug('\nLoading IFB: modprobe ifb numifbs={}'.format(wlans))
        sh('modprobe ifb numifbs={}'.format(wlans))

    def docker_config(self, nradios=0, nodes=None, dir='~/',
                      ip='172.17.0.1', num=0, **params):

        file = self.prefix + 'docker_mn-wifi.sh'
        if path.isfile(file):
            sh('rm {}'.format(file))
        sh("echo '#!/bin/bash' >> {}".format(file))
        sh("echo 'pid=$(sudo -S docker inspect -f '{{.State.Pid}}' "
           "{})' >> {}".format(params['container'], file))
        sh("echo 'sudo -S mkdir -p /var/run/netns' >> {}".format(file))
        sh("echo 'sudo -S ln -s /proc/$pid/ns/net/ /var/run/netns/$pid' >> {}".format(file))

        radios = []
        nodes_ = ''
        phys_ = ''
        for node in nodes:
            nodes_ += node.name + ' '
            radios.append(nodes.index(node))

        for radio in range(nradios):
            sh("echo 'sudo -S hwsim_mgmt -c -n %s%s' >> %s" %
               (self.prefix, "%02d" % radio, file))
            if radio in radios:
                radio_id = self.prefix + "%02d" % radio
                phys_ += radio_id + ' '
        sh("echo 'nodes=({})' >> {}".format(nodes_, file))
        sh("echo 'phys=({})' >> {}".format(phys_, file))
        sh("echo 'j=0' >> {}".format(file))
        sh("echo 'for i in ${phys[@]}' >> %s" % file)
        sh("echo 'do' >> %s" % file)
        sh("echo '    pid=$(ps -aux | grep \"${nodes[$j]}\" | grep -v 'hostapd' "
           "| awk \"{print \$2}\" | awk \"NR>=%s&&NR<=%s\")' "
           ">> %s" % (num+1, num+1, file))
        sh("echo '    sudo iw phy $i set netns $pid' >> %s" % file)
        sh("echo '    j=$((j+1))' >> {}".format(file))
        sh("echo 'done' >> {}".format(file))
        sh("scp %s %s@%s:%s" % (file, params['ssh_user'], ip, dir))
        sh("ssh %s@%s \'chmod +x %s%s; %s%s\'" %
           (params['ssh_user'], ip, dir, file, dir, file))

    @staticmethod
    def rename(node, wintf, newname):
        node.cmd('ip link set {} down'.format(wintf))
        node.cmd('ip link set {} name {}'.format(wintf, newname))
        node.cmd('ip link set {} up'.format(newname))

    def add_phy_id(self, nodes):
        id = 0
        for node in nodes:
            node.phyid = []
            for _ in range(len(node.params['wlan'])):
                node.phyid.append(id)
                id += 1

    def assign_iface(self, node, phys, wlan_list, id=0, **params):
        """Assign virtual interfaces for nodes
        nodes: list of nodes
        """
        from mn_wifi.node import AP

        log_filename = '/tmp/mn-wifi-mac80211_hwsim.log'
        self.logging_to_file(log_filename)

        try:
            pids = co(['pgrep', '-f', 'NetworkManager'])
        except CalledProcessError:
            pids = ''

        try:
            for wlan in range(len(node.params['wlan'])):
                f = open(devnull, 'w')
                rc = call(['which', 'nmcli'], stdout=f)
                if pids and rc == 0:
                        sh('nmcli device set {} managed no'.format(wlan_list[0]))
                        sleep(0.1)
                if isinstance(node, AP) and not node.inNamespace:
                    self.rename(node, wlan_list[0], node.params['wlan'][wlan])
                else:
                    if 'docker' not in params:
                        rfkill = co(
                            'rfkill list | grep %s | awk \'{print $1}\''
                            '| tr -d ":"' % phys[0],
                            shell=True).decode('utf-8').split('\n')
                        debug('rfkill unblock {}\n'.format(rfkill[0]))
                        sh('rfkill unblock {}'.format(rfkill[0]))
                        sh('iw phy {} set netns {}'.format(phys[id], node.pid))
                    node.cmd('ip link set {} down'.format(wlan_list[0]))
                    node.cmd('ip link set {} name {}'.format(wlan_list[0], node.params['wlan'][wlan]))
                wlan_list.pop(0)
                phys.pop(0)
        except:
            exception("Warning:")
            info("Warning! Error when loading mac80211_hwsim. "
                 "Please run sudo 'mn -c' before running your code.\n")
            info("Further information available at {}.\n".format(log_filename))
            exit(1)

    def logging_to_file(self, filename):
        basicConfig(filename=filename, filemode='a', level=DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',)

    @staticmethod
    def get_wlan_iface():
        "Build a new wlan list removing the physical wlan"
        wlan_list = []
        iface_list = co("iw dev 2>&1 | grep Interface | awk '{print $2}'",
                        shell=True).decode('utf-8').split('\n')
        for iface in iface_list:
            if iface and iface not in Mac80211Hwsim.phyWlans:
                wlan_list.append(iface)
        wlan_list = sorted(wlan_list)
        wlan_list.sort(key=len, reverse=False)
        return wlan_list
