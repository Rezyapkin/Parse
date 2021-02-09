from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models


class Database:
    def __init__(self, db_url):
        engine = create_engine(db_url)
        models.Base.metadata.create_all(bind=engine)
        self.maker = sessionmaker(bind=engine)

    def get_or_create(self, session, model, unique_field="url", **data):
        db_data = session.query(model).filter(getattr(model, unique_field) == data[unique_field]).first()

        if not db_data:
            db_data = model(**data)
        return db_data

    def create_post(self, data):
        session = self.maker()
        tags = map(
            lambda tag_data: self.get_or_create(session, models.Tag, **tag_data), data["tags"]
        )
        writer = self.get_or_create(session, models.Writer, **data["writer"])
        post = self.get_or_create(session, models.Post, **data["post_data"], writer=writer)

        for comment in data["comments"]:
            self.get_or_create(session, models.Comment, unique_field="external_id", **comment, post=post)

        post.tags.extend(tags)

        session.add(post)

        try:
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()
