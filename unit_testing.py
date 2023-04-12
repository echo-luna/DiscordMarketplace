from easybcc import easy_bcc as ebcc

bcc_token = ''

with open('../tokens/bcc_token.txt', 'r') as file:
    bcc_token = file.read().rstrip()

endpoint = "http://devpi.local/api"

store_id = "QOpZerUaGIEaRmoPbmrZNjqcQckKREtk"

bcc = ebcc(False)

wal_rep = bcc.get_cryptos(endpoint, bcc_token)
print("Wallets:",wal_rep)

stats_rep = bcc.get_stats(endpoint, bcc_token)
print("Stats:",stats_rep,stats_rep.json())

inv_rep = bcc.gen_invoice(endpoint, bcc_token, store_id, 100, "xmr", "127.0.0.1")
print("Invoice:",inv_rep,inv_rep.json())