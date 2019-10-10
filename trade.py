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

starttime=time.time()


def main():

    
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify'] 

    while True:

        # UNCOMMENT BELOW IF YOU WANT TO RUN THIS CODE PERIODICALLY IN EVERY 10 SEC
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
        #time.sleep(10.0 - ((time.time() - starttime) % 10.0))

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
            results = service.users().messages().list(userId='me',labelIds = ['INBOX', 'UNREAD']).execute()
            messages = results.get('messages', [])
            
            for mssg in reversed(messages):
                m_id = mssg['id'] # get id of individual message
                message = service.users().messages().get(userId='me', id=mssg['id']).execute() # fetch the message using API
                payld = message['payload'] # get payload of the message 
                headr = payld['headers'] # get header of the payload
                for one in headr: # getting the Subject
                    if one['name'] == 'Subject':
                        
                        msg_subject = one['value']
                        name = "MAVRICK"
                        if(name in msg_subject):
                                                    # Marking email as READ from UNREAD
                            service.users().messages().modify(userId='me', id=m_id,body={ 'removeLabelIds': ['UNREAD']}).execute() 

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
                            print(name + " " + subs, "\n", kurssi, "\n", company)
                            bot(kurssi, company, tapahtuma)

                    else:
                        pass

        def sandbox(company, toimeksianto, kurssi, kpl):
            """Sandbox for testing the bot
            """
            shares = 0
            price = 0
            yritys = company.replace(" ", "") # Remove spaces from company name for the file name
            with open("kaupat/bot.txt", "a") as file1:
                file1.seek(0)
            with open("kaupat/bot.txt","r+") as file1: # Opening a text file where bot money and transactions are kept
                read = file1.readline()
                if read == "":
                    file1.write("50000 EUR" + "\n") # If nothing on file, give bot 50 000€ to start
                    bot_bank = 50000
                   
                else:
                    bot_bank = int(re.search(r'\d+', read).group())
                
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

                if 'Buy' in toimeksianto:
                    price = kurssi * float(kpl)
                    if price > bot_bank:
                        print("NO MONEY!!!")
                        return
                    shares += int(kpl)
                    file1.write(" " + company + " Shares: " + str(shares) + " \n")
                    eur_hinta = muunnin(price, 'EUR')
                    bot_bank_after -= eur_hinta
                else: 
                    price = kurssi * float(shares)
                    eur_hinta = muunnin(price, 'EUR')
                    bot_bank_after += eur_hinta
                    file1.write(" " + company + " Shares: 0\n")     

            with open("kaupat/" + yritys + ".txt","a") as file1:
                file1.write("\n------------------------\nTehty toimeksianto: " + toimeksianto + "\n" + str(kpl) + " kpl \nhintaan: "
                 + str(eur_hinta) + " EUR \nKurssi: " + str(kurssi) + "\nBot bank before: " + str(bot_bank) + "\n" + "Bot bank after: " + str(bot_bank_after) + "\n\n")

                percent = muutos(bot_bank, bot_bank_after)
                if bot_bank > 50000:                    # Bots starting bank 50 000 EUR
                    file1.write("Percent difference: " + str(f'{percent:.2f}') + "%\n")
                    print("Percent difference: " + str(f'{percent:.2f}') + "%")
                else:
                    file1.write("Percent difference: -" + str(f'{percent:.2f}') + "%\n")
                    print("Percent difference: -" + str(f'{percent:.2f}') + "%")
            with open("kaupat/bot.txt","r+") as file1:
                if bot_bank > 50000:                    # Bots starting bank 50 000 EUR
                    file1.write(str(bot_bank_after) + "\n\nPercent difference from the 50 000 EUR start: " + str(f'{percent:.2f}') + "%")
                else:           
                    file1.write(str(bot_bank_after) + "\n\nPercent difference from the 50 000 EUR start: -" + str(f'{percent:.2f}') + "%")     

        def bot(kurssi, company, toimeksianto):
            """Bot to make actions in the market based on the emails received
            """

            int_kurssi = re.findall('\d*\.?\d+',kurssi)
            kurssi = int_kurssi[0]
            print("hinta ennen muuntoa: %s NOK" % str(kurssi))
            #price = muunnin(kurssi, 'SEK') # Convert NOK -> SEK
            
            price = float(kurssi)

            #print("hinta muunnon jälkeen: %s SEK" % str(price))

            if 'Buy' in toimeksianto:
                if price < 2:               # How many shares are we buying
                    kpl = 200
                    # price = price * kpl
                elif price < 5:
                    kpl = 100
                    # price = price * kpl
                elif price < 10:
                    kpl = 50
                    # price = price * kpl
                elif price < 20:
                    kpl = 25
                    # price = price * kpl
                else:
                    kpl = 10
                    # price = price * kpl


            
            else:
                kpl = 2000
                # Sell all


            '''CHOOSE IF YOU WANT TO RUN BOT IN SANDBOX OR NORDNET API
            '''
            #nordnet.run(company, toimeksianto, str(round(price, 2)), str(kpl)) # BUY or SELL
            sandbox(company, toimeksianto, round(price, 2), str(kpl))
    

        # Hard coded currency converter
        def muunnin(price, mihin):
            if mihin == 'NOK':
                nok_hinta = float(price) /  9.96261
                return float("{0:.2f}".format(nok_hinta))
                
            elif mihin == 'SEK':
                sek_hinta = float(price) / 1.08069 
                return float("{0:.2f}".format(sek_hinta))
            elif mihin == 'EUR':
                eur_hinta = float(price) * 9.96260
                return float("{0:.2f}".format(eur_hinta))
            else: 
                return price

        # Counts the % difference after made a transaction
        def muutos(bank, loppu_bank):
            bank = 50000
            if bank < loppu_bank:
                var = loppu_bank - bank
            else:
                var = bank - loppu_bank

            percent = var / bank * 100
            return percent
        
        run()

if __name__ == '__main__':
    main()
