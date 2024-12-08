import openai
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import faiss
import numpy as np
from bson.objectid import ObjectId
from main import generate_embedding, load_faiss_index

# Load environment variables
load_dotenv(override=True)

# Set up OpenAI API key and MongoDB connection
openai.api_key = os.getenv("OPENAI_API_KEY")
mongodb_uri = os.getenv("MONGO_URI")
client = MongoClient(mongodb_uri)
db = client["chop-n-shop"]
items_collection = db["items"]
grocery_lists_collection = db["grocery_lists"]

# Load FAISS index and item IDs
faiss_index, item_ids = load_faiss_index("faiss_index_file.index", "ids_list.pkl")
if not faiss_index or not item_ids:
    raise ValueError("FAISS index or item IDs not loaded successfully. Ensure the files exist.")

# Normalize ingredients for consistent processing
def normalize_ingredients(ingredients):
    return [ingredient.strip().lower() for ingredient in ingredients]

# Check allergens in ingredients
def check_allergen_suitability(ingredients, allergens):
    ingredients = normalize_ingredients(ingredients)
    allergens = [allergen.lower() for allergen in allergens]

    return all(allergen not in ingredient for ingredient in ingredients for allergen in allergens)

# Validate dietary preferences and allergens
def is_item_valid(item, dietary_preferences, allergens):
    ingredients = normalize_ingredients(item.get("Ingredients", []))

    # Dietary exclusions based on preferences
    exclusions = {
        "vegan": [
            "meat", "lamb", "chicken", "beef", "pork", "turkey", "duck", "veal", "bison", "goat", "game meat", 
            "salami", "sausage", "bacon", "hot dog", "deli meat", "fish", "salmon", "tuna", "shrimp", "lobster", 
            "crab", "cod", "mackerel", "sardines", "anchovies", "shellfish", "eggs", "chicken eggs", "duck eggs", 
            "quail eggs", "egg powder", "milk", "cow's milk", "goat's milk", "sheep's milk", "cream", "butter", 
            "cheese", "cheddar", "mozzarella", "parmesan", "brie", "gouda", "feta", "yogurt", "ice cream", "whey", 
            "casein", "lactose", "honey", "royal jelly", "bee pollen", "gelatin", "marshmallow", "gummy", "fish sauce", 
            "anchovy paste", "animal fat", "lard", "tallow", "bone marrow", "rennet"
        ],
        "vegetarian": [
            "meat", "lamb", "chicken", "beef", "pork", "turkey", "duck", "veal", "bison", "goat", "game meat", 
            "salami", "sausage", "bacon", "hot dog", "deli meat", "fish", "salmon", "tuna", "shrimp", "lobster", 
            "crab", "cod", "mackerel", "sardines", "anchovies", "shellfish"
        ],
        "gluten-free": [
            "wheat", "barley", "rye", "oats", "seitan", "bulgur", "couscous", "wheat flour", "whole wheat", "wheat germ", 
            "wheat bran", "semolina", "durum", "wheat starch", "spelt", "farro", "malt", "malt syrup", "malt vinegar", 
            "rye flour", "rye bread", "rye crackers", "barley flour", "barley-based products", "seitan", "bread", "cake", 
            "cookie", "pasta"
        ],
        "lactose-free": [
            "milk", "cow's milk", "goat's milk", "sheep's milk", "cheese", "cheddar", "mozzarella", "brie", "gouda", 
            "feta", "parmesan", "cream cheese", "ricotta", "butter", "margarine", "cream", "heavy cream", "sour cream", 
            "half-and-half", "whipped cream", "ice cream", "yogurt", "Greek yogurt", "whey", "lactose"
        ],
        "pescetarian": [
            "meat", "chicken", "beef", "pork", "turkey", "duck", "veal", "bison", "goat", "game meat", 
            "lamb", "chicken breast", "chicken wings", "chicken legs", "chicken thighs", "steak", "ground beef", 
            "pork chops", "bacon", "ham", "sausage", "pork", "duck breast", "duck legs", "confit"
        ]
    }
    if dietary_preferences in exclusions:
        if any(exclusion in ingredient for exclusion in exclusions[dietary_preferences] for ingredient in ingredients):
            return False

    # Allergen check
    return check_allergen_suitability(ingredients, allergens)

# Search for items in the FAISS index by query
def search_items_by_query_faiss(query):
    query_embedding = generate_embedding(query)
    _, indices = faiss_index.search(np.array([query_embedding], dtype=np.float32), k=100)
    return [items_collection.find_one({"_id": ObjectId(item_ids[idx])}) for idx in indices[0] if idx < len(item_ids)]

# Generate grocery list based on user preferences
def generate_grocery_list(user_preferences):
    grocery_lists = {"Trader Joe's": [], "Whole Foods Market": []}
    total_costs = {"Trader Joe's": 0, "Whole Foods Market": 0}
    selected_categories = {"Trader Joe's": set(), "Whole Foods Market": set()}

    for store in grocery_lists.keys():
        for request in user_preferences["Grocery_items"]:
            query_results = search_items_by_query_faiss(request)

            for item in query_results:
                if item and item.get("Store_name") == store:
                    if not is_item_valid(item, user_preferences["Dietary_preferences"], user_preferences["Allergies"]):
                        continue

                    item_price = float(item.get("Price", 0))
                    if total_costs[store] + item_price <= user_preferences["Budget"]:
                        grocery_lists[store].append(item)
                        selected_categories[store].add(item.get("Category", "unknown"))
                        total_costs[store] += item_price
                        break

    # Format grocery lists into JSON format
    formatted_lists = {}
    for store, items in grocery_lists.items():
        formatted_lists[store] = {
            "items": [
                {
                    "Item_name": item["Item_name"],
                    "Price": item["Price"],
                }
                for item in items
            ],
            "Total_Cost": round(total_costs[store], 2),
        }
    # Save the result to the MongoDB grocery_list collection
    # grocery_lists_collection.insert_one(grocery_lists)  # Insert the grocery list as a JSON document

    # Return lists based on store preference
    if user_preferences.get("Store_preference"):
        store = user_preferences["Store_preference"]
        return {store: formatted_lists.get(store, {"message": f"No items found for {store}."})}
    
    grocery_lists_collection.insert_one(formatted_lists)  # Insert here

    return formatted_lists

# Example user preferences
user_preferences = {
    "Budget": 50.00,
    "Grocery_items": ["pizza", "chips", "juice"],
    "Dietary_preferences": "vegan",
    "Allergies": ["peanuts"],
    "Store_preference": None, 
}

# # Generate grocery list
grocery_lists = generate_grocery_list(user_preferences)

# # Save the result to the MongoDB grocery_list collection
#grocery_lists_collection.insert_one(grocery_lists)  # Insert the grocery list as a JSON document

# # Print confirmation
print("Grocery list saved to the database successfully!")