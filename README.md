# Southwest Price Checker

This is the backend for the Southwest Flight Tracker on https://connorxcollins.com. The repository contains scripts using Selenium to scrape flight prices from Google Flights and Southwest, that are integrated with a MongoDB instance
and notify the email address associated with the Mongo record if the flight price has dropped. While the MongoDB references are unique to my project, other parts of the script may be useful to copy.

### Google Scraper
- **Operational** and **ran daily with GitHub Actions**.
- Scrapes flight price information from Google Flights.
- Runs daily and emails users
  
### Southwest Scraper
- **Not actively used** due to **Southwest’s anti-bot measures**, which make it unreliable and difficult to scrape consistently.
- Attempting to change variables in the Chromedriver binary did not get the job done, other techniques may be attempted in the future

### License

This project is licensed under the MIT License.
