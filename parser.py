import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from aiogram import Bot
from database import get_user_links, is_product_tracked, add_tracked_product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "YOUR_TOKEN_BOT"
bot = Bot(token=BOT_TOKEN)

USER_ID = 123456789

def parse_gofish_page(url: str):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        products = []
        items = soup.find_all('a', class_='feeds-item-wrap--rGdH_KoF')
        
        for item in items:
            try:
                link = item.get('href', '')
                if not link.startswith('http'):
                    link = 'https://www.goofish.com' + link
                
                product_id = None
                if 'id=' in link:
                    product_id = link.split('id=')[1].split('&')[0]
                
                if not product_id:
                    continue
                
                title_elem = item.find('span', class_='main-title--sMrtWSJa')
                title = title_elem.get_text(strip=True) if title_elem else 'Без названия'
                
                price_elem = item.find('span', class_='number--NKh1vXWM')
                price = price_elem.get_text(strip=True) if price_elem else '0'
                
                img_elem = item.find('img', class_='feeds-image--TDRC4fV1')
                image_url = img_elem.get('src', '') if img_elem else ''
                if image_url and not image_url.startswith('http'):
                    image_url = 'https:' + image_url
                
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


async def check_links():
    logger.info("Начало проверки ссылок...")
    
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


async def main():
    logger.info("Парсер запущен!")
    
    while True:
        try:
            await check_links()
        except Exception as e:
            logger.error(f"Ошибка в цикле парсера: {e}")
        
        logger.info("Ожидание 60 секунд до следующей проверки...")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())