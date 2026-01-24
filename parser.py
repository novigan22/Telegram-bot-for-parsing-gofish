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
logger = logging.getLogger(**name**)

BOT_TOKEN = “YOUR_BOT_TOKEN_HERE”
bot = Bot(token=BOT_TOKEN)

USER_ID = 123456789 #YOUR_TELEGRAM_ID

def create_driver():
chrome_options = Options()
chrome_options.add_argument(’–headless’)
chrome_options.add_argument(’–no-sandbox’)
chrome_options.add_argument(’–disable-dev-shm-usage’)
chrome_options.add_argument(’–disable-gpu’)
chrome_options.add_argument(’–window-size=1920,1080’)
chrome_options.add_argument(‘user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36’)

```
driver = webdriver.Chrome(options=chrome_options)
return driver
```

def parse_gofish_page(url: str):
driver = None
try:
driver = create_driver()
logger.info(f”Открытие страницы: {url}”)
driver.get(url)

```
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "feeds-item-wrap--rGdH_KoF"))
        )
    except:
        logger.warning("Товары не загрузились за 30 секунд")
        return []
    
    import time
    time.sleep(3)
    
    products = []
    items = driver.find_elements(By.CLASS_NAME, "feeds-item-wrap--rGdH_KoF")
    
    logger.info(f"Найдено элементов товаров: {len(items)}")
    
    for item in items:
        try:
            link = item.get_attribute('href')
            if not link:
                continue
            
            product_id = None
            if 'id=' in link:
                product_id = link.split('id=')[1].split('&')[0]
            
            if not product_id:
                continue
            
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
                if image_url and not image_url.startswith('http'):
                    image_url = 'https:' + image_url
            except:
                image_url = ''
            
            if not title or not price or title == 'Без названия':
                logger.debug(f"Пропущен товар без данных: ID={product_id}")
                continue
            
            products.append({
                'id': product_id,
                'title': title,
                'price': price,
                'link': link,
                'image': image_url
            })
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге товара: {e}")
            continue
    
    return products

except Exception as e:
    logger.error(f"Ошибка при парсинге страницы {url}: {e}")
    return []

finally:
    if driver:
        driver.quit()
```

async def send_product_notification(product: dict):
try:
message = f”””
🆕 <b>Новый товар!</b>

📦 <b>{product[‘title’]}</b>

💰 Цена: <b>¥{product[‘price’]}</b>

🔗 <a href="{product['link']}">Посмотреть товар</a>
“””

```
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
```

async def check_links():
logger.info(“Начало проверки ссылок…”)

```
user_links = get_user_links(USER_ID)

if not user_links:
    logger.info("Нет ссылок для проверки")
    return

for link_obj in user_links:
    logger.info(f"Проверка ссылки: {link_obj.link}")
    
    products = parse_gofish_page(link_obj.link)
    
    logger.info(f"Найдено товаров: {len(products)}")
    
    for product in products:
        if not is_product_tracked(product['id']):
            await send_product_notification(product)
            
            add_tracked_product(product['id'], USER_ID, link_obj.id)
            
            logger.info(f"Новый товар добавлен: {product['id']}")
        else:
            logger.debug(f"Товар уже отслеживается: {product['id']}")
    
    await asyncio.sleep(2)
```

async def main():
logger.info(“Парсер запущен!”)

```
while True:
    try:
        await check_links()
    except Exception as e:
        logger.error(f"Ошибка в цикле парсера: {e}")
    
    logger.info("Ожидание 60 секунд до следующей проверки...")
    await asyncio.sleep(60)
```

if **name** == “**main**”:
asyncio.run(main())
