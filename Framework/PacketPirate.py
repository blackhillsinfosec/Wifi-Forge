import os

def print_banner():
    os.system("clear")
    banner = """
 /$$$$$$$  /$$   /$$ /$$$$$$  /$$$$$$        /$$      /$$ /$$  /$$$$$$  /$$       /$$                 /$$                
| $$__  $$| $$  | $$|_  $$_/ /$$__  $$      | $$  /$ | $$|__/ /$$__  $$|__/      | $$                | $$                
| $$  \ $$| $$  | $$  | $$  | $$  \__/      | $$ /$$$| $$ /$$| $$  \__/ /$$      | $$        /$$$$$$ | $$$$$$$   /$$$$$$$
| $$$$$$$ | $$$$$$$$  | $$  |  $$$$$$       | $$/$$ $$ $$| $$| $$$$    | $$      | $$       |____  $$| $$__  $$ /$$_____/
| $$__  $$| $$__  $$  | $$   \____  $$      | $$$$_  $$$$| $$| $$_/    | $$      | $$        /$$$$$$$| $$  \ $$|  $$$$$$ 
| $$  \ $$| $$  | $$  | $$   /$$  \ $$      | $$$/ \  $$$| $$| $$      | $$      | $$       /$$__  $$| $$  | $$ \____  $$
| $$$$$$$/| $$  | $$ /$$$$$$|  $$$$$$/      | $$/   \  $$| $$| $$      | $$      | $$$$$$$$|  $$$$$$$| $$$$$$$/ /$$$$$$$/
|_______/ |__/  |__/|______/ \______/       |__/     \__/|__/|__/      |__/      |________/ \_______/|_______/ |_______/ 
"""
    print(banner)

def create_wifi_network():
    from wpa_four_way_handshake import create_wifi_network
    create_wifi_network()

def main_menu():
    while True:
        print_banner()
        print("\n\n+==================Simulation Selection==================+")
        print("[1] WPA Handshake Attack")
        print("[2] Option 2")
        print("[3] Option 3")
        print("[q] Quit")

        choice = input("Enter your choice: ")

        if choice == '1':
            create_wifi_network()
        elif choice == '2':
            # Call function for option 2
            pass
        elif choice == '3':
            # Call function for option 3
            pass
        elif choice == '4':
            # Call function for option 4
            pass
        elif choice == '5':
            # Call function for option 5
            pass
        elif choice == '6':
            # Call function for option 6
            pass
        elif choice.lower() == 'q':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main_menu()
