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

    price_to_return = 0

    if flight['roundtrip']:
        google_string = f"https://www.google.com/travel/flights?q=Flights%20to%20{flight['arrivalAirport']}%20from%20{flight['departureAirport']}%20on%20{flight['departureDate']}%20through%20{flight['returnDate']}%20on%20southwest"
    else:
        google_string = f"https://www.google.com/travel/flights?q=Flights%20to%20{flight['arrivalAirport']}%20from%20{flight['departureAirport']}%20on%20{flight['departureDate']}%20oneway%20on%20southwest"

    try:
        print(google_string)
        driver.get(google_string)
        driver.maximize_window()
        driver.save_screenshot('pic1.png')

        wait = WebDriverWait(driver, 20)

        try:
            button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'more flight')]")))
            button.click()

            time.sleep(2)
            driver.save_screenshot('pic2.png')

        except:
            print('There was no button')
            # all of the flights were already loaded

        departure_times = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'Departure time:')]")
        arrival_times = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'Arrival time:')]")
        prices = driver.find_elements(By.XPATH, "//span[contains(@aria-label, 'US dollars')]") # Take every third
        flight_details_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Flight details')]")
        flight_select_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Select flight')]")

        print(len(flight_select_buttons))

        number_on_page = 0

        for i in range(len(departure_times)):
            leaving_time = departure_times[i].get_attribute('innerText')[:-3]
            leaving_meridiem = departure_times[i].get_attribute('innerText')[-2:]
            arrival_time = arrival_times[i].get_attribute('innerText')[:-3]
            arrival_meridiem = arrival_times[i].get_attribute('innerText')[-2:]
            price = prices[i * 3].get_attribute('innerText')[1:]

            if leaving_time == flight['departureTime'] and leaving_meridiem == flight['departureMeridiem'] and arrival_time == flight['arrivalTime'] and arrival_meridiem == flight['arrivalMeridiem']:
                price_to_return += int(price)
                break

            number_on_page += 1

        if flight['roundtrip']:
            flight_details_buttons[number_on_page].click()
            flight_select_buttons[number_on_page].click()
            driver.save_screenshot("clicking through to return.png")

            try:
                button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'more flight')]")))
                button.click()

                time.sleep(2)
                driver.save_screenshot('pic3.png')

            except:
                print('There was no button')
                # all of the flights were already loaded

            # I have no idea why this line isn't working but find_elements is
            # try:
            #     wait.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@aria-label, 'Departure time:')]")))
            
            # except Exception as e:
            #     print(e)

            driver.save_screenshot("after opening all flights.png")

            departure_times_return = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'Departure time:')]")
            arrival_times_return = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'Arrival time:')]")
            prices_return = driver.find_elements(By.XPATH, "//span[contains(@aria-label, 'US dollars')]") # Take every third

            for i in range(len(departure_times_return)):
                leaving_time = departure_times_return[i].get_attribute('innerText')[:-3]
                leaving_meridiem = departure_times_return[i].get_attribute('innerText')[-2:]
                arrival_time = arrival_times_return[i].get_attribute('innerText')[:-3]
                arrival_meridiem = arrival_times_return[i].get_attribute('innerText')[-2:]
                price = prices_return[i * 3].get_attribute('innerText')[1:]

                if leaving_time == flight['returnDepartureTime'] and leaving_meridiem == flight['returnDepartureMeridiem'] and arrival_time == flight['returnArrivalTime'] and arrival_meridiem == flight['returnArrivalMeridiem']:
                    price_to_return += int(price)
                    break

    except Exception as e:
        print(e)

    print(price_to_return)

    return price_to_return

for flight in mongo_flights:

    check_flight(flight, 'd')

driver.quit()