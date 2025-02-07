from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, Product, Supplier



app = FastAPI()



# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Get all products
@app.get("/products/")
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

# Get all suppliers
@app.get("/suppliers/")
def get_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).all()

# Get a product by ID
@app.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.id == product_id).first()
