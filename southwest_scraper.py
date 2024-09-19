from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import time
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import logging
import sys
import random

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)

try:
    database = client.get_database("flights")
    flights_collection = database.get_collection("flights")
    flights = flights_collection.find()

except Exception as e:
    logging.error(f"Couldn't connect to mongodb: {e}", exc_info=True) # Confirm this will work in GitHub WF
    sys.exit(1)

# What needs to happen

"""
1. Create front end page for web app. -> partially done
2. Create Mongodb cluster for flights. -> done
3. Setup script to pull from Mongodb. -> done
4. Create logic to match flight
    - cover if unavailable -> done
    - having problem with second search
    - calculate if flight is match
    - call email function if match
    - handle roundtrip
5. Setup email service within script. -> not done
6. Schedule script.
"""

options = Options()
options.add_argument("--headless=new")

# Hiding automation - if breaks in future, add other arguments
options.add_experimental_option(
    "excludeSwitches", ['enable-automation'])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")

# Initialize the Chrome driver
driver = webdriver.Chrome(options=options)

#Setting up Chrome/83.0.4103.53 as useragent
driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})

driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

def check_flight(flight, leg):
    sw_url = (
            f"https://www.southwest.com/air/booking/select-{leg}.html?+departureTimeOfDay=ALL_DAY&+passengerType=ADULT&adultPassengersCount=1&adultsCount=1&departureDate={flight['departureDate']}&"
            f"departureTimeOfDay=ALL_DAY&destinationAirportCode={flight['arrivalAirport']}&fareType=USD&from={flight['departureAirport']}&int=HOMEQBOMAIR&originationAirportCode={flight['departureAirport']}&"
            f"passengerType=ADULT&returnDate={flight['returnDate']}&returnTimeOfDay=ALL_DAY&to={flight['arrivalAirport']}&tripType={'roundtrip' if flight['roundtrip'] else 'oneway'}"
    )

    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Navigate to the URL
            print(sw_url)
            driver.get(sw_url)
            driver.maximize_window() # Do we need this?

            wait = WebDriverWait(driver, 40)
            ul_element = wait.until(EC.visibility_of_element_located((By.XPATH, "//ul[@id='air-search-results-matrix-0']")))

            # If element is found i.e., the site loads to the flights page
            break

        # A timeout will likely happen if Southwest site suspects a driver is accessing page, and script will need to click search
        except TimeoutException:
            retry_count += 1
            button_to_click = driver.find_element(By.ID, "form-mixin--submit-button")
            button_to_click.click()

            # Now we are on the flights page
            driver.get(sw_url)
            driver.maximize_window()

            wait = WebDriverWait(driver, 40)
            ul_element = wait.until(EC.visibility_of_element_located((By.XPATH, "//ul[@id='air-search-results-matrix-0']")))

    if retry_count == max_retries:
        logging.error(f"Couldn't connect to mongodb: {e}", exc_info=True) # Confirm this will work in GitHub WF
        sys.exit(1)

    ul_html = ul_element.get_attribute('outerHTML')


    soup = BeautifulSoup(ul_html, 'html.parser')

    li_elements = soup.find_all('li')

    list_of_flights = []

    for li in li_elements:

        flight = []

        time_span_elements = li.find_all("span", class_="time--value")
        am_pm_span_elements = li.find_all("span", class_="time--period")
        price_span_elements = li.find_all("span", class_="fare-button--text")

        flight.append(time_span_elements[0].find(string=True, recursive=False) + ' ' + am_pm_span_elements[0].find(string=True, recursive=False))
        flight.append(time_span_elements[1].find(string=True, recursive=False) + ' ' + am_pm_span_elements[1].find(string=True, recursive=False))

        for ele in price_span_elements:
            string_element = ele.find(string=True, recursive=True)
            if string_element[-7:] == 'Dollars':
                flight.append(string_element[:-8])
            elif string_element == 'Unavailable':
                flight.append(10000) # If flight is unavailable, just assign a number that is surely higher than what user paid

        print(flight)


#   price_paid
#   departureDate
#   departureTime
#   departureMeridiem
#   arrivalDate
#   arrivalTime
#   arrivalTimeMeridiem
#   departureAirport
#   arrivalAirport
#   ticketClass
#   roundtrip

for flight in flights:
    price_paid = flight['price_paid']
    current_price = 0

    # This will need to return price of flight
    check_flight(flight, 'depart')

    sleep_time = random.uniform(10, 20)

    time.sleep(sleep_time)

    # Call again if roundtrip

driver.quit()
