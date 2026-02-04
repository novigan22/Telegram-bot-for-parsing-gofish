from sqlalchemy import create_engine, Column, Integer, String, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class UserLink(Base):
    __tablename__ = 'user_links'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    link = Column(String, nullable=False)
    min_price = Column(Integer, nullable=True)
    max_price = Column(Integer, nullable=True)


class TrackedProduct(Base):
    __tablename__ = 'tracked_products'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, nullable=False, unique=True)
    user_id = Column(BigInteger, nullable=False)
    link_id = Column(Integer, nullable=False)


engine = create_engine('sqlite:///gofish_bot.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def add_link_to_db(user_id: int, link: str, min_price: int = None, max_price: int = None):
    session = Session()
    new_link = UserLink(user_id=user_id, link=link, min_price=min_price, max_price=max_price)
    session.add(new_link)
    session.commit()
    session.close()


def get_user_links(user_id: int):
    session = Session()
    links = session.query(UserLink).filter_by(user_id=user_id).all()
    session.close()
    return links


def delete_link_from_db(link_id: int):
    session = Session()
    link = session.query(UserLink).filter_by(id=link_id).first()
    if link:
        session.delete(link)
        session.commit()
    session.close()


def is_product_tracked(product_id: str) -> bool:
    session = Session()
    product = session.query(TrackedProduct).filter_by(product_id=product_id).first()
    session.close()
    return product is not None


def add_tracked_product(product_id: str, user_id: int, link_id: int):
    session = Session()
    try:
        new_product = TrackedProduct(product_id=product_id, user_id=user_id, link_id=link_id)
        session.add(new_product)
        session.commit()
    except:
        session.rollback()
    finally:
        session.close()