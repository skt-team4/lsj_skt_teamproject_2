from fastapi.testclient import TestClient
from server import app, USERNAME, PASSWORD

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "lsj is running"}

def test_send_message():
    response = client.post("/send", json={"text": "Hello, test!"})
    assert response.status_code == 200
    assert response.json() == {"lsj received_message": "Hello, test!"}

def test_list_files_unauthorized():
    response = client.get("/files")
    assert response.status_code == 401

def test_list_files_authorized():
    response = client.get("/files", auth=(USERNAME, PASSWORD))
    assert response.status_code == 200
    assert "files" in response.json()

def test_get_file_unauthorized():
    response = client.get("/files/test.txt")
    assert response.status_code == 401

def test_get_file_authorized():
    response = client.get("/files/test.txt", auth=(USERNAME, PASSWORD))
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"

def test_get_nonexistent_file():
    response = client.get("/files/nonexistent.txt", auth=(USERNAME, PASSWORD))
    assert response.status_code == 404