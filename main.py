from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient
from pydantic import BaseModel
from enum import Enum
from typing import List
from bson import ObjectId
from fastapi.requests import Request


### Database connection ###

MONGO_URI = "mongodb+srv://fastapi:123fastapi@hackyeah-db.3xvq7.mongodb.net/?retryWrites=true&w=majority&appName=hackyeah-db"

app = FastAPI()

client = MongoClient(MONGO_URI)
db = client["hackyeahdb"]
projects = db["projects"]
counters = db["counters"]
users = db["users"]
histories = db["histories"]

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
    user_name: str
    user_id: str
    gathered_money: int
    funded_money: int 

    class Config:
        arbitrary_types_allowed = True
        

### check if user is admin ###
def is_user_admin(id: str):
    user = users.find_one({"_id": ObjectId(id)})
    if user and user.get("role") == "Admin":
        return True
    return False

def serialize_project(project):
    project["_id"] = str(project["_id"])
    return project

@app.get("/")
def root():
    return {"message": "Hello, World!"}

@app.get("/get_projects", response_model=List[dict])
def get_all_projects():
    projects_list = list(projects.find())  
    projects_list = [serialize_project(project) for project in projects_list]
    return projects_list


@app.get("/get_projects/descending_by/")
def get_all_projects(field: str):
    if field not in ["funded_money", "cost", "gathered_money"]:  # Add any other fields you want to allow sorting by
        raise HTTPException(status_code=400, detail="Invalid field for sorting")
    
    projects_list = list(projects.find().sort(field, -1))
    projects_list = [serialize_project(project) for project in projects_list]
    return projects_list

@app.get("/get_projects/ascending_by/")
def get_all_projects(field: str = Query(...)):
    if field not in ["funded_money", "cost", "gathered_money"]:  # Add any other fields you want to allow sorting by
        raise HTTPException(status_code=400, detail="Invalid field for sorting")
    projects_list = list(projects.find().sort(field, 1))  # Sort by the provided field in descending order
    projects_list = [serialize_project(project) for project in projects_list]
    return projects_list

@app.get("/get_project/{project_id}", response_model=dict)
async def get_project(project_id: str, request: Request):
    body = await request.json()
    user_id = body.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    project = projects.find_one({"_id": ObjectId(project_id)})
    if project:
        add_to_history(user_id, project["category"], histories, 1)
        return serialize_project(project)
    else:
        raise HTTPException(status_code=404, detail="Project not found")
        

@app.get("/get_projects_by_user/{user_id}", response_model=List[dict])
def get_projects_by_user(user_id: str):
    projects_list = list(projects.find({"user_id": user_id}))
    projects_list = [serialize_project(project) for project in projects_list]
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
    
@app.patch("/disable_project/{project_id}", response_model=dict)
def disable_project(project_id: str):
    project = projects.find_one({"_id": ObjectId(project_id)})
    project["is_verified"] = False
    if project:
        projects.update_one({"_id": ObjectId(project_id)}, {"$set": project})
        return {"message": "Project disabled successfully"}


@app.get("/get_favourite_categories/{user_id}", response_model=dict)
def get_favourite_categories(user_id: str):
    return get_favourite_categories(ObjectId(user_id), histories, 3)

def add_to_history(userId, category, histories, addCount):
    history = histories.find_one({"user_id": ObjectId(userId)})
    if history:
        try:
            history[category] = history[category] + addCount
        except:
            history[category] = addCount
        histories.update_one({"user_id": ObjectId(userId)}, {"$set": history})
    else:
        history = {"user_id": ObjectId(userId)}
        history[category] = addCount
        histories.insert_one(history)
    return history
    
def get_favourite_categories(userId, histories, count):
    history = histories.find_one({"user_id": ObjectId(userId)})
    if history:
        history.pop("user_id")
        history.pop("_id")
        return dict(sorted(history.items(), key=lambda item: item[1], reverse=True)[:count])
    else:
        return {}