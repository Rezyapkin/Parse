import scrapy
import json
import re
from urllib.parse import unquote, urljoin
from html2text import html2text
import pymongo


class AutoyuolaSpider(scrapy.Spider):
    name = "autoyoula"
    allowed_domains = ["auto.youla.ru"]
    start_urls = ["https://auto.youla.ru/"]
    # Страничку с объявлением проще на мобильной версии разбирать. Там и картинки все без проблем и телефон
    mobile_agent = "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) " \
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.146 Mobile Safari/537.36"

    css_query = {
        "brands": "div.TransportMainFilters_block__3etab a.blackLink",
        "pagination": "div.Paginator_block__2XAPy a.Paginator_button__u1e7D",
        "ads": "article.SerpSnippet_snippet__3O1t2 .SerpSnippet_titleWrapper__38bZM a.blackLink",
    }

    data_query = {
        "title": lambda resp: ", ".join(
            [resp.css("h1.advert__title ::text").get(), resp.css("span.advert__subtitle ::text").get()]
        ),
        "price": lambda resp: float(resp.css("span.advert-price__price ::text").get().replace(" ", "")),
        "description": lambda resp: resp.css(".advert-description p ::text").get(),
        "author": lambda resp: {
            "name": resp.css("div.advert-contacts__name ::text").get(),
            "phone": resp.css(".advert__call a").attrib["href"].replace("tel:", ""),
        },
        "images": lambda resp:
        json.loads(
            html2text(resp.css("div.content.content_full-page script ::text").get()).replace("\n", "")
        ).get("image"),
        "properties": lambda resp: [
            (prop.css(".table__cell:first-child ::text").get(), prop.css(".table__cell:last-child ::text").get())
            for prop in resp.css("div.table__row")
        ],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_client = pymongo.MongoClient()

    @staticmethod
    def get_user_url(response):
        return unquote(response.css("#initial-state ::text").get())

    def parse(self, response, **kwargs):
        brands_links = response.css(self.css_query["brands"])
        yield from self.gen_task(response, brands_links, self.brand_parse)

    def brand_parse(self, response):
        pagination_links = response.css(self.css_query["pagination"])
        yield from self.gen_task(response, pagination_links, self.brand_parse)
        ads_links = response.css(self.css_query["ads"])
        yield from self.gen_task(response, ads_links, self.ads_parse)

    def ads_parse(self, response):
        re_match = re.search(r'sellerLink%22%2C%22(.+?)%22', str(response.body))
        if re_match:
            author_url = urljoin(response.url, unquote(re_match[1]))
        else:
            re_match = re.search(r'%22youlaId%22%2C%22([\d\w]+)%22', str(response.body))
            author_url = f"https://youla.ru/user/{re_match[1]}" if re_match else None

        yield response.follow(
            response.url, callback=self.ads_parse_mobile, dont_filter=True,
            cb_kwargs={"author_url": author_url},
            headers={"User-Agent": self.mobile_agent}
        )

    def ads_parse_mobile(self, response, *args, **kwargs):
        data = {}

        for key, selector in self.data_query.items():
            try:
                data[key] = selector(response)
            except (ValueError, AttributeError):
                continue

        if kwargs.get("author_url"):
            data["author"]["url"] = kwargs.get("author_url")

        #   print(data)
        self.db_client['gb_parse_12_01_2021'][self.name].insert_one(data)

    @staticmethod
    def gen_task(response, link_list, callback, *args, **kwargs):
        for link in link_list:
            yield response.follow(link.attrib["href"], callback=callback, *args, **kwargs)
