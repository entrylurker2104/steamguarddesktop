import sys
import json
import time
import os
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QListWidget, 
                             QProgressBar, QFrame, QFileDialog, QMessageBox, 
                             QTabWidget, QDialog, QLineEdit, QFormLayout, QStackedWidget)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject
import logging
from steam.guard import SteamAuthenticator
from steam.enums import EResult
from steam.steamid import SteamID
from steam.webauth import MobileWebAuth
from steam_auth_helper import SteamAuthHelper
from modern_auth import ModernSteamAuth

# Configura log para console
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
logger = logging.getLogger("SteamAuthApp")

SETTINGS_FILE = "accounts_config.json"

class SteamAuthApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(resource_path('lock.png')))
        self.setWindowTitle("Steam Authenticator Python")
        self.setFixedSize(400, 600)
        self.accounts = {} # Nome da conta -> Dados do maFile
        self.current_auth = None
        self.pending_confirmations = [] # Lista de objetos Confirmation
        
        self.apply_styles()
        self.init_ui()
        self.load_saved_accounts()
        
        # Timer de atualização
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_logic)
        self.timer.start(1000)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1922;
            }
            QTabWidget::pane {
                background-color: #171a21;
                border-top: 2px solid #2a475e;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background: #1b2838;
                color: #8f98a0;
                padding: 15px 30px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                margin-right: 5px;
                font-family: 'Segoe UI', system-ui;
                font-size: 13px;
                font-weight: bold;
                text-transform: uppercase;
            }
            QTabBar::tab:hover {
                background: #2a475e;
                color: white;
            }
            QTabBar::tab:selected {
                background: #2a475e;
                color: #66c0f4;
                border-bottom: 3px solid #66c0f4;
            }
            QLabel {
                color: #e5e5e5;
                font-family: 'Segoe UI', Arial;
            }
            #AccountTitle {
                font-size: 14px;
                font-weight: bold;
                color: #66c0f4;
                letter-spacing: 1px;
            }
            #CodeLabel {
                font-size: 68px;
                font-weight: 900;
                color: #ffffff;
                margin: 10px 0;
            }
            QFrame#MainCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1b2838, stop:1 #171a21);
                border-radius: 20px;
                border: 1px solid #305d7b;
            }
            QListWidget {
                background-color: rgba(23, 26, 33, 0.8);
                border: 1px solid #2a475e;
                border-radius: 15px;
                color: #c7d5e0;
                outline: none;
                padding: 8px;
            }
            QListWidget::item {
                background-color: #1b2838;
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 6px;
                border: 1px solid transparent;
            }
            QListWidget::item:hover {
                background-color: #2a475e;
                border: 1px solid #3d4450;
            }
            QListWidget::item:selected {
                background-color: #214b6b;
                border: 1px solid #66c0f4;
                color: white;
            }
            QPushButton {
                background-color: #3d4450;
                color: white;
                border-radius: 8px;
                padding: 12px 18px;
                font-weight: bold;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #4c5463;
            }
            QPushButton#ActionBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #214b6b, stop:1 #1b2838);
                border: 1px solid #305d7b;
            }
            QPushButton#ActionBtn:hover {
                background-color: #2a475e;
                border-color: #66c0f4;
            }
            QPushButton#AcceptBtn {
                background-color: #5c7e10;
            }
            QPushButton#AcceptBtn:hover {
                background-color: #6a8f13;
            }
            QPushButton#DenyBtn {
                background-color: #a34c32;
            }
            QProgressBar {
                border: none;
                background-color: #0f1922;
                height: 6px;
                border-radius: 3px;
                text-align: center;
                color: transparent;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66c0f4, stop:1 #214b6b);
                border-radius: 3px;
            }
            QLineEdit {
                background-color: #121418;
                border: 1px solid #2a475e;
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #66c0f4;
            }
        """)

    def init_ui(self):
        # Container Principal
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setCentralWidget(container)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # --- ABA 1: AUTENTICADOR ---
        tab1 = QWidget()
        layout1 = QVBoxLayout(tab1)
        layout1.setContentsMargins(20, 20, 20, 20)
        layout1.setSpacing(15)

        self.card = QFrame()
        self.card.setObjectName("MainCard")
        self.card.setMinimumHeight(200)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 30, 0, 30)
        
        self.label_account = QLabel("SELECT AN ACCOUNT")
        self.label_account.setObjectName("AccountTitle")
        self.label_account.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.label_code = QLabel("-----")
        self.label_code.setObjectName("CodeLabel")
        self.label_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Container para a barra de progresso (para dar padding lateral)
        progress_container = QWidget()
        p_layout = QVBoxLayout(progress_container)
        p_layout.setContentsMargins(40, 0, 40, 0)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(30)
        self.progress_bar.setFixedHeight(6)
        p_layout.addWidget(self.progress_bar)
        
        card_layout.addWidget(self.label_account)
        card_layout.addWidget(self.label_code)
        card_layout.addWidget(progress_container)
        
        layout1.addWidget(self.card)
        
        title_accounts = QLabel("AVAILABLE ACCOUNTS")
        title_accounts.setStyleSheet("font-size: 11px; font-weight: bold; color: #8f98a0; margin-top: 5px;")
        layout1.addWidget(title_accounts)
        
        self.list_accounts = QListWidget()
        self.list_accounts.itemClicked.connect(self.change_account)
        layout1.addWidget(self.list_accounts)
        
        btn_grid = QVBoxLayout()
        btn_grid.setSpacing(8)
        
        row1 = QHBoxLayout()
        btn_import = QPushButton("Import .maFile")
        btn_import.setObjectName("ActionBtn")
        btn_import.clicked.connect(self.import_mafile)
        btn_add_acc = QPushButton("Add Account")
        btn_add_acc.setObjectName("ActionBtn")
        btn_add_acc.clicked.connect(self.add_account_dialog)
        row1.addWidget(btn_import)
        row1.addWidget(btn_add_acc)
        
        row2 = QHBoxLayout()
        btn_copy = QPushButton("Copy Code")
        btn_copy.setStyleSheet("background-color: #66c0f4; color: #171a21;")
        btn_copy.clicked.connect(self.copy_code)
        btn_remove = QPushButton("Remove")
        btn_remove.setObjectName("DenyBtn")
        btn_remove.clicked.connect(self.remove_account)
        row2.addWidget(btn_copy)
        row2.addWidget(btn_remove)
        
        btn_grid.addLayout(row1)
        btn_grid.addLayout(row2)
        layout1.addLayout(btn_grid)

        # --- ABA 2: CONFIRMAÇÕES ---
        tab2 = QWidget()
        layout2 = QVBoxLayout(tab2)
        layout2.setContentsMargins(20, 20, 20, 20)
        layout2.setSpacing(15)
        
        conf_title = QLabel("PENDING CONFIRMATIONS")
        conf_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #8f98a0;")
        layout2.addWidget(conf_title)
        
        self.list_confirmations = QListWidget()
        layout2.addWidget(self.list_confirmations)

        conf_btns = QVBoxLayout()
        conf_btns.setSpacing(8)
        
        row_top = QHBoxLayout()
        self.btn_refresh_conf = QPushButton("Refresh List")
        self.btn_refresh_conf.setObjectName("ActionBtn")
        self.btn_refresh_conf.clicked.connect(self.fetch_confirmations)
        self.btn_login_session = QPushButton("Login to Session")
        self.btn_login_session.setObjectName("ActionBtn")
        self.btn_login_session.clicked.connect(self.login_for_session)
        row_top.addWidget(self.btn_refresh_conf)
        row_top.addWidget(self.btn_login_session)
        
        row_bottom = QHBoxLayout()
        self.btn_accept = QPushButton("Accept Selected")
        self.btn_accept.setObjectName("AcceptBtn")
        self.btn_accept.clicked.connect(lambda: self.handle_conf(True))
        self.btn_deny_conf = QPushButton("Deny")
        self.btn_deny_conf.setObjectName("DenyBtn")
        self.btn_deny_conf.clicked.connect(lambda: self.handle_conf(False))
        row_bottom.addWidget(self.btn_accept)
        row_bottom.addWidget(self.btn_deny_conf)
        
        conf_btns.addLayout(row_top)
        conf_btns.addLayout(row_bottom)
        layout2.addLayout(conf_btns)

        self.tabs.addTab(tab1, "Authenticator")
        self.tabs.addTab(tab2, "Confirmations")
    
        # Rodapé com Versão
        version_label = QLabel("SDA Python v1.0.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        version_label.setStyleSheet("color: #4b5259; font-size: 10px; margin-right: 10px; margin-bottom: 5px;")
        main_layout.addWidget(version_label)

    # --- LÓGICA DE DADOS ---
    def load_saved_accounts(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                self.accounts = json.load(f)
                self.list_accounts.clear()
                for acc_name in self.accounts:
                    self.list_accounts.addItem(acc_name)

    def import_mafile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open .maFile", "", "Steam Files (*.maFile)")
        if path:
            with open(path, 'r') as f:
                data = json.load(f)
                # O maFile pode ter 'account_name' or 'AccountName'
                name = data.get('account_name') or data.get('AccountName') or f"Account_{len(self.accounts)}"
                self.accounts[name] = data
                # Salva localmente
                self.save_accounts()
                self.load_saved_accounts()

    def save_accounts(self):
        with open(SETTINGS_FILE, 'w') as f_save:
            json.dump(self.accounts, f_save, indent=4)

    def remove_account(self):
        item = self.list_accounts.currentItem()
        if not item: return
        name = item.text()
        reply = QMessageBox.question(self, "Remove", f"Do you want to remove account '{name}'?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.accounts[name]
            self.save_accounts()
            self.load_saved_accounts()
            self.current_auth = None
            self.label_code.setText("-----")
            self.label_account.setText("SELECT AN ACCOUNT")

    def change_account(self, item):
        name = item.text()
        data = self.accounts[name]
        self.current_auth = SteamAuthenticator(data)
        self.label_account.setText(name.upper())
        
        # Verifica se já tem sessão salva
        if data.get("Session"):
            self.btn_login_session.setEnabled(False)
            self.btn_login_session.setText("Session Saved")
            
            # Restaura a sessão automaticamente
            try:
                session_data = data["Session"]
                class SessionWrapper:
                    def __init__(self, sess_data):
                        import requests
                        from steam.steamid import SteamID
                        self.steam_id = SteamID(sess_data['SteamID'])
                        self.oauth_token = sess_data['AccessToken']
                        self.session = requests.Session()
                        # Restaura cookies
                        self.session.cookies.set('sessionid', sess_data['SessionID'], domain='store.steampowered.com')
                        self.session.cookies.set('steamLoginSecure', f"{sess_data['SteamID']}||{sess_data['AccessToken']}", domain='store.steampowered.com')
                        self.logged_on = True
                
                self.current_auth.backend = SessionWrapper(session_data)
                # logger.info(f"Sessão restaurada para {name}")
            except Exception as e:
                logger.error(f"Error restoring session: {e}")
                # Se falhar a restauração, habilita o botão para logar de novo
                self.btn_login_session.setEnabled(True)
                self.btn_login_session.setText("Invalid Session")
        else:
            self.btn_login_session.setEnabled(True)
            self.btn_login_session.setText("Login to Session")

    def refresh_logic(self):
        rem = 30 - (int(time.time()) % 30)
        self.progress_bar.setValue(rem)
        if self.current_auth:
            self.label_code.setText(self.current_auth.get_code())

    def copy_code(self):
        QApplication.clipboard().setText(self.label_code.text())

    # --- LÓGICA DE CONFIRMAÇÕES ---
    def fetch_confirmations(self):
        if not self.current_auth:
            QMessageBox.warning(self, "Error", "Select an account first!")
            return
        
        self.list_confirmations.clear()
        self.list_confirmations.addItem("Fetching confirmations...")
        
        # Fazemos em uma thread para não travar a UI
        thread = threading.Thread(target=self._fetch_conf_task)
        thread.start()

    def _fetch_conf_task(self):
        try:
            # Note: Para confirmações, precisamos da logic-session.
            # Se o current_auth foi carregado de um maFile, ele tem os segredos.
            # Mas a lib 'steam' precisa que tenhamos feito login para ter os cookies.
            # Se não tivermos session, tentamos listar (pode falhar).
            confs = self.current_auth.get_confirmations()
            
            # Como estamos em thread, usamos QTimer.singleShot ou um sinal para atualizar a UI
            QTimer.singleShot(0, lambda: self._update_conf_ui(confs))
        except Exception as e:
            msg = str(e)
            QTimer.singleShot(0, lambda: self.list_confirmations.addItem(f"Erro: {msg}"))

    def _update_conf_ui(self, confs):
        self.list_confirmations.clear()
        self.pending_confirmations = confs
        if not confs:
            self.list_confirmations.addItem("No pending confirmations.")
            return
        for c in confs:
            # c.type_name costuma ser algo como 'Trade', 'Market'
            # c.creator_id é o ID do trade ou item
            self.list_confirmations.addItem(f"[{c.type_name}] {c.id}")

    def handle_conf(self, accept=True):
        idx = self.list_confirmations.currentRow()
        if idx < 0 or idx >= len(self.pending_confirmations):
            return
        
        conf = self.pending_confirmations[idx]
        action = "Accepting" if accept else "Denying"
        self.list_confirmations.addItem(f"... {action} {conf.id} ...")
        
        thread = threading.Thread(target=self._conf_action_task, args=(conf, accept))
        thread.start()

    def _conf_action_task(self, conf, accept):
        try:
            if accept:
                conf.approve()
            else:
                conf.deny()
            QTimer.singleShot(0, self.fetch_confirmations)
        except Exception as e:
            msg = str(e)
            QTimer.singleShot(0, lambda: QMessageBox.warning(self, "Error", f"Action failed: {msg}"))

    # --- NOVO: ADICIONAR CONTA ---
    def add_account_dialog(self):
        dialog = AddAccountDialog(self, only_session=False)
        if dialog.exec():
            self.load_saved_accounts()

    def login_for_session(self):
        if not self.current_auth:
            QMessageBox.warning(self, "Error", "Select an account first!")
            return
        dialog = AddAccountDialog(self, only_session=True, authenticator=self.current_auth)
        if dialog.exec():
            # Cria um wrapper que simula MobileWebAuth para compatibilidade
            class SessionWrapper:
                def __init__(self, auth):
                    self.session = auth.session
                    self.oauth_token = auth.access_token # ModernAuth usa access_token
                    self.steam_id = auth.steam_id
                    self.logged_on = True
            
            # Usa modern_auth
            self.current_auth.backend = SessionWrapper(dialog.modern_auth)
            
            # --- SALVAR SESSÃO NO ARQUIVO ---
            try:
                # Recupera o nome da conta atual (chave no dicionário self.accounts)
                # Precisamos encontrar qual conta tem o self.current_auth
                account_name = None
                for name, data in self.accounts.items():
                    # Compara por shared_secret ou algo único, ou confiamos no item selecionado da lista
                    if data.get('shared_secret') == self.current_auth.secrets.get('shared_secret'):
                        account_name = name
                        break
                
                if account_name:
                    mauth = dialog.modern_auth
                    session_id = mauth.session.cookies.get('sessionid', domain='store.steampowered.com')
                    
                    session_data = {
                        "SteamID": int(mauth.steam_id.as_64),
                        "AccessToken": mauth.access_token,
                        "RefreshToken": mauth.refresh_token,
                        "SessionID": session_id
                    }
                    
                    self.accounts[account_name]["Session"] = session_data
                    
                    with open(SETTINGS_FILE, 'w') as f:
                        json.dump(self.accounts, f, indent=4)
                        
                    logger.info(f"Session saved for {account_name}")
            except Exception as e:
                logger.error(f"Error saving session: {e}")
            # --------------------------------

            QMessageBox.information(self, "Session", "Session updated and saved! You can now check for confirmations.")
            self.fetch_confirmations()

class LoginSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(object)
    status = pyqtSignal(str)
    change_page = pyqtSignal(int) # Novo sinal para mudar de página

class AddAccountDialog(QDialog):
    def __init__(self, parent=None, only_session=False, authenticator=None):
        super().__init__(parent)
        self.setWindowIcon(QIcon(resource_path('lock.png')))
        self.only_session = only_session
        self.session_authenticator = authenticator # Guarda para auto-input do código
        self.setWindowTitle("Steam Login" if only_session else "Add Steam Account")
        self.setFixedSize(350, 480)
        self.parent_app = parent
        self.auth_helper = None
        self.modern_auth = None
        self.sa = None
        self.signals = LoginSignals()
        self.init_ui()
        self.apply_styles()
        
        # Conecta os sinais DEPOIS de criar a UI
        self.signals.finished.connect(self._handle_login_res)
        self.signals.error.connect(self._handle_login_err)
        self.signals.status.connect(self.label_status.setText)
        self.signals.change_page.connect(self.stack.setCurrentIndex) # Conexão segura

    def apply_styles(self):
        self.setStyleSheet(self.parent_app.styleSheet())
        self.container.setStyleSheet("""
            QFrame#DialogContainer {
                background-color: #171a21;
                border-radius: 15px;
                border: 1px solid #2a475e;
            }
            QLabel { color: #8f98a0; font-size: 13px; }
            QLineEdit { margin-bottom: 5px; }
        """)

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.container = QFrame()
        self.container.setObjectName("DialogContainer")
        self.cont_layout = QVBoxLayout(self.container)
        self.cont_layout.setContentsMargins(20, 20, 20, 20)
        self.cont_layout.setSpacing(15)
        
        self.stack = QStackedWidget()
        
        # --- Pag 1: Login ---
        self.page_login = QWidget()
        layout_login = QVBoxLayout(self.page_login)
        form = QFormLayout()
        self.input_user = QLineEdit()
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username:", self.input_user)
        form.addRow("Password:", self.input_pass)
        layout_login.addLayout(form)
        self.btn_next = QPushButton("Login")
        self.btn_next.clicked.connect(self.do_login)
        layout_login.addWidget(self.btn_next)
        
        # --- Pag 2: Guard Code ---
        self.page_guard = QWidget()
        layout_guard = QVBoxLayout(self.page_guard)
        layout_guard.addWidget(QLabel("Enter Steam Guard code (Email/App):"))
        self.input_guard = QLineEdit()
        layout_guard.addWidget(self.input_guard)
        self.btn_guard = QPushButton("Verify")
        self.btn_guard.clicked.connect(self.verify_guard)
        layout_guard.addWidget(self.btn_guard)

        # --- Pag 3: SMS ---
        self.page_sms = QWidget()
        layout_sms = QVBoxLayout(self.page_sms)
        
        lbl_title_sms = QLabel("STEP 2: FINALIZE LINKING")
        lbl_title_sms.setStyleSheet("font-weight: bold; font-size: 14px; color: #a3cf06;")
        layout_sms.addWidget(lbl_title_sms)
        
        layout_sms.addWidget(QLabel("An activation code has been sent (SMS or Email).\nEnter it below to confirm the authenticator:"))
        
        self.input_sms = QLineEdit()
        self.input_sms.setPlaceholderText("Activation Code")
        layout_sms.addWidget(self.input_sms)
        
        self.btn_finish = QPushButton("Finalize Linking")
        self.btn_finish.setObjectName("btn_green") # Se tiver estilo verde
        self.btn_finish.clicked.connect(self.do_finalize)
        layout_sms.addWidget(self.btn_finish)

        self.stack.addWidget(self.page_login)
        self.stack.addWidget(self.page_guard)
        self.stack.addWidget(self.page_sms)
        
        self.label_status = QLabel("")
        self.label_status.setStyleSheet("color: #66c0f4; font-size: 11px;")
        self.cont_layout.addWidget(self.label_status)
        
        self.cont_layout.addWidget(self.stack)
        self.layout.addWidget(self.container)

    def do_login(self):
        user = self.input_user.text()
        pw = self.input_pass.text()
        if not user or not pw: return
        
        self.label_status.setText("Connecting...")
        self.btn_next.setEnabled(False)
        
        thread = threading.Thread(target=self._login_task, args=(user, pw))
        thread.daemon = True
        thread.start()

    def _login_task(self, user, pw):
        try:
            logger.info("Iniciando login moderno...")
            self.modern_auth = ModernSteamAuth(user, pw)
            result = self.modern_auth.login()
            
            logger.info(f"Resultado Login Moderno: {result}")
            
            if result.get('success'):
                # Login direto
                self.signals.finished.emit(EResult.OK)
            elif result.get('status') == 'awaiting_creds':
                allowed = result.get('allowed', [])
                logger.info(f"Métodos permitidos: {allowed}")
                
                needs_email = False
                needs_app = False
                for confirm in allowed:
                    ctype = confirm.get('confirmation_type')
                    # Tipo 2 é email confirmado. Tipo 1 pode ser email legacy ou device logic
                    if ctype == 2 or ctype == 1: 
                        needs_email = True
                    elif ctype == 3: 
                        needs_app = True
                
                # --- AUTO LOGIN LOGIC ---
                if needs_app and self.session_authenticator:
                    logger.info("Tentando auto-login com autenticador interno...")
                    try:
                        from time_aligner import TimeAligner
                        server_time = TimeAligner.get_steam_time()
                        code = self.session_authenticator.get_code(server_time)
                        logger.info(f"Código gerado automaticamente: {code}")
                        
                        # Tenta enviar o código (Tipo 3 = Device Code)
                        update_res = self.modern_auth.update_auth_session('3', code)
                        if update_res.get('success'):
                             logger.info("Auto-login success!")
                             self.signals.finished.emit(EResult.OK)
                             return
                        else:
                             logger.warning(f"Auto-login failed: {update_res}")
                    except Exception as e:
                        logger.error(f"Erro no auto-login: {e}")
                # ------------------------

                if needs_email:
                    self.signals.finished.emit(EResult.AccountLogonDenied)
                elif needs_app:
                    self.signals.finished.emit(EResult.AccountLoginDeniedNeedTwoFactor)
                else:
                    self.signals.error.emit(Exception(f"Tipo de confirmação desconhecido: {allowed}"))
            else:
                self.signals.error.emit(Exception(f"Falha login: {result}"))
        except Exception as e:
            logger.exception("Erro no login:")
            self.signals.error.emit(e)

    def _handle_login_res(self, res):
        logger.debug(f"Manipulando resultado de login: {res}")
        self.btn_next.setEnabled(True)
        if res == EResult.OK:
            self.label_status.setText("Login OK.")
            if self.only_session: 
                logger.info("Session only. Accepting dialog.")
                self.accept()
            else: 
                logger.info("Starting linking process.")
                self.start_linking()
        elif res in (EResult.AccountLogonDenied, 
                     EResult.AccountLoginDeniedNeedTwoFactor, 
                     EResult.TwoFactorCodeMismatch):
            self.label_status.setText("Guard required.")
            self.stack.setCurrentIndex(1)
        else:
            self.label_status.setText(f"Failure: {res}")
            QMessageBox.warning(self, "Login", "Login failed. Check your credentials.")

    def _handle_login_err(self, e):
        self.btn_next.setEnabled(True)
        error_str = str(e)
        logger.error(f"Erro no login: {error_str}")
        
        # Define o status na label para visibilidade imediata
        if "TwoFactorCodeRequired" in error_str:
            self.label_status.setText("Enter Guard code.")
            self.stack.setCurrentIndex(1)
        elif "incorrect" in error_str.lower():
            self.label_status.setText("Incorrect username or password.")
            QMessageBox.warning(self, "Incorrect Login", "The account name or password entered are incorrect.")
        else:
            self.label_status.setText(f"Error: {error_str[:30]}...")
            QMessageBox.critical(self, "Error", f"Login failed:\n{e}")

    def verify_guard(self):
        code = self.input_guard.text()
        if not code: return
        
        self.label_status.setText("Verifying...")
        self.btn_guard.setEnabled(False)
        
        thread = threading.Thread(target=self._verify_task, args=(code,))
        thread.daemon = True
        thread.start()

    def _verify_task(self, code):
        try:
            logger.info("Enviando código para ModernAuth...")
            # Tenta como email e app
            result = self.modern_auth.update_auth_session('email', code)
            logger.info(f"Resultado Verificação (Email): {result}")
            
            if not result.get('success'):
                 # Se falhou, tenta app code (embora update_auth_session seja meio agnóstico no backend)
                 pass

            if result.get('success'):
                logger.info("Código aceito! Access Token obtido.")
                self.signals.finished.emit(EResult.OK)
            else:
                self.signals.error.emit(Exception(f"Código inválido ou falha: {result}"))
        except Exception as e:
            logger.exception("Falha na verificação:")
            self.signals.error.emit(e)

    def _handle_verify_res(self, success, err=""):
        self.btn_guard.setEnabled(True)
        if success:
            self.label_status.setText("Verified!")
            if self.only_session: self.accept()
            else: self.start_linking()
        else:
            self.label_status.setText("Code failed.")
            QMessageBox.critical(self, "Error", f"Failure: {err}")

    def start_linking(self):
        # Movemos para thread porque sa.add() faz rede
        self.label_status.setText("Linking...")
        self.btn_next.setEnabled(False)
        thread = threading.Thread(target=self._linking_task)
        thread.start()

    def _linking_task(self):
        try:
            logger.info("Iniciando vinculação manual (Estilo C#)...")
            from time_aligner import TimeAligner
            from steam.guard import generate_device_id
            import requests

            # Sincroniza tempo antes
            TimeAligner.align_time()

            # Access Token obtido do login moderno
            self.access_token = self.modern_auth.access_token
            if not self.access_token:
                raise Exception("Access Token não disponível.")

            self.steam_id = self.modern_auth.steam_id
            
            # Parâmetros exatos do C#
            post_data = {
                'steamid': str(self.steam_id.as_64),
                'authenticator_time': str(TimeAligner.get_steam_time()),
                'authenticator_type': '1', 
                'device_identifier': generate_device_id(self.steam_id),
                'sms_phone_id': '1',
                'version': '2'
            }
            
            url = f'https://api.steampowered.com/ITwoFactorService/AddAuthenticator/v1/?access_token={self.access_token}'
            logger.info(f"Enviando POST AddAuthenticator...")
            
            resp = requests.post(url, data=post_data, timeout=30)
            
            logger.info(f"Resposta Add: {resp.status_code}")
            if resp.status_code != 200:
                raise Exception(f"HTTP Error {resp.status_code}: {resp.text}")

            result = resp.json().get('response', {})
            status = result.get('status')
            logger.info(f"Status Add: {status}")

            if status == 1: # OK
                # Inicializa SA com segredos para gerar códigos depois
                self.sa = SteamAuthenticator(backend=None)
                self.sa.secrets = result
                self.sa.steam_id = self.steam_id
                
                logger.info("Segredos recebidos! Aguardando SMS/Código.")
                
                # Usar invokeMethod ou sinais para setWindowTitle é ideal, mas setWindowTitle é thread-safe na maioria das vezes no Windows
                # Vamos arriscar apenas title, mas usar sinais para o resto
                QTimer.singleShot(0, lambda: self.setWindowTitle("Finalizar Adição do Autenticador"))
                
                self.signals.change_page.emit(2) # Sinal seguro
                self.signals.status.emit("Aguardando Código de Ativação...") # Sinal seguro

            elif status == 2:
                raise Exception("Telefone não vinculado à conta.")
            elif status == 29:
                raise Exception("Autenticador já existe nesta conta!")
            else:
                raise Exception(f"Erro Steam Status: {status}")

        except Exception as e:
            logger.exception("Erro ao vincular:")
            self.signals.status.emit(f"Erro: {str(e)}")
            self.signals.error.emit(e) # Usa sinal de erro que já mostra popup
        finally:
            QTimer.singleShot(0, lambda: self.btn_next.setEnabled(True))

    def do_finalize(self):
        logger.info("Botão Finalizar clicado")
        sms = self.input_sms.text()
        if not sms: return
        self.btn_finish.setEnabled(False)
        self.label_status.setText("Finalizando...")
        
        thread = threading.Thread(target=self._finalize_manual, args=(sms,))
        thread.daemon = True
        thread.start()

    def _finalize_manual(self, sms_code):
        try:
            logger.info(f"Finalizando autenticador com código: {sms_code}")
            import time
            import requests
            from time_aligner import TimeAligner
            
            if not self.sa or not self.sa.secrets:
                raise Exception("Segredos não encontrados. Refaça o processo.")

            # Gera código TOTP atual
            server_time = TimeAligner.get_steam_time()
            authenticator_code = self.sa.get_code(server_time)
            
            post_data = {
                'steamid': str(self.steam_id.as_64),
                'authenticator_code': authenticator_code,
                'authenticator_time': str(server_time),
                'activation_code': sms_code,
                'validate_sms_code': '1'
            }
            
            url = f'https://api.steampowered.com/ITwoFactorService/FinalizeAddAuthenticator/v1/?access_token={self.access_token}'
            
            resp = requests.post(url, data=post_data, timeout=30)
            logger.info(f"Resposta Finalize: {resp.status_code}")
            
            if resp.status_code != 200:
                raise Exception(f"HTTP Error {resp.status_code}: {resp.text}")

            result = resp.json().get('response', {})
            success = result.get('success')
            status = result.get('status') # 89 = Bad SMS?
            
            if success:
                logger.info("Finalizado com sucesso!")
                
                # Prepara dados para salvar
                data = self.sa.secrets
                # Importante: Adicionar uri se não vier
                if 'uri' not in data:
                     data['uri'] = f"otpauth://totp/Steam:{self.input_user.text()}?secret={data['shared_secret']}&issuer=Steam"

                acc_name = self.input_user.text()
                
                # Salva no arquivo
                accounts = {}
                if os.path.exists(SETTINGS_FILE):
                    with open(SETTINGS_FILE, 'r') as f:
                        accounts = json.load(f)
                
                accounts[acc_name] = data
                with open(SETTINGS_FILE, 'w') as f:
                    json.dump(accounts, f, indent=4)
                
                QTimer.singleShot(0, lambda: QMessageBox.information(self, "Sucesso", f"Conta {acc_name} adicionada!\nCódigo de Recuperação: {data.get('revocation_code')}"))
                QTimer.singleShot(0, self.accept)
            else:
                 if status == 89:
                     # Bad SMS Code - Permitir tentar novamente
                     logger.warning("Código SMS Incorreto (Status 89)")
                     QTimer.singleShot(0, lambda: QMessageBox.warning(self, "Código Incorreto", "O código SMS está incorreto. Tente novamente."))
                     QTimer.singleShot(0, self.input_sms.clear)
                     QTimer.singleShot(0, lambda: self.btn_finish.setEnabled(True))
                     QTimer.singleShot(0, lambda: self.label_status.setText("Aguardando Código..."))
                     return # Não levanta exceção, apenas retorna para o usuário tentar de novo
                 
                 raise Exception(f"Falha ao finalizar. Success={success}, Status={status}")

        except Exception as e:
            logger.exception("Erro na finalização:")
            QTimer.singleShot(0, lambda: self.label_status.setText("Erro na finalização."))
            QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Erro", f"Erro: {e}"))
            QTimer.singleShot(0, lambda: self.btn_finish.setEnabled(True))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SteamAuthApp()
    window.show()
    sys.exit(app.exec())