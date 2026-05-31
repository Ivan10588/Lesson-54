import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
import schedule
import re
from urllib.parse import urljoin, urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def validate_url(url):
    """Проверяет, что URL корректен"""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if re.match(pattern, url):
        return True
    else:
        logger.error(f"Некорректный URL: {url}")
        return False

def safe_request(url, retries=3):
    """Безопасный запрос с повторными попытками"""
    if not validate_url(url):
        return None

    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response
            elif response.status_code in [401, 503]:
                logger.warning(f"Сервер вернул код {response.status_code} — возможно, требуется дополнительная аутентификация или сайт перегружен")
                time.sleep(10)
            else:
                logger.warning(f"Попытка {attempt + 1} не удалась: код {response.status_code}")
        except requests.RequestException as e:
            logger.warning(f"Попытка {attempt + 1} не удалась: {e}")
        time.sleep(2)

    logger.error(f"Не удалось получить данные после {retries} попыток: {url}")
    return None

def dns_parser(url):
    """Парсинг DNS"""
    response = safe_request(url)
    if not response:
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    items = []

    products = soup.find_all('div', class_='catalog-product')
    for product in products:
        try:
            title_elem = product.find('a', class_='catalog-product__name')
            price_elem = product.find('div', class_='product-purchase__price')

            if title_elem and price_elem:
                title = title_elem.text.strip()
                price = price_elem.text.strip().replace(' ', '').replace('₽', '').replace(',', '.')
                try:
                    price = float(price)
                except ValueError:
                    price = 0.0

                item = {
                    'title': title,
                    'price': price,
                    'store': 'DNS',
                    'url': urljoin(url, title_elem['href']) if title_elem.get('href') else url
                }
                items.append(item)
        except AttributeError as e:
            logger.warning(f"Пропущен элемент DNS из‑за ошибки: {e}")
            continue

    return items

def eldorado_parser(url):
    """Парсинг Эльдорадо"""
    response = safe_request(url)
    if not response:
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    items = []
    products = soup.find_all('div', class_='product-card')
    for product in products:
        try:
            title_elem = product.find('a', class_='product-card__title')
            price_elem = product.find('span', class_='product-card__price-value')

            if title_elem and price_elem:
                title = title_elem.text.strip()
                price = price_elem.text.strip().replace(' ', '').replace('₽', '').replace(',', '.')
                try:
                    price = float(price)
                except ValueError:
                    price = 0.0

                item = {
                    'title': title,
                    'price': price,
                    'store': 'Эльдорадо',
                    'url': urljoin(url, title_elem['href']) if title_elem.get('href') else url
                }
                items.append(item)
        except AttributeError as e:
            logger.warning(f"Пропущен элемент Эльдорадо из‑за ошибки: {e}")
            continue

    return items

def parse_multiple_pages(base_url, parser_func, max_pages=3):
    """Парсинг нескольких страниц"""
    all_data = []
    for page in range(1, max_pages + 1):
        if page == 1:
            url = base_url
        else:
            parsed_url = urlparse(base_url)
            if 'dns-shop' in parsed_url.netloc:
                url = f"{base_url}&page={page}"
            elif 'eldorado' in parsed_url.netloc:
                url = f"{base_url}?page={page}"

        logger.info(f"Парсинг страницы {page}: {url}")
        data = parser_func(url)
        all_data.extend(data)
        time.sleep(5)

    return all_data

def save_to_csv(data, filename='comparison_data.csv'):
    """Сохранение в CSV"""
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding='utf-8')
    logger.info(f"Данные сохранены в {filename}")

def save_to_excel(data, filename='comparison_data.xlsx'):
    """Сохранение в Excel"""
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    logger.info(f"Данные сохранены в {filename}")

def compare_prices(dns_data, eldorado_data):
    """Сравнение цен между магазинами"""
    comparison = []

    dns_dict = {item['title'].lower(): item for item in dns_data}
    eldorado_dict = {item['title'].lower(): item for item in eldorado_data}

    common_titles = set(dns_dict.keys()) & set(eldorado_dict.keys())

    for title in common_titles:
        dns_price = dns_dict[title]['price']
        eldorado_price = eldorado_dict[title]['price']

        comparison.append({
            'title': title,
            'dns_price': dns_price,
            'eldorado_price': eldorado_price,
            'price_difference': dns_price - eldorado_price,
            'better_price': 'DNS' if dns_price < eldorado_price else 'Эльдорадо' if eldorado_price < dns_price else 'Равные цены'
        })

    return comparison

def main_comparison_task():
    """Основной процесс сравнения цен"""
    logger.info("Начало процесса сравнения цен DNS и Эльдорадо")

    dns_url = "https://www.dns-shop.ru/catalog/17a8a01d16404e77/smartfony/"
    eldorado_url = "https://www.eldorado.ru/c/smartfony/"

    logger.info("Парсинг DNS...")
    dns_data = parse_multiple_pages(dns_url, dns_parser, max_pages=2)


    logger.info("Парсинг Эльдорадо...")
    eldorado_data = parse_multiple_pages(eldorado_url, eldorado_parser, max_pages=2)

    comparison_data = []

    if dns_data or eldorado_data:
        comparison_data = compare_prices(dns_data, eldorado_data)

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        save_to_csv(dns_data + eldorado_data, f"raw_data_{timestamp}.csv")
        save_to_excel(dns_data + eldorado_data, f"raw_data_{timestamp}.xlsx")

        if comparison_data:
            save_to_csv(comparison_data, f"comparison_{timestamp}.csv")
            save_to_excel(comparison_data, f"comparison_{timestamp}.xlsx")

            total_common = len(comparison_data)
            dns_better = sum(1 for item in comparison_data if item['better_price'] == 'DNS')
            eldorado_better = sum(1 for item in comparison_data if item['better_price'] == 'Эльдорадо')
            equal = sum(1 for item in comparison_data if item['better_price'] == 'Равные цены')

            logger.info("=== РЕЗУЛЬТАТЫ СРАВНЕНИЯ ===")
            logger.info(f"Всего найдено общих товаров: {total_common}")
            logger.info(f"Выгоднее в DNS: {dns_better} товаров")
            logger.info(f"Выгоднее в Эльдорадо: {eldorado_better} товаров")
            logger.info(f"Цены равны: {equal} товаров")

            if comparison_data:
                avg_diff = sum(abs(item['price_difference']) for item in comparison_data) / total_common
                logger.info(f"Средняя разница в цене: {avg_diff:.2f} руб.")
        else:
            logger.warning("Не найдено общих товаров для сравнения")
    else:
        logger.warning("Не удалось получить данные ни из одного магазина")

    logger.info("Процесс сравнения завершён")
    return comparison_data

def scheduled_comparison():
    """Запланированное сравнение цен"""
    logger.info("Запуск автоматического сравнения цен DNS и Эльдорадо")
    main_comparison_task()

schedule.every().day.at("10:00").do(scheduled_comparison)

schedule.every().friday.at("15:00").do(scheduled_comparison)

if __name__ == "__main__":

    logger.info("Запуск разового сравнения цен")
    results = main_comparison_task()

    logger.info("Планировщик запущен. Ожидание задач...")
    while True:
        schedule.run_pending()
        time.sleep(60)
