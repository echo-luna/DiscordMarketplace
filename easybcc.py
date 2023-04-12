from torpy.http.requests import tor_requests_session
import requests

class easy_bcc:
    
    def __init__(self, tor_enabled):
        if tor_enabled:
            self.session = tor_requests_session()
        else:
            self.session = requests.Session()

    def gen_invoice(self, endpoint, token, store_id, amnt, cur, notif_url):
        data = {
                    "price" : amnt,
                    "store_id" : store_id,
                    "currency" : cur,
                    "notification_url" : notif_url
                }
        
        h_dat = {'Authorization' : f'Bearer {token}'}
        response = self.session.post(f"{endpoint}/invoices", headers=h_dat, json=data)
        
        return response
        
    def get_cryptos(self, endpoint, token):
        
        h_dat = {'Authorization' : f'Bearer {token}'}
        
        response = self.session.get(f"{endpoint}/wallets", headers=h_dat)
        if response.status_code == 200:
            j_dat = response.json()
            c_list = []
            for wallet in j_dat["result"]:
                c_list.append(wallet["currency"])
            return c_list
        else:
            print(response.status_code)
            print(response.json())
            return False
    
    def get_stats(self, endpoint, token):
        
        h_dat = {'Authorization' : f'Bearer {token}'}
        
        response = self.session.get(f"{endpoint}/users/stats", headers=h_dat)
        return response
    