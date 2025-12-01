import pytest
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def setup():
    # Setup code to create necessary files or directories for testing
    os.makedirs("storage/uploads", exist_ok=True)
    yield
    # Teardown code to clean up after tests
    for file in os.listdir("storage/uploads"):
        os.remove(os.path.join("storage/uploads", file))

def test_encode_audio_to_image(setup):
    response = client.post(
        "/api/encode",
        files={"audio_file": ("test_audio.wav", open("tests/test_audio.wav", "rb"))},
        data={"user": "prince"}
    )
    assert response.status_code == 200
    assert "images_zip" in response.json()

def test_decode_image_to_audio(setup):
    response = client.post(
        "/api/decode",
        files={"image_files": ("test_images.zip", open("tests/test_images.zip", "rb"))},
        data={"user": "prince"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"  # Assuming WAV format for output
    assert response.content  # Check that the content is not empty

def test_encode_without_user(setup):
    response = client.post(
        "/api/encode",
        files={"audio_file": ("test_audio.wav", open("tests/test_audio.wav", "rb"))},
        data={}
    )
    assert response.status_code == 422  # Unprocessable Entity due to missing user

def test_decode_without_user(setup):
    response = client.post(
        "/api/decode",
        files={"image_files": ("test_images.zip", open("tests/test_images.zip", "rb"))},
        data={}
    )
    assert response.status_code == 422  # Unprocessable Entity due to missing user

def test_invalid_audio_file(setup):
    response = client.post(
        "/api/encode",
        files={"audio_file": ("invalid_file.txt", open("tests/invalid_file.txt", "rb"))},
        data={"user": "prince"}
    )
    assert response.status_code == 400  # Bad Request due to invalid audio file format

def test_invalid_image_file(setup):
    response = client.post(
        "/api/decode",
        files={"image_files": ("invalid_file.txt", open("tests/invalid_file.txt", "rb"))},
        data={"user": "prince"}
    )
    assert response.status_code == 400  # Bad Request due to invalid image file format