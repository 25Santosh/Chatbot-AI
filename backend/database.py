from sqlalchemy import create_engine, Column, Integer, String, DECIMAL, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Retrieve the database URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Create Database Engine
engine = create_engine(DATABASE_URL)

# Create a session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define Base class
Base = declarative_base()

# Product Model
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(100), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)      
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))

# Supplier Model
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    contact_info = Column(Text, nullable=False)
    product_categories = Column(Text, nullable=False)

# Create tables in the database
Base.metadata.create_all(bind=engine)
