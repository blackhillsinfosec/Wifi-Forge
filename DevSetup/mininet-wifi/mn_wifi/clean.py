"""
Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)
"""

from subprocess import ( Popen, PIPE, check_output as co,
                         CalledProcessError )
from time import sleep
from os import system as sh, getpid
from glob import glob

from mininet.log import info
from mininet.util import decode
from mn_wifi.sixLoWPAN.clean import Cleanup as CleanLowpan
from mn_wifi.wwan.clean import Cleanup as CleanWwan
from mn_wifi.wmediumdConnector import w_server


class Cleanup(object):
    "Wrapper for cleanup()"
    socket_port = 0
    plot = None

    @classmethod
    def sh(cls, cmd):
        "Print a command and send it to the shell"
        result = Popen(['/bin/sh', '-c', cmd], stdout=PIPE).communicate()[0]
        return decode(result)

    @classmethod
    def killprocs(cls, pattern):
        "Reliably terminate processes matching a pattern (including args)"
        cls.sh('pkill -9 -f {}'.format(pattern))
        # Make sure they are gone
        while True:
            try:
                pids = co(['pgrep', '-f', pattern])
            except CalledProcessError:
                pids = ''
            if pids:
                cls.sh('pkill -9 -f {}'.format(pattern))
                sleep(.5)
            else:
                break

    @classmethod
    def module_loaded(cls, module):
        "Checks if module is loaded"
        lsmod_proc = Popen(['lsmod'], stdout=PIPE)
        grep_proc = Popen(['grep', module], stdin=lsmod_proc.stdout, stdout=PIPE)
        grep_proc.communicate()  # Block until finished
        return grep_proc.returncode == 0

    @classmethod
    def kill_mod(cls, module):
        if cls.module_loaded(module):
            info("*** Killing {}\n".format(module))
            sh('rmmod {}'.format(module))

    @classmethod
    def kill_mod_proc(cls):
        if cls.plot:
            cls.plot.close_plot()

        cls.killprocs('simple_switch_grpc')
        cls.killprocs('sumo-gui')
        cls.killprocs('olsrd2_static')
        cls.killprocs('hostapd')
        sleep(0.1)
        cls.sh('pkill babel')
        cls.sh('pkill batmand')

        w_server.disconnect()
        cls.sh('pkill wmediumd')
        sleep(0.1)

        info("\n*** Removing WiFi module and Configurations\n")        
        phy = co('find /sys/kernel/debug/ieee80211 -name hwsim | cut -d/ -f 6 | sort',
                 shell=True).decode('utf-8').split("\n")
        phy.pop()
        phy.sort(key=len, reverse=False)

        for phydev in phy:
            if str(getpid()) in phydev:
                p = Popen(["hwsim_mgmt", "-x", phydev], stdin=PIPE,
                          stdout=PIPE, stderr=PIPE, bufsize=-1)
                output, err_out = p.communicate()

        cls.kill_mod('mac80211_hwsim')
        cls.kill_mod('ifb')

        try:
            sh('pkill -f \'wpa_supplicant -B -Dnl80211\'')
        except:
            pass

        if glob('*.apconf'):
            sh('rm *.apconf')
        if glob('*.staconf'):
            sh('rm *.staconf')
        if glob('*wifiDirect.conf'):
            sh('rm *wifiDirect.conf')
        if glob('*.nodeParams'):
            sh('rm *.nodeParams')

        if cls.socket_port:
            info('\n*** Done\n')
            cls.sh('fuser -k %s/tcp >/dev/null 2>&1' % cls.socket_port)

        CleanLowpan.cleanup_6lowpan()
        CleanWwan.cleanup_wwan()

    @classmethod
    def cleanup_wifi(cls):
        """Clean up junk which might be left over from old runs;
           do fast stuff before slow dp and link removal!"""

        cls.kill_mod_proc()

        if glob('*-mn-telemetry.txt'):
            sh('rm *-mn-telemetry.txt')


cleanup_wifi = Cleanup.cleanup_wifi
