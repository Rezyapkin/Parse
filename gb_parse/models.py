from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import Column, Integer, String, Boolean, Table, ForeignKey


Base = declarative_base()


followers = Table(
    "followers",
    Base.metadata,
    Column('follower_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('followed_id', Integer, ForeignKey('user.id'), primary_key=True)
)


class FriendShip(Base):
    __tablename__ = 'friendship'
    start_user_id = Column(Integer, ForeignKey('user.id'), primary_key=True, nullable=False)
    end_user_id = Column(Integer, ForeignKey('user.id'), primary_key=True, nullable=False)
    prev_user_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    depth = Column(Integer, nullable=False, default=0)
    start_user = relationship("User", foreign_keys="FriendShip.start_user_id")
    end_user = relationship("User", foreign_keys="FriendShip.end_user_id")


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, autoincrement=False, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    followed = relationship('User',
        secondary = followers,
        primaryjoin = (followers.c.follower_id == id),
        secondaryjoin = (followers.c.followed_id == id),
        lazy = 'dynamic')

    followers = relationship('User',
        secondary = followers,
        primaryjoin = (followers.c.followed_id == id),
        secondaryjoin = (followers.c.follower_id == id),
        lazy = 'dynamic')


    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)
            return self

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)
            return self

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def get_depth_handshake(self, user):
        pass