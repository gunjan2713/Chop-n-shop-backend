import os
import pymongo
import pandas as pd
import pickle
import faiss
import numpy as np
#from bson import ObjectId
#from bson.binary import Binary
from dotenv import load_dotenv
from scipy.spatial.distance import cosine
from sentence_transformers import SentenceTransformer  # Using sentence transformers for embeddings

# Load environment variables and connect to MongoDB
load_dotenv(override=True)

mongodb_uri = os.getenv("MONGO_URI")
print(mongodb_uri)
client = pymongo.MongoClient(mongodb_uri)
db = client["chop-n-shop"]
users_collection = db["users"]
stores_collection = db["stores"]
items_collection = db["items"]
recipes_collection = db["recipes"]
grocery_lists_collection = db["grocery_lists"]

# Initialize the sentence-transformers model
model = SentenceTransformer('all-MPNet-base-v2')

# Ping to check the connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Build a FAISS index from MongoDB embeddings
def build_faiss_index():
    # Fetch all items with embeddings from MongoDB
    items = items_collection.find({"embedding": {"$exists": True}})
    
    # Extract embeddings and their corresponding IDs
    embeddings = []
    ids = []
    count = 0  # Counter for progress tracking

    for item in items:
        embedding = pickle.loads(item["embedding"])  # Deserialize embedding
        embeddings.append(embedding)
        ids.append(str(item["_id"]))  # Use stringified ObjectId as ID
        count += 1
        if count % 100 == 0:
            print(f"{count} embeddings processed...")

    # Convert embeddings to numpy array (required by FAISS)
    embeddings_np = np.array(embeddings).astype("float32")
    
    # Initialize a FAISS index
    dimension = embeddings_np.shape[1]
    index = faiss.IndexFlatL2(dimension)  # L2 distance for similarity
    
    # Add embeddings to the FAISS index
    index.add(embeddings_np)
    
    print(f"FAISS index built with {index.ntotal} items.")
    return index, ids  # Return the index and IDs

# Function to generate embeddings for an item name (or description)
def generate_embedding(text):
    try:
        return model.encode(text).tolist()
    except Exception as e:
        print(f"Error generating embedding for '{text}': {e}")
        return None

# Function to search items based on a query
def search_items_by_query_faiss(query, index, ids, top_k=25):
    query_embedding = generate_embedding(query)

    if query_embedding:
        query_np = np.array([query_embedding]).astype("float32")
        distances, indices = index.search(query_np, top_k)
        
        similar_items = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1:  # Check if a valid index is returned
                item_id = ids[idx]
                item = items_collection.find_one({"_id": ObjectId(item_id)})
                if item:
                    similar_items.append((item["Item_name"], 1 - dist))  # Convert distance to similarity
        
        return similar_items
    else:
        print("Error generating query embedding.")
        return []

# Save the FAISS index and IDs list to disk
def save_faiss_index(index, ids, index_file, ids_file):
    try:
        # Save the FAISS index
        faiss.write_index(index, index_file)
        # Save the IDs list
        with open(ids_file, "wb") as f:
            pickle.dump(ids, f)
        print("FAISS index and IDs saved successfully.")
    except Exception as e:
        print(f"Error saving FAISS index or IDs: {e}")

# Load the FAISS index and IDs list from disk
def load_faiss_index(index_file, ids_file):
    try:
        # Load the FAISS index
        index = faiss.read_index(index_file)
        # Load the IDs list
        with open(ids_file, "rb") as f:
            ids = pickle.load(f)
        print("FAISS index and IDs loaded successfully.")
        return index, ids
    except Exception as e:
        print(f"Error loading FAISS index: {e}")
        return None, None

# Main menu
def main():
    global faiss_index, item_ids  # To use the FAISS index in menu options

    # Check if FAISS index files exist before attempting to load
    if os.path.exists("faiss_index_file.index") and os.path.exists("ids_list.pkl"):
        faiss_index, item_ids = load_faiss_index("faiss_index_file.index", "ids_list.pkl")
    else:
        print("FAISS index files not found, rebuilding index...")
        faiss_index, item_ids = build_faiss_index()
        save_faiss_index(faiss_index, item_ids, "faiss_index_file.index", "ids_list.pkl")

    if not faiss_index or not item_ids:
        print("Error loading FAISS index. Exiting...")
        return

    while True:
        print("\nChoose an option:")
        print("1. Search Items by Query")
        print("2. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            query = input("Enter your search query: ")
            results = search_items_by_query_faiss(query, faiss_index, item_ids)
            if results:
                for item_name, score in results:
                    print(f"Item: {item_name}, Similarity Score: {score:.2f}")
            else:
                print("No similar items found.")
        elif choice == "2":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    print("Building FAISS index...")

    # Check if FAISS index files exist before attempting to load
    if os.path.exists("faiss_index_file.index") and os.path.exists("ids_list.pkl"):
        faiss_index, item_ids = load_faiss_index("faiss_index_file.index", "ids_list.pkl")
    else:
        faiss_index, item_ids = build_faiss_index()
        save_faiss_index(faiss_index, item_ids, "faiss_index_file.index", "ids_list.pkl")
    
    main()
