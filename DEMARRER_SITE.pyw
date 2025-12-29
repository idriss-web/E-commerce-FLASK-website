"""

MIT License

Copyright (c) 2025 Idriss Chadili

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import sys
import subprocess
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QGroupBox,
    QLineEdit, QFormLayout, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class ServerControl(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Serveur Flask + ngrok")
        self.setFixedSize(350, 250)
        self.setStyleSheet("background-color: #121212; color: #eee;")

        font_bigger = QFont("Segoe UI", 14)
        font_bigger_bold = QFont("Segoe UI", 16)
        font_bigger_bold.setBold(True)

        self.status_group = QGroupBox("État du serveur")
        self.status_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; }")
        self.status_label = QLabel("OFF")
        self.status_label.setFont(font_bigger_bold)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: red")

        self.toggle_btn = QPushButton("Démarrer")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setFont(font_bigger)
        self.toggle_btn.clicked.connect(self.toggle_server)

        status_layout = QVBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.toggle_btn)
        self.status_group.setLayout(status_layout)

        self.config_group = QGroupBox("Configuration")
        self.config_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; }")

        form_layout = QFormLayout()
        self.port_input = QLineEdit()
        self.port_input.setFont(font_bigger)
        self.port_input.setText("5000")
        self.port_input.setMaxLength(5)
        self.port_input.setAlignment(Qt.AlignCenter)

        form_layout.addRow(QLabel("Port du serveur Flask :"), self.port_input)
        self.config_group.setLayout(form_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.config_group)
        main_layout.addWidget(self.status_group)
        self.setLayout(main_layout)

        self.index_process = None
        self.main_process = None
        self.ngrok_process = None

    def toggle_server(self):
        if self.toggle_btn.isChecked():
            port = self.port_input.text()
            if not port.isdigit() or not (1 <= int(port) <= 65535):
                QMessageBox.warning(self, "Erreur", "Veuillez entrer un port valide (1-65535).")
                self.toggle_btn.setChecked(False)
                return
            if port == "3000":
                QMessageBox.warning(self, "Erreur", "Port 3000 est réservé pour la page d'accueil.")
                self.toggle_btn.setChecked(False)
                return
            self.start_processes(port)
            self.status_label.setText("ON")
            self.status_label.setStyleSheet("color: #00ff00")
            self.toggle_btn.setText("Arrêter")
            self.port_input.setEnabled(False)
            webbrowser.open("http://127.0.0.1:3000")
        else:
            self.stop_processes()
            self.status_label.setText("OFF")
            self.status_label.setStyleSheet("color: red")
            self.toggle_btn.setText("Démarrer")
            self.port_input.setEnabled(True)

    def start_processes(self, port):
        self.index_process = subprocess.Popen([sys.executable, "index.py", "3000"])
        self.main_process = subprocess.Popen([sys.executable, "main.py", port])
        self.ngrok_process = subprocess.Popen(["ngrok", "http", port])

    def stop_processes(self):
        for process in [self.index_process, self.main_process, self.ngrok_process]:
            if process:
                process.terminate()
        self.index_process = None
        self.main_process = None
        self.ngrok_process = None

app = QApplication([])
window = ServerControl()
window.show()
sys.exit(app.exec_())
