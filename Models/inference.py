import os
from io import BytesIO

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchaudio

# ==========================================
# CONFIGURATION
# ==========================================
CONFIG = {
    "sample_rate": 16000,
    "n_fft": 1024,
    "hop_length": 256,
    "n_mels": 80,
    "device": "cuda" if torch.cuda.is_available() else "cpu",

    # PATH TO YOUR TRAINED MODEL
    "model_path": r"E:\Minor-Project-For-Amity-Patna\Models\best_denoiser_model.pth",
}

# Global model cache (so it doesn't reload every request)
_MODEL = None


# ==========================================
# MODEL ARCHITECTURE (must match training)
# ==========================================
class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(out_channels)

        self.shortcut = nn.Sequential()
        if in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1),
                nn.BatchNorm2d(out_channels),
            )

    def forward(self, x):
        residual = self.shortcut(x)
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += residual
        return F.relu(out)


class AdvancedResUNet(nn.Module):
    def __init__(self):
        super().__init__()
        # Encoder
        self.enc1 = ResidualBlock(1, 32)
        self.pool1 = nn.MaxPool2d(2)
        self.enc2 = ResidualBlock(32, 64)
        self.pool2 = nn.MaxPool2d(2)
        self.enc3 = ResidualBlock(64, 128)
        self.pool3 = nn.MaxPool2d(2)
        # Bottleneck
        self.bottleneck = ResidualBlock(128, 256)
        # Decoder
        self.up3 = nn.ConvTranspose2d(256, 128, kernel_size=2, stride=2)
        self.dec3 = ResidualBlock(256, 128)
        self.up2 = nn.ConvTranspose2d(128, 64, kernel_size=2, stride=2)
        self.dec2 = ResidualBlock(128, 64)
        self.up1 = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
        self.dec1 = ResidualBlock(64, 32)

        self.final_conv = nn.Conv2d(32, 1, kernel_size=1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        e1 = self.enc1(x)
        p1 = self.pool1(e1)

        e2 = self.enc2(p1)
        p2 = self.pool2(e2)

        e3 = self.enc3(p2)
        p3 = self.pool3(e3)

        b = self.bottleneck(p3)

        d3 = self.up3(b)
        if d3.shape != e3.shape:
            d3 = F.interpolate(d3, size=e3.shape[2:])
        d3 = torch.cat([d3, e3], dim=1)
        d3 = self.dec3(d3)

        d2 = self.up2(d3)
        if d2.shape != e2.shape:
            d2 = F.interpolate(d2, size=e2.shape[2:])
        d2 = torch.cat([d2, e2], dim=1)
        d2 = self.dec2(d2)

        d1 = self.up1(d2)
        if d1.shape != e1.shape:
            d1 = F.interpolate(d1, size=e1.shape[2:])
        d1 = torch.cat([d1, e1], dim=1)
        d1 = self.dec1(d1)

        mask = self.sigmoid(self.final_conv(d1))
        return x * mask


# ==========================================
# MODEL LOADING
# ==========================================
def load_model():
    """
    Lazily load the model once and reuse it.
    """
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    device = CONFIG["device"]
    model_path = CONFIG["model_path"]

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}. Train it first.")

    print(f"[inference] Loading model from: {model_path} on {device}")
    model = AdvancedResUNet().to(device)

    # Safe to use weights_only=True because you saved with model.state_dict()
    state_dict = torch.load(model_path, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()

    _MODEL = model
    return _MODEL


# ==========================================
# AUDIO HELPERS
# ==========================================
def _to_mono_and_resample(waveform: torch.Tensor, sr: int) -> torch.Tensor:
    # waveform shape: (channels, time)
    if waveform.dim() != 2:
        raise ValueError(f"Expected waveform with shape (channels, time), got {waveform.shape}")

    # Mono
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    # Resample if needed
    if sr != CONFIG["sample_rate"]:
        resampler = torchaudio.transforms.Resample(sr, CONFIG["sample_rate"])
        waveform = resampler(waveform)

    return waveform


def _normalize_waveform(waveform: torch.Tensor) -> torch.Tensor:
    max_val = waveform.abs().max()
    if max_val > 0:
        waveform = waveform / max_val
    return waveform


# ==========================================
# CORE DENOISING USING ORIGINAL PHASE + ISTFT
# ==========================================
def denoise_waveform_tensor(waveform: torch.Tensor, sr: int) -> torch.Tensor:
    """
    waveform: (channels, time) on CPU
    returns: denoised waveform (1, time) on CPU
    """
    device = CONFIG["device"]
    n_fft = CONFIG["n_fft"]
    hop_length = CONFIG["hop_length"]

    # 1. Preprocess: mono + resample
    waveform = _to_mono_and_resample(waveform, sr)  # (1, T)
    orig_len = waveform.shape[-1]

    waveform = waveform.to(device)

    # 2. STFT to get complex spectrogram (for magnitude + phase)
    window = torch.hann_window(n_fft, device=device)
    stft_complex = torch.stft(
        waveform,
        n_fft=n_fft,
        hop_length=hop_length,
        window=window,
        return_complex=True,
    )  # shape: (1, freq, frames)

    noisy_phase = torch.angle(stft_complex)  # (1, freq, frames)
    noisy_mag = torch.abs(stft_complex)      # (1, freq, frames)

    # Determine n_stft dynamically from STFT result to avoid shape mismatch
    n_freq = noisy_mag.shape[-2]

    # 3. Linear magnitude -> Mel
    mel_scale = torchaudio.transforms.MelScale(
        n_mels=CONFIG["n_mels"],
        sample_rate=CONFIG["sample_rate"],
        n_stft=n_freq,
    ).to(device)

    # noisy_mag shape: (1, freq, frames) => MelScale expects (..., freq, time)
    noisy_mel = mel_scale(noisy_mag)  # (1, n_mels, frames)

    noisy_log_mel = torch.log1p(noisy_mel + 1e-6)  # (1, n_mels, frames)

    # Add batch dimension for model: (batch, channels, n_mels, time)
    # Here: batch=1, channels=1
    model_input = noisy_log_mel.unsqueeze(0)  # (1, 1, n_mels, frames)

    model = load_model()
    with torch.no_grad():
        denoised_log_mel = model(model_input)  # (1, 1, n_mels, frames)

    denoised_log_mel = denoised_log_mel.squeeze(0).squeeze(0)  # (n_mels, frames)

    # 4. Log Mel -> Linear magnitude (Mel)
    denoised_mel = torch.expm1(denoised_log_mel)
    denoised_mel = torch.clamp(denoised_mel, min=0.0)

    # 5. Mel -> Linear magnitude (freq)
    inverse_mel = torchaudio.transforms.InverseMelScale(
        n_stft=n_freq,
        n_mels=CONFIG["n_mels"],
        sample_rate=CONFIG["sample_rate"],
    ).to(device)

    pred_mag = inverse_mel(denoised_mel)  # (freq, frames)

    # Match shape with phase: (1, freq, frames)
    pred_mag = pred_mag.unsqueeze(0)

    # 6. Combine predicted magnitude with original phase
    complex_pred = pred_mag * torch.exp(1j * noisy_phase)  # (1, freq, frames)

    # 7. ISTFT back to waveform
    rec_waveform = torch.istft(
        complex_pred,
        n_fft=n_fft,
        hop_length=hop_length,
        window=window,
        length=orig_len,  # make sure length matches original
    )  # (1, time)

    # Ensure 2D: (channels, time)
    if rec_waveform.dim() == 1:
        rec_waveform = rec_waveform.unsqueeze(0)

    rec_waveform = _normalize_waveform(rec_waveform)
    return rec_waveform.cpu()  # (1, time) on CPU


# ==========================================
# BYTES-LEVEL API FOR FastAPI
# ==========================================
def denoise_file_bytes(file_bytes: bytes) -> bytes:
    """
    Takes raw WAV file bytes, returns denoised WAV file bytes.
    Used by FastAPI endpoint.
    """
    # Read from memory buffer
    in_buffer = BytesIO(file_bytes)
    waveform, sr = torchaudio.load(in_buffer)  # waveform: (channels, time)

    denoised = denoise_waveform_tensor(waveform, sr)  # (1, time) on CPU

    # Write to memory buffer
    out_buffer = BytesIO()
    torchaudio.save(out_buffer, denoised, CONFIG["sample_rate"], format="wav")
    out_buffer.seek(0)
    return out_buffer.read()


# ==========================================
# OPTIONAL: CLI / batch folder denoising
# ==========================================
def denoise_folder(input_folder: str, output_folder: str):
    """
    Utility to denoise all .wav files in a folder.
    Not required for API, but useful for testing.
    """
    import glob
    from tqdm import tqdm

    os.makedirs(output_folder, exist_ok=True)

    wav_files = glob.glob(os.path.join(input_folder, "*.wav"))
    print(f"[inference] Found {len(wav_files)} files to denoise.")

    for path in tqdm(wav_files, desc="Denoising files"):
        fname = os.path.basename(path)
        waveform, sr = torchaudio.load(path)
        denoised = denoise_waveform_tensor(waveform, sr)
        out_path = os.path.join(output_folder, f"clean_{fname}")
        torchaudio.save(out_path, denoised, CONFIG["sample_rate"])

    print(f"[inference] Done. Results in: {output_folder}")


if __name__ == "__main__":
    # Example standalone usage:
    test_in = r"E:\Test Audio Data\Test Audio Data"
    test_out = r"E:\Test Audio Data\Denoised Results"
    denoise_folder(test_in, test_out)
