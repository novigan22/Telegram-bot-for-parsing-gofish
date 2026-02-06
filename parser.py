import asyncio
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from aiogram import Bot
from database import get_user_links, is_product_tracked, add_tracked_product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "YOUR_TOKEN_BOT"
bot = Bot(token=BOT_TOKEN)

USER_ID = 123456789

HEADLESS = False
MAX_PAGES = 3


def create_driver():
    chrome_options = Options()
    
    if HEADLESS:
        chrome_options.add_argument('--headless=new')
    
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


def parse_gofish_page(driver, url: str, min_price: int = None, max_price: int = None):
    try:
        logger.info(f"Открытие страницы: {url}")
        driver.get(url)
        
        import time
        time.sleep(5)
        
        try:
            logger.info("Ожидание и закрытие модальных окон...")
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.common.action_chains import ActionChains
            
            time.sleep(3)
            
            try:
                close_icon = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "closeIcon--gwB7wNKs"))
                )
                logger.info("Плашка регистрации найдена, закрываем...")
                time.sleep(1)
                
                driver.execute_script("arguments[0].scrollIntoView(true);", close_icon)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", close_icon)
                logger.info("Закрыта плашка регистрации")
                time.sleep(2)
            except:
                logger.info("Плашка регистрации не появилась или уже закрыта")
            
            actions = ActionChains(driver)
            actions.send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
            
        except Exception as e:
            logger.debug(f"Ошибка при закрытии модальных окон: {e}")
        
        logger.info("Скроллинг страницы для загрузки товаров...")
        for i in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(1)
        
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(3)
        
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "feeds-item-wrap--rGdH_KoF"))
            )
            logger.info("Товары найдены!")
        except:
            logger.warning("Товары не загрузились за 30 секунд")
            logger.info("Попытка найти товары по альтернативным селекторам...")
            
            html = driver.page_source
            if "feeds-item-wrap" not in html:
                logger.error("HTML не содержит элементов товаров. Возможна блокировка или изменение структуры.")
                logger.info(f"Первые 500 символов HTML: {html[:500]}")
            
            return []
        
        import time
        
        if min_price or max_price:
            logger.info(f"Применение фильтра цен: {min_price} - {max_price}")
            try:
                from selenium.webdriver.common.keys import Keys
                time.sleep(3)
                
                price_inputs = driver.find_elements(By.CLASS_NAME, "search-price-input--p1NQEAuz")
                
                if len(price_inputs) < 2:
                    logger.error(f"Найдено только {len(price_inputs)} полей ввода цены, нужно 2")
                    raise Exception("Поля ввода цены не найдены")
                
                logger.info(f"Найдено {len(price_inputs)} полей ввода цены")
                
                if min_price:
                    min_input = price_inputs[0]
                    min_input.click()
                    time.sleep(0.5)
                    min_input.clear()
                    time.sleep(0.3)
                    min_input.send_keys(str(min_price))
                    logger.info(f"Установлена минимальная цена: {min_price}")
                    time.sleep(1)
                
                if max_price:
                    max_input = price_inputs[1]
                    max_input.click()
                    time.sleep(0.5)
                    max_input.clear()
                    time.sleep(0.3)
                    max_input.send_keys(str(max_price))
                    logger.info(f"Установлена максимальная цена: {max_price}")
                    time.sleep(0.5)
                    max_input.send_keys(Keys.ENTER)
                    logger.info("Нажат Enter для применения фильтра")
                    time.sleep(1)
                elif min_price:
                    min_input = price_inputs[0]
                    min_input.send_keys(Keys.ENTER)
                    logger.info("Нажат Enter для применения фильтра")
                    time.sleep(1)
                
                logger.info("Ожидание обновления товаров после фильтра...")
                time.sleep(5)
                
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "feeds-item-wrap--rGdH_KoF"))
                )
                time.sleep(2)
                logger.info("Фильтр цен успешно применён")
                
            except Exception as e:
                logger.error(f"Не удалось применить фильтр цен: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        time.sleep(3)
        
        all_products = []
        seen_ids = set()
        
        for page in range(MAX_PAGES):
            logger.info(f"Обработка страницы {page + 1}/{MAX_PAGES}...")
            
            if page > 0:
                time.sleep(2)
            
            logger.info("Скроллинг для загрузки товаров на текущей странице...")
            for i in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
            
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            items = driver.find_elements(By.CLASS_NAME, "feeds-item-wrap--rGdH_KoF")
            logger.info(f"Найдено элементов товаров: {len(items)}")
            
            if len(items) == 0:
                logger.info("Товары не найдены, прекращаем")
                break
            
            logger.info("Дополнительный скроллинг для загрузки всех изображений...")
            for i in range(len(items)):
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", items[i])
                    time.sleep(0.1)
                except:
                    pass
            
            time.sleep(2)
            
            items = driver.find_elements(By.CLASS_NAME, "feeds-item-wrap--rGdH_KoF")
            
            new_products_count = 0
            
            for item in items:
                try:
                    link = item.get_attribute('href')
                    if not link:
                        continue
                    
                    product_id = None
                    if 'id=' in link:
                        product_id = link.split('id=')[1].split('&')[0]
                    
                    if not product_id or product_id in seen_ids:
                        continue
                    
                    seen_ids.add(product_id)
                    
                    try:
                        title_elem = item.find_element(By.CLASS_NAME, "main-title--sMrtWSJa")
                        title = title_elem.text.strip()
                    except:
                        title = ''
                    
                    try:
                        price_elem = item.find_element(By.CLASS_NAME, "number--NKh1vXWM")
                        price = price_elem.text.strip()
                    except:
                        price = ''
                    
                    try:
                        img_elem = item.find_element(By.CLASS_NAME, "feeds-image--TDRC4fV1")
                        image_url = img_elem.get_attribute('src')
                        
                        if not image_url or image_url == '' or 'data:image' in image_url:
                            image_url = img_elem.get_attribute('data-src')
                        
                        if not image_url or image_url == '' or 'data:image' in image_url:
                            image_url = img_elem.get_attribute('data-lazy-src')
                        
                        if image_url and not image_url.startswith('http'):
                            image_url = 'https:' + image_url
                        
                        if not image_url or 'data:image' in image_url or len(image_url) < 20:
                            logger.debug(f"Некорректное изображение для товара {product_id}")
                            image_url = ''
                    except:
                        image_url = ''
                    
                    if not title or not price or title == 'Без названия':
                        logger.debug(f"Пропущен товар без данных: ID={product_id}")
                        continue
                    
                    if not image_url:
                        logger.debug(f"Пропущен товар без изображения: ID={product_id}, название={title[:30]}")
                        continue
                    
                    all_products.append({
                        'id': product_id,
                        'title': title,
                        'price': price,
                        'link': link,
                        'image': image_url
                    })
                    
                    new_products_count += 1
                    
                except Exception as e:
                    logger.error(f"Ошибка при парсинге товара: {e}")
                    continue
            
            logger.info(f"Новых товаров на странице {page + 1}: {new_products_count}")
            
            if page < MAX_PAGES - 1:
                try:
                    logger.info(f"Переход на страницу {page + 2}...")
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    
                    next_button = driver.find_element(By.CLASS_NAME, "search-pagination-arrow-right--CKU78u4z")
                    parent_button = next_button.find_element(By.XPATH, "..")
                    
                    if parent_button.get_attribute("disabled"):
                        logger.info("Кнопка 'Следующая страница' неактивна, достигнута последняя страница")
                        break
                    
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", parent_button)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", parent_button)
                    logger.info(f"Нажата кнопка перехода на страницу {page + 2}")
                    time.sleep(4)
                    
                except Exception as e:
                    logger.error(f"Не удалось перейти на следующую страницу: {e}")
                    break
        
        logger.info(f"Всего уникальных товаров найдено: {len(all_products)}")
        return all_products
    
    except Exception as e:
        logger.error(f"Ошибка при парсинге страницы {url}: {e}")
        return []


async def send_product_notification(product: dict):
    try:
        message = f"""
🆕 <b>Новый товар!</b>

📦 <b>{product['title']}</b>

💰 Цена: <b>¥{product['price']}</b>

🔗 <a href="{product['link']}">Посмотреть товар</a>
"""
        
        if product['image']:
            await bot.send_photo(
                chat_id=USER_ID,
                photo=product['image'],
                caption=message,
                parse_mode='HTML'
            )
        else:
            await bot.send_message(
                chat_id=USER_ID,
                text=message,
                parse_mode='HTML'
            )
        
        logger.info(f"Уведомление отправлено для товара {product['id']}")
    
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления: {e}")


async def check_links(driver):
    logger.info("Начало проверки ссылок...")
    
    user_links = get_user_links(USER_ID)
    
    if not user_links:
        logger.info("Нет ссылок для проверки")
        return
    
    for link_obj in user_links:
        logger.info(f"Проверка ссылки: {link_obj.link}")
        
        min_price = link_obj.min_price
        max_price = link_obj.max_price
        
        if min_price or max_price:
            logger.info(f"Фильтр цен: от {min_price} до {max_price}")
        
        products = parse_gofish_page(driver, link_obj.link, min_price, max_price)
        
        logger.info(f"Найдено товаров: {len(products)}")
        
        for product in products:
            if not is_product_tracked(product['id']):
                await send_product_notification(product)
                
                add_tracked_product(product['id'], USER_ID, link_obj.id)
                
                logger.info(f"Новый товар добавлен: {product['id']}")
            else:
                logger.debug(f"Товар уже отслеживается: {product['id']}")
        
        await asyncio.sleep(2)


async def main():
    logger.info("Парсер запущен!")
    
    driver = create_driver()
    logger.info("Браузер запущен и будет работать постоянно")
    
    try:
        while True:
            try:
                await check_links(driver)
            except Exception as e:
                logger.error(f"Ошибка в цикле парсера: {e}")
            
            logger.info("Ожидание 60 секунд до следующей проверки...")
            await asyncio.sleep(60)
    finally:
        logger.info("Закрытие браузера...")
        driver.quit()


if __name__ == "__main__":
    asyncio.run(main())