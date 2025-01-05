# flake8: noqa

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service

import time
import sys
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
gmail_username = os.getenv("GMAIL_USERNAME")
gmail_password = os.getenv("GMAIL_APP_PASSWORD")
client = MongoClient(mongo_uri)

try:
    database = client.get_database("flights")
    flights_collection = database.get_collection("flights")
    mongo_flights = flights_collection.find()

except Exception as e:
    logging.error(f"Couldn't connect to mongodb: {e}", exc_info=True) # Confirm if this works in GH
    sys.exit(1)

# Create options object
options = Options()
options.add_argument("--headless=new")

# Hiding automation - if breaks in future, add other arguments
options.add_experimental_option("excludeSwitches", ['enable-automation'])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument('--disable-blink-features=AutomationControlled')

#Setting up Chrome/83.0.4103.53 as useragent
driver = webdriver.Chrome(options=options)

driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")


def check_flight(flight):

    price_to_return = 0

    if flight['roundtrip'] == 'roundtrip':
        google_string = f"https://www.google.com/travel/flights?q=Flights%20to%20{flight['arrivalAirport']}%20from%20{flight['departureAirport']}%20on%20{flight['departureDate']}%20through%20{flight['returnDate']}%20on%20southwest"
    else:
        google_string = f"https://www.google.com/travel/flights?q=Flights%20to%20{flight['arrivalAirport']}%20from%20{flight['departureAirport']}%20on%20{flight['departureDate']}%20oneway%20on%20southwest"

    try:
        driver.get(google_string)
        driver.maximize_window()
        driver.save_screenshot('pic1.png')

        wait = WebDriverWait(driver, 20)

        try:
            button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'more flight')]")))
            button.click()

        except:  # All of the flights were already loaded
            print('There was no button')

        departure_times = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'Departure time:')]")
        arrival_times = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'Arrival time:')]")
        prices = driver.find_elements(By.XPATH, "//span[contains(@aria-label, 'US dollars')]")  # Take every third
        flight_details_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Flight details')]")
        flight_select_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Select flight')]")

        if len(flight_select_buttons) == 0:
            return False

        number_on_page = -1

        for i in range(len(departure_times)):
            leaving_time = departure_times[i].get_attribute('innerText')[:-3]
            leaving_meridiem = departure_times[i].get_attribute('innerText')[-2:]

            # If flight lands next day, need to exclude '+1' from check
            if arrival_times[i].get_attribute('innerText')[-2:] != '+1':
                arrival_time = arrival_times[i].get_attribute('innerText')[:-3]
                arrival_meridiem = arrival_times[i].get_attribute('innerText')[-2:]
            else:
                arrival_time = arrival_times[i].get_attribute('innerText')[:-5]
                arrival_meridiem = arrival_times[i].get_attribute('innerText')[-4:-2]

            price = prices[i * 3].get_attribute('innerText')[1:]
            number_on_page += 1

            if leaving_time == flight['departureTime'] and leaving_meridiem == flight['departureMeridiem'] and arrival_time == flight['arrivalTime'] and arrival_meridiem == flight['arrivalMeridiem']:
                price_to_return = int(price)
                break

        if flight['roundtrip'] == 'roundtrip':
            flight_details_buttons[number_on_page].click()
            flight_select_buttons[number_on_page].click()

            try:
                button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'more flight')]")))
                button.click()

            except:  # All of the flights were already loaded
                print('There was no button')

            departure_times_return = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'Departure time:')]")
            arrival_times_return = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'Arrival time:')]")
            prices_return = driver.find_elements(By.XPATH, "//span[contains(@aria-label, 'US dollars')]") # Take every third

            for i in range(len(departure_times_return)):
                leaving_time = departure_times_return[i].get_attribute('innerText')[:-3]
                leaving_meridiem = departure_times_return[i].get_attribute('innerText')[-2:]

                # If flight lands next day, need to exclude '+1' from check
                if arrival_times_return[i].get_attribute('innerText')[-2:] != '+1':
                    arrival_time = arrival_times_return[i].get_attribute('innerText')[:-3]
                    arrival_meridiem = arrival_times_return[i].get_attribute('innerText')[-2:]
                else:
                    arrival_time = arrival_times_return[i].get_attribute('innerText')[:-5]
                    arrival_meridiem = arrival_times_return[i].get_attribute('innerText')[-4:-2]
                price = prices_return[i * 3].get_attribute('innerText')[1:]

                print(leaving_time, leaving_meridiem, arrival_time, arrival_meridiem, price)

                if (leaving_time == flight['returnDepartureTime'] and leaving_meridiem == flight['returnDepartureMeridiem']
                        and arrival_time == flight['returnArrivalTime'] and arrival_meridiem == flight['returnArrivalMeridiem']):
                    price_to_return = int(price)
                    break

    except Exception as e:
        logging.error(f"Error running script: {e}", exc_info=True)
        sys.exit(1)

    print(price_to_return)

    return price_to_return

def send_email(flight):
    msg = MIMEMultipart()
    msg['From'] = gmail_username
    msg['To'] = flight['email']
    msg['Subject'] = f"Your Southwest flight from {flight['departureAirport']} to {flight['arrivalAirport']} has decreased in price"
    body = "You should rebook your flight!"
    msg.attach(MIMEText(body, 'plain'))

    try:
        smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        smtp_server.login(gmail_username, gmail_password)
        smtp_server.sendmail(msg["From"], flight['email'], msg.as_string())
    
    except Exception as e:
        logging.error(f"Couldn't connect to server: {e}", exc_info=True)
        sys.exit(1)

    finally:
        smtp_server.quit()

for flight in mongo_flights:

    new_price = check_flight(flight)

    if new_price == False:
        logging.warning("Flight wasn't found")
        continue

    if new_price < flight['pricePaid']:
        send_email(flight)

driver.quit()