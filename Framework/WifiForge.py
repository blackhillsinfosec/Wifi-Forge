from subprocess import Popen, DEVNULL
import os
import importlib.util
import inspect
import keyboard  # Import the keyboard module for key handling
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

#The mininet-wifi API is not designed to be used within a menu loop,
#this function clears out variables from previous loops. Removing will cause the program to crash between runs.
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
    functions = {name: func for name, func in inspect.getmembers(module, inspect.isfunction) if name != 'print_banner'}
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

def main_menu():
    selected_index = 0
    total_functions = len(functions)
    redraw_needed = True  # Flag to track when to redraw

    while True:
        # Only clear the screen and redraw when an arrow key is pressed
        if redraw_needed:
            os.system("clear")  # Clear the terminal screen

            print_banner()
            print("\n\n                      " + GREEN + "Brought to you by "+ RED +"Black Hills InfoSec "+ RESET +"and "+ PURPLE +"Antisyphon"+ RESET)
            print("                   ┌────────────────────────────────────────────────────────┐")
            
            # Sort the functions alphabetically by function_name (lab title)
            sorted_functions = sorted(functions.items(), key=lambda x: x[1][0].lower())

            # Display all labs with the current selection
            for i, (filename, (function_name, _)) in enumerate(sorted_functions):
                formatted_name = function_name.replace('_', ' ').title()
                if i == selected_index:
                    lab_display = f"{BOLD_WHITE}[•] {formatted_name:<50}{RESET}"  # Highlight selected lab
                else:
                    lab_display = f"[ ] {formatted_name}"
                print(f"                   │ {lab_display:<54} │")  # Keep the borders white
                              
            print("                   ├────────────────────────────────────────────────────────┤")
            print("                   │  " + MAGENTA  + "Last Updated 12/19/2024 " + RESET  + "   │    " + RED + "Version 2.0.0" + RESET + "         │")
            print("                   ├────────────────────────────────────────────────────────┤")
            print("                   │           Version Name: "+CYAN+"Time for an upgrade"+RESET+"            │")
            print("                   └────────────────────────────────────────────────────────┘")
            
            redraw_needed = False  # Set the flag to false after drawing the screen

        # Read a key event (without showing output)
        event = keyboard.read_event(suppress=True)  # `suppress=True` suppresses key echoing

        if event.event_type == keyboard.KEY_DOWN:  # Check if a key is pressed down
            if event.name == 'up':
                selected_index = (selected_index - 1) % total_functions
                redraw_needed = True  # Set the flag to true to redraw
            elif event.name == 'down':
                selected_index = (selected_index + 1) % total_functions
                redraw_needed = True  # Set the flag to true to redraw
            elif event.name == 'enter':
                # Call the function for the selected lab
                func = sorted_functions[selected_index][1][1]
                os.system("clear")
                input() #clears keyboard input buffer before moving to CLI - otherwise up arrow + enter will cause a command from history to execute in mininet CLI.
                func()
                redraw_needed = True
                remove_old_variables()
            elif event.name == 'q' or event.name == 'Q':
                exit()
            else:
                redraw_needed = True

if __name__ == "__main__":
    os.system("service openvswitch-switch start")
    main_menu()
