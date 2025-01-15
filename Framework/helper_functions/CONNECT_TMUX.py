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

        #Split the window up into panes

        for index, node in enumerate(nodes):
            if index != len(nodes) - 1:
                panes[node] = window.panes[len(window.panes) - 1].split(direction=PaneDirection.Left, attach=False)
            process_id = check_output(["ps aux | grep -G 'mininet:"+node+"' | grep -v 'grep' | grep -v 'ap' | awk '{print $2}'"], shell=True).decode("utf-8")
            subprocess.Popen(["tmux", "send-keys", "-t", f"{session_name}:0.{index}", f"exec sudo nsenter -t {process_id.rstrip()} -m -u -i -n -p bash", "C-m"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(session.cmd("select-layout", "tiled").stderr)

        session.attach()
    except Exception as err:
        print(err)
        subprocess.Popen(["tmux", "kill-session", "-t", session_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    subprocess.Popen(["tmux", "kill-session", "-t", session_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)





