from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, aliased
from .models import Base, User, FriendShip


# Получился антипаттерн "Супер-класс", но из-за болезни отстаю и не успеваю отрефакторить(((
class Database:
    def __init__(self, db_url):
        engine = create_engine(db_url)
        Base.metadata.create_all(bind=engine)
        self.maker = sessionmaker(bind=engine)

    #Не знаю насколько тут уместен такой декоратор. Просто иначе DRY буду нарушать(((
    def db_session(function_to_decorate):
        def wrapper(self, *args, **kwargs):
            session = self.maker()
            value = function_to_decorate(self,  *args, session=session, **kwargs)
            session.commit()
            try:
                pass

            except Exception:
                session.rollback()
            finally:
                session.close()
            return value

        return wrapper

    @db_session
    def clear_model(self, model, session):
        session.query(model).delete()

    def clear_friendship(self):
        self.clear_model(FriendShip)

    def get_friends(self, user, session):
        sub_query = user.followers.subquery()
        friends = user.followed.join(sub_query, User.id == sub_query.c.id)
        return friends

    def get_or_create_realationship(self, session, start_user_id, end_user_id, prev_user_id=None, depth=0):
        return self.get_or_create(
            session,
            FriendShip,
            ["start_user_id", "end_user_id"],
            start_user_id=start_user_id,
            end_user_id=end_user_id,
            prev_user_id=prev_user_id,
            depth=depth
        )

    @db_session
    def create_start_node_in_friendship(self, data, session=None):
        user = self.get_or_create(session, User, id=data["id"], name=data["name"])
        session.add(user)
        friendship = self.get_or_create_realationship(session, user.id, user.id)
        session.add(friendship)

    @db_session
    def get_users_next_depth(self, handshakes=[], session=None):
        # Найдем последнего пользователя в текущей ветке рукопожатий
        prev_user_id = handshakes[-1]["id"]
        user_last = session.query(User).filter(User.id == handshakes[-1]["id"]).first()
        friends_last = self.get_friends(user_last, session)
        user_first = session.query(User).filter(User.id == handshakes[0]["id"]).first()
        depth = len(handshakes)
        list_next_user = []

        for friend in friends_last:
            relation = self.get_or_create_realationship(session, user_first.id, friend.id, prev_user_id, depth)
            if relation.depth == depth:
                session.add(relation)
                list_next_user.append({"id": friend.id, "username": friend.name})

        return list_next_user

    def get_chain_friends(self, session, relation):
        chain = []
        query = session.query(FriendShip).filter(FriendShip.start_user_id == relation.start_user_id)
        prev_user_id = relation.prev_user_id
        while prev_user_id:
            f_sh = query.filter(FriendShip.end_user_id == prev_user_id).first()
            chain.append(f_sh.end_user.name)
            prev_user_id = None if not f_sh else f_sh.prev_user_id
        return chain

    @db_session
    def find_min_path(self, user1_name, user2_name, session=None):
        user1 = session.query(User).filter(User.name == user1_name).first()
        user2 = session.query(User).filter(User.name == user2_name).first()

        if user1 is None or user2 is None:
            return None

        relation1 = aliased(FriendShip)
        relation2 = aliased(FriendShip)
        q_join = session.query(relation1, relation2).join(relation2, relation1.end_user_id == relation2.end_user_id)
        q_filter = q_join.filter(and_(relation1.start_user_id == user1.id, relation2.start_user_id == user2.id))
        result = q_filter.order_by(relation1.depth + relation2.depth).first()

        return " <-> ".join(
            self.get_chain_friends(session, result[0]) + [result[0].end_user.name] + \
            self.get_chain_friends(session, result[1])
        ) if result else None


    def get_or_create(self, session, model, check_fields=["id"], **data):
        db_query = session.query(model)
        for field in check_fields:
            db_query = db_query.filter(getattr(model, field) == data[field])
        db_data = db_query.first()
        if not db_data:
            db_data = model(**data)
        return db_data

    def create_user(self, session, **data):
        comment = self.get_or_create(session, User, **data)
        session.add(comment)

    @db_session
    def create_follow_link(self, data, session):
        follower = self.get_or_create(session, User, id=data["follower_id"], name=data["follower_name"])
        followed = self.get_or_create(session, User, id=data["followed_id"], name=data["followed_name"])
        session.add(follower)
        follower.follow(followed)
        session.add(follower)
        session.add(followed)
