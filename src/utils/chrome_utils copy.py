import os
import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager  # Import webdriver_manager
import urllib
from src.logging import logger

def chrome_browser_options():
    logger.debug("Setting Chrome browser options")
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")  # Opzionale, utile in alcuni ambienti
    options.add_argument("window-size=1200x800")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-autofill")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-animations")
    options.add_argument("--disable-cache")
    # options.add_argument("--incognito")
    options.add_argument("--allow-file-access-from-files")  # Consente l'accesso ai file locali
    options.add_argument("--disable-web-security")         # Disabilita la sicurezza web
    logger.debug("Using Chrome in incognito mode")
    
    return options

def init_browser() -> webdriver.Firefox:
    try:
        options = chrome_browser_options()
        # Use webdriver_manager to handle ChromeDriver
        driver = webdriver.Chrome(service=FirefoxService(GeckoDriverManager().install()), options=options)
        logger.debug("Chrome browser initialized successfully.")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize browser: {str(e)}")
        raise RuntimeError(f"Failed to initialize browser: {str(e)}")



def HTML_to_PDF(html_content, driver, output_path="output.pdf"):
    """
    Converts an HTML string to PDF using Firefox's native print-to-PDF.
    """
    # Validate HTML content
    if not isinstance(html_content, str) or not html_content.strip():
        raise ValueError("Il contenuto HTML deve essere una stringa non vuota.")

    # Encode the HTML content and load it as a data URL
    encoded_html = urllib.parse.quote(html_content)
    data_url = f"data:text/html;charset=utf-8,{encoded_html}"

    try:
        driver.get(data_url)
        time.sleep(2)  # Allow time for the page to fully load

        # Use Firefox to print the page to PDF
        driver.execute_script("window.print();")
        driver.save_screenshot(output_path)
        logger.debug(f"PDF successfully saved to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"WebDriver error occurred: {e}")
        raise RuntimeError(f"WebDriver error occurred: {e}")
