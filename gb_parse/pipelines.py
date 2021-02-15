# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy import Request
from scrapy.pipelines.images import ImagesPipeline
import pymongo
import os

from gb_parse.items import InstaPost, InstaFollower, InstaFollowed


class GbParsePipeline:
    def process_item(self, item, spider):
        return item

class SaveToDb:
    def __init__(self):
        pass

    def process_item(self, item, spider):

        if isinstance(item, (InstaFollowed, InstaFollower)):

            data = {
                "follower_id": item["user_id"] if type(item) == InstaFollowed else item["follow_id"],
                "follower_name": item["user_name"] if type(item) == InstaFollowed else item["follow_name"],
                "followed_id": item["follow_id"] if type(item) ==  InstaFollowed else item["user_id"],
                "followed_name": item["follow_name"] if type(item) == InstaFollowed else item["user_name"],
            }

            spider.db.create_follow_link(data)

        return item


class GbImagePipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        if isinstance(item, InstaPost):
            pass
        to_download = []
        to_download.extend(item.get("images", []))
        if item.get("data") and item["data"].get("display_url"):
            to_download.append(item["data"]["display_url"])
        for img_url in to_download:
            yield Request(img_url)

    def item_completed(self, results, item, info):
        if "images" in item:
            item["images"] = [itm[1] for itm in results]
        return item
