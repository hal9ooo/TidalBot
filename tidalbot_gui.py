import sys
import os
import json
from PyQt5 import QtWidgets, QtGui, QtCore

CONFIG_FILE = 'config.json'

class TidalBotGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TidalBot Configuration & Runner")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        self.setup_ui()
        self.load_config()

        self.process = QtCore.QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.stateChanged.connect(self.handle_state_changed)
        self.process.finished.connect(self.handle_finished)

    def setup_ui(self):
        # Configuration Group Box
        config_group = QtWidgets.QGroupBox("Configurazione TidalBot")
        config_layout = QtWidgets.QFormLayout(config_group)

        self.playlist_name_input = QtWidgets.QLineEdit()
        config_layout.addRow("Nome Playlist:", self.playlist_name_input)

        self.debug_mode_checkbox = QtWidgets.QCheckBox("Attiva modalità Debug")
        config_layout.addRow("Modalità Debug:", self.debug_mode_checkbox)

        self.search_limit_spinbox = QtWidgets.QSpinBox()
        self.search_limit_spinbox.setRange(1, 10)
        config_layout.addRow("Limite Ricerca Tidal:", self.search_limit_spinbox)

        self.candidate_limit_spinbox = QtWidgets.QSpinBox()
        self.candidate_limit_spinbox.setRange(1, 10)
        config_layout.addRow("Limite Candidati Debug:", self.candidate_limit_spinbox)

        self.layout.addWidget(config_group)

        # Song List Group Box
        songs_group = QtWidgets.QGroupBox("Lista Canzoni (una per riga)")
        songs_layout = QtWidgets.QVBoxLayout(songs_group)

        self.songs_textarea = QtWidgets.QPlainTextEdit()
        self.songs_textarea.setPlaceholderText("Inserisci qui le canzoni, una per riga (Artista - Titolo)")
        songs_layout.addWidget(self.songs_textarea)

        self.layout.addWidget(songs_group)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.save_button = QtWidgets.QPushButton("Salva Configurazione")
        self.save_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_button)

        self.run_button = QtWidgets.QPushButton("Esegui TidalBot")
        self.run_button.clicked.connect(self.run_tidalbot)
        button_layout.addWidget(self.run_button)
        
        self.clear_output_button = QtWidgets.QPushButton("Pulisci Output")
        self.clear_output_button.clicked.connect(self.clear_output)
        button_layout.addWidget(self.clear_output_button)

        self.layout.addLayout(button_layout)

        # Output Console
        self.output_console = QtWidgets.QTextEdit()
        self.output_console.setReadOnly(True)
        self.output_console.setFont(QtGui.QFont("Monospace", 10))
        self.layout.addWidget(QtWidgets.QLabel("Output TidalBot:"))
        self.layout.addWidget(self.output_console)

        # Status Bar
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status("Pronto.")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.playlist_name_input.setText(config.get('NOME_PLAYLIST', ""))
                self.debug_mode_checkbox.setChecked(config.get('DEBUG_MODE', False))
                self.search_limit_spinbox.setValue(config.get('TIDAL_SEARCH_LIMIT', 3))
                self.candidate_limit_spinbox.setValue(config.get('DEBUG_CANDIDATE_LIMIT', 3))
                self.songs_textarea.setPlainText("\n".join(config.get('LISTA_CANZONI', [])))
                self.update_status(f"Configurazione caricata da '{CONFIG_FILE}'.")
            except json.JSONDecodeError:
                self.update_status(f"Errore: Il file '{CONFIG_FILE}' non è un JSON valido.", is_error=True)
            except Exception as e:
                self.update_status(f"Errore durante il caricamento della configurazione: {e}", is_error=True)
        else:
            self.update_status(f"Il file '{CONFIG_FILE}' non esiste. Caricata configurazione predefinita.")
            # Set default values if file doesn't exist
            self.playlist_name_input.setText("Rock Power Classics – 100 brani energici")
            self.debug_mode_checkbox.setChecked(False)
            self.search_limit_spinbox.setValue(3)
            self.candidate_limit_spinbox.setValue(3)
            self.songs_textarea.setPlainText("")

    def save_config(self):
        config = {
            'NOME_PLAYLIST': self.playlist_name_input.text().strip(),
            'DEBUG_MODE': self.debug_mode_checkbox.isChecked(),
            'TIDAL_SEARCH_LIMIT': self.search_limit_spinbox.value(),
            'DEBUG_CANDIDATE_LIMIT': self.candidate_limit_spinbox.value(),
            'LISTA_CANZONI': [line.strip() for line in self.songs_textarea.toPlainText().split('\n') if line.strip()]
        }
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.update_status(f"Configurazione salvata in '{CONFIG_FILE}'.")
        except Exception as e:
            self.update_status(f"Errore durante il salvataggio della configurazione: {e}", is_error=True)

    def run_tidalbot(self):
        if self.process.state() == QtCore.QProcess.Running:
            self.update_status("TidalBot è già in esecuzione. Attendere il completamento.", is_error=True)
            return

        # First, save the current configuration
        self.save_config()

        self.output_console.clear()
        self.update_status("Avvio di tidalbot.py...")
        
        # Determine the Python executable path
        # It's good practice to use sys.executable to ensure the correct Python environment is used
        python_executable = sys.executable 
        
        # Start the tidalbot.py script as a new process
        # Using [python_executable, "tidalbot.py"] ensures it runs with the same python interpreter as the GUI
        self.process.start(python_executable, ["tidalbot.py"])

        if not self.process.waitForStarted(5000): # Wait up to 5 seconds for the process to start
            self.update_status("Errore nell'avvio di tidalbot.py.", is_error=True)
            self.output_console.append("Controlla che python e tidalbot.py siano nel PATH e che le dipendenze siano installate.")
        else:
            self.update_status("TidalBot avviato con successo.")
            self.run_button.setEnabled(False) # Disable run button while running

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode('utf-8').strip()
        if stdout:
            self.output_console.append(stdout)
            # Auto-scroll to the bottom
            self.output_console.verticalScrollBar().setValue(self.output_console.verticalScrollBar().maximum())

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode('utf-8').strip()
        if stderr:
            self.output_console.append(f"ERROR: {stderr}")
            # Auto-scroll to the bottom
            self.output_console.verticalScrollBar().setValue(self.output_console.verticalScrollBar().maximum())

    def handle_state_changed(self, state):
        if state == QtCore.QProcess.Running:
            self.update_status("TidalBot in esecuzione...")
        elif state == QtCore.QProcess.NotRunning:
            self.update_status("TidalBot non in esecuzione.")

    def handle_finished(self, exit_code, exit_status):
        self.run_button.setEnabled(True) # Re-enable run button
        if exit_status == QtWidgets.QProcess.NormalExit:
            self.update_status(f"TidalBot completato con codice di uscita: {exit_code}.")
            self.output_console.append(f"\n--- TidalBot completato (codice di uscita: {exit_code}) ---")
        else:
            self.update_status(f"TidalBot terminato in modo anomalo (codice: {exit_code}).", is_error=True)
            self.output_console.append(f"\n--- TidalBot terminato in modo anomalo (codice di uscita: {exit_code}) ---")
        self.output_console.verticalScrollBar().setValue(self.output_console.verticalScrollBar().maximum())


    def clear_output(self):
        self.output_console.clear()
        self.update_status("Output console pulita.")

    def update_status(self, message, is_error=False):
        if is_error:
            self.status_bar.setStyleSheet("color: red;")
        else:
            self.status_bar.setStyleSheet("color: black;")
        self.status_bar.showMessage(message)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    gui = TidalBotGUI()
    gui.show()
    sys.exit(app.exec_())