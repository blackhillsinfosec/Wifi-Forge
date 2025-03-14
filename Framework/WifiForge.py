#!/usr/bin/env python

import curses
from curses import panel
from subprocess import Popen, DEVNULL
import os
import importlib.util
import inspect
import sys
from mn_wifi.mobility import Mobility, ConfigMobLinks
from mn_wifi.module import Mac80211Hwsim


def print_banner():
	print("  ")

ascii_art = """
    
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
	 By Black Hills Information Security and Antisyphon
    """

def remove_old_variables():
	ConfigMobLinks.aps = []
	Mac80211Hwsim.hwsim_ids = []
	os.system("mn -c > /dev/null 2>&1")

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

class suspend_curses():
    """Context Manager to temporarily leave curses mode"""

    def __enter__(self):
        curses.endwin()

    def __exit__(self, exc_type, exc_val, tb):
        newscr = curses.initscr()
        newscr.addstr('Newscreen is %s\n' % newscr)
        newscr.refresh()
        curses.doupdate()

# Ensure this variable is populated before it's used
directory = os.path.dirname(os.path.realpath(__file__)) + "/labs"  # Current directory
functions = load_functions_from_py_files(directory)
file_names = []
menu = []

for file in functions.keys():
	formatted_name = file.replace("_", ' ').title()[:-3]
	file_names.append(file)
	menu.append(formatted_name)

def print_menu(stdscr, selected_row_index):
	h, w = stdscr.getmaxyx()
	stdscr.clear()
    #print the banner
	minH = 34
	minW = 148
	if (h > minH and w > minW):
		for index, line in enumerate(ascii_art.splitlines(), 2):
			x = w//2 - len(line)//2
			y = h//3 - len(ascii_art.splitlines())//2 + index
			stdscr.addstr(y, x, line)

		for index, row in enumerate(menu):
			x = w//2 - len(row)//2
			y = h//2 - (len(menu) - len(ascii_art.splitlines()))//2 + index
			if index == selected_row_index:
				stdscr.attron(curses.color_pair(1))
				stdscr.addstr(y, x, row)
				stdscr.attroff(curses.color_pair(1))
			else:
				stdscr.addstr(y, x, row)
	elif (h <= minH or  w <= minW) and (h > 23 and w > 40):
		for index, row in enumerate(menu):
			x = w//2 - len(row)//2
			y = h//2 - len(menu) + index
			if index == selected_row_index:
				stdscr.attron(curses.color_pair(1))
				stdscr.addstr(y, x, row)
				stdscr.attroff(curses.color_pair(1))
			else:
				stdscr.addstr(y, x, row)
	else:
		stdscr.addstr(0,0,"Window too small!")
	stdscr.refresh()


def main(stdscr):
	# turn off cursor blinking
	curses.curs_set(0)

	# color scheme for selected row
	curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

	# specify the current selected row
	current_row = 0

	print_menu(stdscr, current_row)


	while True:
		key = stdscr.getch()
		if key == curses.KEY_UP and current_row > 0:
			current_row -= 1
		elif key == curses.KEY_DOWN and current_row < len(menu)-1:
			current_row += 1
		elif key == curses.KEY_ENTER or key in [10, 13]:
			sys.stdout = open(os.devnull, 'w')
			with suspend_curses():
				func = functions[file_names[current_row]][1]
				func()
				remove_old_variables()
			sys.stdout = sys.__stdout__
	
		print_menu(stdscr, current_row)

		

if __name__ == "__main__":
	curses.wrapper(main)
