from fastapi import FastAPI, HTTPException
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
counters = db["counters"]
user = db["users"]
### Autoincremental Field ###
def get_next_id():
    counter = counters.find_one_and_update(
        {"_id": "projectid"},
        {"$inc": {"sequence_value": 1}},
        return_document=True,
        upsert=True
    )
    return counter["sequence_value"]

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
    date_added: str
    date_ended: str
    cost: int
    gathered_money: int
    funded_money: int 

@app.get("/")
def root():
    return {"message": "Hello, World!"}

@app.get("/get_projects", response_model=List[dict])
def get_all_projects():
    projects_list = list(projects.find({}, {"_id": 0}))  # Exclude the MongoDB _id field
    return projects_list

@app.get("/get_projects/descending_by/")
def get_all_projects(field: str):
    if field not in ["funded_money", "cost", "gathered_money"]:  # Add any other fields you want to allow sorting by
        raise HTTPException(status_code=400, detail="Invalid field for sorting")
    
    projects_list = list(projects.find({}, {"_id": 0}).sort(field, -1))  # Sort by the provided field in descending order
    return projects_list

@app.get("/get_projects/ascending_by/")
def get_all_projects(field: str):
    if field not in ["funded_money", "cost", "gathered_money"]:  # Add any other fields you want to allow sorting by
        raise HTTPException(status_code=400, detail="Invalid field for sorting")
    
    projects_list = list(projects.find({}, {"_id": 0}).sort(field, 1))  # Sort by the provided field in descending order
    return projects_list

@app.post("/add_project", response_model=dict)
def add_project(project: Projet):
    project_dict = project.dict()
    project_dict["ID"] = get_next_id()
    result = projects.insert_one(project_dict)
    if result.inserted_id:
        return {"message": "Project added successfully", "id": str(result.inserted_id)}
    else:
        raise HTTPException(status_code=500, detail="Failed to add project")




    