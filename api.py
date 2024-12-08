from fastapi import FastAPI, HTTPException, Depends, status,Header
from pydantic import BaseModel, condecimal
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum
from main import users_collection, stores_collection, items_collection, recipes_collection, grocery_lists_collection
from openai_grocerylist import generate_grocery_list 
from openai_json_recipe import generate_recipe, save_recipe_to_db
from openai_recipe_grocery_list import generate_grocery_list_from_recipe
import jwt
from jwt.exceptions import PyJWTError

app = FastAPI()

SECRET_KEY = "2@1&]."  
ALGORITHM = "HS256" 
ACCESS_TOKEN_EXPIRE_MINUTES = 3000  


# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chop-n-shop-frontend-534070775559.us-central1.run.app"],  
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Cryptography (for hashing passwords)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing or invalid")
    try:
        token = authorization.split(" ")[1]  # "Bearer <token>"
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")
        return user_id
    except PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")

# Enum for dietary preferences
class DietaryPreference(str, Enum):
    vegan = "vegan"
    vegetarian = "vegetarian"
    gluten_free = "gluten-free"
    lactose_free = "lactose-free"
    pescetarian = "pescetarian"
    none = "none"

# Pydantic models for input validation
class UserPreferences(BaseModel):
    list_name: str
    Budget: float
    Grocery_items: List[str]
    Dietary_preferences: str
    Allergies: List[str]
    Store_preference: Optional[str] = None

class SaveRecipeRequest(BaseModel):
    recipe_name: str
    ingredients: List[str]
    instructions: List[str]
    cooking_time: int
    servings: int
    dietary_preferences: Optional[List[str]] = None
    allergies: Optional[List[str]] = None

class User(BaseModel):
    first_name: str
    email: str
    password: str
    allergies: Optional[str] = None

class LoginUser(BaseModel):
    email: str
    password: str

class Item(BaseModel):
    Item_name: str
    Store_name: str
    Price: float
    Ingredients: list[str]
    Calories: int

class RecipeGroceryItem(BaseModel):
    ingredient: str
    item_name: str
    price: float
    store: str

class RecipeGroceryListResponse(BaseModel):
    grocery_list: List[RecipeGroceryItem]
    total_cost: float
    over_budget: float

class RecipePrompt(BaseModel):
    recipe_prompt: str

class GroceryItem(BaseModel):
    ingredient: str
    item_name: str
    price: float
    store: str

# Define user preferences model
class RecipeListUserPreferences(BaseModel):
    Budget: float
    Dietary_preferences: str
    Allergies: List[str]

# Define request and response models
class RecipeRequest(BaseModel):
    recipe_name: str
    user_preferences: RecipeListUserPreferences
    list_name: Optional[str] = None  # Optional field for list name


class RecipeResponse(BaseModel):
    recipe_id: str
    recipe_name: str
    grocery_list: List[GroceryItem]
    total_cost: float
    over_budget: float
    user_id: str

class NewGroceryItem(BaseModel):
    Item_name: str
    Store_name: str
    Price: float

# Generate recipe with grocery list
@app.post("/generate_recipe_with_grocery_list", response_model=RecipeResponse)
async def generate_recipe_with_grocery_list(
    recipe_request: RecipeRequest,
    current_user: str = Depends(get_current_user)
):
    try:
        # Step 1: Check if the recipe exists
        recipe = recipes_collection.find_one({"name": recipe_request.recipe_name})
        if not recipe:
            raise HTTPException(status_code=404, detail="This recipe does not exist.")

        # Step 2: Generate the grocery list
        recipe_id = recipe["_id"]
        try:
            grocery_list, total_cost, over_budget = generate_grocery_list_from_recipe(
                recipe_id=recipe_id, user_preferences=recipe_request.user_preferences.dict()
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating grocery list: {str(e)}")

        # Step 3: Save the grocery list with user ID
        recipe_list_document = {
            "list_name": recipe_request.list_name or f"Recipe List for {recipe_request.recipe_name}",
            "recipe_name": recipe_request.recipe_name,
            "recipe_id": str(recipe_id),
            "grocery_list": grocery_list,
            "total_cost": total_cost,
            "over_budget": over_budget,
            "created_at": datetime.utcnow(),
            "user_id": current_user
        }
        try:
            result = grocery_lists_collection.insert_one(recipe_list_document)
            inserted_id = result.inserted_id
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving grocery list: {str(e)}")
        print(grocery_list)
        # Step 4: Return the response
        return RecipeResponse(
            recipe_id=str(recipe_id),
            recipe_name=recipe["name"],
            grocery_list=[GroceryItem(**item) for item in grocery_list],
            total_cost=total_cost,
            over_budget=over_budget,
            user_id=current_user 
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
# Fetch saved recipe lists by name
@app.get("/recipe_lists/")
async def get_recipe_list_by_name(list_name: str):
    """
    Fetch a saved recipe list by its name.
    """
    try:
        recipe_list = grocery_lists_collection.find_one({"list_name": list_name})
        if not recipe_list:
            raise HTTPException(status_code=404, detail="Recipe list not found")

        # Convert ObjectId to string and return the recipe list
        recipe_list["_id"] = str(recipe_list["_id"])
        return recipe_list

    except Exception as e:
        print(f"Error fetching recipe list by name: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    
# Utility functions for password handling
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Routes for user registration and authentication

# User Registration Route
@app.post("/register/")
async def add_user(user: User):
    existing_user = users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already in use")

    hashed_password = hash_password(user.password)

    user_document = {
        "first_name": user.first_name,
        "email": user.email,
        "password": hashed_password,
        "allergies": user.allergies.split(",") if user.allergies else []
    }

    try:
        result = users_collection.insert_one(user_document)
        return {"message": f"User {user.first_name} added with ID: {result.inserted_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while adding the user: {str(e)}")

# User Login Route
@app.post("/login/")
async def login(user: LoginUser):
    existing_user = users_collection.find_one({"email": user.email})
    if not existing_user or not verify_password(user.password, existing_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Generate JWT token
    access_token = create_access_token(data={"sub": str(existing_user["_id"])})
    return {"message": "Login successful", "access_token": access_token, "token_type": "bearer"}

@app.post("/generate_grocery_list/")
async def generate_grocery_list_endpoint(user_preferences: UserPreferences, list_name: Optional[str] = None, current_user: str = Depends(get_current_user)):
    try:
        # Validate input items
        if not user_preferences.Grocery_items:
            raise HTTPException(status_code=400, detail="Items list cannot be empty.")

        # Handle the store name being None
        store_preference = user_preferences.Store_preference if user_preferences.Store_preference else None

        # Generate grocery list based on preferences
        grocery_list = generate_grocery_list({
            "Budget": user_preferences.Budget,
            "Grocery_items": user_preferences.Grocery_items,
            "Dietary_preferences": user_preferences.Dietary_preferences,
            "Allergies": user_preferences.Allergies,
            "Store_preference": store_preference,
        })

        # Remove _id if present before inserting into the database
        if "_id" in grocery_list:
            del grocery_list["_id"]

        # Insert the generated grocery list into the collection with user association
        grocery_list["user_id"] = current_user  # Associate the list with the logged-in user
        grocery_list["created_at"] = datetime.utcnow()

        # If a list name is provided, include it in the grocery list document
        if user_preferences.list_name:
            grocery_list["list_name"] = user_preferences.list_name

        # Insert the grocery list into the database
        grocery_lists_collection.insert_one(grocery_list)

        # Return the grocery list with its new _id
        grocery_list["_id"] = str(grocery_list["_id"])
        print(grocery_list)
        return {"grocery_list": grocery_list}

    except Exception as e:
        print(f"Error generating grocery list: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.")

# Fetch previous grocery lists for a user
@app.get("/grocery_lists")
async def get_grocery_lists(list_name: Optional[str] = None, current_user: str = Depends(get_current_user)):
    try:
        query = {"user_id": current_user}
        
        # If a list name is provided, filter by name as well
        if list_name:
            query["list_name"] = list_name
        
        grocery_lists = grocery_lists_collection.find(query)
        
        if not grocery_lists:
            return {"grocery_lists": []}
            
        grocery_list_items = []
        for list_item in grocery_lists:
            list_item["_id"] = str(list_item["_id"])
            grocery_list_items.append(list_item)
            
        return {"grocery_lists": grocery_list_items}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching grocery lists.",
        )


@app.delete("/grocery_lists/{list_id}")
async def delete_grocery_list(list_id: str, current_user: str = Depends(get_current_user)):
    try:
        if not list_id or list_id == "undefined":
            raise HTTPException(status_code=400, detail="Invalid list ID")
            
        result = grocery_lists_collection.delete_one({
            "_id": ObjectId(list_id), 
            "user_id": current_user
        })
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404, 
                detail="Grocery list not found or you don't have permission to delete it"
            )
            
        return {"message": "Grocery list deleted successfully"}
        
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid list ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while deleting the grocery list: {str(e)}"
        )

@app.get("/items/")
async def get_items():
    items = list(items_collection.find())
    return [{"Item_name": item["Item_name"], "Price": item["Price"]} for item in items]

# Route to fetch all stores (can be useful for frontend)
@app.get("/stores/")
async def get_stores():
    stores = list(stores_collection.find())
    return [{"Store_name": store["Store_name"]} for store in stores]

@app.post("/generate_recipe/")
async def generate_recipe_route(prompt: RecipePrompt):
    try:
        # Call the function directly
        recipe = generate_recipe(prompt.recipe_prompt)
        if not recipe:
            raise HTTPException(status_code=400, detail="Failed to generate recipe. Please try again.")
        
        recipe_id = save_recipe_to_db(recipe)
        if not recipe_id:
            raise HTTPException(status_code=500, detail="Failed to save recipe to database.")
        return {"recipe": recipe}

    except Exception as e:
        print(f"Error generating recipe: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

# from bson import json_util
# from fastapi.encoders import jsonable_encoder

# @app.post("/generate_recipe/")
# async def generate_recipe_route(prompt: RecipePrompt):
#     try:
#         recipe = generate_recipe(prompt.recipe_prompt)
#         if not recipe:
#             raise HTTPException(status_code=400, detail="Failed to generate recipe. Please try again.")
        
#         recipe_id = save_recipe_to_db(recipe)
#         if not recipe_id:
#             raise HTTPException(status_code=500, detail="Failed to save recipe to database.")
        
#         # Use FastAPI's jsonable_encoder to ensure the response is JSON serializable
#         return {"recipe": jsonable_encoder(recipe), "recipe_id": recipe_id}

#     except Exception as e:
#         print(f"Error generating recipe: {str(e)}")
#         raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.")

@app.get("/recipes/{recipe_name}/")
async def get_recipe_by_name(recipe_name: str):
    """
    Fetch the first recipe that matches the given name, with case-insensitive partial matching.
    """
    try:
        # Create a case-insensitive regex pattern
        name_pattern = f".*{recipe_name}.*"
        
        # Use a case-insensitive regex query and get only the first match
        recipe = recipes_collection.find_one(
            {"name": {"$regex": name_pattern, "$options": "i"}}
        )

        if not recipe:
            raise HTTPException(status_code=404, detail="No recipe found matching the query")

        # Convert ObjectId to string
        recipe["_id"] = str(recipe["_id"])

        return recipe

    except Exception as e:
        print(f"Error fetching recipe by name: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@app.get("/api/user")
async def get_current_user(user_email: str):
    user = users_collection.find_one({"email": user_email}) 
    if not user:
        raise HTTPException(status_code=404, detail=f"User with email {user_email} not found")

    return {
        "id": str(user["_id"]),
        "first_name": user.get("first_name", ""),
        "email": user.get("email", ""),
        "allergies": user.get("allergies", []),
    }

# @app.post("/grocery_lists/{list_id}/add_item")
# async def add_item_to_grocery_list(
#     list_id: str, 
#     new_item: NewGroceryItem, 
#     current_user: str = Depends(get_current_user)
# ):
#     try:
#         # Validate the list_id
#         if not ObjectId.is_valid(list_id):
#             raise HTTPException(status_code=400, detail="Invalid list ID")

#         # Find the grocery list
#         grocery_list = grocery_lists_collection.find_one({
#             "_id": ObjectId(list_id),
#             "user_id": current_user
#         })

#         if not grocery_list:
#             raise HTTPException(status_code=404, detail="Grocery list not found or you don't have permission to modify it")

#         # Add the new item to the grocery list
#         new_item_dict = new_item.dict()
#         grocery_lists_collection.update_one(
#             {"_id": ObjectId(list_id)},
#             {"$push": {"grocery_list": new_item_dict}}
#         )

#         # Update the total cost
#         new_total_cost = grocery_list.get("total_cost", 0) + new_item.Price
#         grocery_lists_collection.update_one(
#             {"_id": ObjectId(list_id)},
#             {"$set": {"total_cost": new_total_cost}}
#         )

#         return {"message": f"Item '{new_item.Item_name}' added to the grocery list successfully"}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An error occurred while adding the item: {str(e)}")

@app.post("/recipes/save")
async def save_recipe(
    recipe: SaveRecipeRequest,
    current_user: str = Depends(get_current_user)
):
    try:
        # Check if recipe already exists for this user
        existing_recipe = recipes_collection.find_one({
            "name": recipe.recipe_name,
            "user_id": current_user
        })
        
        if existing_recipe:
            raise HTTPException(
                status_code=400, 
                detail="A recipe with this name already exists"
            )

        # Create recipe document
        recipe_document = {
            "name": recipe.recipe_name,
            "ingredients": recipe.ingredients,
            "instructions": recipe.instructions,
            "cooking_time": recipe.cooking_time,
            "servings": recipe.servings,
            "dietary_preferences": recipe.dietary_preferences or [],
            "allergies": recipe.allergies or [],
            "user_id": current_user,
            "created_at": datetime.utcnow()
        }

        # Insert into database
        result = recipes_collection.insert_one(recipe_document)
        
        return {
            "message": "Recipe saved successfully",
            "recipe_id": str(result.inserted_id)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving recipe: {str(e)}"
        )
#testing
@app.get("/recipes/saved")
async def get_saved_recipes(current_user: str = Depends(get_current_user)):
    try:
        # Find all recipes saved by the current user
        saved_recipes = recipes_collection.find({"user_id": current_user})
        
        # Convert cursor to list and format the response
        recipes_list = []
        for recipe in saved_recipes:
            recipes_list.append({
                "recipe_id": str(recipe["_id"]),
                "name": recipe["name"],
                "ingredients": recipe["ingredients"],
                "instructions": recipe["instructions"],
                "cooking_time": recipe["cooking_time"],
                "servings": recipe["servings"],
                "dietary_preferences": recipe.get("dietary_preferences", []),
                "allergies": recipe.get("allergies", []),
                "created_at": recipe["created_at"] 
            })
            
        return {
            "recipes": recipes_list,
            "total_count": len(recipes_list)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching saved recipes: {str(e)}"
        )

@app.delete("/grocery_lists/{list_id}/items/{item_name}")
async def delete_item_from_grocery_list(
    list_id: str,
    item_name: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        current_user_id = current_user.get('id')
        # print(f"Attempting to delete item '{item_name}' from list '{list_id}' for user ID '{current_user_id}'")
        
        if not ObjectId.is_valid(list_id):
            raise HTTPException(status_code=400, detail="Invalid list ID")

        grocery_list = grocery_lists_collection.find_one({"_id": ObjectId(list_id)})
        
        if not grocery_list:
            print(f"No list found with id '{list_id}'")
            raise HTTPException(status_code=404, detail="Grocery list not found")

        # print(f"Found grocery list: {grocery_list}")
        
        list_user_id = grocery_list.get('user_id')
        # print(f"List user_id: {list_user_id}, Current user ID: {current_user_id}")
        
        if str(list_user_id) != str(current_user_id):
            print(f"User '{current_user_id}' doesn't have permission. List user_id: {list_user_id}")
            raise HTTPException(status_code=403, detail="You don't have permission to modify this list")

        # Find and remove the item from the grocery list
        item_removed = False
        for store in ["Trader Joe's", "Whole Foods Market"]:
            result = grocery_lists_collection.update_one(
                {"_id": ObjectId(list_id)},
                {"$pull": {f"{store}.items": {"Item_name": item_name}}}
            )
            if result.modified_count > 0:
                item_removed = True
                break

        if not item_removed:
            raise HTTPException(status_code=404, detail=f"Item '{item_name}' not found in the grocery list")

        # Update the total cost for each store
        updated_list = grocery_lists_collection.find_one({"_id": ObjectId(list_id)})
        if updated_list:
            for store in ["Trader Joe's", "Whole Foods Market"]:
                if store in updated_list:
                    new_total_cost = sum(item.get('Price', 0) for item in updated_list[store].get('items', []))
                    grocery_lists_collection.update_one(
                        {"_id": ObjectId(list_id)},
                        {"$set": {f"{store}.Total_Cost": new_total_cost}}
                    )
        else:
            print(f"Warning: Updated list not found. List ID: {list_id}")

        return {"message": f"Item '{item_name}' removed from the grocery list successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in delete_item_from_grocery_list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while removing the item: {str(e)}")
