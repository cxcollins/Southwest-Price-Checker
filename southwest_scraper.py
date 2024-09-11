from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import time

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

sw_url = """
https://www.southwest.com/air/booking/select-depart.html?+departureTimeOfDay=ALL_DAY&+passengerType=ADULT&adultPassengersCount=1&adultsCount=1&departureDate=2024-11-17&
departureTimeOfDay=ALL_DAY&destinationAirportCode=BOS&fareType=USD&from=SFO&int=HOMEQBOMAIR&originationAirportCode=SFO&passengerType=ADULT&returnDate=&returnTimeOfDay=
ALL_DAY&to=BOS&tripType=oneway
"""

# Going to need to add functionality to click search if the home screen comes up

max_retries = 3
retry_count = 0

# while retry_count < max_retries:
try:
    # Navigate to the URL
    driver.get(sw_url)
    driver.maximize_window()

    wait = WebDriverWait(driver, 40)
    ul_element = wait.until(EC.visibility_of_element_located((By.ID, "air-search-results-matrix-0")))
    # break

except TimeoutException:
    # print("Page load timed out, retrying...")
    # retry_count += 1
    button_to_click = driver.findElement(By.ID, "form-mixin--submit-button")
    button_to_click.click()

    # Now we are on the flights page
    driver.get(sw_url)
    driver.maximize_window()

    wait = WebDriverWait(driver, 40)
    ul_element = wait.until(EC.visibility_of_element_located((By.ID, "air-search-results-matrix-0")))


ul_html = ul_element.get_attribute('outerHTML')

driver.quit()

soup = BeautifulSoup(ul_html, 'html.parser')

li_elements = soup.find_all('li')

list_of_flights = []

for li in li_elements:

    flight = []

    time_span_elements = li.find_all("span", class_="time--value")
    am_pm_span_elements = li.find_all("span", class_="time--period")
    price_span_elements = li.find_all("span", class_="swa-g-screen-reader-only")

    flight.append(time_span_elements[0].find(string=True, recursive=False) + ' ' + am_pm_span_elements[0].find(string=True, recursive=False))
    flight.append(time_span_elements[1].find(string=True, recursive=False) + ' ' + am_pm_span_elements[1].find(string=True, recursive=False))

    for ele in price_span_elements:
        string_element = ele.find(string=True, recursive=False)
        if string_element[-7:] == 'Dollars':
            flight.append(string_element[:-8])

    print(flight)

    # for ele in time_span_elements:
    #     print(ele.find(string=True, recursive=False))

    time_span_counter = 0
    am_pm_span_counter = 0
    price_span_counter = 0

    print('')

    # for i in range(len(time_span_elements)) / 2:
    #     flight = []

    #     for _ in range(2):
    #         flight.append(time_span_elements[time_span_counter] + ' ' + am_pm_span_elements[am_pm_span_counter])
    #         time_span_counter += 1
    #         am_pm_span_counter += 1

    #     for _ in range(4):
    #         flight.append(price_span_counter)
    #         price_span_counter += 1



# Comment back in after testing

# departure_date = input('When do you want to leave? YYYY-MM-DD format \n')
# roundtrip = input('Is this roundtrip or oneway? \n')

# if roundtrip == 'roundtrip':
#     return_date = input('When do you want to return? YYYY-MM-DD format \n')
# else:
#     return_date = ''

# departure_airport = input('What is your departing airport\'s code? \n')
# destination_airport = input('What is your destination airport\'s code? \n')

# url_string = f"""
# https://www.southwest.com/air/booking/select-depart.html?adultPassengersCount=1&adultsCount=1&departureDate={departure_date}&
# departureTimeOfDay=ALL_DAY&destinationAirportCode={destination_airport}&fareType=USD&from={departure_airport}&int=HOMEQBOMAIR&
# originationAirportCode={departure_airport}&passengerType=ADULT&returnDate={return_date}&returnTimeOfDay=ALL_DAY&to={destination_airport}&tripType={roundtrip}
# """

# url_string = "https://www.southwest.com/air/booking/select-depart.html?adultPassengersCount=1&adultsCount=1&departureDate=2024-11-07&departureTimeOfDay=ALL_DAY&destinationAirportCode=BOS&fareType=USD&from=SFO&int=HOMEQBOMAIR&originationAirportCode=SFO&passengerType=ADULT&returnDate=&returnTimeOfDay=ALL_DAY&to=BOS&tripType=oneway"

# response = requests.get(url_string)

# soup = BeautifulSoup(response.text, 'html.parser')

# # times = soup.find_all('span', class_='time--value')

# print(soup.prettify())