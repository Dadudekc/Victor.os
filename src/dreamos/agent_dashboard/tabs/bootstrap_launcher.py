from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QSpinBox, QCheckBox, QGroupBox, QLineEdit,
    QMessageBox, QTextEdit
)
from PyQt5.QtCore import Qt, QProcess
import json
from pathlib import Path
from typing import List, Dict
import sys

class BootstrapLauncherTab(QWidget):
    def __init__(self):
        super().__init__()
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_output)
        self.process.readyReadStandardError.connect(self.handle_error)
        
        # Set working directory to project root
        self.process.setWorkingDirectory(str(Path.cwd()))
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Help Section
        help_group = QGroupBox("Quick Start Guide")
        help_layout = QVBoxLayout()
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h3>Dream.OS Bootstrap Launcher</h3>
        <p>This tool helps you manage and monitor agent bootstrap operations.</p>
        
        <h4>Operation Modes:</h4>
        <ul>
            <li><b>all</b>: Run both initial activation and continuous loop</li>
            <li><b>initial-only</b>: Just run initial agent activation</li>
            <li><b>loop-only</b>: Skip activation, run continuous loop</li>
        </ul>
        
        <h4>Overwatch Modes:</h4>
        <ul>
            <li><b>executional</b>: Focused task execution (default)</li>
            <li><b>planning</b>: Multi-phase planning process</li>
            <li><b>research</b>: Research and data collection</li>
            <li><b>exploratory</b>: Creative, fluid context</li>
        </ul>
        
        <h4>Timing:</h4>
        <ul>
            <li>Default delay: 3 minutes between cycles</li>
            <li>Use "No delay" for rapid testing (1 second)</li>
        </ul>
        
        <h4>Tips:</h4>
        <ul>
            <li>Select specific agents or run all 8</li>
            <li>Monitor status in the output window below</li>
            <li>Use Stop button to safely terminate operation</li>
        </ul>
        """)
        help_layout.addWidget(help_text)
        help_group.setLayout(help_layout)
        layout.addWidget(help_group)
        
        # Mode Selection
        mode_group = QGroupBox("Operation Mode")
        mode_layout = QVBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["all", "initial-only", "loop-only"])
        mode_layout.addWidget(QLabel("Mode:"))
        mode_layout.addWidget(self.mode_combo)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Overwatch Settings
        overwatch_group = QGroupBox("Overwatch Settings")
        overwatch_layout = QVBoxLayout()
        
        # Overwatch Mode
        self.overwatch_combo = QComboBox()
        self.overwatch_combo.addItems(["executional", "planning", "research", "exploratory"])
        overwatch_layout.addWidget(QLabel("Overwatch Mode:"))
        overwatch_layout.addWidget(self.overwatch_combo)
        
        # Overwatch Reason
        self.reason_input = QLineEdit()
        self.reason_input.setPlaceholderText("Enter reason for overwatch mode...")
        overwatch_layout.addWidget(QLabel("Reason:"))
        overwatch_layout.addWidget(self.reason_input)
        
        overwatch_group.setLayout(overwatch_layout)
        layout.addWidget(overwatch_group)
        
        # Timing Settings
        timing_group = QGroupBox("Timing Settings")
        timing_layout = QVBoxLayout()
        
        # Delay between cycles
        delay_layout = QHBoxLayout()
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 3600)
        self.delay_spin.setValue(180)
        self.delay_spin.setSuffix(" seconds")
        delay_layout.addWidget(QLabel("Delay between cycles:"))
        delay_layout.addWidget(self.delay_spin)
        timing_layout.addLayout(delay_layout)
        
        # No delay checkbox
        self.no_delay_check = QCheckBox("No delay (1 second)")
        timing_layout.addWidget(self.no_delay_check)
        
        timing_group.setLayout(timing_layout)
        layout.addWidget(timing_group)
        
        # Agent Selection
        agent_group = QGroupBox("Agent Selection")
        agent_layout = QVBoxLayout()
        
        # Agent list
        self.agent_list = []
        for i in range(1, 9):
            agent_name = f"Agent-{i}"
            checkbox = QCheckBox(agent_name)
            checkbox.setChecked(True)
            self.agent_list.append(checkbox)
            agent_layout.addWidget(checkbox)
        
        agent_group.setLayout(agent_layout)
        layout.addWidget(agent_group)
        
        # Control Buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Bootstrap")
        self.start_button.clicked.connect(self.start_bootstrap)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Bootstrap")
        self.stop_button.clicked.connect(self.stop_bootstrap)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        layout.addLayout(button_layout)
        
        # Status Output
        status_group = QGroupBox("Status Output")
        status_layout = QVBoxLayout()
        self.status_output = QTextEdit()
        self.status_output.setReadOnly(True)
        status_layout.addWidget(self.status_output)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
    def get_selected_agents(self) -> List[str]:
        return [cb.text() for cb in self.agent_list if cb.isChecked()]
    
    def build_command(self) -> List[str]:
        cmd = [sys.executable, "src/dreamos/tools/agent_bootstrap_runner.py"]
        
        # Mode
        cmd.extend(["--mode", self.mode_combo.currentText()])
        
        # Overwatch settings
        cmd.extend(["--overwatch", self.overwatch_combo.currentText()])
        if self.reason_input.text():
            cmd.extend(["--overwatch-reason", self.reason_input.text()])
        
        # Timing
        if self.no_delay_check.isChecked():
            cmd.append("--no-delay")
        else:
            cmd.extend(["--delay", str(self.delay_spin.value())])
        
        # Agents
        selected_agents = self.get_selected_agents()
        if selected_agents:
            cmd.extend(["--agents", ",".join(selected_agents)])
        
        return cmd
    
    def start_bootstrap(self):
        if not self.get_selected_agents():
            QMessageBox.warning(self, "Warning", "Please select at least one agent")
            return
        
        cmd = self.build_command()
        self.status_output.clear()
        self.status_output.append(f"Starting bootstrap with command:\n{' '.join(cmd)}\n")
        
        self.process.start(cmd[0], cmd[1:])
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
    
    def stop_bootstrap(self):
        if self.process.state() == QProcess.Running:
            self.process.terminate()
            self.process.waitForFinished(1000)
            if self.process.state() == QProcess.Running:
                self.process.kill()
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_output.append("\nBootstrap stopped by user")
    
    def handle_output(self):
        try:
            output = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
            self.status_output.append(output.strip())
        except Exception as e:
            self.status_output.append(f"Error reading output: {str(e)}")
    
    def handle_error(self):
        try:
            error = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
            self.status_output.append(f"Error: {error.strip()}")
        except Exception as e:
            self.status_output.append(f"Error reading error output: {str(e)}") 