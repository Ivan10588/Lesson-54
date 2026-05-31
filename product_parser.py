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

def extract_data(soup):
    items = []
    products = soup.find_all('div', class_='product-item')
    for product in products:
        try:
            title = product.find('h3', class_='title').text.strip()
            price = product.find('span', class_='price').text.strip()
            description = product.find('p', class_='description').text.strip() if product.find('p', class_='description') else 'Нет описания'
            item = {
                'title': title,
                'price': price,
                'description': description
            }
            items.append(item)
        except AttributeError as e:
            logger.warning(f"Пропущен элемент из‑за ошибки: {e}")
            continue
    return items


