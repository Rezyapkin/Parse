import os
from dotenv import load_dotenv
import requests
from urllib.parse import urljoin
import bs4
import pymongo
import time


class ParseError(Exception):
    def __init__(self, txt):
        self.txt = txt


class MagnitParser:
    TRY_COUNT = 2

    def __init__(self, start_url, data_base):
        self.start_url = start_url
        self.database = data_base["gb_parse_magnit"]

    @staticmethod
    def __get_response(url, *args, **kwargs):
        for _ in range(__class__.TRY_COUNT):
            try:
                response = requests.get(url, *args, **kwargs)
                if response.status_code > 399:
                    raise ParseError(response.status_code)
                time.sleep(0.1)
                return response
            except (requests.RequestException, ParseError):
                time.sleep(0.5)
                continue

    @staticmethod
    def __get_price(tag):
        print(tag.find(
                "div", attrs={"class": "card-sale__title"}
            ).text)
        return float(tag.find("span", attrs={"class": "label__price-integer"}).text) + \
               float(tag.find("span", attrs={"class": "label__price-decimal"}).text or 0) / 100

    @property
    def data_template(self):
        return {
            "url": lambda tag: urljoin(self.start_url, tag.attrs.get("href")),
            "promo_name": lambda tag: tag.find(
                "div", attrs={"class": "card-sale__name"}
            ).text,
            "product_name": lambda tag: tag.find(
                "div", attrs={"class": "card-sale__title"}
            ).text,
            "old_price": lambda tag: self.__get_price(tag.find(
                "div", attrs={"class": "label__price_new"}
            )),
            "new_price": lambda tag: self.__get_price(tag.find(
                "div", attrs={"class": "label__price_new"}
            )),
            "image_url": lambda tag: urljoin(self.start_url, tag.find(
                "img", attrs={"class": "lazy"}
            ).attrs.get("data-src")),
            "date_from": lambda tag: tag.find(
                "div", attrs={"class": "card-sale__date"}
            ).text,
            "date_to": lambda tag: tag.find(
                "div", attrs={"class": "card-sale__date"}
            ).text,
        }

    @staticmethod
    def __get_soup(response):
        return bs4.BeautifulSoup(response.text, "lxml")

    def run(self):
        for product in self.parse(self.start_url):
            self.save(product)

    def validate_product(self, product_data):
        return product_data

    def parse(self, url):
        soup = self.__get_soup(self.__get_response(url))
        catalog_main = soup.find("div", attrs={"class": "сatalogue__main"})
        for product_tag in catalog_main.find_all(
            "a", attrs={"class": "card-sale"}, reversive=False
        ):
            yield self.__get_product_data(product_tag)

    def __get_product_data(self, product_tag):
        data = {}
        for key, pattern in self.data_template.items():
            try:
                data[key] = pattern(product_tag)
            except AttributeError:
                continue
        return data

    def save(self, data):
        collection = self.database["magnit_product"]
        collection.insert_one(data)


if __name__ == "__main__":
    load_dotenv('.env')
    data_base = pymongo.MongoClient(os.getenv("DATA_BASE_URL"))
    parser = MagnitParser("https://magnit.ru/promo/?geo=moskva", data_base)
    parser.run()
