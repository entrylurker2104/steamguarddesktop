"""
Modern Steam Authentication Helper
Uses IAuthenticationService via HTTP to get access tokens without gevent.
"""
import requests
import time
import base64
import json
import struct
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, PKCS1_v1_5
from steam.steamid import SteamID

class ModernSteamAuth:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.client_id = 0
        self.request_id = None
        self.steam_id = None
        self.access_token = None
        self.refresh_token = None
        
    def _encryption_setup(self):
        """Get public key for password encryption"""
        # A nova API IAuthenticationService pode ser usada, mas GetPasswordRSAPublicKey é o primeiro passo
        # endpoint: IAuthenticationService/GetPasswordRSAPublicKey/v1
        resp = self.session.get(
            'https://api.steampowered.com/IAuthenticationService/GetPasswordRSAPublicKey/v1/',
            params={'account_name': self.username}
        )
        if resp.status_code != 200:
            raise Exception(f"Failed to get RSA key: {resp.status_code}")
            
        data = resp.json()['response']
        return data['publickey_mod'], data['publickey_exp'], data['timestamp']

    def _encrypt_password(self, mod, exp, password):
        """RSA Encrypt Password"""
        rsa_key = RSA.construct((int(mod, 16), int(exp, 16)))
        # Trocando para PKCS1_v1_5 pois OAEP pode estar falhando na decriptação do lado do servidor
        # O comportamento anterior com interval:5 sugere erro de logica/dados
        cipher = PKCS1_v1_5.new(rsa_key) 
        encrypted = cipher.encrypt(password.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')

    def login(self):
        """Start authentication session"""
        mod, exp, timestamp = self._encryption_setup()
        encrypted_password = self._encrypt_password(mod, exp, self.password)
        
        # BeginAuthSessionViaCredentials
        import random
        import string
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        
        params = {
            'device_friendly_name': f'PythonSDA_{suffix}',
            'account_name': self.username,
            'encrypted_password': encrypted_password,
            'encryption_timestamp': str(timestamp),
            'remember_login': 'true',
            'platform_type': '1', # k_EAuthTokenPlatformType_SteamClient - Força envio de email
            'persistence': '1',   # k_ESessionPersistence_Persistent
            'website_id': 'Mobile' 
        }
        
        print(f"[DEBUG] Enviando BeginAuthSessionViaCredentials (Form-Data - PKCS1_v1_5)...")
        # Header necessário
        headers = {'User-Agent': 'Valve/Steam HTTP Client 1.0'}
        
        resp = self.session.post(
            'https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaCredentials/v1/',
            data=params, # Volta para form-data
            headers=headers
        )
        
        print(f"[DEBUG] BeginAuth Status: {resp.status_code}")
        print(f"[DEBUG] BeginAuth Body: {resp.text}")
        
        if resp.status_code != 200:
            raise Exception(f"Auth init failed: {resp.text}")
            
        try:
            data = resp.json().get('response', {})
        except:
            raise Exception("Falha ao decodificar JSON do BeginAuth")
            
        self.client_id = data.get('client_id')
        self.request_id = data.get('request_id')
        self.steam_id = SteamID(data.get('steamid', 0))
        
        print(f"[DEBUG] ClientID: {self.client_id}, RequestID: {self.request_id}, SteamID: {self.steam_id}")
        
        # Tenta poll imediatamente para ver se já autenticou (alguns tipos de confirmação podem ser auto-resolvidos ou não bloqueantes)
        poll_result = self._poll_status()
        if poll_result.get('success'):
            return {'success': True}
        
        # Se não, verifica confirmações permitidas
        allowed = data.get('allowed_confirmations', [])
        
        if not allowed:
             # Se não tem allowed e o poll falhou, retorno o erro do poll ou genérico
             return poll_result
            
        return {'status': 'awaiting_creds', 'allowed': allowed, 'steam_id': str(self.steam_id)}

    def update_auth_session(self, code_type, code):
        """Send 2FA code"""
        # code_type: 'email' (Type 2), '3' (Type 3)
        
        actual_type = '3' # Default Device Code
        endpoint = 'UpdateAuthSessionWithMobileConfirmation/v1'

        if code_type == 'email':
            actual_type = '2'
            endpoint = 'UpdateAuthSessionWithSteamGuardCode/v1'
        elif code_type == '3':
            actual_type = '3'
            # TOTP também usa SteamGuardCode, não MobileConfirmation
            endpoint = 'UpdateAuthSessionWithSteamGuardCode/v1'
            
        params = {
            'client_id': str(self.client_id),
            'steamid': str(self.steam_id.as_64),
            'code': str(code),
            'code_type': actual_type,
            'signature': '' 
        }
        
        print(f"[DEBUG] Enviando código para {endpoint} (Type={actual_type})...")
        resp = self.session.post(
            f'https://api.steampowered.com/IAuthenticationService/{endpoint}/',
            data=params
        )
        print(f"[DEBUG] UpdateAuth Status: {resp.status_code}")
        print(f"[DEBUG] UpdateAuth Body: {resp.text}")
        
        # Loop de polling para dar tempo ao backend processar
        import time
        max_retries = 10
        for i in range(max_retries):
            print(f"[DEBUG] Polling tentativa {i+1}/{max_retries}...")
            result = self._poll_status()
            
            if result.get('success'):
                return result
                
            # Se a resposta for explicita de falha (e não apenas polling), paramos?
            # Geralmente se ainda não validou, apenas não retorna tokens.
            
            time.sleep(1.5)
            
        return {'success': False, 'message': 'Timeout polling status'}

    def _poll_status(self):
        """Poll for final status"""
        if not self.client_id or not self.request_id:
            print("[DEBUG] ClientID ou RequestID ausentes, não é possível fazer o poll.")
            return {'success': False, 'message': 'Missing IDs'}

        params = {
            'client_id': str(self.client_id),
            'request_id': self.request_id # Base64 string
        }
        
        print(f"[DEBUG] Polling status (Form-Data)...")
        resp = self.session.post(
            'https://api.steampowered.com/IAuthenticationService/PollAuthSessionStatus/v1/',
            data=params
        )
        
        print(f"[DEBUG] Poll Status: {resp.status_code}")
        print(f"[DEBUG] Poll Body: {resp.text}")
        
        if resp.status_code != 200:
             return {'success': False, 'message': f'HTTP Error {resp.status_code}'}

        try:
            data = resp.json().get('response', {})
        except:
             return {'success': False, 'message': 'JSON Decode Error'}
        
        if data.get('access_token'):
            self.access_token = data['access_token']
            self.refresh_token = data['refresh_token']
            return {'success': True, 'access_token': self.access_token}
            
        return {'success': False, 'message': 'Polling...', 'details': data}
