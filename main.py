from fastapi import FastAPI
import pymongo
from pymongo import MongoClient
from pydantic import BaseModel
from enum import Enum
from typing import List


### Database connection ###
MONGO_URI = "mongodb+srv://fastapi:123fastapi@hackyeah-db.3xvq7.mongodb.net/?retryWrites=true&w=majority&appName=hackyeah-db"

app = FastAPI()

client = MongoClient(MONGO_URI)
db = client["hackyeahdb"]
projects = db["projects"]

### Enums ###
class NeighborhoodProjectCategory(str, Enum):
    INFRASTRUCTURE = "Infrastructure Improvements"
    GREEN_SPACES = "Green Spaces and Parks"
    COMMUNITY_EVENTS = "Community Events"
    SPORTS = "Sports and Recreation"
    SAFETY = "Safety and Security"
    EDUCATION = "Education and Workshops"
    CULTURE = "Art and Culture"
    SUSTAINABILITY = "Sustainability and Eco Projects" 

class SatusOfProject(str, Enum):
    COMPLEATED = "project compleated"
    IN_PROGRRES = "project in progres"
    

### Models ###
class Projet(BaseModel):
    title: str 
    photo: str
    category: NeighborhoodProjectCategory
    abstract: str 
    detailed_desc: str 
    location: str 
    coordinates: str 
    is_verified: bool
    status_of_project: SatusOfProject
    dateAdded: str
    dateEnded: str
    Cost: int
    GatheredMoney: int
    FundedMoney: int 

@app.get("/")
def root():
    return {"message": "Hello, World!"}

@app.get("/projects", response_model=List[dict])
def get_all_projects():
    return projects

    