# Trade bot to follow specified traders from Shareville
# Patrik Jokela 8/2019
from __future__ import print_function
import pickle
import os.path
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
import time
import nordnet
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

starttime=time.time()


def main():

    
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify'] 

    while True:

        # UNCOMMENT BELOW IF YOU WANT TO RUN THIS CODE PERIODICALLY IN EVERY 10 SEC
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
        time.sleep(10.0 - ((time.time() - starttime) % 10.0))

        def run():

            creds = None
            # The file token.pickle stores the user's access and refresh tokens, and is
            # created automatically when the authorization flow completes for the first
            # time.
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            # If there are no (valid) credentials available, let the user log in.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)

            service = build('gmail', 'v1', credentials=creds)

            # Call the Gmail API to fetch INBOX
            results = service.users().messages().list(userId='me',labelIds = ['INBOX', 'UNREAD']).execute() # pylint: disable=maybe-no-member
            messages = results.get('messages', [])
            
            for mssg in reversed(messages):
                m_id = mssg['id'] # get id of individual message
                message = service.users().messages().get(userId='me', id=mssg['id']).execute() # fetch the message using API    # pylint: disable=maybe-no-member
                payld = message['payload'] # get payload of the message 
                headr = payld['headers'] # get header of the payload
                for one in headr: # getting the Subject
                    if one['name'] == 'Subject':
                        
                        msg_subject = one['value']
                        name = "MAVRICK"
                        if(name in msg_subject):
                                                    # Marking email as READ from UNREAD
                            service.users().messages().modify(userId='me', id=m_id,body={ 'removeLabelIds': ['UNREAD']}).execute() # pylint: disable=maybe-no-member

                            snippet = message['snippet'] # fetching message snippet
                            idx = snippet.find('profiili')
                            idx_end = snippet.find('Näytä', idx) # using idx to find word after the first idx
                            subs = snippet[idx + 8 : idx_end -1 ] 
                            idx = subs.find('kurssiin')
                            kurssi = subs[idx + 9 :]
                            idx = subs.find('arvopaperia')
                            idx_end = subs.find('kurssiin')
                            company = subs[idx + 12: idx_end -1]
                            if 'Osti' in subs:
                                tapahtuma = 'Buy'
                            else:
                                tapahtuma = 'Sell'
                            print(name + " " + subs, "\n", kurssi, "\n", company, "\n")
                            bot(kurssi, company, tapahtuma)

                    else:
                        pass

        def haeOmistus(company):
            options = Options()

            #options.add_argument('headless')
            options.add_argument("--disable-infobars")
            driver = webdriver.Chrome(chrome_options=options, executable_path=r'D:\chromedriver.exe') # PUT HERE YOUR CHROMEDRIVER LOCATION
            driver.get('https://www.shareville.fi/jasenet/mavrick/portfolios/87052/positions')

            #driver.implicitly_wait(10)
            #ig_site = driver.find_element_by_link_text('Developer Website')
            #print(ig_site)
            #ig_site.click()
            driver.implicitly_wait(10)

        def sandbox(company, toimeksianto, hinta, kpl, kurssi):
            """Sandbox for testing the bot
            """
            
            yritys = company.replace(" ", "") # Remove spaces from company name for the file name
            with open("kaupat/bot.txt","r+") as file1: # Opening a text file where bot money and transactions are kept
                read = file1.readline()
                bot_bank = float(re.search(r'\d+', read).group())
            with open("kaupat/" + yritys + ".txt","a") as file1:
                file1.seek(0)
            with open("kaupat/" + yritys + ".txt","r+") as file1: # Opening a text file where company transactions are kept
                read = file1.readline()
                if read == "":
                    shares = 0
                else:
                    shares = int(re.search(r'\d+', read).group())
                file1.seek(0)

                if 'Buy' in toimeksianto:           # OSTO
                    
                    shares += int(kpl)
                    file1.write(" " + company + " Shares: " + str(shares) + " \n")
                    bot_bank_after = bot_bank - hinta
                else:                               # MYYNTI
                    bot_bank_after = bot_bank + hinta
                    file1.write(" " + company + " Shares: 0\n")     

            with open("kaupat/" + yritys + ".txt","a") as file1:
                file1.write("\n------------------------\nTehty toimeksianto: " + toimeksianto + "\n" + str(kpl) + " kpl \nhintaan: "
                 + str(hinta) + " EUR \nKpl hinta: " + str(kurssi) + " NOK\nBot bank before: " + str(bot_bank) + "\n" + "Bot bank after: " + str(bot_bank_after) + "\n\n")

                percent = muutos(bot_bank, bot_bank_after)          
                file1.write("Percent difference: " + str(f'{percent:.2f}') + "%\n")
                print("Percent difference: " + str(f'{percent:.2f}') + "%\n-----------------------\n")
                
                percent_bot = muutos(10000, bot_bank_after)
            with open("kaupat/bot.txt","r+") as file1:
                file1.write(str(bot_bank_after) + "\n\nPercent difference from the 10 000 EUR start: " + str(f'{percent_bot:.2f}') + "%")

        def bot(kurssi, company, toimeksianto):
            """Bot to make actions in the market based on the emails received
            """
            price = 0

            int_kurssi = re.findall('\d*\.?\d+',kurssi)
            kurssi = int_kurssi[0]
            #print("hinta ennen muuntoa: %s EUR" % str(kurssi))
            #price = muunnin(kurssi, 'NOK') # Convert EUR -> NOK
            
            kurssi = float(kurssi)

            with open("kaupat/bot.txt", "a") as file1:
                file1.seek(0)
            with open("kaupat/bot.txt","r+") as file1: # Opening a text file where bot money and transactions are kept
                read = file1.readline()
                if read == "":
                    file1.write("10000 EUR" + "\n") # If nothing on file, give bot 10 000€ to start
                    bot_bank = 10000
                   
                else:
                    bot_bank = float(re.search(r'\d+', read).group())

            
            yritys = company.replace(" ", "") # Remove spaces from company name for the file name
            
            with open("kaupat/" + yritys + ".txt","a") as file1:
                file1.seek(0)
            with open("kaupat/" + yritys + ".txt","r+") as file1: # Opening a text file where company transactions are kept
                read = file1.readline()
                bot_bank_after = bot_bank
                if read == "":
                    shares = 0
                else:
                    shares = int(re.search(r'\d+', read).group())
                file1.seek(0)
            eur_hinta = muunnin(kurssi, 'EUR')

            if 'Buy' in toimeksianto:           # OSTO
                #price = kurssi * float(kpl)
                #if 3000 < price < 5000:
                #    kpl = int(kpl) / 2
                #elif 300 < price < 1000:
                #    kpl = int(kpl) * 2         # VAIHDETTIIN VANHASTA TOTEUTUKSESTA SEURAAVAAN:
                kpl = round(2000 / eur_hinta)            # NYT OSTETAAN AINA ~2000€ per osto ja jos omistetaan jo yritystä, ei osteta lisää

                price = eur_hinta * float(kpl)
                if price > bot_bank:
                    print("NO MONEY!!!")
                    return
                if shares > 0:                  # TÄMÄ if ON OSA UUTTA TOTEUTUSTA JOLLOIN OSTETAAN VAIN KERRAN KERRALLAAN YRITYSTÄ
                    print("We already have stocks for this company")
                    return
                shares += int(kpl)
                eur_hinta = muunnin(price, 'EUR')
            
            else:
                kpl = shares
                price = eur_hinta * float(kpl)
                # Sell all


            '''CHOOSE IF YOU WANT TO RUN BOT IN SANDBOX OR NORDNET API
            '''
            #nordnet.run(company, toimeksianto, str(round(price, 2)), str(kpl)) # BUY or SELL
            sandbox(company, toimeksianto, round(price, 2), str(kpl), kurssi)
    

        # Hard coded currency converter
        def muunnin(price, mihin):
            if mihin == 'EUR':
                nok_hinta = float(price) /  10.95288
                return float("{0:.2f}".format(nok_hinta))
                
            elif mihin == 'SEK':
                sek_hinta = float(price) / 1.08069 
                return float("{0:.2f}".format(sek_hinta))
            elif mihin == 'NOK':
                eur_hinta = float(price) * 10.95288
                return float("{0:.2f}".format(eur_hinta))
            else: 
                return price

        # Counts the % difference after made a transaction
        def muutos(loppu_bank, bank):

            percent = ((bank - loppu_bank) / ((bank + loppu_bank) / 2)) * 100
            return percent
        
        run()

if __name__ == '__main__':
    main()