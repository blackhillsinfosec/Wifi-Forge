import os
with open("first_install_check","r+") as file:
	content = file.read()
	if "1" in content:
		os.system("cd MiniNet-Framework/DevSetup/mininet-wifi && sudo python3 Joes_setup.py && cd  ../../")
		file.truncate(0)
# ANSI escape codes for colors
RED = "\033[91m"
GREEN = "\033[92m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
RESET = "\033[0m"

# BANNER CALL

def print_banner():
    os.system("clear")
    banner = """                             ,                     ,                                                 
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
  ;       ;@         ,;.    ;#t      ,;.          ;#t                                  ;;           """
    print(banner)

# IMPORT THE FUNCTIONS FROM FILES

def create_wifi_network_4_way_handshake():
    from wpa_four_way_handshake import create_wifi_network_4_way_handshake
    create_wifi_network_4_way_handshake()

# SWITCH CASE WITH FUNCTION CALLS

def main_menu():
    while True:
        print_banner()
        print("\n\n                             " + GREEN + "Brought to you by Black Hills InfoSec" + RESET)
        print("                   +==================Simulation Selection==================+")
        print("                   | ["+CYAN+"1"+RESET+"] WPA 4 Way Handshake Attack                         |")
        print("                   | ["+CYAN+"h"+RESET+"] Help                                               |")
        print("                   | ["+CYAN+"q"+RESET+"] Quit                                               |")
        print("                   +========================================================+")
        print("                   |  " + MAGENTA  + "Last Updated 5/15/2024 " + RESET  + "   |    " + RED + "Version 1.0.0" + RESET + "          |")
        print("                   +========================================================+")
        print("                   |                Version Name: "+CYAN+"New Frontier"+RESET+"              |")
        print("                   +========================================================+")
        choice = input("\n                    Select Lab: ")

        if choice == '1':
            

            create_wifi_network_4_way_handshake()
        elif choice == '2':
            # Call function for option 2
            pass
        elif choice == 'h':
            # Call function for option 2
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
            continue
        elif choice.lower() == 'q':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main_menu()
