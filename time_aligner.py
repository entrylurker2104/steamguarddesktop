
import time
import struct
import requests
import threading

class TimeAligner:
    _time_difference = 0
    _aligned = False
    
    @staticmethod
    def get_steam_time():
        if not TimeAligner._aligned:
            TimeAligner.align_time()
        return int(time.time()) + TimeAligner._time_difference

    @staticmethod
    def align_time():
        try:
            # Tenta obter tempo do servidor Steam
            resp = requests.post('https://api.steampowered.com/ITwoFactorService/QueryTime/v0001', data={'steamid': '0'})
            if resp.status_code == 200:
                server_time = int(resp.json()['response']['server_time'])
                current_time = int(time.time())
                TimeAligner._time_difference = server_time - current_time
                TimeAligner._aligned = True
                print(f"[TimeAligner] Tempo sincronizado. Diferença: {TimeAligner._time_difference}s")
        except Exception as e:
            print(f"[TimeAligner] Falha ao sincronizar tempo: {e}")
