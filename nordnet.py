# nordnet API test 
# https://api.test.nordnet.se/
# Patrik Jokela 8/2019
import time
import base64
import requests
import json
import trade
import re
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

def print_json(j,prefix=''):
    if prefix=='':
        print('*'*20)
    if not isinstance(j,list):
        j=[j]
    for d in j:
        for key, value in d.items():
            if isinstance (value,dict):
                print('%s%s' % (prefix,key))
                print_json(value, prefix+'  ')
            else:
                print('%s%s:%s' % (prefix,key,value))

timestamp = int(round(time.time()*1000))
timestamp = str(timestamp).encode('ascii')

mylogin, mypassword = open('creds.txt','r').read().split('\n')

username = base64.b64encode(mylogin.encode('ascii'))
password = base64.b64encode(mypassword.encode('ascii'))
phrase = base64.b64encode(timestamp)

auth_val = username + b':' + password + b':' + phrase
rsa_key = RSA.importKey(open('NEXTAPI_TEST_public.pem').read())
cipher_rsa = PKCS1_v1_5.new(rsa_key)
encrypted_hash = cipher_rsa.encrypt(auth_val)
hash = base64.b64encode(encrypted_hash)

BASE_URL='api.test.nordnet.se:443/next'
API_VERSION='2'
URL = 'https://%s/%s' % (BASE_URL,API_VERSION)

def req(cmd=''):
    r=requests.get(URL + '/%s' % cmd ,auth = auth, headers=headers)
    return json.loads(r.text)

    # connects to the API, login and do all the heavy lifting 
def login():
    global headers, params, session_key, auth, account_id
    headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "application/json",'Accept-Language':'en'}
    params = {'service': 'NEXTAPI', 'auth': hash}
    r = requests.get(URL, headers = headers)
    print_json(json.loads(r.text))

    r=requests.post(URL + '/login',data=params, headers=headers) # LOGIN POST method

    rj=json.loads(r.text)
    session_key=rj['session_key']
    auth = (session_key,session_key)

    account_id = req('accounts')[0]['accno']

# Persistent login. Stays logged in until time runs out
def touch(): requests.put(URL+'/login/%s' % session_key, auth = auth, headers=headers)

def logout():    
    r=requests.delete(URL + '/login/%s' % session_key, auth = auth, headers=headers)
    print_json(json.loads(r.text))

# Make a BUY or SELL transaction in the market
def buy(company,hinta,volume,currency, toimeksianto): 
    market_ID = req('instruments?query=%s&limit=10' % company)[0]['tradables'][0]['market_id']
    identifier = req('instruments?query=%s&limit=10' % company)[0]['tradables'][0]['identifier']
    company_NAME = req('instruments?query=%s&limit=10' % company)[0]['name']
    print('-------------MARKET ID: %s\n\n' % market_ID)
    print('-------------COMPANY ID: %s\n\n' % identifier)
    print('-------------COMPANY NAME: %s\n\n' % company_NAME)
    yritys = company.replace(" ", "") # Remove spaces from company name for the file name
    price = hinta.replace('.', ',')
    if toimeksianto == 'Sell':
        with open("kaupat/" + yritys + ".txt", "a") as file1:
            file1.seek(0)
        with open("kaupat/" + yritys + ".txt","r+") as file1:
            read = file1.readline()             # Find how much we own so we know how much to sell
            if read == "" or " ":
                file1.write("0" + "\n")
                volume = 0
            else:
                volume = int(re.search(r'\d+', read).group())   
            print("kpl määrä on: " + str(volume))

    r = requests.post(URL + '/accounts/%s/orders' % account_id,
        data={'identifier':identifier,'market_id':market_ID,'price':price,'currency':currency, 'volume':volume, 'side':toimeksianto, 'order_type':'LIMIT'}, 
        auth=auth, headers=headers).text
    
    print('price: %s NOK, volume: %s' % (price, volume))
    if json.loads(r)['result_code'] == 'OK' and toimeksianto == 'Buy': # If the BUY order is placed 
        with open("kaupat/" + yritys + ".txt", "a") as file1:
            file1.seek(0)
        with open("kaupat/" + yritys + ".txt","r+") as file1:
            file1.write(volume)      # Write down how much we bought
    
    with open("kaupat/" + yritys + ".txt","a+") as file1:
                file1.write("\n\nTehty toimeksianto: " + toimeksianto + "\n" + str(volume) + " kpl \n hintaan: " + price + " NOK \n\n")


    return json.loads(r)

# Delete specified order
def delete_order(order_id): 
    return json.loads(requests.delete(URL+'/accounts/%s/orders/%s' % (account_id, order_id), auth=auth, headers=headers).text)

# Delete all orders from the user
def delete_all_orders():
    r = req('accounts/%s/orders' % account_id)
    for i in range(len(r)):
        id = r[i]['order_id']
        print_json(json.loads(requests.delete(URL+'/accounts/%s/orders/%s' % (account_id, id), auth=auth, headers=headers).text))
    print('\nEverything succesfully deleted if possible..')

# Search for a company
def find(company):
    return print_json(req('/instruments?query=name(%s)&limit=10' % company)) 

# Main function
def run(company = '', toimeksianto = '', hinta = '0', maara = '0'):
    login()
    #delete_all_orders()
    

    r=buy(company, hinta, maara,'NOK', toimeksianto)          # BUY identifier,marketID,price,volume,currency
    print(print_json(r))

    
    #print_json(delete_order(r['order_id']))

    #print_json(req('accounts/%s/orders' % account_id)) # Exchange orders
    logout()
    

if __name__ == '__main__':
   # run('Seabird', 'Buy', '0,81', '2000')
   run()