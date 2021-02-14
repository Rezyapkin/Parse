import datetime as dt
import json
import scrapy
from ..items import InstaTag, InstaPost, InstaUser, InstaFollow, InstaFollower

# Урок 6 я делал сам. Сделал по другому получение query_hash из js-файла. Скачал стартовый git 7ого урока. А тут все
# решено. С Вашего позволения возьму за основу Ваш код и приступлю к курсовой.
# На windows в USERNAME прилетает имя пользователя Windows. Поэтому у меня переменная среды окружения INSTA_USERNAME

class InstagramSpider(scrapy.Spider):
    name = "instagram"
    allowed_domains = ["www.instagram.com"]
    start_urls = ["https://www.instagram.com/"]
    login_url = "https://www.instagram.com/accounts/login/ajax/"
    api_url = "/graphql/query/"
    query_hash = {
        "posts": "56a7068fea504063273cc2120ffd54f3",
        "tag_posts": "9b498c08113f1e09617a1703c22b2f32",
        "follow": "d04b0a864b4b54837c0d870b0e77e076",
        "followers": "c76146de99bb02f6415203be841dd25a",
    }

    type_requests = {
        "follow": "edge_follow",
        "followers": "edge_followed_by",
    }

    def __init__(self, login, password, users, *args, **kwargs):
        self.users = users
        self.login = login
        self.enc_passwd = password
        super().__init__(*args, **kwargs)

    def parse(self, response, **kwargs):
        try:
            js_data = self.js_data_extract(response)
            yield scrapy.FormRequest(
                self.login_url,
                method="POST",
                callback=self.parse,
                formdata={
                    "username": self.login,
                    "enc_password": self.enc_passwd,
                },
                headers={"X-CSRFToken": js_data["config"]["csrf_token"]},
            )
        except AttributeError as e:
            if response.json().get("authenticated"):
                for user in self.users:
                    yield response.follow(f"/{user}/", callback=self.user_page_parse)

    def user_page_parse(self, response):
        user_data = self.js_data_extract(response)["entry_data"]["ProfilePage"][0]["graphql"]["user"]
        yield from self.get_api_follow_request(response, user_data)
        yield from self.get_api_followers_request(response, user_data)

    def get_api_request(self, response, user_data, variables=None, type_request="follow"):
        if not variables:
            variables = {
                "id": user_data["id"],
                "first": 100,
            }
        url = f'{self.api_url}?query_hash={self.query_hash[type_request]}&variables={json.dumps(variables)}'
        yield response.follow(
            url, callback=self.get_api_follow, cb_kwargs={"user_data": user_data, "type_request": type_request}
        )

    def get_api_follow_request(self, response, user_data, variables=None):
        yield from self.get_api_request(response, user_data, variables, type_request="follow")

    def get_api_followers_request(self, response, user_data, variables=None):
        yield from self.get_api_request(response, user_data, variables, type_request="followers")

    def get_api_follow(self, response, user_data, type_request):
        data = response.json()

        if not (data.get("data") and data["data"].get("user")):
            return

        edges_data = data["data"]["user"][self.type_requests[type_request]]

        yield from self.get_follow_item(
            user_data, edges_data["edges"], type_request
        )

        if edges_data["page_info"]["has_next_page"]:
            variables = {
                "id": user_data["id"],
                "first": 100,
                "after": edges_data["page_info"]["end_cursor"],
            }
            yield from self.get_api_request(response, user_data, variables, type_request)

    def get_follow_item(self, user_data, users_data, type_request):
        for user in users_data:
            yield self.get_item_class(type_request)(
                user_id=user_data["id"],
                user_name=user_data["username"],
                follow_id=user["node"]["id"],
                follow_name=user["node"]["username"],
            )

    @staticmethod
    def get_item_class(type_request):
        if type_request == "follow":
            return InstaFollow
        elif type_request == "followers":
            return InstaFollower

    @staticmethod
    def js_data_extract(response):
        script = response.xpath('//script[contains(text(), "window._sharedData =")]/text()').get()
        return json.loads(script.replace("window._sharedData =", "")[:-1])
