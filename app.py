import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, firestore, auth, initialize_app
import json

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
firebase_creds = st.secrets["firebase"]["credentials"]
cred = credentials.Certificate(json.loads(firebase_creds))

if not firebase_admin._apps:
    initialize_app(cred)

# Get API Key from secrets
API_KEY = st.secrets["api_keys"]["spoonacular"]

# Initialize Firestore
db = firestore.client()

# Function to fetch recipe suggestions
def get_recipes(ingredients, diet=""):
    url = f"https://api.spoonacular.com/recipes/findByIngredients?ingredients={','.join(ingredients)}&diet={diet}&number=5&apiKey={API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        st.error("Error fetching data from Spoonacular API. Please try again later.")
        return []
    
    return response.json()

# Function to fetch ingredient suggestions (autocomplete)
def get_ingredient_suggestions(query):
    url = f"https://api.spoonacular.com/food/ingredients/autocomplete?query={query}&number=5&apiKey={API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        st.error("Error fetching ingredient suggestions.")
        return []
    
    return [ingredient['name'] for ingredient in response.json()]

# Function to generate a shareable link
def generate_shareable_link(recipe):
    return f"https://www.spoonacular.com/recipes/{recipe['id']}/{recipe['title'].replace(' ', '-')}"


# Streamlit UI configuration
st.title("MealMate - Dynamic Recipe Generator 🍽️")
st.subheader("Enter your ingredients and let MealMate suggest delicious recipes!")

# Firebase Authentication (Login/Logout)
def login_user():
    email = st.text_input("Email", key="email")
    password = st.text_input("Password", type="password", key="password")
    
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

if "user" in st.session_state:
    st.write(f"Logged in as {st.session_state['user'].email}")
    if st.button("Logout"):
        logout_user()
else:
    login_user()

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
            st.image(f"https://spoonacular.com/recipeImages/{recipe['id']}-312x231.jpg", use_container_width=True)
            prep_time = recipe.get("readyInMinutes", "N/A")
            servings = recipe.get("servings", "N/A")
            st.markdown(f'<p class="text-sm text-gray-700">Prep Time: {prep_time} minutes | Servings: {servings}</p>', unsafe_allow_html=True)
            st.write("**Ingredients:**")
            ingredients = recipe.get('extendedIngredients', [])
            if ingredients:
                st.write("**Ingredients:**")
                st.write(", ".join([ingredient['name'] for ingredient in ingredients]))
            else:
                st.write("No ingredients listed.")
            st.write("**Instructions:**")
            st.write(recipe.get("instructions", "No instructions available"))
            
            # Nutritional Information
            if recipe.get('nutrition'):
                st.write("#### Nutritional Information:")
                for nutrient in recipe['nutrition']['nutrients']:
                    st.write(f"{nutrient['title']}: {nutrient['amount']} {nutrient['unit']}")

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
if "user" in st.session_state:
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
