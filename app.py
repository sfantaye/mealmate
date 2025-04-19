import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, firestore, auth, initialize_app
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Streamlit Page Configuration
st.set_page_config(page_title="MealMate", page_icon="🍽️")

# Inject Tailwind CSS and animations (AOS)
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/npm/tailwindcss@2.1.2/dist/tailwind.min.css');
    @import url('https://cdn.jsdelivr.net/npm/aos@2.3.4/dist/aos.css');
    </style>
    <script src="https://cdn.jsdelivr.net/npm/aos@2.3.4/dist/aos.js"></script>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        AOS.init();
    });
    </script>
""", unsafe_allow_html=True)

# Firebase initialization
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase/credentials.json")  # Load credentials from JSON file
        initialize_app(cred)
except Exception as e:
    st.error(f"Firebase initialization failed: {e}")

# Get API Key from .env
API_KEY = os.getenv("SPOONACULAR_API_KEY")

# Initialize Firestore
db = firestore.client()

# Function to fetch recipe suggestions
def get_recipes(ingredients, diet=""):
    # Step 1: Find recipes by ingredients
    url = f"https://api.spoonacular.com/recipes/findByIngredients?ingredients={','.join(ingredients)}&diet={diet}&number=5&apiKey={API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        st.error("Error fetching data from Spoonacular API. Please try again later.")
        return []
    
    recipes = response.json()
    
    # Step 2: Fetch detailed information for each recipe
    detailed_recipes = []
    for recipe in recipes:
        recipe_id = recipe['id']
        info_url = f"https://api.spoonacular.com/recipes/{recipe_id}/information?includeNutrition=true&apiKey={API_KEY}"
        info_response = requests.get(info_url)
        
        if info_response.status_code == 200:
            detailed_recipes.append(info_response.json())
        else:
            st.error(f"Failed to fetch detailed information for recipe ID {recipe_id}.")
    
    return detailed_recipes

# Function to generate a shareable link
def generate_shareable_link(recipe):
    return f"https://www.spoonacular.com/recipes/{recipe['id']}/{recipe['title'].replace(' ', '-')}"

# Function to fetch ingredient suggestions (autocomplete)
def get_ingredient_suggestions(query):
    url = f"https://api.spoonacular.com/food/ingredients/autocomplete?query={query}&number=5&apiKey={API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        st.error("Error fetching ingredient suggestions.")
        return []
    
    return [ingredient['name'] for ingredient in response.json()]

# Firebase Authentication (Login/Logout)
def login_user():
    email = st.text_input("Email", key="email_login")
    password = st.text_input("Password", type="password", key="password_login")
    
    if st.button("Login"):
        try:
            user = auth.get_user_by_email(email)
            st.session_state["user"] = user
            st.success(f"Welcome, {user.email}")
        except Exception as e:
            st.error(f"Login failed: {e}")

def logout_user():
    if "user" in st.session_state:
        del st.session_state["user"]
        st.success("Logged out successfully")

# Firebase Signup
def signup_user():
    st.subheader("Create an Account")
    email = st.text_input("Email", key="email_signup")
    password = st.text_input("Password", type="password", key="password_signup")
    
    if st.button("Sign Up"):
        try:
            user = auth.create_user(email=email, password=password)
            st.success(f"Account created successfully! Welcome, {user.email}")
            st.session_state["user"] = user
        except Exception as e:
            st.error(f"Signup failed: {e}")

# Streamlit UI configuration
st.title("MealMate - Dynamic Recipe Generator 🍽️")
st.subheader("Enter your ingredients and let MealMate suggest delicious recipes!")

# Authentication Section
if "user" in st.session_state:
    st.write(f"Logged in as {st.session_state['user'].email}")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Logout"):
            logout_user()
    with col2:
        if st.button("View Favorites"):
            st.session_state["show_favorites"] = True
else:
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        login_user()
    with tab2:
        signup_user()

# Ingredient input (autocomplete and manual)
ingredient_input = st.text_input("Enter an ingredient to get suggestions:", key="ingredient_input")

if ingredient_input:
    suggestions = get_ingredient_suggestions(ingredient_input)
    if suggestions:
        ingredient_input = st.selectbox("Choose an ingredient", suggestions)

# Input for ingredients (comma-separated)
ingredients = st.text_input("Enter your ingredients (comma-separated):", "")

# Validate ingredients input and fetch recipes
if ingredients:
    ingredients_list = [ingredient.strip() for ingredient in ingredients.split(',')]
    selected_diet = st.selectbox("Select a diet preference:", ["", "vegan", "gluten free", "dairy free", "paleo", "ketogenic", "low carb"])
    
    recipes = get_recipes(ingredients_list, selected_diet)
    
    if recipes:
        for recipe in recipes:
            st.markdown(f'<div class="bg-white rounded-lg shadow-lg p-5 mb-5" data-aos="fade-up">', unsafe_allow_html=True)
            st.markdown(f'<h3 class="text-xl font-bold text-orange-600">{recipe["title"]}</h3>', unsafe_allow_html=True)
            st.image(recipe['image'], use_container_width=True)
            
            prep_time = recipe.get("readyInMinutes", "N/A")
            servings = recipe.get("servings", "N/A")
            st.markdown(f'<p class="text-sm text-gray-700">Prep Time: {prep_time} minutes | Servings: {servings}</p>', unsafe_allow_html=True)
            
            # Ingredients
            ingredients = recipe.get('extendedIngredients', [])
            if ingredients:
                st.write("**Ingredients:**")
                st.write(", ".join([ingredient['original'] for ingredient in ingredients]))
            else:
                st.write("No ingredients listed.")
            
            # Instructions
            instructions = recipe.get("instructions", "No instructions available")
            if instructions:
                st.write("**Instructions:**")
                st.markdown(instructions.replace("\n", "<br>"), unsafe_allow_html=True)  # Format instructions with line breaks
            else:
                st.write("No instructions available.")
            
            # Nutritional Information
            # Nutritional Information
            if recipe.get('nutrition'):
               st.write("#### Nutritional Information:")
               nutrients = recipe['nutrition'].get('nutrients', [])
               for nutrient in nutrients:
                # Check if all required keys exist
                     title = nutrient.get('title', 'Unknown Nutrient')
                     amount = nutrient.get('amount', 'N/A')
                     unit = nutrient.get('unit', '')
                     st.write(f"{title}: {amount} {unit}")
            else:
                st.write("No nutritional information available.")
            # Shareable link
            shareable_link = generate_shareable_link(recipe)
            st.markdown(f'<a href="{shareable_link}" class="bg-orange-500 text-white py-2 px-4 rounded-md hover:bg-orange-600" target="_blank">Share Recipe</a>', unsafe_allow_html=True)
            
            # Button to save recipe to favorites
            if "user" in st.session_state:
                user = st.session_state["user"]
                favorites_ref = db.collection("favorites").document(user.uid)
                
                if st.button(f"Save {recipe['title']} to Favorites", key=recipe['id']):
                    favorites_ref.set({
                        "favorites": firestore.ArrayUnion([recipe])
                    })
                    st.success(f"Saved {recipe['title']} to favorites!")
            st.markdown('</div>', unsafe_allow_html=True)
            
    else:
        st.write("No recipes found for the given ingredients.")
else:
    st.info("Please enter ingredients to get recipe suggestions.")

# Display favorites (if user is logged in)
if "user" in st.session_state and st.session_state.get("show_favorites", False):
    user = st.session_state["user"]
    favorites_ref = db.collection("favorites").document(user.uid)
    favorites_doc = favorites_ref.get()
    
    if favorites_doc.exists:
        favorites = favorites_doc.to_dict().get("favorites", [])
        if favorites:
            st.write("### Your Favorite Recipes:")
            for recipe in favorites:
                st.write(f"- {recipe['title']}")
        else:
            st.write("You have no favorite recipes.")
    else:
        st.write("No favorites found.")

# Footer with your name
st.markdown("""
    <footer class="text-center p-4 mt-10 text-sm text-gray-500">
        Made by Sintayehu Fantaye
    </footer>
""", unsafe_allow_html=True)