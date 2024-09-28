from fastapi import FastAPI
import pymongo
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://fastapi:123fastapi@hackyeah-db.3xvq7.mongodb.net/?retryWrites=true&w=majority&appName=hackyeah-db"


app = FastAPI()

client = MongoClient(MONGO_URI)
db = client["project"]


@app.get("/")
def root():
    return {"message": "Hello, World!"}
