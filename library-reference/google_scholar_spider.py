import datetime
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from time import sleep

now = datetime.datetime.now()
current_year = now.year
MAX_CSV_FNAME = 255

# Websession Parameters
GSCHOLAR_URL = 'https://scholar.google.com/scholar?start={}&q={}&hl=en&as_sdt=0,5'
YEAR_RANGE = ''  # &as_ylo={start_year}&as_yhi={end_year}'
STARTYEAR_URL = '&as_ylo={}'
ENDYEAR_URL = '&as_yhi={}'
ROBOT_KW = ['unusual traffic from your computer network', 'not a robot']

class PaperCrawler:
    def __init__(self, keyword, start_year=None, end_year=current_year, nresults=10):
        self.keyword = keyword
        self.start_year = start_year
        self.end_year = end_year
        self.nresults = nresults

    def crawl(self):
        # Create main URL based on command line arguments
        gscholar_main_url = self.create_main_url()

        # Start new session
        session = requests.Session()

        # Call fetch_data() with pbar argument
        with tqdm(total=self.nresults) as pbar:
            data = self.fetch_data(session, gscholar_main_url, pbar)

        # Create markdown results
        markdown_results = self.format_results_as_markdown(data)

        return markdown_results

    def create_main_url(self):
        if self.start_year:
            gscholar_main_url = GSCHOLAR_URL + STARTYEAR_URL.format(self.start_year)
        else:
            gscholar_main_url = GSCHOLAR_URL

        if self.end_year != current_year:
            gscholar_main_url = gscholar_main_url + ENDYEAR_URL.format(self.end_year)

        return gscholar_main_url

    def fetch_data(self, session, gscholar_main_url, pbar):
        links, titles, citations, years, authors, venues, publishers, describes = [], [], [], [], [], [], [], []
        rank = [0]

        # Initialize progress bar
        pbar.reset(total=self.nresults)

        # Get content from number_of_results URLs
        n = 0
        while n < self.nresults:
            remaining = self.nresults - n
            batch_size = min(remaining, 10)
            pbar.update(batch_size)

            url = gscholar_main_url.format(str(n), self.keyword.replace(' ', '+'))
            page = session.get(url)
            c = page.content

            if any(kw in c.decode('ISO-8859-1') for kw in ROBOT_KW):
                print("Robot checking detected, handling with selenium (if installed)")
                try:
                    c = self.get_content_with_selenium(url)
                except Exception as e:
                    print("No success. The following error was raised:")
                    print(e)

            # Create parser
            soup = BeautifulSoup(c, 'html.parser', from_encoding='utf-8')

            # Get stuff
            mydivs = soup.findAll("div", {"class": "gs_or"})[:batch_size]

            for div in mydivs:
                try:
                    links.append(div.find('h3').find('a').get('href'))
                except:
                    links.append('Look manually at: ' + url)

                try:
                    titles.append(div.find('h3').find('a').text)
                except:
                    titles.append('Could not catch title')

                try:
                    citations.append(self.get_citations(str(div.format_string)))
                except:
                    citations.append(0)

                try:
                    years.append(self.get_year(div.find('div', {'class': 'gs_a'}).text))
                except:
                    years.append(0)

                try:
                    authors.append(self.get_author(div.find('div', {'class': 'gs_a'}).text))
                except:
                    authors.append("Author not found")

                try:
                    publishers.append(div.find('div', {'class': 'gs_a'}).text.split("-")[-1])
                except:
                    publishers.append("Publisher not found")

                try:
                    venues.append(" ".join(div.find('div', {'class': 'gs_a'}).text.split("-")[-2].split(",")[:-1]))
                except:
                    venues.append("Venue not found")
                
                try:
                    describes.append(self.get_author(div.find('div', {'class': 'gs_rs'}).text))
                except:
                    describes.append("Describe not found")

                rank.append(rank[-1] + 1)
                n += 1

            if n >= self.nresults:
                break

        # Create a dataset
        data = list(zip(authors, titles, citations, years, publishers, venues, describes, links))
        return data

    def format_results_as_markdown(self, data):
        markdown_results = ""
        for i, result in enumerate(data, start=1):
            author, title, citations, year, publisher, venue, describe, link = result
            markdown_results += f"{i}. **{title}** ({year})\n"
            markdown_results += f"   - Author: {author}\n"
            markdown_results += f"   - Citations: {citations}\n"
            markdown_results += f"   - Publisher: {publisher}\n"
            markdown_results += f"   - Venue: {venue}\n"
            markdown_results += f"   - Describe: {describe}\n"
            markdown_results += f"   - Link: {link}\n\n"
        return markdown_results

    # Helper functions (unchanged)
    def get_citations(content):
        citation_start = content.find('Cited by ')
        if citation_start == -1:
            return 0
        citation_end = content.find('<', citation_start)
        return int(content[citation_start + 9:citation_end])


    def get_year(content):
        for char in range(0, len(content)):
            if content[char] == '-':
                out = content[char - 5:char - 1]
        if not out.isdigit():
            out = 0
        return int(out)
    
    def get_author(content):
        author_end = content.find('-')
        return content[2:author_end - 1]


def setup_driver():
    try:
        from selenium import webdriver
        from selenium.common.exceptions import StaleElementReferenceException
        from selenium.webdriver.chrome.options import Options
    except Exception as e:
        print(e)
        print("Please install Selenium and chrome webdriver for manual checking of captchas")

    chrome_options = Options()
    chrome_options.add_argument("disable-infobars")
    driver = webdriver.Chrome(chrome_options=chrome_options)
    return driver



def get_element(driver, xpath, attempts=5, count=0):
    '''Safe get_element method with multiple attempts'''
    try:
        element = driver.find_element_by_xpath(xpath)
        return element
    except Exception as e:
        if count < attempts:
            sleep(1)
            return get_element(driver, xpath, attempts=attempts, count=count + 1)
        else:
            print("Element not found")
            return None


def get_content_with_selenium(url):
    global driver
    if 'driver' not in globals():
        driver = setup_driver()

    driver.get(url)
    el = get_element(driver, "/html/body")
    content = el.get_attribute('innerHTML')

    if any(kw in content for kw in ROBOT_KW):
        input("Solve captcha manually and press enter here to continue...")
        driver.get(url)
        el = get_element(driver, "/html/body")
        content = el.get_attribute('innerHTML')

    return content.encode('utf-8')  