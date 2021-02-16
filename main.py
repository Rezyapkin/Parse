import os
from dotenv import load_dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from gb_parse.spiders.instagram import InstagramSpider
from gb_parse.database import Database

if __name__ == "__main__":
    load_dotenv('.env')
    users = [
            "dolgam_net", "svmokka"
        ]
    db = Database(os.getenv("SQL_DB"))

    print("Алгоритм не сложно доработать для поиска рукопожатий для более чем двух вводных пользователей")
    chunk_str = db.find_min_path(users[0], users[1])
    # Не будем запускать паука, если цепочка лежит в базе
    if chunk_str:
        print(chunk_str)
        exit()

    crawler_settings = Settings()
    crawler_settings.setmodule("gb_parse.settings")
    crawler_process = CrawlerProcess(settings=crawler_settings)
    crawler_process.crawl(
        InstagramSpider,
        login=os.getenv('INSTA_USERNAME'),
        password=os.getenv('ENC_PASSWORD'),
        users=users,
        db=db,
        max_depth=3
    )
    crawler_process.start()

    #Вывод результата работы паука
    chunk_str = db.find_min_path(users[0], users[1])
    print("Цепочка рукопожатий не найдена попробуйте увеличить глубину поиска" if chunk_str is None else chunk_str)