import os
import random
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchaudio
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
import glob

# ==========================================
# CONFIGURATION & HYPERPARAMETERS
# ==========================================
CONFIG = {
    "sample_rate": 16000,
    "n_fft": 1024,
    "hop_length": 256,
    "n_mels": 80,
    "batch_size": 32,               # INCREASED: Higher batch size fills GPU memory better
    "num_workers": 6,               # NEW: Loads data in parallel (CPU optimization)
    "epochs": 100,
    "learning_rate": 1e-4,
    "target_accuracy": 0.99,        
    "patience": 10,
    "device": "cuda" if torch.cuda.is_available() else "cpu",
    
    # USER DATA CONFIGURATION
    "data_root": r"E:\Minor-Project-For-Amity-Patna\Models\Audio Data",  
    "noisy_folder": "Noisy Data",                        
    "clean_folder": "Noiseless Data",                    
    "val_split": 0.2,                               
    "save_path": r"E:\Minor-Project-For-Amity-Patna\Models\best_denoiser_model.pth"
}

# ==========================================
# 1. ADVANCED DATASET LOADING (Optimized for Throughput)
# ==========================================
class AudioDenoisingDataset(Dataset):
    def __init__(self, file_pairs, config):
        self.file_pairs = file_pairs
        self.config = config

    def __len__(self):
        return len(self.file_pairs)

    def load_audio(self, path):
        # We assume files are valid. If read fails, error will bubble up.
        waveform, sr = torchaudio.load(path)
        
        # Force Mono
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
            
        # Resample on CPU (Optimized: usually better done offline, but workers handle it ok)
        if sr != self.config["sample_rate"]:
            resampler = torchaudio.transforms.Resample(sr, self.config["sample_rate"])
            waveform = resampler(waveform)
        return waveform

    def __getitem__(self, idx):
        # NOTE: This function now ONLY returns raw waveforms.
        # The Spectrogram calculation is moved to GPU for speed.
        
        noisy_path, clean_path = self.file_pairs[idx]
        
        noisy_wav = self.load_audio(noisy_path)
        clean_wav = self.load_audio(clean_path)

        # 1. Sync Lengths
        min_len = min(noisy_wav.shape[1], clean_wav.shape[1])
        noisy_wav = noisy_wav[:, :min_len]
        clean_wav = clean_wav[:, :min_len]

        # 2. Pad or Cut to fixed length (32000 samples)
        max_len = 32000 
        
        if min_len < max_len:
            pad_amount = max_len - min_len
            noisy_wav = F.pad(noisy_wav, (0, pad_amount))
            clean_wav = F.pad(clean_wav, (0, pad_amount))
        else:
            start = random.randint(0, min_len - max_len)
            noisy_wav = noisy_wav[:, start:start+max_len]
            clean_wav = clean_wav[:, start:start+max_len]

        return noisy_wav, clean_wav

# ==========================================
# 2. ADVANCED ARCHITECTURE: ResUNet
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
# 3. UTILITIES
# ==========================================
def calculate_fidelity(pred, target):
    l1_diff = torch.abs(pred - target).mean()
    signal_energy = torch.abs(target).mean() + 1e-6
    accuracy = 1.0 - (l1_diff / signal_energy)
    return max(0.0, accuracy.item()) * 100

def get_file_pairs(config):
    noisy_dir = os.path.join(config['data_root'], config['noisy_folder'])
    clean_dir = os.path.join(config['data_root'], config['clean_folder'])
    
    if not os.path.exists(noisy_dir) or not os.path.exists(clean_dir):
        print(f"ERROR: Could not find folders at {config['data_root']}")
        return []

    noisy_files = sorted(glob.glob(os.path.join(noisy_dir, "*.wav")))
    clean_files = sorted(glob.glob(os.path.join(clean_dir, "*.wav")))
    
    clean_map = {os.path.basename(f): f for f in clean_files}
    
    pairs = []
    for nf in noisy_files:
        fname = os.path.basename(nf)
        if fname in clean_map:
            pairs.append((nf, clean_map[fname]))
    
    print(f"Found {len(pairs)} matched audio pairs.")
    return pairs

# ==========================================
# 4. TRAINING LOOP
# ==========================================
def train_model():
    print(f"--- Starting GPU-Optimized Audio Denoiser Training on {CONFIG['device']} ---")
    
    all_pairs = get_file_pairs(CONFIG)
    if len(all_pairs) == 0:
        return

    random.shuffle(all_pairs)
    split_idx = int(len(all_pairs) * (1 - CONFIG['val_split']))
    train_pairs = all_pairs[:split_idx]
    val_pairs = all_pairs[split_idx:]
    
    print(f"Training Samples: {len(train_pairs)} | Validation Samples: {len(val_pairs)}")

    train_dataset = AudioDenoisingDataset(train_pairs, CONFIG)
    val_dataset = AudioDenoisingDataset(val_pairs, CONFIG)
    
    # OPTIMIZATION: num_workers > 0 allows CPU to prepare next batch while GPU processes current one
    # pin_memory=True speeds up transfer to CUDA
    train_loader = DataLoader(
        train_dataset, 
        batch_size=CONFIG['batch_size'], 
        shuffle=True, 
        num_workers=CONFIG['num_workers'], 
        pin_memory=True,
        persistent_workers=True
    )
    val_loader = DataLoader(
        val_dataset, 
        batch_size=CONFIG['batch_size'], 
        shuffle=False, 
        num_workers=CONFIG['num_workers'], 
        pin_memory=True,
        persistent_workers=True
    )

    # 2. Setup Model & Transforms
    model = AdvancedResUNet().to(CONFIG['device'])
    optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG['learning_rate'], weight_decay=1e-5)
    criterion = nn.MSELoss()
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'max', patience=3, factor=0.5) 

    # OPTIMIZATION: Create Spectrogram transform ON GPU
    # This moves the heavy FFT math from CPU to GPU
    mel_transform = torchaudio.transforms.MelSpectrogram(
        sample_rate=CONFIG["sample_rate"],
        n_fft=CONFIG["n_fft"],
        hop_length=CONFIG["hop_length"],
        n_mels=CONFIG["n_mels"]
    ).to(CONFIG['device'])

    best_fidelity = 0.0
    
    # 3. Training Loop
    for epoch in range(CONFIG['epochs']):
        model.train()
        train_loss = 0
        loop = tqdm(train_loader, desc=f"Epoch {epoch+1}/{CONFIG['epochs']} [Train]")
        
        # NOTE: Dataloader now returns waveforms, not specs
        for noisy_wav, clean_wav in loop:
            # 1. Move raw audio to GPU
            noisy_wav = noisy_wav.to(CONFIG['device'], non_blocking=True)
            clean_wav = clean_wav.to(CONFIG['device'], non_blocking=True)
            
            # 2. Compute Spectrograms on GPU (FAST)
            with torch.no_grad():
                noisy_spec = mel_transform(noisy_wav)
                clean_spec = mel_transform(clean_wav)
                
                # Log Scaling (with Epsilon)
                noisy_spec = torch.log1p(noisy_spec + 1e-6)
                clean_spec = torch.log1p(clean_spec + 1e-6)
                
                # Check widths (rarely needed with fixed input size, but good for safety)
                # If sizes drift due to FFT rounding, we crop to common size
                if noisy_spec.shape[-1] != clean_spec.shape[-1]:
                    min_w = min(noisy_spec.shape[-1], clean_spec.shape[-1])
                    noisy_spec = noisy_spec[..., :min_w]
                    clean_spec = clean_spec[..., :min_w]

            optimizer.zero_grad()
            
            # 3. Forward Pass
            output = model(noisy_spec)
            loss = criterion(output, clean_spec)
            
            loss.backward()
            
            # Clip Gradients
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            optimizer.step()
            
            train_loss += loss.item()
            loop.set_postfix(loss=loss.item())
            
        avg_train_loss = train_loss / len(train_loader)
        
        # 4. Validation
        model.eval()
        val_fidelity_accum = 0
        val_loop = tqdm(val_loader, desc=f"Epoch {epoch+1}/{CONFIG['epochs']} [Valid]")
        
        with torch.no_grad():
            for noisy_wav, clean_wav in val_loop:
                # Move to GPU
                noisy_wav = noisy_wav.to(CONFIG['device'], non_blocking=True)
                clean_wav = clean_wav.to(CONFIG['device'], non_blocking=True)
                
                # Spec on GPU
                noisy_spec = mel_transform(noisy_wav)
                clean_spec = mel_transform(clean_wav)
                noisy_spec = torch.log1p(noisy_spec + 1e-6)
                clean_spec = torch.log1p(clean_spec + 1e-6)
                
                # Resize check
                if noisy_spec.shape[-1] != clean_spec.shape[-1]:
                    min_w = min(noisy_spec.shape[-1], clean_spec.shape[-1])
                    noisy_spec = noisy_spec[..., :min_w]
                    clean_spec = clean_spec[..., :min_w]

                output_spec = model(noisy_spec)
                
                batch_fidelity = calculate_fidelity(output_spec, clean_spec)
                val_fidelity_accum += batch_fidelity
                
                val_loop.set_postfix(acc=f"{batch_fidelity:.1f}%")
        
        avg_val_fidelity = val_fidelity_accum / len(val_loader) if len(val_loader) > 0 else 0
        
        print(f"Epoch {epoch+1} Results | Loss: {avg_train_loss:.6f} | Val Accuracy: {avg_val_fidelity:.2f}%")
        
        scheduler.step(avg_val_fidelity)
        
        if avg_val_fidelity > best_fidelity:
            best_fidelity = avg_val_fidelity
            torch.save(model.state_dict(), CONFIG['save_path'])
            print(f">>> New Best Model Saved to {CONFIG['save_path']}! Accuracy: {best_fidelity:.2f}%")
            
        if avg_val_fidelity >= CONFIG['target_accuracy'] * 100:
            print("Target accuracy reached! Stopping training.")
            break

if __name__ == "__main__":
    # Windows requires this guard for multiprocessing
    train_model()