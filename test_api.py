import requests
import json

def test_login():
    # Login endpoint
    login_url = "http://localhost:8000/api/users/login"
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    # Make login request
    response = requests.post(login_url, data=login_data)
    print("Login Response:", response.status_code)
    print("Login Response Body:", response.text)
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        return token
    return None

def test_upload(token, file_path):
    # Upload endpoint
    upload_url = "http://localhost:8000/api/upload"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Open file in binary mode
    with open(file_path, 'rb') as f:
        files = {
            'file': (file_path.split('\\')[-1], f, 'application/pdf')
        }
        
        # Make upload request
        response = requests.post(upload_url, headers=headers, files=files)
        print("\nUpload Response:", response.status_code)
        print("Upload Response Body:", response.text)

def test_query(token, query):
    # Query endpoint
    query_url = "http://localhost:8000/api/chat"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "message": query,
        "mode": "documents_only"
    }
    
    # Make query request
    response = requests.post(query_url, headers=headers, json=data)
    print("\nQuery Response:", response.status_code)
    print("Query Response Body:", response.text)

if __name__ == "__main__":
    # Test login
    token = test_login()
    
    if token:
        # Test upload with the actual PDF file
        test_upload(token, r"C:\Users\Dell\Documents\110992.pdf")
        
        # Test query
        test_query(token, "What documents are available?") 