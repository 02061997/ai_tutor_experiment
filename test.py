import google.generativeai as genai
import os # Good practice for API keys

# --- Correct Initialization ---
# 1. Configure the API Key
# It's highly recommended *not* to hardcode your API key directly in the script.
# Use environment variables instead for security.
# Example: Set an environment variable GOOGLE_API_KEY="YOUR_API_KEY" in your terminal
# api_key = os.getenv("GOOGLE_API_KEY")
# If you must hardcode for testing (not recommended for production/sharing):
api_key = "AIzaSyBw91HZf7CCDJRVBiFR6e4JZ7YQb4FLHPI" # Replace with your actual key if needed

genai.configure(api_key=api_key)

# 2. Create the model instance
# Replace 'gemini-1.5-flash' with the specific model you intend to use if different.
# Note: 'gemini-2.0-flash' from your original code might not be a valid public model name.
# Check the Google AI documentation for available model names.
model = genai.GenerativeModel('gemini-1.5-flash')
# --- End Correct Initialization ---


# --- Correct Content Generation Call ---
# 3. Generate content using the model instance
try:
    # Call generate_content on the 'model' object, not a 'client' object
    response = model.generate_content("Explain how AI works in a few words")
    print(response.text)
except Exception as e:
    # Catch potential errors (e.g., invalid API key, model not found, network issues)
    print(f"An error occurred: {e}")
# --- End Correct Content Generation Call ---