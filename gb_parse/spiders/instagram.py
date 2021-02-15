import json
import scrapy
from ..items import InstaFollowed, InstaFollower
import json

import scrapy
import os
from ..items import InstaFollowed, InstaFollower
from ..database import Database


class InstagramSpider(scrapy.Spider):
    name = "instagram"
    allowed_domains = ["www.instagram.com"]
    start_urls = ["https://www.instagram.com/"]
    login_url = "https://www.instagram.com/accounts/login/ajax/"
    api_url = "/graphql/query/"
    query_hash = {
        "posts": "56a7068fea504063273cc2120ffd54f3",
        "tag_posts": "9b498c08113f1e09617a1703c22b2f32",
        "followed": "d04b0a864b4b54837c0d870b0e77e076",
        "followers": "c76146de99bb02f6415203be841dd25a",
    }

    type_requests = {
        "followed": "edge_follow",
        "followers": "edge_followed_by",
    }

    def __init__(self, login, password, users, db: Database, max_depth=3, *args, **kwargs):
        self.users = users
        self.login = login
        self.enc_passwd = password
        self.max_depth = max_depth
        self.db = db
        self.db.clear_friendship()
        super().__init__(*args, **kwargs)

    def check_target(self):
        chunk_str = self.db.find_min_path(self.users[0], self.users[1])
        if chunk_str:
            print(chunk_str)
            self.crawler.stop()
            return True

        return False

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
                    yield from self.follow_user(response, user)

    def follow_user(self, response, user_name, handshakes=[]):
        yield response.follow(
            f"/{user_name}/",
            callback=self.user_page_parse,
            cb_kwargs={"handshakes": handshakes}
        )

    def user_page_parse(self, response, handshakes):
        user_data = self.js_data_extract(response)["entry_data"]["ProfilePage"][0]["graphql"]["user"]
        yield from self.parse_friends(response, user_data, handshakes)

    def parse_friends(self, response, user_data, handshakes):
        new_handshakes = self.get_new_handshake(handshakes, user_data)
        yield from self.get_api_request(response, user_data, new_handshakes, "followers")

    def get_new_handshake(self, handshakes, user_data):
        new_handshakes = handshakes.copy()
        new_handshakes.append({
            "id": user_data["id"],
            "name": user_data["username"],
        })
        return new_handshakes

    def get_api_request(self, response, user_data, handshakes, type_request, variables=None):
        if not variables:
            variables = {
                "id": user_data["id"],
                "first": 50,
            }
        url = f'{self.api_url}?query_hash={self.query_hash[type_request]}&variables={json.dumps(variables)}'
        yield response.follow(
            url, callback=self.get_api_follow,
            cb_kwargs={
                "user_data": user_data,
                "type_request": type_request,
                "handshakes": handshakes,
            },
            priority=-5*len(handshakes)
        )


    def get_api_follow(self, response, user_data, handshakes, type_request):
        data = response.json()

        if not (data.get("data") and data["data"].get("user")):
            return

        edges_data = data["data"]["user"][self.type_requests[type_request]]

        yield from self.get_follow_item(
            user_data, edges_data["edges"], type_request
        )
        variables = {
            "id": user_data["id"],
            "first": 50
        }

        if edges_data["page_info"]["has_next_page"]:
            variables["after"] = edges_data["page_info"]["end_cursor"]
            yield from self.get_api_request(response, user_data, handshakes, type_request, variables)
        elif type_request == "followers":
            yield from self.get_api_request(response, user_data, handshakes, "followed", variables)
        else:
            friends = self.db.get_users_next_depth(handshakes)
            if not self.check_target() and len(handshakes) < self.max_depth:
                for friend in friends:
                    yield from self.parse_friends(response, friend, handshakes)

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
        if type_request == "followed":
            return InstaFollowed
        elif type_request == "followers":
            return InstaFollower

    @staticmethod
    def js_data_extract(response):
        script = response.xpath('//script[contains(text(), "window._sharedData =")]/text()').get()
        return json.loads(script.replace("window._sharedData =", "")[:-1])
