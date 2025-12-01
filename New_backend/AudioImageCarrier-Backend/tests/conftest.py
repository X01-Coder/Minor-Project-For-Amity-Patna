import pytest

@pytest.fixture(scope="session")
def master_key():
    return "00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF"  # Example master key in hex format

@pytest.fixture(scope="session")
def user_id():
    return "prince"  # Example user ID for testing purposes

@pytest.fixture(scope="session")
def test_audio_file(tmp_path_factory):
    # Create a temporary audio file for testing
    temp_dir = tmp_path_factory.mktemp("audio")
    audio_file_path = temp_dir / "test_audio.wav"
    with open(audio_file_path, "wb") as f:
        f.write(b"RIFF" + b"\x00" * 100)  # Placeholder for a WAV file header
    return audio_file_path

@pytest.fixture(scope="session")
def test_image_file(tmp_path_factory):
    # Create a temporary image file for testing
    temp_dir = tmp_path_factory.mktemp("images")
    image_file_path = temp_dir / "test_image.png"
    with open(image_file_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # Placeholder for a PNG file header
    return image_file_path