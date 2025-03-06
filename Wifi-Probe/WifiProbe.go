package main

import (
	"bufio"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strings"
	"gopkg.in/yaml.v2"
)

type Geofence struct {
	SSIDs []string `yaml:"ssids"`
}

var (
	iface   string
	outFile string
	geoFile string
)

func init() {
	flag.StringVar(&iface, "i", "wlan0", "Wireless interface to use")
	flag.StringVar(&outFile, "o", "output.py", "Output Python file to save network data")
	flag.StringVar(&geoFile, "gf", "", "YAML file with SSIDs to deauth")
	flag.Parse()

	if len(os.Args) == 1 {
		flag.Usage()
		os.Exit(1)
	}
}

// runCommand executes a system command and returns the output or error.
func runCommand(cmd string, args ...string) (string, error) {
	out, err := exec.Command(cmd, args...).CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("error running %s: %v", cmd, err)
	}
	return string(out), nil
}

// scanNetworks scans for networks using iwlist and captures WEP and WPS PIN.
func scanNetworks() []map[string]string {
	fmt.Println("[*] Performing multiple scans to capture all networks...")

	networkMap := make(map[string]map[string]string) // Stores networks by SSID
	reSSID := regexp.MustCompile(`ESSID:"(.*?)"`)
	reBSSID := regexp.MustCompile(`Address: ([\dA-Fa-f:]+)`)
	reChannel := regexp.MustCompile(`Channel (\d+)`)
	reEncKey := regexp.MustCompile(`Encryption key:(on|off)`)
	reSignal := regexp.MustCompile(`Signal level=(-?\d+) dBm`)
	reWPA2 := regexp.MustCompile(`IE: IEEE 802.11i/WPA2 Version 1`)
	reWPA3 := regexp.MustCompile(`IE: IEEE 802.11i/WPA3 Version 1`)
	reWEP := regexp.MustCompile(`IE: WEP`)
	reWPS := regexp.MustCompile(`WPS Version`)

	for i := 0; i < 10; i++ {
		fmt.Printf("[*] Scan %d/10...\n", i+1)
		output, err := runCommand("iwlist", iface, "scan")
		if err != nil {
			fmt.Println("[!] Scan failed:", err)
			continue
		}

		scanner := bufio.NewScanner(strings.NewReader(output))
		network := make(map[string]string)

		for scanner.Scan() {
			line := scanner.Text()

			if matches := reBSSID.FindStringSubmatch(line); matches != nil {
				network["BSSID"] = matches[1]
			}
			if matches := reSSID.FindStringSubmatch(line); matches != nil {
				network["SSID"] = matches[1]
			}
			if matches := reChannel.FindStringSubmatch(line); matches != nil {
				network["Channel"] = matches[1]
			}
			if matches := reSignal.FindStringSubmatch(line); matches != nil {
				network["Signal"] = matches[1] + " dBm"
			}

			// Detect encryption key status and WPA2/WPA3/WEP
			if matches := reEncKey.FindStringSubmatch(line); matches != nil {
				if matches[1] == "on" {
					// Check for WPA2, WPA3, or WEP encryption
					if reWPA2.MatchString(line) {
						network["Encryption"] = "WPA2"
					} else if reWPA3.MatchString(line) {
						network["Encryption"] = "WPA3"
					} else if reWEP.MatchString(line) {
						network["Encryption"] = "WEP"
					} else {
						network["Encryption"] = "Unknown"
					}
				} else {
					network["Encryption"] = "None"
				}
			}

			// Detect WPS Version (indicating WPS PIN availability)
			if reWPS.MatchString(line) {
				network["WPS"] = "Enabled"
			}

			// When a full network entry is found, add it
			if len(network) > 0 && strings.Contains(line, "Quality=") {
				ssid := network["SSID"]
				if ssid != "" {
					networkMap[ssid] = network // Overwrites duplicate SSIDs
				}
				network = make(map[string]string) // Reset for next entry
			}
		}
	}

	// Remove SSIDs that appear more than once
	seenSSIDs := make(map[string]int)
	for ssid := range networkMap {
		seenSSIDs[ssid]++
	}

	finalNetworks := []map[string]string{}
	for ssid, count := range seenSSIDs {
		if count == 1 {
			finalNetworks = append(finalNetworks, networkMap[ssid])
		}
	}

	fmt.Printf("[*] Total unique networks found: %d\n", len(finalNetworks))
	return finalNetworks
}

// loadGeofence loads the geofence file with SSIDs to target for deauth.
func loadGeofence(filename string) ([]string, error) {
	var geo Geofence
	data, err := os.ReadFile(filename)
	if err != nil {
		return nil, err
	}
	if err := yaml.Unmarshal(data, &geo); err != nil {
		return nil, err
	}
	return geo.SSIDs, nil
}

// saveToPythonFile saves the captured networks to a Python file with updated format.
func saveToPythonFile(networks []map[string]string) {
	file, err := os.Create(outFile)
	if err != nil {
		fmt.Println("[!] Failed to save:", err)
		return
	}
	defer file.Close()

	writer := bufio.NewWriter(file)

	// Write imports
	writer.WriteString("from mn_wifi.net import Mininet_wifi\n")
	writer.WriteString("from helper_functions.CONNECT_TMUX import CONFIG_TMUX\n")
	writer.WriteString("import os\n\n")

	// Write function definition
	writer.WriteString("def CRACKING_WPA_WITH_AIRCRACK():\n")
	writer.WriteString("    net = Mininet_wifi()\n\n")

	// Create attacker and AP sections
	writer.WriteString("    print('Creating Stations')\n")
	writer.WriteString("    attacker = net.addStation('a', wlans=1)\n\n")

	// Iterate over networks and generate AP configurations
	for _, net := range networks {
		ssid := net["SSID"]
		encType := net["Encryption"]
		channel := net["Channel"]
		passwd := "password" // Example password, can be customized based on the network type

		writer.WriteString(fmt.Sprintf("    # %s Network\n", encType))
		writer.WriteString(fmt.Sprintf("    host1 = net.addStation('host1', passwd='%s', encrypt='%s')\n", passwd, encType))
		writer.WriteString(fmt.Sprintf("    ap0 = net.addAccessPoint('ap0', ssid='%s', mode='g', channel='%s', passwd='%s', encrypt='%s', failMode='standalone', datapath='user')\n\n", ssid, channel, passwd, encType))

		// Add stations and AP links
		writer.WriteString("    print('Creating the Access Points...')\n")
		writer.WriteString("    net.configureWifiNodes()\n")
		writer.WriteString("    print('Adding Stations...')\n")
		writer.WriteString("    net.addLink(host1, ap0)\n\n")
	}

	// Finalize the configuration
	writer.WriteString("    net.build()\n")
	writer.WriteString("    ap0.start([])\n\n")
	writer.WriteString("    CONFIG_TMUX(['a'], 'WPA_CRACK')\n\n")
	writer.WriteString("    net.stop()\n")
	writer.WriteString("    os.system('clear')\n")

	writer.Flush()
	fmt.Println("[*] Scan results saved to", outFile)
}

func main() {
	networks := scanNetworks()
	if networks == nil {
		return
	}

	if geoFile != "" {
		geoSSIDs, err := loadGeofence(geoFile)
		if err != nil {
			fmt.Println("[!] Failed to load geofence file:", err)
			return
		}
		for _, net := range networks {
			for _, ssid := range geoSSIDs {
				if net["SSID"] == ssid {
					// Deauth Network Logic Here
				}
			}
		}
	} else {
		// Deauth Networks if needed
	}

	saveToPythonFile(networks) // Save networks to the new format
}
