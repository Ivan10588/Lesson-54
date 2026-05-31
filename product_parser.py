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

def parse_multiple_pages(base_url, max_pages=5):
    all_data = []
    for page in range(1, max_pages + 1):
        url = f"{base_url}?page={page}"
        soup = basic_parser(url)
        if soup:
            data = extract_data(soup)
            all_data.extend(data)
            time.sleep(1)
        else:
            logger.error(f"Не удалось загрузить страницу {page}")
    return all_data

def save_to_csv(data, filename='parsed_data.csv'):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding='utf-8')

def save_to_json(data, filename='parsed_data.json'):
    import json
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_to_excel(data, filename='parsed_data.xlsx'):
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)

def safe_request(url, retries=3):
    for attempt in range(retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response
        except requests.RequestException as e:
            logger.warning(f"Попытка {attempt + 1} не удалась: {e}")
            time.sleep(2)
    logger.error(f"Не удалось получить данные после {retries} попыток")
    return None

