import os
import importlib.util
import inspect

with open("first_install_check","r+") as file:
	content = file.read()
	if "1" in content:
		os.system("sudo python3 ../setupwififorge.py")
		print("First Time Setup Successful! Run WifiForge again!")
		exit()
# ANSI escape codes for colors
RED = "\033[91m"
GREEN = "\033[92m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
RESET = "\033[0m"

# BANNER CALL
def print_banner():
    os.system("clear")
    print("""                             ,                     ,                                                 
                             Et                    Et           :                                    
                             E#t                   E#t         t#,                                 ,;
                      t      E##t     t            E##t       ;##W.   j.               .Gt       f#i 
             ;        Ej     E#W#t    Ej           E#W#t     :#L:WE   EW,             j#W:     .E#t  
           .DL        E#,    E#tfL.   E#,          E#tfL.   .KG  ,#D  E##j          ;K#f      i#W,   
   f.     :K#L     LWLE#t    E#t      E#t          E#t      EE    ;#f E###D.      .G#D.      L#D.    
   EW:   ;W##L   .E#f E#t ,ffW#Dffj.  E#t       ,ffW#Dffj. f#.     t#iE#jG#W;    j#K;      :K#Wfff;  
   E#t  t#KE#L  ,W#;  E#t  ;LW#ELLLf. E#t        ;LW#ELLLf.:#G     GK E#t t##f ,K#f   ,GD; i##WLLLLt 
   E#t f#D.L#L t#K:   E#t    E#t      E#t          E#t      ;#L   LW. E#t  :K#E:j#Wi   E#t  .E#L     
   E#jG#f  L#LL#G     E#t    E#t      E#t          E#t       t#f f#:  E#KDDDD###i.G#D: E#t    f#E:   
   E###;   L###j      E#t    E#t      E#t          E#t        f#D#;   E#f,t#Wi,,,  ,K#fK#t     ,WW;  
   E#K:    L#W;       E#t    E#t      E#t          E#t         G#t    E#t  ;#W:      j###t      .D#; 
   EG      LE.        E#t    E#t      E#t          E#t          t     DWi   ,KK:      .G#t        tt 
   ;       ;@         ,;.    ;#t      ,;.          ;#t                                  ;;           """)

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
        if filename.endswith(".py") and filename != current_script:
            module_name = filename[:-3]  # Remove the .py extension
            file_path = os.path.join(directory, filename)
            function_name, function = import_module_and_get_function(file_path, module_name)
            if function_name and function:
                function_dict[filename] = (function_name, function)
    return function_dict

directory = os.getcwd()  # Current directory
functions = load_functions_from_py_files(directory)
    
# Display the loaded functions
# for filename, (function_name, function) in functions.items():
#     print(f"FUNCTION '{function_name}' FROM '{filename}'")
    
# SWITCH CASE WITH FUNCTION CALLS

def main_menu():
    print_banner()
    print("\n\n                             " + GREEN + "Brought to you by Black Hills InfoSec" + RESET)
    print("                   +==================Simulation Selection==================+")
    for i, (filename, (function_name, _)) in enumerate(functions.items(), start=1):
        formatted_name = function_name.replace('_', ' ').title()
        print("                   | [{: <1}] {: <50} |".format(i, formatted_name))                                       
    print("                   +========================================================+")
    print("                   |  " + MAGENTA  + "Last Updated 5/15/2024 " + RESET  + "   |    " + RED + "Version 1.0.0" + RESET + "          |")
    print("                   +========================================================+")
    print("                   |                Version Name: "+CYAN+"New Frontier"+RESET+"              |")
    print("                   +========================================================+")
    choice = input("\n                    Select Lab: ")

    choice.lower()     
    if choice == 'h':
        os.system("clear")
        print_banner()
        print("\n\n                   +=========================Help Page==============================+")
        print("                   | This tool was created with the intent to help upcoming testers |")
        print("                   | learn how to pentest Wireless networks. This is achieved by    |")
        print("                   | using Mininet. Mininet is a Software Defined network that was  |")
        print("                   | created to help learn and understand how networks work. By     |")
        print("                   | using tool we have created a foundation for learning about     |")
        print("                   | Wifi and security risks that come with it. To get start please |")
        print("                   | select a simulation and complete the given task.               |")
        print("                   +================================================================+")
        input("                   Press any key to continue...")
    elif choice == 'q':
        os.system("sudo mn -c")
        print("Exiting...")
    elif choice.isdigit() and 1 <= int(choice) <= len(functions):
        filename = list(functions.keys())[int(choice) - 1]
        _, func = functions[filename]
        os.system("clear")
        func()
    else:
        print("Invalid choice. Please try again.")

if __name__ == "__main__":
    os.system("service openvswitch-switch start")
    main_menu()
