import os
import subprocess
import paramiko
import sys
import socket
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, QVBoxLayout, QComboBox


class ServerControlGUI(QMainWindow):
    def __init__(self):
        super(ServerControlGUI, self).__init__()

        self.setWindowTitle("Hexapod Server Control by Sazid")
        self.setGeometry(200, 200, 420, 420)
        self.setStyleSheet("background-color: #F0F8FF;")  # Light blue background

        self.layout = QVBoxLayout()

        # Wi-Fi Selection
        self.ssid_dropdown = QComboBox(self)
        self.ssid_dropdown.setGeometry(50, 50, 300, 30)
        self.ssid_dropdown.addItem("🔍 Scanning Wi-Fi...")  # Default placeholder
        self.scan_wifi()  # Call the scan_wifi method to populate the dropdown

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Enter Wi-Fi Password")
        self.password_input.setGeometry(50, 90, 300, 30)
        self.password_input.setEchoMode(QLineEdit.Password)

        self.connect_wifi_btn = QPushButton("📡 Connect to Wi-Fi", self)
        self.connect_wifi_btn.setGeometry(50, 130, 300, 40)
        self.connect_wifi_btn.clicked.connect(self.connect_to_wifi)

        self.status_label = QLabel("🔴 Not Connected", self)
        self.status_label.setGeometry(50, 180, 300, 30)
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: red;")

        self.start_btn = QPushButton("🟢 Start Server", self)
        self.start_btn.setGeometry(50, 220, 300, 40)
        self.start_btn.clicked.connect(self.start_server)
        self.start_btn.setEnabled(False)

        self.stop_btn = QPushButton("🔴 Stop Server", self)
        self.stop_btn.setGeometry(50, 270, 300, 40)
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)

        self.exit_btn = QPushButton("🚪 Exit", self)
        self.exit_btn.setGeometry(50, 320, 300, 40)
        self.exit_btn.clicked.connect(self.close)

        self.rpi_host = None  # Dynamic IP will be stored here

    def scan_wifi(self):
        """Scan for available Wi-Fi networks on Raspberry Pi using nmcli."""
        try:
            # Run the nmcli command with sudo to list Wi-Fi networks
            command = ["sudo", "nmcli", "device", "wifi", "list"]

            # Run the command and capture the output
            result = subprocess.run(command, capture_output=True, text=True)

            # Check if the command executed successfully
            if result.returncode != 0:
                print("Error scanning Wi-Fi:", result.stderr)
                self.ssid_dropdown.clear()
                self.ssid_dropdown.addItem("❌ Wi-Fi scan failed")
                return

            # Print output to debug and verify network scan
            print(result.stdout)

            # Parse the output to extract SSIDs
            networks = []
            for line in result.stdout.splitlines():
                if "SSID" not in line and line.strip():
                    networks.append(line.split()[0])  # Extract SSID

            # Return networks found and populate the dropdown
            self.ssid_dropdown.clear()  # Clear old data
            if networks:
                for network in networks:
                    self.ssid_dropdown.addItem(network)
            else:
                self.ssid_dropdown.addItem("❌ No networks found")

        except Exception as e:
            print("Wi-Fi Scan Error:", e)
            self.ssid_dropdown.clear()
            self.ssid_dropdown.addItem("❌ Wi-Fi scan error")

    def connect_to_wifi(self):
        """Connect Raspberry Pi to Wi-Fi using selected SSID and entered Password."""
        ssid = self.ssid_dropdown.currentText().strip()
        password = self.password_input.text().strip()

        if not ssid or ssid.startswith("❌") or not password:
            self.status_label.setText("❌ Select a Wi-Fi & enter password!")
            self.status_label.setStyleSheet("color: red;")
            return

        try:
            wifi_config = f"""
            country=US
            ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
            update_config=1

            network={{
                ssid="{ssid}"
                psk="{password}"
                key_mgmt=WPA-PSK
            }}
            """
            with open("/etc/wpa_supplicant/wpa_supplicant.conf", "w") as file:
                file.write(wifi_config)

            subprocess.run(["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"])
            self.status_label.setText("✅ Wi-Fi Connected, Getting IP...")
            self.status_label.setStyleSheet("color: green;")

            self.rpi_host = self.get_raspberry_pi_ip()
            if self.rpi_host:
                self.status_label.setText(f"✅ Connected! IP: {self.rpi_host}")
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(True)
            else:
                self.status_label.setText("❌ Failed to get IP")
                self.status_label.setStyleSheet("color: red;")

        except Exception as e:
            self.status_label.setText(f"❌ Error: {e}")
            self.status_label.setStyleSheet("color: red;")

    def get_raspberry_pi_ip(self):
        """Find the Raspberry Pi's dynamic IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect(("8.8.8.8", 80))  # Google's DNS
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            print("IP Retrieval Error:", e)
            return None

    def connect_ssh(self):
        """Establish SSH connection to Raspberry Pi."""
        if not self.rpi_host:
            self.status_label.setText("❌ No IP found! Connect Wi-Fi first.")
            return None

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.rpi_host, username="sakhtar", password="raspberry", timeout=5)
            return ssh
        except Exception as e:
            self.status_label.setText("❌ SSH Connection Failed")
            print("SSH Error:", e)
            return None

    def start_server(self):
        """Start `server.py` on Raspberry Pi."""
        ssh = self.connect_ssh()
        if ssh:
            try:
                stdin, stdout, stderr = ssh.exec_command("pgrep -f server.py")
                if stdout.read().strip():
                    self.status_label.setText("🟢 Server is already running")
                    self.status_label.setStyleSheet("color: green;")
                    ssh.close()
                    return

                command = "source ~/HexapodGUI/myenv/bin/activate && nohup python ~/HexapodGUI/server.py > server.log 2>&1 &"
                ssh.exec_command(command)
                self.status_label.setText("🟢 Server Started")
                self.status_label.setStyleSheet("color: green;")

            except Exception as e:
                self.status_label.setText(f"❌ Error: {e}")
                self.status_label.setStyleSheet("color: red;")
            finally:
                ssh.close()

    def stop_server(self):
        """Stop `server.py` on Raspberry Pi."""
        ssh = self.connect_ssh()
        if ssh:
            try:
                ssh.exec_command("pkill -f server.py")
                self.status_label.setText("🔴 Server Stopped")
                self.status_label.setStyleSheet("color: red;")
            except Exception as e:
                self.status_label.setText(f"❌ Error: {e}")
                self.status_label.setStyleSheet("color: red;")
            finally:
                ssh.close()


def run_gui():
    app = QApplication(sys.argv)
    win = ServerControlGUI()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run_gui()
