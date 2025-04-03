from blessed import Terminal
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
                                  ██████████                                  
                             ████████████████████                             
                          ██████████████████████████                          
                       ████████████████████████████████                       
                     ███████████████████████████████████                      
                    █████████████████████████████████████                     
                    00 ███████                 ███████ 00                     
                    11 0 ██    ███████████████    ██ 0 11                     
                    00 1  0 █████████████████████ 0  1 00                     
                    11 0  1 █████████████████████ 1  0 11                     
                    00 1  0 0 ██████     ██████ 0 0  1 00                     
             11 0      1 0 1  \u001b[31m███\u001b[0m  1 0 1      0 11      
                1      0 1 0 \u001b[31m█████\u001b[0m 0 1 0      1         
                0      1 0   \u001b[31m1███1\u001b[0m   0 1      0         
                       1   \u001b[31m0 1 0\u001b[0m   1                
                            \u001b[31m1 0 1\u001b[0m                    
                            \u001b[31m0 1 0\u001b[0m                    
                            \u001b[31m1 0 1\u001b[0m                    
                                \u001b[31m1\u001b[0m                        
                                                                              
    ██╗       ██╗██╗███████╗██╗  ███████╗ █████╗ ██████╗  ██████╗ ███████╗    
    ██║  ██╗  ██║██║██╔════╝██║  ██╔════╝██╔══██╗██╔══██╗██╔════╝ ██╔════╝    
    ╚██╗████╗██╔╝██║█████╗  ██║  █████╗  ██║  ██║██████╔╝██║  ██╗ █████╗      
     ████╔═████║ ██║██╔══╝  ██║  ██╔══╝  ██║  ██║██╔══██╗██║  ╚██╗██╔══╝      
      ██╔╝ ╚██╔╝ ██║██║     ██║  ██║     ╚█████╔╝██║  ██║╚██████╔╝███████╗    
      ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝      ╚════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝    
            \u001b[31mBy BHIS\u001b[0m                                                                   
"""

def remove_old_variables():
    ConfigMobLinks.aps = []
    Mac80211Hwsim.hwsim_ids = []
    os.system("mn -c > /dev/null 2>&1")

def import_module_and_get_function(file_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    functions = {name: func for name, func in inspect.getmembers(module, inspect.isfunction) if name not in ('print_banner', 'CONFIG_TMUX')}
    return next(iter(functions.items()), (None, None))

def load_functions_from_py_files(directory):
    function_dict = {}
    current_script = os.path.basename(__file__)
    for filename in os.listdir(directory):
        if filename.endswith(".py") and not filename.startswith(".") and filename != current_script:
            module_name = filename[:-3]
            file_path = os.path.join(directory, filename)
            function_name, function = import_module_and_get_function(file_path, module_name)
            if function_name and function:
                function_dict[filename] = (function_name, function)
    return function_dict

directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), "framework", "labs")
functions = load_functions_from_py_files(directory)
file_names = list(functions.keys())
menu = [file.replace("_", " ").title()[:-3] for file in file_names]

def print_menu(term, selected_row_index):
    with term.hidden_cursor():
        print(term.clear)
        h, w = term.height, term.width
        banner_height = len(ascii_art.splitlines())
        menu_start_y = banner_height + 2

        # Print banner at the top
        for index, line in enumerate(ascii_art.splitlines()):
            print(term.move(index, w // 2 - len(line) // 2) + line)
        
        # Print menu below the banner, centered
        for index, row in enumerate(menu):
            y = menu_start_y + index
            x = w // 2 - len(row) // 2
            text = term.reverse(row) if index == selected_row_index else row
            print(term.move(y, x) + text)

def main():
    term = Terminal()
    current_row = 0
    with term.cbreak(), term.fullscreen():
        while True:
            print_menu(term, current_row)
            key = term.inkey()
            
            if key.code == term.KEY_UP and current_row > 0:
                current_row -= 1
            elif key.code == term.KEY_DOWN and current_row < len(menu) - 1:
                current_row += 1
            elif key.code in (term.KEY_ENTER, '\n', '\r'):
                os.system("clear")
                sys.stdout = open(os.devnull, 'w')
                functions[file_names[current_row]][1]()
                remove_old_variables()
                sys.stdout = sys.__stdout__
            elif key.lower() == 'q':
                exit(0)

os.system("clear")

if __name__ == "__main__":
    main()
