import scrapy
import re
from ..loaders import HHVacancyLoader, HHEmployerLoader


class HhRuSpider(scrapy.Spider):
    name = 'hh_ru'
    allowed_domains = ['hh.ru']
    start_urls = ['https://hh.ru/search/vacancy?schedule=remote&L_profession_id=0&area=113']

    xpath_start_url_hh = {
        "pagination": "//div[@data-qa='pager-block']//a[@data-qa='pager-page']/@href",
        "ads": "//div[contains(@class,'vacancy-serp')]//div[contains(@data-qa,'vacancy-serp__vacancy')]//"
               "a[@data-qa='vacancy-serp__vacancy-title']/@href"
    }

    xpath_ads = {
        "title": '//h1[@data-qa="vacancy-title"]/text()',
        "salary": '//p[@class="vacancy-salary"]//text()',
        "description": '//div[@data-qa="vacancy-description"]//text()',
        "skills": '//div[@class="bloko-tag-list"]//span[@data-qa="bloko-tag__text"]/text()',
        "employer_url": "//a[@data-qa='vacancy-company-name']/@href"
    }

    xpath_employer = {
        "name": '//h1/span[contains(@class, "company-header-title-name")]/text()',
        "url": '//a[contains(@data-qa, "company-site")]/@href',
        "areas_activity": '//div[@data-qa="sidebar-header-color"][contains(text(), "Сферы деятельности")]'
                          '/following-sibling::p/text()',
        "description": '//div[contains(@data-qa, "company-description")]//text()',
    }

    xpath_employer_ads_list = {
        "ads_url": "//a[@data-qa='vacancy-serp__vacancy-title']/@href",
        "more": "//span[@class='company-vacancies-group__more-button-wrapper']",
    }

    def parse(self, response):
        for pagination in response.xpath(self.xpath_start_url_hh["pagination"]):
            yield response.follow(pagination, callback=self.parse)

        for ads in response.xpath(self.xpath_start_url_hh["ads"]):
            yield response.follow(ads, callback=self.parse_ads)

    def parse_ads(self, response):
        loader = HHVacancyLoader(response=response)
        loader.add_value("url", response.url)
        for key, value in self.xpath_ads.items():
            loader.add_xpath(key, value)
        yield loader.load_item()

        yield response.follow(response.xpath(self.xpath_ads["employer_url"]).get(), callback=self.parse_employer)

    @staticmethod
    def get_employer_id_from_url(url):
        match = re.search("employer/(\d+)/?", url)
        return match[1] if match else None

    def parse_employer(self, response):
        loader = HHEmployerLoader(response=response)
        for key, value in self.xpath_employer.items():
            loader.add_xpath(key, value)
        yield loader.load_item()

        employer_id = self.get_employer_id_from_url(response.url)
        if employer_id:
            yield from self.follow__employer_ads_list(response, employer_id)

    def parse_employer_ads_list(self, response, *args, **kwargs):
        # Список объявлений
        for ads in response.xpath(self.xpath_employer_ads_list["ads_url"]):
            yield response.follow(ads, callback=self.parse_ads)
        # Кнопка ЕЩЕ
        if response.xpath(self.xpath_employer_ads_list["more"]).get():
            yield from self.follow__employer_ads_list(response, **kwargs)

    def follow__employer_ads_list(self, response, employer_id, page=0):
        yield response.follow(
            f"https://hh.ru/shards/employerview/vacancies"
            f"?page={page}&regionType=CURRENT&currentEmployerId={employer_id}",
            callback=self.parse_employer_ads_list,
            cb_kwargs={
                "employer_id": employer_id,
                "page": page + 1,
            }
        )