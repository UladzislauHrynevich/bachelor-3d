import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError("DB URL is not set")

engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    print("DB connect")

SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase)
    pass