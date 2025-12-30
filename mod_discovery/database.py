import os
from sqlalchemy import create_engine, Column, Integer, String, engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Mod(Base):
    __tablename__ = 'mods'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    source = Column(String, default='modrinth')
    wiki_url = Column(String, nullable=True)
    external_url = Column(String, nullable=True)
    description = Column(String, nullable=True)
    downloads = Column(Integer, default=0)

    def __repr__(self):
        return f"<Mod(name='{self.name}', slug='{self.slug}')>"

# Database Setup
DB_NAME = "mods.db"
# Use absolute path relative to this file's directory if possible, or just local
# For this environment, we'll store it in the same directory as this file.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, DB_NAME)

engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    print(f"📦 Initializing database at {DB_PATH}...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
