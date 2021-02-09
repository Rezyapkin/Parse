from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime

Base = declarative_base()

"""
one to one
one to many - many to one
many to many 
"""

tag_post = Table(
    "tag_post",
    Base.metadata,
    Column('post_id', Integer, ForeignKey('post.id')),
    Column('tag_id', Integer, ForeignKey('tag.id'))
)


class Post(Base):
    __tablename__ = 'post'
    id = Column(Integer, autoincrement=True, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String, unique=False, nullable=False)
    image_url = Column(String, unique=False, nullable=True)
    date = Column(DateTime, unique=False, nullable=False)
    writer_id = Column(Integer, ForeignKey('writer.id'))
    writer = relationship("Writer")
    comments = relationship("Comment")
    tags = relationship('Tag', secondary=tag_post)


class Comment(Base):
    __tablename__ = 'comment'
    id = Column(Integer, autoincrement=True, primary_key=True)
    external_id = Column(Integer, unique=True, nullable=False)
    author = Column(String, unique=False, nullable=False)
    text = Column(String, unique=True, nullable=False)
    post_id = Column(Integer, ForeignKey('post.id'))
    post = relationship("Post")


class Writer(Base):
    __tablename__ = 'writer'
    id = Column(Integer, autoincrement=True, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    name = Column(String, unique=False)
    posts = relationship("Post")


class Tag(Base):
    __tablename__ = 'tag'
    id = Column(Integer, autoincrement=True, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    name = Column(String, unique=True, nullable=False)
    posts = relationship("Post", secondary=tag_post)
