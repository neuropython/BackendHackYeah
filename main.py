from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello, World!"}

@app.post("/items/")
def create_item(item: dict):
    # Process the item data
    return {"message": "Item created successfully"}