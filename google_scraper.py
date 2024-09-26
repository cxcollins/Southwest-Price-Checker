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

options = Options()
options.add_argument("--headless=new")

# Hiding automation - if breaks in future, add other arguments
options.add_experimental_option(
    "excludeSwitches", ['enable-automation'])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument('--disable-blink-features=AutomationControlled')

driver = webdriver.Chrome(options=options)

#Setting up Chrome/83.0.4103.53 as useragent
driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

def check_flight(flight, leg):

    if flight['roundtrip']:
        google_string = f"https://www.google.com/travel/flights?q=Flights%20to%20{flight['arrivalAirport']}%20from%20{flight['departureAirport']}%20on%20{flight['departureDate']}%20through%20{flight['returnDate']}%20southwest"
    else:
        google_string = f"https://www.google.com/travel/flights?q=Flights%20to%20{flight['arrivalAirport']}%20from%20{flight['departureAirport']}%20on%20{flight['departureDate']}%20oneway%20on%20southwest"

    try:
        print(google_string)
        driver.get(google_string)
        driver.maximize_window()
        driver.save_screenshot('pic1.png')

        wait = WebDriverWait(driver, 10)

        try:
            button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'more flight')]")))
            button.click()

            time.sleep(10)
            driver.save_screenshot('pic2.png')

        except:
            print('There was no button')
            # all of the flights were already loaded

        departure_times = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'Departure time:')]")
        arrival_times = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'Arrival time:')]")
        prices = driver.find_elements(By.XPATH, "//span[contains(@aria-label, 'US dollars')]") # Take every third

        for i in range(len(departure_times)):
            print(departure_times[i].get_attribute('outerHTML')[:-3])
            print(departure_times[i].get_attribute('outerHTML')[-2:])
            print(arrival_times[i].get_attribute('innerText')[:-3])
            print(arrival_times[i].get_attribute('innerText')[-2:])
            print(prices[i * 3].get_attribute('innerText')[-1:])

    except:
        print('problem')

        # //button[@aria-label='Select flight'] -> this is the button to select

for flight in mongo_flights:

    check_flight(flight, 'd')