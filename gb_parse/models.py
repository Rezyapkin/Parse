from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime

Base = declarative_base()


class Follows(Base):
    __tablename__ = 'follows'
    initiator_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    folow_id =  Column(Integer, ForeignKey('users.id'), primary_key=True)
    initiator = relationship("Users", foreign_keys=initiator_id)
    folow = relationship("Users", foreign_keys=folow_id)


class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    follows = relationship("Users", secondary=Follows,
                    primaryjoin=Follows.c.initiator_id==id,
                    secondaryjoin=Follows.c.folow_id==id,
                    backref="children")
    followers = relationship("Users", secondary=Follows,
                    primaryjoin=Follows.c.folow_id==id,
                    secondaryjoin=Follows.c.initiator_id==id,
                    backref="children")
