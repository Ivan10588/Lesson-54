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

def emkashop_parser(url):
    """Парсинг emkashop"""
    response = safe_request(url)
    if not response:
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    items = []

    catalog_container = soup.find('div', id='cat-150')

    if catalog_container:
        products = catalog_container.find_all(
            'div',
            class_='body__noindex body__catalog l-ss-c-is-responsive popmechanic-desktop'
        )
    else:
        logger.warning("Блок с ID 'cat-150' не найден, ищем товары по всей странице")
        products = soup.find_all(
            'div',
            class_='body__noindex body__catalog l-ss-c-is-responsive popmechanic-desktop'
        )

    for product in products:
        try:
            title_elem = product.find('a', class_='catalog-product__name')
            price_elem = product.find('div', class_='product-purchase__price')

            if title_elem and price_elem:
                title = title_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True)\
                    .replace(' ', '')\
            .replace('₽', '')\
            .replace(',', '.')
                try:
                    price = float(price_text)
                except ValueError:
                    price = 0.0

                item = {
                    'title': title,
            'price': price,
            'store': 'emkashop',
            'url': urljoin(url, title_elem['href']) if title_elem.get('href') else url
                }
                items.append(item)
        except AttributeError as e:
            logger.warning(f"Пропущен элемент emkashop из‑за ошибки: {e}")
            continue
        except Exception as e:
            logger.warning(f"Неожиданная ошибка при обработке товара: {e}")
            continue

    logger.info(f"Найдено товаров: {len(items)}")
    return items

def dayoffmood_parser(url):
    """Парсинг dayoffmood"""
    response = safe_request(url)
    if not response:
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    items = []

    catalog_container = soup.find('div', id='mse2_results')

    if catalog_container:
        products = catalog_container.find_all('div', class_='product-card')
    else:
        logger.warning("Блок с ID 'mse2_results' не найден, ищем товары по всей странице")
        products = soup.find_all('div', class_='product-card')

    for product in products:
        try:
            title_elem = product.find('a', class_='product-card__title')
            price_elem = product.find('span', class_='product-card__price-value')

            if title_elem and price_elem:
                title = title_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True)\
                    .replace(' ', '')\
            .replace('₽', '')\
            .replace(',', '.')
                try:
                    price = float(price_text)
                except ValueError:
                    price = 0.0

                item = {
                    'title': title,
            'price': price,
            'store': 'dayoffmood',
            'url': urljoin(url, title_elem['href']) if title_elem.get('href') else url
                }
                items.append(item)
        except AttributeError as e:
            logger.warning(f"Пропущен элемент dayoffmood из‑за ошибки: {e}")
            continue
        except Exception as e:
            logger.warning(f"Неожиданная ошибка при обработке товара: {e}")
            continue

    logger.info(f"Найдено товаров: {len(items)}")
    return items

def parse_multiple_pages(base_url, parser_func, max_pages=3):
    """Парсинг нескольких страниц"""
    all_data = []
    for page in range(1, max_pages + 1):
        if page == 1:
            url = base_url
        else:
            parsed_url = urlparse(base_url)
            if page == 1:
                url = base_url
            else:
                parsed_url = urlparse(base_url)
                if 'emkashop' in parsed_url.netloc:
                    url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?page={page}"
                elif 'dayoffmood' in parsed_url.netloc:
                    url = f"{base_url}?page={page}"

        logger.info(f"Парсинг страницы {page}: {url}")
        data = parser_func(url)
        all_data.extend(data)
        time.sleep(3)

    return all_data

def save_to_csv(data, filename='comparison_data.csv'):
    """Сохранение в CSV"""

    if not data:
        logger.warning(f"Нет данных для сохранения в {filename}")
        return

    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding='utf-8')
    logger.info(f"Данные сохранены в {filename}")

def save_to_excel(data, filename='comparison_data.xlsx'):
    """Сохранение в Excel"""

    if not data:
        logger.warning(f"Нет данных для сохранения в {filename}")
        return

    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    logger.info(f"Данные сохранены в {filename}")


def compare_prices(emkashop_data, dayoffmood_data):
    """Сравнение цен между магазинами"""
    comparison = []

    emkashop_dict = {item['title'].lower().strip(): item for item in emkashop_data}
    dayoffmood_dict = {item['title'].lower().strip(): item for item in dayoffmood_data}

    common_titles = set(emkashop_dict.keys()) & set(dayoffmood_dict.keys())

    for title in common_titles:
        emkashop_price = emkashop_dict[title]['price']
        dayoffmood_price = dayoffmood_dict[title]['price']

        comparison.append({
            'title': title,
            'emkashop_price': emkashop_price,
            'dayoffmood_price': dayoffmood_price,
            'price_difference': emkashop_price - dayoffmood_price,
            'better_price': 'emkashop' if emkashop_price < dayoffmood_price else 'dayoffmood' if dayoffmood_price < emkashop_price else 'Равные цены'
        })

    return comparison

def main_comparison_task():
    """Основной процесс сравнения цен"""
    logger.info("Начало процесса сравнения цен emkashop и dayoffmood")

    emkashop_url = "https://emkashop.ru/platya"
    dayoffmood_url = "https://dayoffmood.com/collection/"

    logger.info("Парсинг emkashop...")
    emkashop_data = parse_multiple_pages(emkashop_url, emkashop_parser, max_pages=2)

    logger.info("Парсинг dayoffmood...")
    dayoffmood_data = parse_multiple_pages(dayoffmood_url, dayoffmood_parser, max_pages=2)

    comparison_data = []

    if emkashop_data or dayoffmood_data:
        comparison_data = compare_prices(emkashop_data, dayoffmood_data)

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        if emkashop_data + dayoffmood_data:
            save_to_csv(emkashop_data + dayoffmood_data, f"raw_data_{timestamp}.csv")
            save_to_excel(emkashop_data + dayoffmood_data, f"raw_data_{timestamp}.xlsx")

        if comparison_data:
            save_to_csv(comparison_data, f"comparison_{timestamp}.csv")
            save_to_excel(comparison_data, f"comparison_{timestamp}.xlsx")

            total_common = len(comparison_data)
            emkashop_better = sum(1 for item in comparison_data if item['better_price'] == 'emkashop')
            dayoffmood_better = sum(1 for item in comparison_data if item['better_price'] == 'dayoffmood')
            equal = sum(1 for item in comparison_data if item['better_price'] == 'Равные цены')


            logger.info("=== РЕЗУЛЬТАТЫ СРАВНЕНИЯ ===")
            logger.info(f"Всего найдено общих товаров: {total_common}")
            logger.info(f"Выгоднее в emkashop: {emkashop_better} товаров")
            logger.info(f"Выгоднее в dayoffmood: {dayoffmood_better} товаров")
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