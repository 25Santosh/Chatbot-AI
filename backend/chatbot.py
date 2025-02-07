from langgraph.graph import Graph
from sqlalchemy.orm import Session
from transformers import pipeline
from fastapi import FastAPI, Depends
from database import SessionLocal, Product, Supplier
import logging
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Open-Source LLM for Summarization
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Load NLP Model for Entity Extraction
ner_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize LangGraph
chatbot_graph = Graph()

# ---- Nodes ----

def start_node(inputs):
    logger.info("Starting chatbot execution.")
    return inputs

def extract_entities(inputs):
    query = inputs.get("query")
    if not query:
        return inputs
    
    ner_results = ner_pipeline(query)
    extracted_data = {"supplier_name": None, "brand": None, "product_name": None}

    for entity in ner_results:
        entity_text = entity['word']
        entity_type = entity['entity']
        
        if entity_type == "B-ORG":  # Organization (Supplier or Brand)
            extracted_data["supplier_name"] = entity_text
        elif entity_type == "B-MISC":  # Miscellaneous (Brand names)
            extracted_data["brand"] = entity_text
        elif entity_type == "B-PRODUCT":
            extracted_data["product_name"] = entity_text
    
    inputs.update(extracted_data)
    return inputs

def fetch_supplier(inputs):
    supplier_id = inputs.get("supplier_id")
    db = inputs["db"]

    if not supplier_id:
        return {"error": "Supplier ID is required"}

    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        return {"error": "Supplier not found"}

    supplier_data = {col.name: getattr(supplier, col.name) for col in Supplier.__table__.columns}
    return {"supplier_data": supplier_data}

def summarize_supplier_info(inputs):
    if "supplier_data" not in inputs:
        return {"error": "Missing supplier data"}
    
    supplier_info = inputs["supplier_data"]
    summary_text = f"Supplier {supplier_info['name']} specializes in {supplier_info.get('product_categories', 'various products')}. Contact: {supplier_info.get('contact_info', 'N/A')}."
    summary = summarizer(summary_text, max_length=50, min_length=20, do_sample=False)
    return {"supplier_summary": summary[0]['summary_text']}

def fetch_products(inputs):
    brand = inputs.get("brand")
    db = inputs["db"]

    logger.info(f"Fetching products for brand: {brand}")

    if not brand:
        return {"error": "Brand name is required"}

    products = db.query(Product).filter(Product.brand.ilike(f"%{brand}%")).all()

    if not products:
        logger.error(f"No products found for brand {brand}")
        return {"error": f"No products found for brand {brand}"}

    product_data = [{col.name: getattr(p, col.name) for col in Product.__table__.columns} for p in products]

    logger.info(f"Fetched products: {product_data}")
    return {"products": product_data}


def fetch_product_details(inputs):
    product_name = inputs.get("product_name")
    db = inputs["db"]
    
    if not product_name:
        return {"error": "Product name is required"}
    
    product = db.query(Product).filter(Product.name.ilike(f"%{product_name}%")).first()
    if not product:
        return {"error": f"Product {product_name} not found"}
    
    return {"product_details": {col.name: getattr(product, col.name) for col in Product.__table__.columns}}

def summarize_product_info(inputs):
    if "product_details" not in inputs:
        return {"error": "Missing product data"}
    
    product_info = inputs["product_details"]
    summary_text = f"Product {product_info['name']} is a {product_info.get('category', 'general item')} from {product_info.get('brand', 'an unknown brand')}. It is priced at {product_info.get('price', 'N/A')}."
    summary = summarizer(summary_text, max_length=50, min_length=20, do_sample=False)
    return {"summary": summary[0]['summary_text']}

# ---- Add Nodes ----
chatbot_graph.add_node("start", start_node)
chatbot_graph.add_node("extract_entities", extract_entities)
chatbot_graph.add_node("fetch_supplier", fetch_supplier)
chatbot_graph.add_node("summarize_supplier_info", summarize_supplier_info)
chatbot_graph.add_node("fetch_products", fetch_products)
chatbot_graph.add_node("fetch_product_details", fetch_product_details)
chatbot_graph.add_node("summarize_product_info", summarize_product_info)

# ---- Routing ----
def decide_route(inputs):
    logger.info(f"Deciding route based on inputs: {inputs}")

    supplier_id = inputs.get("supplier_id")
    brand = inputs.get("brand")
    product_name = inputs.get("product_name")

    if supplier_id:
        logger.info("Routing to fetch_supplier")
        return "fetch_supplier"
    elif brand and brand.strip():
        logger.info("Routing to fetch_products")
        return "fetch_products"
    elif product_name and product_name.strip():
        logger.info("Routing to fetch_product_details")
        return "fetch_product_details"

    logger.warning("No valid input detected for routing.")
    return None


chatbot_graph.add_edge("start", "extract_entities")
chatbot_graph.add_conditional_edges("extract_entities", decide_route, {
    "fetch_supplier": "fetch_supplier",
    "fetch_products": "fetch_products",
    "fetch_product_details": "fetch_product_details"
})
chatbot_graph.add_edge("fetch_supplier", "summarize_supplier_info")
chatbot_graph.add_edge("fetch_product_details", "summarize_product_info")

chatbot_graph.set_entry_point("start")
chatbot_graph.set_finish_point("summarize_supplier_info")
chatbot_executor = chatbot_graph.compile()

# ---- FastAPI Routes ----
@app.get("/chatbot/")
def chatbot(query: str = None, supplier_id: int = None, brand: str = None, db: Session = Depends(get_db)):
    inputs = {"db": db}

    if query:
        inputs["query"] = query
    if supplier_id:
        inputs["supplier_id"] = supplier_id
    if brand:
        inputs["brand"] = brand

    response = chatbot_executor.invoke(inputs)

    logger.info(f"Chatbot response: {response}")

    # Ensure correct response format
    if "products" in response:
        return {"products": response["products"]}
    
    if "supplier_summary" in response:
        return {"supplier_summary": response["supplier_summary"]}
    
    if "error" in response:
        return response  # Return error messages
    
    return {"error": "Unexpected response format"}


@app.get("/test-db/")
def test_db_connection(db: Session = Depends(get_db)):
    return {"suppliers": db.query(Supplier).all()}
