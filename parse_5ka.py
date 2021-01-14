import json
import time
from pathlib import Path
import requests


"""
GET
POST 
PUT 
PUTCH
DELETE
"""

"""
1xx - Information
2xx - OK
3xx - Redirect
4xx - Client error
5xx - Server error
"""


# ?store=&records_per_page=12&page=1&categories=&ordering=&price_promo__gte=&price_promo__lte=&search=
# url = "https://5ka.ru/api/v2/special_offers/"
# params = {
#     "records_per_page": 100,
#     "page": 1,
# }
# headers = {
#     "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.16; rv:84.0) Gecko/20100101 Firefox/84.0",
#     "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
# }
#
# response: requests.Response = requests.get(url, params=params, headers=headers)
#
# with open("5ka.ru.html", "w", encoding="UTF-8") as file:
#     file.write(response.text)
# print(1)
#


class ParseError(Exception):
    def __init__(self, txt):
        self.txt = txt


class Parse5ka:
    params = {
        "records_per_page": 100,
        "page": 1,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.16; rv:84.0) Gecko/20100101 Firefox/84.0",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    }

    def __init__(self, start_url, result_path):
        self.start_url = start_url
        self.result_path = result_path

    @staticmethod
    def _get_response(url, *args, **kwargs) -> requests.Response:
        while True:
            try:
                response = requests.get(url, *args, **kwargs)
                if response.status_code > 399:
                    raise ParseError(response.status_code)
                time.sleep(0.1)
                return response
            except (requests.RequestException, ParseError):
                time.sleep(0.5)
                continue

    def run(self):
        for product in self.parse(self.start_url):
            path = self.result_path.joinpath(f"{product['id']}.json")
            self.save(product, path)

    def parse(self, url):
        params = self.params
        while url:
            response = self._get_response(url, params=params, headers=self.headers)
            if params:
                params = {}
            data = json.loads(response.text)
            url = data.get("next")
            for product in data.get("results"):
                yield product

    @staticmethod
    def save(data, path: Path):
        with path.open("w", encoding="UTF-8") as file:
            json.dump(data, file, ensure_ascii=False)


class MyParse5ka(Parse5ka):
    def __init__(self, start_url, result_path, url_categories):
        super().__init__(start_url, result_path)
        self.url_categories = url_categories

    def get_categories(self):
        response = self.__class__._get_response(self.url_categories, params={}, headers=self.headers)
        return json.loads(response.text)

    def run(self):
        params = self.params
        for category in self.get_categories():
            self.params["categories"] = category.get("parent_group_code")
            if not self.params["categories"].isdigit():
                continue
            products = list(self.parse(self.start_url))
            if not len(products):
                continue
            result = {
                "name": category.get("parent_group_name"),
                "code": category.get("parent_group_code"),
                "products": products,
            }
            path = self.result_path.joinpath(f"{self.params['categories']}.json")
            self.save(result, path)
        self.params = params


if __name__ == "__main__":
    result_path = Path(__file__).parent.joinpath("products")
    base_url = "https://5ka.ru/api/v2/special_offers/?categories="
    url_categories = "https://5ka.ru/api/v2/categories/"
    parser = MyParse5ka(base_url, result_path, url_categories)
    parser.run()
