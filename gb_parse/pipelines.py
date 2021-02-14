# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy import Request
from scrapy.pipelines.images import ImagesPipeline
import pymongo

from gb_parse.items import InstaPost


class GbParsePipeline:
    def process_item(self, item, spider):
        return item


class SaveToMongo:
    def __init__(self):
        client = pymongo.MongoClient()
        self.db = client["gb_parse_12_01_2021"]

    def process_item(self, item, spider):
        self.db[spider.name].insert_one(item)
        return item


class GbImagePipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        if isinstance(item, InstaPost):
            pass
        to_download = []
        to_download.extend(item.get("images", []))
        if item["data"].get("display_url"):
            to_download.append(item["data"]["display_url"])
        for img_url in to_download:
            yield Request(img_url)

    def item_completed(self, results, item, info):
        if "images" in item:
            item["images"] = [itm[1] for itm in results]
        return item
