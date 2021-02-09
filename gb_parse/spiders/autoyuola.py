import scrapy
import json
import re
from urllib.parse import unquote
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
            "phone": resp.css(".advert__call a").attrib["href"].replace("tel:",""),
        },
        "images": lambda resp:
        json.loads(
            html2text(resp.css("div.content.content_full-page script ::text").get()).replace("\n","")
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
        yield from self.gen_task(response, ads_links, self.ads_parse, headers={"User-Agent": self.mobile_agent})

    def ads_parse(self, response):
        data = {}

        for key, selector in self.data_query.items():
            try:
                data[key] = selector(response)
            except (ValueError, AttributeError):
                continue

        self.db_client['gb_parse_12_01_2021'][self.name].insert_one(data)

    @staticmethod
    def get_url_user(response):
        #Истина была рядом, но дожал вопрос с url пользователя. Он разный для салонов и юзера
        j_script = unquote(response.css("#initial-state ::text").get())
        site_user_id = re.findall('"siteUserId":"(\d+)"',j_script)
        if len(site_user_id):
            resp = response.follow(
                f"https://auto.youla.ru/api/profile/youla?userId={site_user_id[0]}",
                headers={"User-Agent": __class__.mobile_agent}
            )

    @staticmethod
    def gen_task(response, link_list, callback, *args, **kwargs):
        for link in link_list:
            yield response.follow(link.attrib["href"], callback=callback,  *args, **kwargs)
