import google.generativeai as genai
import config as c
import logging
import db

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Gemini (Dynamically read key from DB)
def get_model():
    api_key = db.get_setting('google_api_key', c.GOOGLE_API_KEY)
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(c.GEMINI_MODEL)

async def analyze_screenshot(file_path, task_type):
    """
    Sends the screenshot to Gemini to verify if the task is completed.
    Returns: "PASS", "FAIL", or "UNSURE"
    """
    model = get_model()
    prompt = f"""
    You are an automated task verifier for a TikTok points bot. 
    Analyze this screenshot and determine if the user has completed a '{task_type}' task.
    
    CRITERIA:
    - If task_type is 'Follow': Check if the button says 'Following', 'Follow back', 'Friends', or shows the 'unfollow' icon.
    - If task_type is 'Like': Check if the heart icon is red/filled.
    
    RESPONSE FORMAT:
    Reply with exactly ONE word:
    - PASS: If you are 100% sure the task is completed correctly.
    - FAIL: If you are sure the task is NOT completed (e.g., button still says 'Follow').
    - UNSURE: If the image is blurry, irrelevant, or you cannot tell.
    
    """
    
    try:
        # Load the image
        with open(file_path, "rb") as f:
            img_data = f.read()
        
        # Call Gemini
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": img_data}
        ])
        
        result = response.text.strip().upper()
        
        if result in ["PASS", "FAIL", "UNSURE"]:
            return result
        else:
            logger.warning(f"AI returned unexpected result: {result}")
            return "UNSURE"
            
    except Exception as e:
        logger.error(f"Error in Vision AI: {str(e)}")
        return "UNSURE"
