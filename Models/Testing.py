import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchaudio
import glob
from tqdm import tqdm

# ==========================================
# CONFIGURATION
# ==========================================
CONFIG = {
    "sample_rate": 16000,
    "n_fft": 1024,
    "hop_length": 256,
    "n_mels": 80,
    "device": "cuda" if torch.cuda.is_available() else "cpu",
    "model_path": "best_denoiser_model.pth",  
    
    # INPUT / OUTPUT
    "input_folder": r"E:\Test Audio Data\Test Audio Data", 
    "output_folder": r"E:\Test Audio Data\Denoised Results"      
}

# ==========================================
# MODEL ARCHITECTURE (Must match Training)
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
                nn.BatchNorm2d(out_channels)
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
        if d3.shape != e3.shape: d3 = F.interpolate(d3, size=e3.shape[2:])
        d3 = torch.cat([d3, e3], dim=1)
        d3 = self.dec3(d3)
        d2 = self.up2(d3)
        if d2.shape != e2.shape: d2 = F.interpolate(d2, size=e2.shape[2:])
        d2 = torch.cat([d2, e2], dim=1)
        d2 = self.dec2(d2)
        d1 = self.up1(d2)
        if d1.shape != e1.shape: d1 = F.interpolate(d1, size=e1.shape[2:])
        d1 = torch.cat([d1, e1], dim=1)
        d1 = self.dec1(d1)
        
        mask = self.sigmoid(self.final_conv(d1))
        return x * mask

# ==========================================
# INFERENCE LOGIC (Updated for Phase Reconstruction)
# ==========================================
def load_model():
    print(f"Loading model from {CONFIG['model_path']}...")
    model = AdvancedResUNet().to(CONFIG['device'])
    
    if not os.path.exists(CONFIG['model_path']):
        raise FileNotFoundError(f"Model not found at {CONFIG['model_path']}. Train first!")
        
    state_dict = torch.load(CONFIG['model_path'], map_location=CONFIG['device'])
    model.load_state_dict(state_dict)
    model.eval()
    return model

def make_loud_and_clear(waveform):
    """Normalize volume"""
    max_val = torch.abs(waveform).max()
    if max_val > 0:
        waveform = waveform / max_val
    return waveform

def denoise_files():
    if not os.path.exists(CONFIG['output_folder']):
        os.makedirs(CONFIG['output_folder'])

    model = load_model()
    
    # 1. We need the Mel Scale (to feed the model)
    mel_scale = torchaudio.transforms.MelScale(
        n_mels=CONFIG['n_mels'],
        sample_rate=CONFIG['sample_rate'],
        n_stft=CONFIG['n_fft'] // 2 + 1
    ).to(CONFIG['device'])

    # 2. We need Inverse Mel (to get back to Linear Magnitude)
    inverse_mel = torchaudio.transforms.InverseMelScale(
        n_stft=CONFIG["n_fft"] // 2 + 1,
        n_mels=CONFIG["n_mels"],
        sample_rate=CONFIG["sample_rate"]
    ).to(CONFIG['device'])

    files = glob.glob(os.path.join(CONFIG['input_folder'], "*.wav"))
    print(f"Found {len(files)} files to process.")

    for file_path in tqdm(files, desc="Denoising"):
        filename = os.path.basename(file_path)
        
        # Load and Preprocess
        waveform, sr = torchaudio.load(file_path)
        if waveform.shape[0] > 1: waveform = torch.mean(waveform, dim=0, keepdim=True)
        if sr != CONFIG["sample_rate"]:
            resampler = torchaudio.transforms.Resample(sr, CONFIG["sample_rate"])
            waveform = resampler(waveform)
        
        waveform = waveform.to(CONFIG['device'])

        # --- STEP 1: Compute STFT to get Phase & Linear Magnitude ---
        # We use standard STFT instead of MelSpectrogram directly so we can keep phase
        window = torch.hann_window(CONFIG['n_fft']).to(CONFIG['device'])
        stft_complex = torch.stft(
            waveform, 
            n_fft=CONFIG['n_fft'], 
            hop_length=CONFIG['hop_length'], 
            window=window, 
            return_complex=True
        )
        
        # Extract Parts
        noisy_phase = torch.angle(stft_complex)  # Save the natural phase!
        noisy_mag = torch.abs(stft_complex)
        
        # --- STEP 2: Convert Linear Mag -> Mel -> Model ---
        noisy_mel = mel_scale(noisy_mag)
        noisy_log_mel = torch.log1p(noisy_mel + 1e-6).unsqueeze(0) # Add batch dim

        with torch.no_grad():
            # Run Model
            denoised_log_mel = model(noisy_log_mel)
            denoised_log_mel = denoised_log_mel.squeeze(0) # Remove batch dim

        # --- STEP 3: Reconstruct using Original Phase ---
        # 1. Log Mel -> Linear Mel
        denoised_mel = torch.expm1(denoised_log_mel)
        denoised_mel = torch.clamp(denoised_mel, min=0.0)

        # 2. Mel -> Linear Magnitude (Approximation)
        pred_mag = inverse_mel(denoised_mel)
        
        # 3. COMBINE: Predicted Magnitude + Original Noisy Phase
        # This removes "robotic" artifacts because the phase is natural
        complex_pred = pred_mag * torch.exp(1j * noisy_phase)
        
        # 4. ISTFT (Inverse Short-Time Fourier Transform)
        rec_waveform = torch.istft(
            complex_pred, 
            n_fft=CONFIG['n_fft'], 
            hop_length=CONFIG['hop_length'], 
            window=window,
            length=waveform.shape[-1] # Ensure exact length match
        )

        # Post-Processing
        rec_waveform = make_loud_and_clear(rec_waveform.cpu())

        # Save
        out_path = os.path.join(CONFIG['output_folder'], f"clean_{filename}")
        torchaudio.save(out_path, rec_waveform, CONFIG["sample_rate"])

    print(f"Done! Results saved to {CONFIG['output_folder']}")

if __name__ == "__main__":
    denoise_files()