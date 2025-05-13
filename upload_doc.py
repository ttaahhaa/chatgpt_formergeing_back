import requests
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upload_document(file_path, token):
    url = "http://localhost:8000/api/upload"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"Error: File not found at {file_path}")
        return
    
    # Get file size
    file_size = os.path.getsize(file_path)
    logger.info(f"File size: {file_size} bytes")
    
    # Open file in binary mode
    with open(file_path, 'rb') as f:
        files = {
            'file': (os.path.basename(file_path), f, 'application/pdf')
        }
        
        try:
            logger.info(f"Uploading file: {file_path}")
            response = requests.post(url, headers=headers, files=files)
            logger.info(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Error response: {response.text}")
            else:
                logger.info(f"Response: {response.json()}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    # Your JWT token
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOiJkYjRjNzBhNC1jM2VlLTRkYzktYWU3Ny1hYzhiYTA5MTRkYWIiLCJleHAiOjE3NDcxMzY1NTZ9.J24QkzA9D1hwh52Z4Nev1rgbkTGLTMnB4sUukrK5J14"
    
    # Path to your PDF file
    file_path = r"C:\Users\Dell\Documents\110992.pdf"
    
    upload_document(file_path, token) 