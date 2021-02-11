import json
import scrapy
import re
from datetime import datetime
from ..items import InstaTag, InstaPost
from urllib.parse import unquote

class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    login_url = "https://www.instagram.com/accounts/login/ajax/"
    graphql_path = "/graphql/query/"
    tag_path = "/explore/tags/"
    allowed_domains = ['www.instagram.com']
    start_urls = ['https://www.instagram.com/']
    query_hash = {}
    
    def __init__(self, login, password, tags:list, *args, **kwargs):
        self.__login = login
        self.__password = password
        self.tags = tags
        super().__init__(*args, **kwargs)

    def parse(self, response):
        try:
            js_data = self.js_data_extract(response)
            yield scrapy.FormRequest(
                self.login_url,
                method='POST',
                callback=self.parse,
                formdata={
                    'username': self.__login,
                    'enc_password': self.__password,
                },
                headers={'X-CSRFToken': js_data['config']['csrf_token']}
            )
        except AttributeError:
            if response.json().get('authenticated'):
                for tag in self.tags:
                    tag_url = f'{self.tag_path}{tag}'
                    yield response.follow(tag_url, callback=self.tag_parse)

    def get_tag_data(self, response):
        try:
            js_data = self.js_data_extract(response)
            return js_data['entry_data']['TagPage'][0]['graphql']['hashtag']
        except (KeyError, AttributeError):
            return {}

    def tag_parse(self, response):
        #Получим адрес JS
        js_url = response.xpath("//link[contains(@href,'/static/bundles/es6/TagPageContainer.js')]/@href").get()
        data = self.get_tag_data(response)

        #Нет такого хэша
        if not self.query_hash.get(js_url):
            yield response.follow(
                js_url,
                callback=self.js_parse,
                cb_kwargs={"tag_name": data.get('name')},
                dont_filter=True
            )
        else:
            yield response.follow(self.get_api_url(data.get('name'), js_url), callback=self.tag_api_parse)

        #Отдачу данных у Вас списал, остальное сам
        yield InstaTag(
            date_parse = datetime.utcnow(),
            data = {
                "id": data["id"],
                "name": data["name"],
                "profile_pic_url": data["profile_pic_url"],
            },
        )

    #JS-скрипт из которого возьмем заветный hash-query
    def js_parse(self, response, *args, **kwargs):
        match = re.search('queryId\s*:\s*"(.*?)",', str(response.body))
        if match:
            self.query_hash[response.url] = match[1]
            yield response.follow(self.get_api_url(kwargs['tag_name'], response.url), callback=self.tag_api_parse)

    def get_api_url(self, tag, js_url):
        base_url = f"{self.graphql_path}?query_hash={self.query_hash.get(js_url)}"
        par_variables = f"variables={self.get_query_variables(tag)}"
        return f"{base_url}&{par_variables}"

    def tag_api_parse(self, response):
        js_data = response.json()
        data = js_data["data"]["hashtag"]

        if data["edge_hashtag_to_media"]["page_info"]["has_next_page"]:
            variables = self.get_query_variables(data['name'],data["edge_hashtag_to_media"]["page_info"]["end_cursor"])
            url = re.sub("variables={.*}",f"variables={variables}",unquote(response.url))
            yield response.follow(
                url,
                callback=self.tag_api_parse,
            )

        yield from self.get_post_item(data["edge_hashtag_to_media"]["edges"])

    @staticmethod
    def get_query_variables(tag_name, after=""):
        return json.dumps({
            "tag_name": tag_name,
            "first": 50,
            "after": after
        })

    @staticmethod
    def js_data_extract(response) -> dict:
        script = response.xpath("/html/body/script[contains(text(), 'window._sharedData = ')]/text()").get()
        return json.loads(script.replace('window._sharedData = ', '')[:-1])

    @staticmethod
    def get_post_item(edges):
        for node in edges:
            yield InstaPost(date_parse = datetime.utcnow(), data = node["node"])