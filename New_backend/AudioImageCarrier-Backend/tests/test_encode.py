import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_encode_audio_to_image():
    with open("tests/test_audio.wav", "rb") as audio_file:
        response = client.post(
            "/api/encode",
            files={"audio_file": audio_file},
            data={"user": "prince"}
        )
    assert response.status_code == 200
    assert "images.zip" in response.content.decode()

def test_decode_image_to_audio():
    with open("tests/test_images.zip", "rb") as image_file:
        response = client.post(
            "/api/decode",
            files={"image_files": image_file},
            data={"user": "prince"}
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"  # Assuming WAV format for the output
    assert response.content  # Ensure there is content in the response

def test_encode_audio_missing_user():
    with open("tests/test_audio.wav", "rb") as audio_file:
        response = client.post(
            "/api/encode",
            files={"audio_file": audio_file}
        )
    assert response.status_code == 422  # Unprocessable Entity due to missing user

def test_decode_image_missing_user():
    with open("tests/test_images.zip", "rb") as image_file:
        response = client.post(
            "/api/decode",
            files={"image_files": image_file}
        )
    assert response.status_code == 422  # Unprocessable Entity due to missing user