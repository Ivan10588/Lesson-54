import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
import schedule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def basic_parser(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    else:
        print(f"Ошибка: {response.status_code}")
        return None


