#!/usr/bin/env python

import curses
from curses import panel
from subprocess import Popen, DEVNULL
import os
import importlib.util
import inspect
from mn_wifi.mobility import Mobility, ConfigMobLinks
from mn_wifi.module import Mac80211Hwsim

# ANSI escape codes for colors
RED = "\033[91m"
GREEN = "\033[92m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
PURPLE = "\033[35m"
BLUE = "\033[34m"
YELLOW = "\033[93m"  # Yellow for highlighting
RESET = "\033[0m"
BOLD_WHITE = "\033[1;97m"

# BANNER CALL
def print_banner():
    os.system("clear")
    print("""
    
                                     ⣀⣤⣶⣿⠷⠾⠛⠛⠛⠛⠷⠶⢶⣶⣤⣄⡀⠀⠀⠀⠀⠀⠀
                                  ⣀⣴⡾⠛⠉⠁⠀⣰⡶⠶⠶⠶⠶⠶⣶⡄⠀⠉⠛⠿⣷⣄⡀⠀⠀⠀
                                ⣠⣾⠟⠁⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⣼⠃⠀⠀⠀⠀⠈⠛⢿⣦⡀⠀
                              ⢠⣼⠟⠁⠀⠀⠀⠀⣠⣴⣶⣿⡇⠀⠀⠀⠀⠀⣿⣷⣦⣄⠀⠀⠀⠀⠀⠙⣧⡀
                              ⣿⡇⠀⠀⠀⢀⣴⣾⣿⣿⣿⣿⣇⠀⠀⠀⠀⠸⣿⣿⣿⣿⣿⣦⡀⠀⠀⠀⢈⣷
                              ⣿⣿⣦⡀⣠⣾⣿⣿⣿⡿⠟⢻⣿⠀⠀⠀⠀⢠⣿⠻⢿⣿⣿⣿⣿⣆⣀⣠⣾⣿
                              ⠉⠻⣿⣿⣿⣿⣽⡿⠋⠀⠀⠸⣿⠀⠀⠀⠀⢸⡿⠀⠀⠉⠻⣿⣿⣿⣿⣿⠟⠁
                                ⠈⠙⠛⣿⣿⠀⠀⠀⠀⢀⣿⠀⠀⠀⠀⢸⣇⠀⠀⠀⠀⣹⣿⡟⠋⠁⠀⠀
                                    ⢿⣿⣷⣄⣀⣴⣿⣿⣤⣤⣤⣤⣼⣿⣷⣀⣀⣾⣿⣿⠇⠀⠀⠀⠀
                                    ⠈⠻⢿⣿⣿⣿⣿⣿⠟⠛⠛⠻⣿⣿⣿⣿⣿⡿⠛⠉⠀⠀⠀⠀⠀
                                       ⠉⠉⠁⣿⡇⠀⠀⠀⠀⢸⣿⡏⠙⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀
                                          ⣿⣷⣄⠀⠀⣀⣾⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                           ⠙⢿⣿⣿⣿⣿⣿⣏

            ██╗       ██╗██╗███████╗██╗  ███████╗ █████╗ ██████╗  ██████╗ ███████╗
            ██║  ██╗  ██║██║██╔════╝██║  ██╔════╝██╔══██╗██╔══██╗██╔════╝ ██╔════╝
            ╚██╗████╗██╔╝██║█████╗  ██║  █████╗  ██║  ██║██████╔╝██║  ██╗ █████╗  
             ████╔═████║ ██║██╔══╝  ██║  ██╔══╝  ██║  ██║██╔══██╗██║  ╚██╗██╔══╝  
              ██╔╝ ╚██╔╝ ██║██║     ██║  ██║     ╚█████╔╝██║  ██║╚██████╔╝███████╗
              ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝      ╚════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
    """)

def remove_old_variables():
    ConfigMobLinks.aps = []
    Mac80211Hwsim.hwsim_ids = []
    os.system("mn -c")

# Function to import module and get the first function from it
def import_module_and_get_function(file_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Get the first function defined in the module, ignoring 'print_banner'
    functions = {name: func for name, func in inspect.getmembers(module, inspect.isfunction) if name != 'print_banner' and name != "CONFIG_TMUX"}
    if functions:
        function_name, function = next(iter(functions.items()))
        return function_name, function
    return None, None

# Function to read the names of .py files in a directory, import the first function from each, and allow calling them
def load_functions_from_py_files(directory):
    function_dict = {}
    current_script = os.path.basename(__file__)
    for filename in os.listdir(directory):
        if filename.endswith(".py") and not filename.startswith(".") and filename != current_script:
            module_name = filename[:-3]  # Remove the .py extension
            file_path = os.path.join(directory, filename)
            function_name, function = import_module_and_get_function(file_path, module_name)
            if function_name and function:
                function_dict[filename] = (function_name, function)
    return function_dict

# Ensure this variable is populated before it's used
directory = os.path.dirname(os.path.realpath(__file__)) + "/labs"  # Current directory
functions = load_functions_from_py_files(directory)

print(functions)

class Menu(object):
    def __init__(self, items, stdscreen):
        self.window = stdscreen.subwin(0, 0)
        self.window.keypad(1)
        self.panel = panel.new_panel(self.window)
        self.panel.hide()
        panel.update_panels()

        self.position = 0
        self.items = items
        self.items.append(("exit", "exit"))

    def navigate(self, n):
        self.position += n
        if self.position < 0:
            self.position = 0
        elif self.position >= len(self.items):
            self.position = len(self.items) - 1

    def display(self):
        self.panel.top()
        self.panel.show()
        self.window.clear()

        while True:
            self.window.refresh()
            curses.doupdate()
            for index, item in enumerate(self.items):
                if index == self.position:
                    mode = curses.A_REVERSE
                else:
                    mode = curses.A_NORMAL

                msg = "%d. %s" % (index, item[0])
                self.window.addstr(1 + index, 1, msg, mode)

            key = self.window.getch()

            if key in [curses.KEY_ENTER, ord("\n")]:
                if self.position == len(self.items) - 1:
                    break
                else:
                    self.items[self.position][1]()

            elif key == curses.KEY_UP:
                self.navigate(-1)

            elif key == curses.KEY_DOWN:
                self.navigate(1)

        self.window.clear()
        self.panel.hide()
        panel.update_panels()
        curses.doupdate()

class MyApp(object):
    def __init__(self, stdscreen):
        self.screen = stdscreen
        curses.curs_set(0)

        test = [("HELLO", curses.beep), ("TEST", curses.flash)]
        main_menu = []

        for item in test:
            main_menu.append(item)

        print(main_menu)
        main_menu = Menu(main_menu, self.screen)
        main_menu.display()



if __name__ == "__main__":
    curses.wrapper(MyApp)
