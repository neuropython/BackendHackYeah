from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient
from pydantic import BaseModel
from enum import Enum
from typing import List
from bson import ObjectId
from fastapi.requests import Request
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware


### Database connection ###

load_dotenv()

PASSWORD = os.getenv("password")
USERNAME = os.getenv("user") 
print(PASSWORD)
print(USERNAME)
MONGO_URI = f"mongodb+srv://{USERNAME}:{PASSWORD}@hackyeah-db.3xvq7.mongodb.net/?retryWrites=true&w=majority&appName=hackyeah-db"

print(MONGO_URI)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = MongoClient(MONGO_URI)
db = client["hackyeahdb"]
projects = db["projects1"]
counters = db["counters"]
users = db["users"]
wallets = db["wallets"]
tranzactions = db["tranzactions"]
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
    INFRASTRUCTURE = "Infrastructure"
    GREEN_SPACES = "Environment"
    COMMUNITY_EVENTS = "Events"
    SPORTS = "Sports"
    SAFETY = "Safety"
    EDUCATION = "Education"
    CULTURE = "Culture"
    SUSTAINABILITY = "Sustainability" 

class SatusOfProject(str, Enum):
    COMPLEATED = "Completed"
    IN_PROGRRES = "Pending"

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
        arbitrary_types_allowed=True
        

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

@app.get("/get_projects/{limit}", response_model=List[dict])
def get_all_projects(limit: int):
    projects_list = list(projects.find().limit(limit))  
    projects_list = [serialize_project(project) for project in projects_list]
    return projects_list

@app.get("/get_projects/{by_field}")
def get_all_projects(by_field: str, field: str):
    if field not in ["funded_money", "cost", "gathered_money"]:
        raise HTTPException(status_code=400, detail="Invalid field for sorting")
    
    if by_field == "descending_by":
        sign = -1
    elif by_field == "ascending_by":
        sign = 1
    else:
        raise HTTPException(status_code=400, detail="Invalid order for sorting")
    
    query = projects.find().sort(field, 1)

    projects_list = list(projects.find().sort(field, sign))
    projects_list = [serialize_project(project) for project in projects_list]
    return projects_list

@app.get("/get_project/{project_id}", response_model=dict)
def get_project(project_id: str, user_id: str):
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

@app.get("/get_projects_by_category/{category}", response_model=List[dict])
def get_projects_by_category(category: NeighborhoodProjectCategory):
    projects_list = list(projects.find({"category": category}))
    projects_list = [serialize_project(project) for project in projects_list]
    return projects_list

@app.post("/add_project/", response_model=dict)
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
def enable_project(project_id: str = Query(...), payment_amount: int = Query(...), user_id: str = Query(...)):
    project = projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project["gathered_money"] += payment_amount 
    result = wallets.update_one({"user_id": ObjectId(str(user_id))}, {"$inc": {"money_balance": -(payment_amount)}})
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update wallet")
    projects.update_one({"_id": ObjectId(project_id)}, {"$set": project})
    return {"message": "Payment successful"}

@app.patch("/fund_project/", response_model=dict)
def fund_project(project_id: str = Query(...), payment_amount: int = Query(...)):
    project = projects.find_one_and_update(
        {"_id": ObjectId(project_id)},
        {"$inc": {"funded_money": payment_amount}},
        return_document=True
    )
    if project:
        return {"message": "Project funded successfully"}
    else:
        raise HTTPException(status_code=404, detail="Project not found")
    
@app.patch("/verify_project/{project_id}", response_model=dict)
def verify_project(project_id: str):
    project = projects.find_one({"_id": ObjectId(project_id)})
    project["is_verified"] = True
    if project:
        projects.update_one({"_id": ObjectId(project_id)}, {"$set": project})
        return {"message": "Project verified successfully"}
    else:
        raise HTTPException(status_code=404, detail="Project not found")

@app.patch("/neglect_project/{project_id}", response_model=dict)
def verify_project(project_id: str):
    project = projects.find_one({"_id": ObjectId(project_id)})
    project["is_verified"] = False
    if project:
        projects.update_one({"_id": ObjectId(project_id)}, {"$set": project})
        return {"message": "Project neglected successfully"}
    else:
        raise HTTPException(status_code=404, detail="Project not found")
    
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
    



import datetime
from enum import Enum
from gzip import READ
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from pymongo.mongo_client import MongoClient
from fastapi import status
import secrets
from openai import OpenAI

OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY")
OPENAI_ORGANIZATION_ID="org-s0MEUTdIYlEUfLGXlECYOT63"


client = OpenAI(
    api_key=OPENAI_API_KEY
)


class TransactionType(str, Enum):
    MONEY_DEPOSIT = "MONEY_DEPOSIT"
    TOKEN_DEPOSIT = "TOKEN_DEPOSIT"
    MONEY_PAYMENT = "MONEY_PAYMENT"
    TOKEN_PAYMENT = "TOKEN_PAYMENT" 

class ProjectPayment(BaseModel):
    id : str = secrets.token_hex(nbytes=16)
    transaction_type: TransactionType = TransactionType.MONEY_PAYMENT
    project_id: str
    amount: float
    date: datetime.datetime = datetime.datetime.now()

class MoneyDeposit(BaseModel):
    id : str = secrets.token_hex(nbytes=16)
    transaction_type: TransactionType = TransactionType.MONEY_DEPOSIT
    amount: float
    date: datetime.datetime = datetime.datetime.now()

class TokenDeposit(BaseModel):
    id : str = secrets.token_hex(nbytes=16)
    transaction_type: TransactionType = TransactionType.TOKEN_DEPOSIT
    amount: float 
    date: datetime.datetime = datetime.datetime.now()

class TokenPayment(BaseModel):
    id : str = secrets.token_hex(nbytes=16)
    transaction_type: TransactionType = TransactionType.TOKEN_PAYMENT
    benefit_id: str
    amount: float 
    date: datetime.datetime = datetime.datetime.now()

class Wallet(BaseModel):
    user_id: str
    money_balance:float = 0
    toke_balance:float = 0
    bank_number: str = ""
    transaction_history: list =     []

class VoteResponse(BaseModel):
    upvotes: int
    downvotes: int


class DB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self):
        
        self.client = MongoClient(MONGO_URI)
        self.db = self.client['hackyeahdb']

        try:
            self.client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)

    def get_vote_by_user_id(self, entity_id:str,  user_id:str):
        collection = self.db['votes']
        return collection.find_one({"$and" : [{"user_id" : user_id}, {"entity_id":entity_id}]}, {"_id":0})

    def insert_vote(self, entity_id, user_id, value):
        collection = self.db['votes']
        collection.insert_one({"entity_id": entity_id, "user_id": user_id, "value": value})

    def update_vote(self, entity_id, user_id, value):
        collection = self.db['votes']
        collection.update_one({"$and" : [{"user_id" : user_id}, {"entity_id":entity_id}]}, {"$set": {"value": value}})

    def delete_vote(self, entity_id, user_id):
        collection = self.db['votes']
        collection.delete_one({"$and" : [{"user_id" : user_id}, {"entity_id":entity_id}]})

    def create_wallet(self, user_id):
        collection = self.db['wallets']

        if not collection.find_one({"user_id": user_id}):
            wallet = Wallet(user_id=user_id)
            collection.insert_one(wallet.model_dump())
            
            return status.HTTP_201_CREATED
        else:
            return status.HTTP_409_CONFLICT

    def get_wallet(self, user_id):
        collection = self.db['wallets']
        return collection.find_one({"user_id": user_id}, {"_id":0})
    
    def add_money(self, user_id, amount):
        if amount < 0:
            return          HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        
        collection = self.db['wallets']
        wallet = collection.find_one({"user_id": user_id})
        wallet['money_balance'] += amount
        collection.update_one({"user_id": user_id}, {"$set": wallet})


    def substract_money(self, user_id, amount):
        if amount < 0:
            return     HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        
        collection = self.db['wallets']
        wallet = collection.find_one({"user_id": user_id})
        if wallet['money_balance'] >= amount:
            wallet['money_balance'] -= amount
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)


        collection.update_one({"user_id": user_id}, {"$set": wallet})
        
        return status.HTTP_200_OK

    def add_token(self, user_id, amount):
        if amount < 0:
            return              HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        
        collection = self.db['wallets']
        wallet = collection.find_one({"user_id": user_id})
        wallet['token_balance'] += amount
        collection.update_one({"user_id": user_id}, {"$set": wallet})

    def substract_token(self, user_id, amount):
        if amount < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
        
        collection = self.db['wallets']
        wallet = collection.find_one({"user_id": user_id})
        if wallet['token_balance'] >= amount:
            wallet['token_balance'] -= amount
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        collection.update_one({"user_id": user_id}, {"$set": wallet})

    def add_transaction(self, user_id, transaction: dict):
        collection = self.db['wallets']
        wallet = collection.find_one({"user_id": user_id})
        # transaction.transaction_type = str(transaction.transaction_type)
        print(transaction)
        wallet['transaction_history'].append(transaction)
        collection.update_one({"user_id": user_id}, {"$set": wallet})


db = DB()

@app.post("/vote/{entity_id}/{user_id}/{value}", tags=["vote"])
def post_vote(entity_id: str, user_id: str, value: int) -> Response:
    vote = db.get_vote_by_user_id(entity_id, user_id)
    
    if vote:
        if vote['value'] == value:
            db.delete_vote(entity_id, user_id)
        if vote['value'] != value:
            db.update_vote(entity_id, user_id, value)
        

        return status.HTTP_200_OK
    else:
        db.insert_vote(entity_id, user_id, value)
    
    return status.HTTP_201_CREATED

@app.get("/vote/{entity_id}", tags=["vote"])
def get_votes_count(entity_id:str) -> VoteResponse:
    dct = {"upvotes": 0, "downvotes": 0}

    collection = db.db['votes']
    for vote in collection.find({"entity_id": entity_id}):
        value = vote['value']
        if value == 1:
            dct['upvotes'] += 1
        if value == -1:
            dct['downvotes'] += 1             

    return dct


@app.post("/wallet/{user_id}", tags=["wallet"])
def create_wallet(user_id:str) -> Response:
    db.create_wallet(user_id)
    return status.HTTP_201_CREATED


@app.post("/wallet/{user_id}/add_money/{amount}", tags=["wallet"])
def add_money(user_id:str, amount:float) -> Response:
    db.add_money(user_id, amount)
    db.add_transaction(user_id, MoneyDeposit(amount=amount).model_dump())
    return status.HTTP_200_OK

@app.post("/wallet/{user_id}/substract_money/{amount}", tags=["wallet"])
def substract_money(user_id:str, amount:float) -> Response:
    db.substract_money(user_id, amount)
    return status.HTTP_200_OK


@app.post("/wallet/{user_id}/add_token/{amount}", tags=["wallet"])
def add_token(user_id:str, amount:float) -> Response:
    db.add_token(user_id, amount)
    db.add_transaction(user_id, TokenDeposit(amount=amount).model_dump())
    return status.HTTP_200_OK

@app.post("/wallet/{user_id}/substract_token/{amount}", tags=["wallet"])
def substract_token(user_id:str, amount:float) -> Response:
    db.substract_token(user_id, amount)
    return status.HTTP_200_OK

@app.get("/wallet/{user_id}", tags=["wallet"])
def get_wallet(user_id:str) -> Wallet:
    return db.get_wallet(user_id)

class AiResponse(BaseModel):
    grade: int
    corrected_text: str

@app.post("/ai", tags=['ai'])
def ai(text: str) -> AiResponse:


    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"""Zweryfikuj podane podanie pod względem poprawności językowej i oficjalności, wszystkie niecenzuralne slowa obnizaja ocene do 0. zwróć w pierwszej linii tylko liczbę, ocenę w skali od 1 do 100.
                w następnej linii wypisz tylko poprawioną wersję: {text}""",
            }
        ],
        model="gpt-4o",
    )

    grade = chat_completion.choices[0].message.content.split("\n")[0]
    corrected_text = "".join(chat_completion.choices[0].message.content.split("\n")[1:])

    return {"grade": grade, "corrected_text": corrected_text}
