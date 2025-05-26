import requests

BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOiJmMWExNzJjMS05ZTQ5LTQ5OTEtYmU5Yi1kMDllZWMyMzIyM2YiLCJleHAiOjE3NDgyNTQ3OTN9.XiaY4VaSCMsZl0vFZT4KHRtBcG1p4GR-5gEbCaNl89w"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

def test_endpoints():
    # Test getting documents
    print("\nTesting GET /api/documents:")
    response = requests.get(f"{BASE_URL}/api/documents", headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # Test rebuilding index
    print("\nTesting POST /api/rebuild_index:")
    response = requests.post(f"{BASE_URL}/api/rebuild_index", headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # Test getting user info
    print("\nTesting GET /api/users/me:")
    response = requests.get(f"{BASE_URL}/api/users/me", headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_endpoints() 