#!/bin/python3
'''
Filename = CONNECT_TMUX.py
Author = Joseph Boyd

Purpose: Create a TMUX session with a pane for each mininet node. 
         Connect each pane to a mininet node session.
'''
import libtmux
from libtmux.pane import PaneDirection
import subprocess
from subprocess import check_output

def CONFIG_TMUX(nodes, lab_name):
    try:
        #Start TMUX server; intialize variables 
        server = libtmux.Server()
        session_name = f"WIFIFORGE-{lab_name}"
        session = server.new_session(session_name=session_name, attach=False)
        window = session.windows[0]
        panes = {}

        #Split the window up into panes; 1 pane for each required host 
        while len(window.panes) != len(nodes):
            window.panes[len(window.panes) - 1].split(direction=PaneDirection.Left, attach=False)

        #connect and name each pane after the node it's connected to
        for index, pane, in enumerate(window.panes):
            #host machine pane used when needing to launch browser/chrome processes
            #guis do not play well with the "remote bash" with nsenter 
            if nodes[index] == "host_machine": 
                session.cmd("select-pane", "-t", index, "-T", "host_machine")
            else:
                process_id = check_output(["ps aux | grep -G 'mininet:"+nodes[index]+"' | grep -v 'grep' | grep -v 'ap' | awk '{print $2}'"], shell=True).decode("utf-8")
                subprocess.Popen(
                    ["tmux", "send-keys", "-t", f"{session_name}:0.{index}", 
                    f"sudo nsenter -t {process_id.rstrip()} -m -u -i -n -p bash -c 'clear; exec bash'", "C-m"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                session.cmd("select-pane", "-t", index, "-T", nodes[index])

        #let the user click; make it look nice
        session.cmd("set", "-g", "pane-border-status", "top")
        session.cmd("set", "-g", "mouse", "on")
        print(session.cmd("select-layout", "tiled").stderr)

        #attach to the tmux session
        session.attach()
    except Exception as err:
        print(err)
        subprocess.Popen(["tmux", "kill-session", "-t", session_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    subprocess.Popen(["tmux", "kill-session", "-t", session_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)





