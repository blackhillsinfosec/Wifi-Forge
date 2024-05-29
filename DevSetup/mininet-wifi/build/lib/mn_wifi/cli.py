import sys
from select import poll

from mininet.cli import CLI as MN_CLI
from mininet.log import output, error


class CLI(MN_CLI):
    "Simple command-line interface to talk to nodes."
    MN_CLI.prompt = 'mininet-wifi> '

    def __init__(self, mn_wifi, stdin=sys.stdin, script=None, cmd=None):
        self.cmd = cmd
        if self.cmd:
            MN_CLI.mn = mn_wifi
            MN_CLI.stdin = stdin
            MN_CLI.inPoller = poll()
            MN_CLI.locals = { 'net': mn_wifi }
            self.do_cmd(self.cmd)
            return
        MN_CLI.__init__(self, mn_wifi, stdin=stdin, script=script)

    def do_cmd(self, cmd):
        """Read commands from an input file.
           Usage: source <file>"""
        MN_CLI.onecmd(self, line=cmd)
        self.cmd = None

    def do_stop(self, line):
        "stop mobility for a while"
        self.mn.stop_simulation()

    def do_start(self, line):
        "pause mobility for a while"
        self.mn.start_simulation()

    def do_distance(self, line):
        "Distance between two nodes."
        args = line.split()
        if len(args) != 2:
            error('invalid number of args: distance [sta or ap] [sta or ap]\n')
        elif len(args) == 2 and args[ 0 ] == args[ 1 ]:
            error('invalid. Source and Destination are equals\n')
        else:
            self.mn.get_distance(*args)

    def do_dpctl(self, line):
        """Run dpctl (or ovs-ofctl) command on all switches.
           Usage: dpctl command [arg1] [arg2] ..."""
        args = line.split()
        if len(args) < 1:
            error('usage: dpctl command [arg1] [arg2] ...\n')
            return
        nodesL2 = self.mn.switches + self.mn.aps
        for sw in nodesL2:
            output('*** ' + sw.name + ' ' + ('-' * 72) + '\n')
            output(sw.dpctl(*args))
