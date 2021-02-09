import os
import requests
import bs4
from urllib.parse import urljoin
from dotenv import load_dotenv

from database import Database

# todo обойти пагинацию блога
# todo обойти каждую статью
# todo Извлечь данные: Url, Заголовок, имя автора, url автора, список тегов (url, имя)


# В исходной версии есть нарушение принципа DRY в коде, который ставит задачи

class Task:

    def __init__(self):
        self.tasks = []
        self.done_urls = set()

    def add(self, url, parse_func):
        if url not in self.done_urls:
            self.tasks.append(parse_func)
            self.done_urls.add(url)


class GbParse:

    def __init__(self, start_url, database):
        self.start_url = start_url
        self.done_urls = set()
        self.task = Task()
        self.task.add(self.start_url, self.parse_task(self.start_url, self.pag_parse))
        self.database = database

    def _get_soup(self, *args, **kwargs):
        response = requests.get(*args, **kwargs)
        soup = bs4.BeautifulSoup(response.text, "lxml")
        return soup

    def parse_task(self, url, callback):
        def wrap():
            soup = self._get_soup(url)
            return callback(url, soup)

        return wrap

    def run(self):
        for task in self.task.tasks:
            result = task()
            if result:
                print(result)
                # self.database.create_post(result)

    def post_parse(self, url, soup: bs4.BeautifulSoup) -> dict:
        author_name_tag = soup.find("div", attrs={"itemprop": "author"})
        data = {
            "post_data": {
                "url": url,
                "title": soup.find("h1", attrs={"class": "blogpost-title"}).text,
            },
            "author": {
                "url": urljoin(url, author_name_tag.parent.get("href")),
                "name": author_name_tag.text,
            },
            "tags": [
                {
                    "name": tag.text,
                    "url": urljoin(url, tag.get("href")),
                }
                for tag in soup.find_all("a", attrs={"class": "small"})
            ],
        }
        return data

    def pag_parse(self, url, soup: bs4.BeautifulSoup):
        gb_pagination = soup.find("ul", attrs={"class": "gb__pagination"})
        a_tags = gb_pagination.find_all("a")

        for a in a_tags:
            pag_url = urljoin(url, a.get("href"))
            self.task.add(pag_url, self.parse_task(pag_url, self.pag_parse))

        posts_urls = soup.find_all("a", attrs={"class": "post-item__title"})
        for post_url in posts_urls:
            post_href = urljoin(url, post_url.get("href"))
            self.task.add(post_href, self.parse_task(post_href, self.post_parse))


if __name__ == "__main__":
    load_dotenv(".env")
    parser = GbParse("https://geekbrains.ru/posts", Database(os.getenv("SQL_DB")))
    parser.run()
