import requests
import json

# Test the search endpoint
search_url = "http://localhost:5001/api/search"
search_data = {
    "query": "Ihring"
}

response = requests.post(search_url, json=search_data)
print("Search Response:")
print(json.dumps(response.json(), indent=2))

# Test the chat endpoint
chat_url = "http://localhost:5001/api/chat"
chat_data = {
    "message": "Finde Dokumente über den BMW von Herrn Ihring"
}

response = requests.post(chat_url, json=chat_data)
print("\nChat Response:")
print(json.dumps(response.json(), indent=2))