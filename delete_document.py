import requests

BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOiJmMWExNzJjMS05ZTQ5LTQ5OTEtYmU5Yi1kMDllZWMyMzIyM2YiLCJleHAiOjE3NDgyNTQ3OTN9.XiaY4VaSCMsZl0vFZT4KHRtBcG1p4GR-5gEbCaNl89w"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/x-www-form-urlencoded"
}

def delete_document():
    # Delete the document
    document_id = "doc_677c32b8-adb4-481b-bf9a-4204d131bf28"  # From the previous response
    response = requests.post(
        f"{BASE_URL}/api/delete_document",
        headers=HEADERS,
        data={"document_id": document_id}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    delete_document() 