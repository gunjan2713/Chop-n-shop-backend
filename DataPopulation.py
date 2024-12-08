# User Data
users = [
    {
        "_id": "67044483b9c2ac3499945950",
        "First_name": "Bob",
        "Email": "bob@gmail.com",
        "Budget": 30.0,
        "Dietary_restrictions": ["Vegan", "Vegetarian"],
        "Allergies": ["Peanuts", "Fish"],
        "Food_request": ["pizza", "sandwich"],
        "Preferred_stores": ["Trader Joes", "Wegmans"]
    },
    {
        "_id": "6704500f30d76813016565fd",
        "First_name": "Emma",
        "Email": "emma@gmail.com",
        "Budget": 40.0,
        "Dietary_restrictions": [],
        "Allergies": [],
        "Food_request": ["pasta", "snacks"],
        "Preferred_stores": ["Wegmans"]
    },
    {
        "_id": "670452810fd21996425cbf6b",
        "First_name": "Steve",
        "Email": "steve2927@gmail.com",
        "Budget": 53.0,
        "Dietary_restrictions": ["Vegan"],
        "Allergies": [],
        "Food_request": ["salad"],
        "Preferred_stores": []
    },
    {
        "_id": "67045302234be6469e0cc442",
        "First_name": "Amy",
        "Email": "amy22332@gmail.com",
        "Budget": 35.0,
        "Dietary_restrictions": ["Kosher"],
        "Allergies": ["Dairy"],
        "Food_request": ["stew", "chips", "popcorn", "fruits"],
        "Preferred_stores": ["Whole Foods"]
    },
    {
        "_id": "670453643032a399358ac018",
        "First_name": "Sarah",
        "Email": "sarah@gmail.com",
        "Budget": 47.0,
        "Dietary_restrictions": ["Halal"],
        "Allergies": [],
        "Food_request": ["soup", "salad", "pasta"],
        "Preferred_stores": []
    },
    {
        "_id": "67047b69e8b55eb331670d0d",
        "First_name": "Adam",
        "Email": "adam@gmail.com",
        "Budget": 40.0,
        "Dietary_restrictions": [],
        "Allergies": [],
        "Food_request": ["pizza"],
        "Preferred_stores": ["Wegmans"]
    },
    {
        "_id": "6704a1886c41fa011757b9e7",
        "First_name": "Tiffany",
        "Email": "tiff@gmail.com",
        "Budget": 60.0,
        "Dietary_restrictions": ["Vegan"],
        "Allergies": [],
        "Food_request": ["ramen", "rice"],
        "Preferred_stores": ["Whole Foods"]
    }
]

# Store Data
stores = [
    {
        "Store_id": "1",
        "Name": "Trader Joes",
        "Items": [
            {
                "Item_id": "101",
                "Item_name": "Organic Bananas",
                "Price": 0.99,
                "Ingredients": ["Bananas"],
                "Calories": 105
            },
            {
                "Item_id": "102",
                "Item_name": "Almond Milk",
                "Price": 3.99,
                "Ingredients": ["Almonds", "Water"],
                "Calories": 60
            }
        ]
    },
    {
        "Store_id": "2",
        "Name": "Whole Foods",
        "Items": [
            {
                "Item_id": "201",
                "Item_name": "Organic Chicken Breast",
                "Price": 6.99,
                "Ingredients": ["Chicken"],
                "Calories": 165
            },
            {
                "Item_id": "202",
                "Item_name": "Organic Apples",
                "Price": 2.49,
                "Ingredients": ["Apples"],
                "Calories": 95
            }
        ]
    },
    {
        "Store_id": "3",
        "Name": "Wegmans",
        "Items": [
            {
                "Item_id": "301",
                "Item_name": "Greek Yogurt",
                "Price": 1.49,
                "Ingredients": ["Milk", "Live Active Cultures"],
                "Calories": 100
            },
            {
                "Item_id": "302",
                "Item_name": "Whole Wheat Bread",
                "Price": 2.99,
                "Ingredients": ["Whole Wheat", "Yeast"],
                "Calories": 120
            }
        ]
    }
]

# Item Data
items = [
    {
        "Item_id": "101",
        "Item_name": "Organic Bananas",
        "Store_id": "1",
        "Store_name": "Trader Joes",
        "Price": 0.99,
        "Ingredients": ["Bananas"],
        "Calories": 105
    },
    {
        "Item_id": "102",
        "Item_name": "Almond Milk",
        "Store_id": "1",
        "Store_name": "Trader Joes",
        "Price": 3.99,
        "Ingredients": ["Almonds", "Water"],
        "Calories": 60
    },
    {
        "Item_id": "201",
        "Item_name": "Organic Chicken Breast",
        "Store_id": "2",
        "Store_name": "Whole Foods",
        "Price": 6.99,
        "Ingredients": ["Chicken"],
        "Calories": 165
    },
    {
        "Item_id": "202",
        "Item_name": "Organic Apples",
        "Store_id": "2",
        "Store_name": "Whole Foods",
        "Price": 2.49,
        "Ingredients": ["Apples"],
        "Calories": 95
    },
    {
        "Item_id": "301",
        "Item_name": "Greek Yogurt",
        "Store_id": "3",
        "Store_name": "Wegmans",
        "Price": 1.49,
        "Ingredients": ["Milk", "Live Active Cultures"],
        "Calories": 100
    },
    {
        "Item_id": "302",
        "Item_name": "Whole Wheat Bread",
        "Store_id": "3",
        "Store_name": "Wegmans",
        "Price": 2.99,
        "Ingredients": ["Whole Wheat", "Yeast"],
        "Calories": 120
    }
]

# Recipe Data
recipes = [
    {
        "Recipe_id": "1",
        "Recipe_name": "Banana Smoothie",
        "Ingredients": ["Bananas", "Almond Milk"]
    },
    {
        "Recipe_id": "2",
        "Recipe_name": "Chicken Salad",
        "Ingredients": ["Organic Chicken Breast", "Greek Yogurt"]
    },
    {
        "Recipe_id": "3",
        "Recipe_name": "Apple and Yogurt Bowl",
        "Ingredients": ["Organic Apples", "Greek Yogurt"]
    }
]
