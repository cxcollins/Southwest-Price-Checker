from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service

import time
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import logging
import sys
import random
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
    logging.error(f"Couldn't connect to mongodb: {e}", exc_info=True) # Confirm this will work in GitHub WF
    sys.exit(1)

options = Options()
options.add_argument("--headless=new")

# Hiding automation - if breaks in future, add other arguments
options.add_experimental_option(
    "excludeSwitches", ['enable-automation'])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument('--disable-blink-features=AutomationControlled')

# Use path for custom driver executable
driver_path = './chromedriver-mac-x64/chromedriver'
service = Service(driver_path)

# Initialize the Chrome driver
driver = webdriver.Chrome(options=options, service=service)

#Setting up Chrome/83.0.4103.53 as useragent
driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

def send_email(flight):
    msg = MIMEMultipart()
    msg['From'] = gmail_username
    msg['To'] = flight['email']
    msg['Subject'] = f'Your Southwest flight from {flight['departureAirport']} to {flight['arrivalAirport']} has decreased in price'
    body = "You should rebook your flight!"
    msg.attach(MIMEText(body, 'plain'))

    try:
        smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        smtp_server.login(gmail_username, gmail_password)
        smtp_server.sendmail(msg["From"], flight['email'], msg.as_string())
    
    except Exception as e:
        logging.error("Couldn't connect to server")

    finally:
        smtp_server.quit()

def check_flight(flight, leg):
    flights_to_return = []
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
            driver.maximize_window()
            driver.save_screenshot('pic1.png') # Remove after finishing

            wait = WebDriverWait(driver, 40)

            if leg == 'depart':
                ul_element = wait.until(EC.visibility_of_element_located((By.XPATH, "//ul[@id='air-search-results-matrix-0']")))

            else:
                ul_element = wait.until(EC.visibility_of_element_located((By.XPATH, "//ul[@id='air-search-results-matrix-1']")))

            # If element is found i.e., the site loads to the flights page
            break

        # A timeout will likely happen if Southwest site suspects a driver is accessing page, and script will need to click search
        except TimeoutException:

            try:
                button_to_click = driver.find_element(By.ID, "form-mixin--submit-button")
                button_to_click.click()

                # Now we are on the flights page
                driver.get(sw_url)
                driver.maximize_window()

                wait = WebDriverWait(driver, 40)
                
                if leg == 'depart':
                    ul_element = wait.until(EC.visibility_of_element_located((By.XPATH, "//ul[@id='air-search-results-matrix-0']")))

                else:
                    ul_element = wait.until(EC.visibility_of_element_located((By.XPATH, "//ul[@id='air-search-results-matrix-1']")))

            except TimeoutException:
                # Southwest blocked the whole operation; try again
                retry_count += 1

    if retry_count == max_retries:
        logging.error("Couldn't connect to Southwest") # Confirm this will work in GitHub WF
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

        flight.append(time_span_elements[0].find(string=True, recursive=False))
        flight.append(am_pm_span_elements[0].find(string=True, recursive=False))
        flight.append(time_span_elements[1].find(string=True, recursive=False))
        flight.append(am_pm_span_elements[1].find(string=True, recursive=False))

        for ele in price_span_elements:
            string_element = ele.find(string=True, recursive=True)
            if string_element[-7:] == 'Dollars':
                flight.append(string_element[:-8])
            elif string_element == 'Unavailable':
                flight.append(10000) # If flight is unavailable, just assign a number that is surely higher than what user paid

        print(flight)
        flights_to_return.append(flight)
    return flights_to_return

for flight in mongo_flights:
    price_paid = flight['price_paid']
    current_price = 0

    scraped_flights = check_flight(flight, 'depart')
    
    for scraped_flight in scraped_flights:
        if scraped_flight[0] == flight['departureTime'] and scraped_flight[1] == flight['departureMeridiem'] and scraped_flight[2] == flight['arrivalTime'] and scraped_flight[3] == flight['arrivalMeridiem']:
            if flight['ticketClass'] == 'wga':
                current_price += int(scraped_flight[7])
            elif flight['ticketClass'] == 'wgap':
                current_price += int(scraped_flight[6])
            elif flight['ticketClass'] == 'anytime':
                current_price += int(scraped_flight[5])
            elif flight['ticketClass'] == 'bs':
                current_price += int(scraped_flight[4])
            break

    # Sleep for 10 - 20 seconds to simulate a human picking through
    sleep_time = random.uniform(10, 20)
    time.sleep(sleep_time)

    if flight['roundtrip'] == True:
        scraped_return_flights = check_flight(flight, 'return')
        for scraped_return_flight in scraped_flights:
            if scraped_return_flight[0] == flight['returnDepartureTime'] and scraped_return_flight[1] == flight['returnDepartureMeridiem'] and scraped_return_flight[2] == flight['returnArrivalTime'] and scraped_return_flight[3] == flight['returnArrivalMeridiem']:
                if flight['ticketClass'] == 'wga':
                    current_price += int(scraped_flight[7])
                elif flight['ticketClass'] == 'wgap':
                    current_price += int(scraped_flight[6])
                elif flight['ticketClass'] == 'anytime':
                    current_price += int(scraped_flight[5])
                elif flight['ticketClass'] == 'bs':
                    current_price += int(scraped_flight[4])
                break

    if current_price < price_paid:
        send_email(flight)

driver.quit()
