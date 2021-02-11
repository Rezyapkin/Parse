from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from hh_parse.spiders.hh_ru import HhRuSpider

if __name__ == "__main__":
    crawler_settings = Settings()
    crawler_settings.setmodule("hh_parse.settings")
    crawler_process = CrawlerProcess(settings=crawler_settings)
    crawler_process.crawl(HhRuSpider)
    crawler_process.start()