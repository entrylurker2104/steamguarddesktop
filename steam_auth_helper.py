"""
Helper para autenticação Steam sem depender de MobileWebAuth quebrado
Baseado no fluxo do SteamDesktopAuthenticator
"""
import requests
import time
import base64
import json
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from steam.steamid import SteamID

class SteamAuthHelper:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; U; Android 4.1.1; en-us; Google Nexus 4 - 4.1.1 - API 16 - 768x1280 Build/JRO03S) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30',
            'Accept': 'text/javascript, text/html, application/xml, text/xml, */*'
        })
        self.steam_id = None
        self.oauth_token = None
        self.session_id = None
        
    def _get_rsa_key(self):
        """Obtém a chave RSA pública do Steam"""
        resp = self.session.post(
            'https://steamcommunity.com/login/getrsakey/',
            data={'username': self.username}
        )
        data = resp.json()
        return data['publickey_mod'], data['publickey_exp'], data['timestamp']
    
    def _encrypt_password(self, mod, exp):
        """Criptografa a senha com RSA"""
        rsa_key = RSA.construct((int(mod, 16), int(exp, 16)))
        cipher = PKCS1_v1_5.new(rsa_key)
        encrypted = cipher.encrypt(self.password.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')
    
    def login(self, twofactor_code='', email_code=''):
        """Realiza o login no Steam"""
        mod, exp, timestamp = self._get_rsa_key()
        encrypted_password = self._encrypt_password(mod, exp)
        
        login_data = {
            'username': self.username,
            'password': encrypted_password,
            'emailauth': email_code,
            'emailsteamid': '',
            'twofactorcode': twofactor_code,
            'captchagid': '-1',
            'captcha_text': '',
            'loginfriendlyname': 'python-sda',
            'rsatimestamp': timestamp,
            'remember_login': 'true',
            'donotcache': str(int(time.time() * 1000)),
            'oauth_client_id': 'DE45CD61',
            'oauth_scope': 'read_profile write_profile read_client write_client'
        }
        
        # Headers mobile
        self.session.cookies.set('mobileClientVersion', '0 (2.1.3)')
        self.session.cookies.set('mobileClient', 'android')
        
        resp = self.session.post(
            'https://steamcommunity.com/login/dologin/',
            data=login_data
        )
        
        # Remove cookies mobile
        self.session.cookies.pop('mobileClientVersion', None)
        self.session.cookies.pop('mobileClient', None)
        
        result = resp.json()
        
        # Verifica se precisa de 2FA
        if result.get('requires_twofactor'):
            return {'success': False, 'requires_twofactor': True}
        
        if result.get('emailauth_needed'):
            return {'success': False, 'emailauth_needed': True}
        
        if not result.get('success'):
            return {'success': False, 'message': result.get('message', 'Login falhou')}
        
        # Login bem-sucedido - extrai dados
        if 'oauth' in result:
            oauth_data = json.loads(result['oauth'])
            self.steam_id = SteamID(oauth_data['steamid'])
            self.oauth_token = oauth_data['oauth_token']
            print(f"[DEBUG] oauth_token obtido: {self.oauth_token[:20]}...")
        else:
            # Tenta extrair do cookie ou transfer_parameters
            if 'transfer_parameters' in result:
                self.steam_id = SteamID(result['transfer_parameters']['steamid'])
            
            # CRÍTICO: Sem oauth_token, o SteamAuthenticator não funciona
            # Tenta obter via cookies
            print("[DEBUG] oauth não encontrado na resposta, tentando extrair SteamID...")
            for cookie in self.session.cookies:
                if 'steamLoginSecure' in cookie.name:
                    parts = cookie.value.split('%7C%7C')
                    if len(parts) >= 1:
                        self.steam_id = SteamID(parts[0])
                        print(f"[DEBUG] SteamID extraído do cookie: {self.steam_id}")
                        break
            
            # Tenta obter access_token
            if self.steam_id:
                print("[DEBUG] Tentando obter access_token via API...")
                try:
                    token_resp = self.session.post(
                        'https://api.steampowered.com/IMobileAuthService/GetWGToken/v1/',
                        data={'access_token': ''}
                    )
                    if token_resp.status_code == 200:
                        token_data = token_resp.json().get('response', {})
                        self.oauth_token = token_data.get('token')
                        print(f"[DEBUG] access_token obtido: {self.oauth_token}")
                except Exception as e:
                    print(f"[DEBUG] Falha ao obter access_token: {e}")
            
        # Configura cookies de sessão
        self.session_id = self._generate_session_id()
        for domain in ['store.steampowered.com', 'help.steampowered.com', 'steamcommunity.com']:
            self.session.cookies.set('Steam_Language', 'english', domain=domain)
            self.session.cookies.set('birthtime', '-3333', domain=domain)
            self.session.cookies.set('sessionid', self.session_id, domain=domain)
        
        print(f"[DEBUG] Login finalizado - SteamID: {self.steam_id}, oauth_token: {self.oauth_token is not None}")
        return {'success': True, 'steam_id': str(self.steam_id), 'oauth_token': self.oauth_token}
    
    def _generate_session_id(self):
        """Gera um session ID aleatório"""
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=24))
    
    def get_oauth_token(self):
        """Retorna o oauth_token necessário para SteamAuthenticator"""
        return self.oauth_token
