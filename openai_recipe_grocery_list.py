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
recipes_collection = db["recipes"]

# Load FAISS index and item IDs
faiss_index, item_ids = load_faiss_index("faiss_index_file.index", "ids_list.pkl")
if not faiss_index or not item_ids:
    raise ValueError("FAISS index or item IDs not loaded successfully. Ensure the files exist.")

# Normalize simplified ingredients for consistent processing
def normalize_ingredients(simplified_ingredients):
    return [simplified_ingredients.strip().lower() for simplified_ingredients in simplified_ingredients]

# Search for items in the FAISS index by query
def search_items_by_query_faiss(query):
    """
    Search the FAISS index for items that match a query and return the MongoDB documents.
    """
    query_embedding = generate_embedding(query)
    _, indices = faiss_index.search(np.array([query_embedding], dtype=np.float32), k=100)
    return [items_collection.find_one({"_id": ObjectId(item_ids[idx])}) for idx in indices[0] if idx < len(item_ids)]

# Validate dietary preferences and allergens
def is_item_valid(item, dietary_preferences, allergens):
    """
    Validate if an item satisfies dietary preferences and does not contain allergens.
    """
    simplified_ingredients = normalize_ingredients(item.get("Simplified Ingredients", []))

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
        if any(exclusion in simplified_ingredients for exclusion in exclusions[dietary_preferences]):
            return False

    # Check allergens
    return all(allergen.lower() not in ingredient for allergen in allergens for ingredient in simplified_ingredients)

# Generate grocery list based on a recipe
def generate_grocery_list_from_recipe(recipe_id, user_preferences):
    """
    Generate a grocery list by matching recipe ingredients with items in the FAISS index.
    """
    recipe = recipes_collection.find_one({"_id": ObjectId(recipe_id)})
    if not recipe or "simplified_ingredients" not in recipe:
        raise ValueError(f"Recipe with ID {recipe_id} not found or has no simplified ingredients.")

    grocery_list = []
    total_cost = 0
    over_budget = 0

    for ingredient in recipe["simplified_ingredients"]:
        query_results = search_items_by_query_faiss(ingredient)

        for item in query_results:
            if not item or not is_item_valid(item, user_preferences["Dietary_preferences"], user_preferences["Allergies"]):
                continue

            item_price = float(item.get("Price", 0))
            new_total_cost = total_cost + item_price
            if new_total_cost <= user_preferences["Budget"]:
                grocery_list.append({
                    "ingredient": ingredient,
                    "item_name": item["Item_name"],
                    "price": item_price,
                    "store": item["Store_name"]
                })
                total_cost = round(new_total_cost, 2)  # Round to two decimal places
                break  # Add only the first valid match for each ingredient
            else:
                # If adding the item exceeds the budget, track the over-budget amount
                over_budget = round(new_total_cost - user_preferences["Budget"], 2)  # Round to two decimal places
                break  # Skip to next item once the budget is exceeded

    # Check if total cost exceeds the budget and calculate over-budget
    if over_budget > 0:
        over_budget = round(total_cost - user_preferences["Budget"], 2)

    return grocery_list, total_cost, over_budget

# # Example Usage
# user_preferences = {
#     "Budget": 100.00,
#     "Dietary_preferences": "vegan",
#     "Allergies": ["peanuts"],
# }

# recipe_id = ObjectId("673cb0f48d075af54e90fa77")  # Replace with your recipe's ObjectId

# try:
#     grocery_list, total_cost, over_budget = generate_grocery_list_from_recipe(recipe_id, user_preferences)
#     print("Generated Grocery List:")
#     for item in grocery_list:
#         print(f"{item['ingredient']} -> {item['item_name']} (${item['price']}) at {item['store']}")
#     print(f"\nTotal Cost: ${total_cost:.2f}")

#     if over_budget > 0:
#         print(f"Warning: You are over budget by ${over_budget:.2f}")
#     else:
#         print("You are within your budget.")
# except ValueError as e:
#     print(e)
