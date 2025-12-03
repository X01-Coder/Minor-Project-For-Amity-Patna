# api.py
from fastapi import FastAPI, UploadFile, File, Response
from fastapi.middleware.cors import CORSMiddleware
from inference import denoise_file_bytes  # this must exist in inference.py

app = FastAPI(title="Audio Denoiser API")

# Optional CORS (handy if you later call from a frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Audio Denoiser API is running"}

# IMPORTANT: this is POST, not GET
@app.post("/denoise")
async def denoise_endpoint(file: UploadFile = File(...)):
    """
    Upload a noisy audio file (wav), get back denoised audio bytes.
    """
    # Read uploaded file into bytes
    contents = await file.read()

    # Call your model inference – must return raw WAV bytes
    denoised_bytes = denoise_file_bytes(contents)

    # Return as an audio/wav HTTP response
    return Response(
        content=denoised_bytes,
        media_type="audio/wav",
        headers={
            # Makes browser / client see it as downloadable file
            "Content-Disposition": f'attachment; filename="denoised_{file.filename}"'
        },
    )
