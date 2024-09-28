from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient
from pydantic import BaseModel
from enum import Enum
from typing import List
from bson import ObjectId


### Database connection ###

MONGO_URI = "mongodb+srv://fastapi:123fastapi@hackyeah-db.3xvq7.mongodb.net/?retryWrites=true&w=majority&appName=hackyeah-db"

app = FastAPI()

client = MongoClient(MONGO_URI)
db = client["hackyeahdb"]
projects = db["projects"]
counters = db["counters"]
users = db["users"]
wallets = db["wallets"]

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
    """
        Retrieve all projects from the database.

        This endpoint retrieves all projects from the MongoDB collection and returns them as a list of dictionaries.
        Each project dictionary includes the project's details, with the MongoDB ObjectId converted to a string.

        Returns:
            List[dict]: A list of dictionaries, each representing a project.
        Example:
        [
        {
            "_id": "66f86091c7006b2b170c9db2",
            "title": "Neighborhood Playground Renovation",
            "photo": "https://example.com/images/playground_renovation.jpg",
            "category": "Sports and Recreation",
            "abstract": "Renovating the old playground with new equipment and safety features.",
            "detailed_desc": "The current playground is outdated and in need of new equipment. This project involves replacing old slides, swings, and adding new safety features such as soft ground mats to ensure children can play safely. We also plan to add a small section for younger children and a shaded seating area for parents.",
            "location": "Elm Street Park, Neighborhood B",
            "coordinates": "51.5074, -0.1278",
            "is_verified": false,
            "status_of_project": "project in progres",
            "date_added": "2024-07-01",
            "date_ended": "2024-12-01",
            "cost": 15000,
            "user_name": "test_username",
            "user_id": "66f83be392c360b2cbedb66a",
            "gathered_money": 8500,
            "funded_money": 12000,
            "ID": 9
        }
    ]
    """
    projects_list = list(projects.find())  
    projects_list = [serialize_project(project) for project in projects_list]
    return projects_list

@app.get("/get_projects/{by_field}")
def get_all_projects(by_field: str, field: str):
    """
    Retrieve all projects from the database, sorted by the specified field in either ascending or descending order.

    This endpoint retrieves all projects from the MongoDB collection and returns them as a list of dictionaries,
    sorted by the specified field in either ascending or descending order. The field must be one of the allowed fields for sorting.

    Args:
        by_field (str): The order by which to sort the projects. Must be either "ascending_by" or "descending_by".
        field (str): The field by which to sort the projects. Must be one of ["funded_money", "cost", "gathered_money"].

    Returns:
        List[dict]: A list of dictionaries, each representing a project, sorted by the specified field in the specified order.

    Raises:
        HTTPException: If the specified field is not one of the allowed fields for sorting, a 400 status code is returned.
        HTTPException: If the specified order is not "ascending_by" or "descending_by", a 400 status code is returned.

    Example:
        Request:
            GET /get_projects/descending_by/?field=funded_money

        Response:
            [
                {
                    "_id": "60d5f9b8f8d2f8b0c8b0c8b0",
                    "name": "Project 1",
                    "description": "Description of Project 1",
                    "user_id": "60d5f9b8f8d2f8b0c8b0c8b1",
                    "funded_money": 1000
                },
                {
                    "_id": "60d5f9b8f8d2f8b0c8b0c8b2",
                    "name": "Project 2",
                    "description": "Description of Project 2",
                    "user_id": "60d5f9b8f8d2f8b0c8b0c8b3",
                    "funded_money": 500
                }
            ]
    """
    if field not in ["funded_money", "cost", "gathered_money"]:
        raise HTTPException(status_code=400, detail="Invalid field for sorting")
    
    if by_field == "descending_by":
        sign = -1
    elif by_field == "ascending_by":
        sign = 1
    else:
        raise HTTPException(status_code=400, detail="Invalid order for sorting")
    
    projects_list = list(projects.find().sort(field, sign))
    projects_list = [serialize_project(project) for project in projects_list]
    return projects_list

@app.get("/get_project/{project_id}", response_model=dict)
def get_project(project_id: str):

    project = projects.find_one({"_id": ObjectId(project_id)})
    if project:
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
    
@app.patch("/pay_to_project/", response_model=dict)
def enable_project(project_id: str = Query(...), payment_amount: int = Query(...)):
    project = projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project["gathered_money"] += payment_amount 
    wallet = wallets.find_one({"user_id": ObjectId(project_id)})
    print(wallet)
    if not wallet:
        raise HTTPException(status_code=404, detail="User wallet not found")
    wallet["money_balance"] -= payment_amount
    if wallet["money_balance"] < 0:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    if project["gathered_money"] >= project["cost"]:
        project["status_of_project"] = "project compleated"
    projects.update_one({"_id": ObjectId(project_id)}, {"$set": project})
    wallets.update_one({"user_id": project["user_id"]}, {"$set": wallet})
    return {"message": "Payment successful"}