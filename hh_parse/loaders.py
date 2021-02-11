from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose
from .items import HHVacancyItem, HHEmployerItem
from urllib.parse import unquote, urljoin
import re


def get_employer_url(item):
    base_url = "https://hh.ru/"
    return urljoin(base_url, item)


def get_employer_name(item):
    return str.strip("".join(item[0:len(item) // 2]))


def get_areas_list(items):
    return list(map(str.strip, items[0].split(',')))


class HHVacancyLoader(ItemLoader):
    default_item_class = HHVacancyItem
    title_out = TakeFirst()
    url_out = TakeFirst()
    employer_url_in = MapCompose(get_employer_url)
    skills_in = MapCompose(str.lower)
    employer_url_out = TakeFirst()
    description_out = " ".join
    salary_out = "".join


class HHEmployerLoader(ItemLoader):
    default_item_class = HHEmployerItem
    name_in = get_employer_name
    name_out = TakeFirst()
    url_out = TakeFirst()
    areas_activity_in = MapCompose(str.lower)
    areas_activity_out = get_areas_list
    description_in = " ".join
    description_out = TakeFirst()
