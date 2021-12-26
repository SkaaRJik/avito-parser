import logging
import pickle
from os import getenv, mkdir

from aiogram.types import ParseMode
from aiogram.utils.markdown import bold, link
import requests
from bs4 import BeautifulSoup, ResultSet
from fake_useragent import UserAgent
from aiogram import Bot
import asyncio

ua = UserAgent()

TOKEN = getenv('BOT_TOKEN')
if not TOKEN:
    exit('Error: no token provided')

minPrice: int = 20000
maxPrice: int = 100000


class Good:

    def __init__(self, title, price, img, url, description):
        self.title = title
        self.price = price
        self.img = img
        self.url = url
        self.description = description

    def __hash__(self):
        # necessary for instances to behave sanely in dicts and sets.
        return hash((self.title, self.price, self.url))

    def __eq__(self, other):
        """Override the default Equals behavior"""
        return self.title == other.title and self.price == other.price and self.url == other.url

    def markdown(self) -> str:
        return f'{link(self.title, self.url)}\n' \
               f'{bold("Цена:")} {self.price}'


ALREADY_SENT_GOODS: set[Good] = set()

dump_valve_index_filename = 'valve_index.bin'
try:
    with open(dump_valve_index_filename, 'rb') as f:
        ALREADY_SENT_GOODS = pickle.load(file=f)
except Exception as e:
    logging.error(e, exc_info=True)


def init_logger():
    logPath = './logs'
    fileName = 'logs'

    try:
        mkdir(logPath)
    except OSError:
        print('Создать директорию %s не удалось' % logPath)
    # Set up logging and formatting
    logger = logging.getLogger()
    logFormatter = logging.Formatter('%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s')

    # Set up the console handler
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)

    # Set up the file handler
    fileHandler = logging.FileHandler('{0}/{1}.log'.format(logPath, fileName))
    fileHandler.setFormatter(logFormatter)
    logger.addHandler(fileHandler)

    # Set up logging levels
    consoleHandler.setLevel(logging.INFO)
    fileHandler.setLevel(logging.INFO)
    logger.setLevel(logging.INFO)


def determine_valve_index():
    response = requests.get(
        url='https://www.avito.ru/rossiya/tovary_dlya_kompyutera/aksessuary-ASgBAgICAUTGB5Ro?cd=1&p=1&q=valve+index&user=1'
    )
    domain: str = 'https://www.avito.ru'

    soup: BeautifulSoup = BeautifulSoup(response.text, 'lxml')
    # with open('result.html', 'w', encoding='utf-8') as file:
    #     file.write(soup.prettify())

    items: ResultSet = soup.find_all(attrs={'data-marker': 'item'})
    goods_to_sent: set[Good] = set()
    for item in items:
        # goods.append({
        #     'title': item.h3.text,
        # })
        name: str = item.find('h3', attrs={'itemprop': 'name'}).text
        if not (name.find('valve') != -1 or name.find('index') != -1):
            continue

        price: int = int(item.find('meta', attrs={'itemprop': 'price'})['content'])

        if (not (price >= minPrice and price <= maxPrice)):
            continue

        descr: str = item.find('meta', attrs={'itemprop': 'description'})['content']

        url: str = domain + item.find('a', attrs={'itemprop': 'url'})['href']

        img = item.find('img', attrs={'itemprop': 'image'})
        img: str = img['src'] if img is not None else ''

        good = Good(url=url, img=img, description=descr, price=price, title=name)
        if not (good in ALREADY_SENT_GOODS):
            goods_to_sent.add(good)

    ALREADY_SENT_GOODS.update(goods_to_sent)
    pickle.dump(ALREADY_SENT_GOODS, open(dump_valve_index_filename, 'wb'), protocol=pickle.HIGHEST_PROTOCOL)
    return goods_to_sent


async def main():
    init_logger()
    operator: Bot = None
    try:
        operator = Bot(TOKEN)
    except Exception as e:
        logging.error(e, exc_info=True)
        exit('Operator is None')

    await notify_users(operator=operator, user_id='466881052')


async def notify_users(operator: Bot, user_id: str, ):
    try:
        goods = determine_valve_index()
        for idx, good in enumerate(goods):
            await operator.send_message(user_id, good.markdown(), parse_mode=ParseMode.MARKDOWN)
            if idx % 10 == 0:
                await asyncio.sleep(delay=10)
    except Exception as exc:
        logging.error(exc, exc_info=True)
        try:
            await operator.send_message(user_id, str(exc))
        except Exception as ex:
            logging.error(ex, exc_info=True)
    finally:
        operator.close_bot


if __name__ == '__main__':
    asyncio.run(main())
