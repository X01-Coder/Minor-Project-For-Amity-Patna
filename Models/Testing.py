import os
import glob
import random

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchaudio

from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np

# ==========================================
# CONFIGURATION
# ==========================================
CONFIG = {
    "sample_rate": 16000,
    "n_fft": 1024,
    "hop_length": 256,
    "n_mels": 80,

    "batch_size": 32,
    "num_workers": 6,
    "device": "cuda" if torch.cuda.is_available() else "cpu",

    # paths
    "data_root": r"E:\Minor-Project-For-Amity-Patna\Models\Audio Data",
    "noisy_folder": "Noisy Data",
    "clean_folder": "Noiseless Data",
    "model_path": r"E:\Minor-Project-For-Amity-Patna\Models\best_denoiser_model.pth",

    # threshold for turning spectrogram into 0/1 for classification-style metrics
    "energy_threshold": 0.1,
}


# ==========================================
# DATASET (same as training)
# ==========================================
class AudioDenoisingDataset(Dataset):
    def __init__(self, file_pairs, config):
        self.file_pairs = file_pairs
        self.config = config

    def __len__(self):
        return len(self.file_pairs)

    def load_audio(self, path):
        waveform, sr = torchaudio.load(path)

        # mono
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # resample if needed
        if sr != self.config["sample_rate"]:
            resampler = torchaudio.transforms.Resample(sr, self.config["sample_rate"])
            waveform = resampler(waveform)

        return waveform

    def __getitem__(self, idx):
        noisy_path, clean_path = self.file_pairs[idx]

        noisy_wav = self.load_audio(noisy_path)
        clean_wav = self.load_audio(clean_path)

        # sync length
        min_len = min(noisy_wav.shape[1], clean_wav.shape[1])
        noisy_wav = noisy_wav[:, :min_len]
        clean_wav = clean_wav[:, :min_len]

        # pad or crop to fixed length
        max_len = 32000  # ~2s @16kHz
        if min_len < max_len:
            pad_amount = max_len - min_len
            noisy_wav = F.pad(noisy_wav, (0, pad_amount))
            clean_wav = F.pad(clean_wav, (0, pad_amount))
        else:
            start = random.randint(0, min_len - max_len)
            noisy_wav = noisy_wav[:, start:start + max_len]
            clean_wav = clean_wav[:, start:start + max_len]

        return noisy_wav, clean_wav


# ==========================================
# MODEL (same as training)
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
        # encoder
        self.enc1 = ResidualBlock(1, 32)
        self.pool1 = nn.MaxPool2d(2)
        self.enc2 = ResidualBlock(32, 64)
        self.pool2 = nn.MaxPool2d(2)
        self.enc3 = ResidualBlock(64, 128)
        self.pool3 = nn.MaxPool2d(2)

        # bottleneck
        self.bottleneck = ResidualBlock(128, 256)

        # decoder
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
# UTILITIES
# ==========================================
def get_file_pairs(config):
    noisy_dir = os.path.join(config["data_root"], config["noisy_folder"])
    clean_dir = os.path.join(config["data_root"], config["clean_folder"])

    if not os.path.exists(noisy_dir) or not os.path.exists(clean_dir):
        print(f"[ERROR] Data folders not found under: {config['data_root']}")
        return []

    noisy_files = sorted(glob.glob(os.path.join(noisy_dir, "*.wav")))
    clean_files = sorted(glob.glob(os.path.join(clean_dir, "*.wav")))

    clean_map = {os.path.basename(f): f for f in clean_files}

    pairs = []
    for nf in noisy_files:
        fname = os.path.basename(nf)
        if fname in clean_map:
            pairs.append((nf, clean_map[fname]))

    print(f"[TEST] Found {len(pairs)} matched audio pairs.")
    return pairs


# ==========================================
# TESTING FUNCTION
# ==========================================
def test_model():
    device = CONFIG["device"]
    print(f"Testing on device: {device}")

    # 1. Collect pairs
    all_pairs = get_file_pairs(CONFIG)
    if len(all_pairs) == 0:
        return

    test_dataset = AudioDenoisingDataset(all_pairs, CONFIG)
    test_loader = DataLoader(
        test_dataset,
        batch_size=CONFIG["batch_size"],
        shuffle=False,
        num_workers=CONFIG["num_workers"],
        pin_memory=True,
        persistent_workers=CONFIG["num_workers"] > 0,
    )

    # 2. Load model
    model = AdvancedResUNet().to(device)
    state_dict = torch.load(CONFIG["model_path"], map_location=device)
    model.load_state_dict(state_dict)
    model.eval()
    print(f"Loaded model from: {CONFIG['model_path']}")

    # 3. Spectrogram transform
    mel_transform = torchaudio.transforms.MelSpectrogram(
        sample_rate=CONFIG["sample_rate"],
        n_fft=CONFIG["n_fft"],
        hop_length=CONFIG["hop_length"],
        n_mels=CONFIG["n_mels"],
    ).to(device)

    # 4. Metrics accumulators
    mse_list = []  # batch-wise mse for plotting

    total_mae = 0.0
    total_mse = 0.0
    num_batches = 0

    # confusion matrix components
    tp = tn = fp = fn = 0
    threshold = CONFIG["energy_threshold"]

    loop = tqdm(test_loader, desc="[Testing]")
    with torch.no_grad():
        for noisy_wav, clean_wav in loop:
            noisy_wav = noisy_wav.to(device, non_blocking=True)
            clean_wav = clean_wav.to(device, non_blocking=True)

            # spectrograms
            noisy_spec = mel_transform(noisy_wav)
            clean_spec = mel_transform(clean_wav)

            noisy_spec = torch.log1p(noisy_spec + 1e-6)
            clean_spec = torch.log1p(clean_spec + 1e-6)

            # safety: match time dimension
            if noisy_spec.shape[-1] != clean_spec.shape[-1]:
                min_w = min(noisy_spec.shape[-1], clean_spec.shape[-1])
                noisy_spec = noisy_spec[..., :min_w]
                clean_spec = clean_spec[..., :min_w]

            # forward model
            pred_spec = model(noisy_spec)

            # regression metrics
            batch_mse = F.mse_loss(pred_spec, clean_spec, reduction="mean").item()
            batch_mae = F.l1_loss(pred_spec, clean_spec, reduction="mean").item()

            mse_list.append(batch_mse)
            total_mse += batch_mse
            total_mae += batch_mae
            num_batches += 1

            loop.set_postfix(mse=batch_mse)

            # --- classification-style metrics via thresholding spectrogram energy ---
            # binarize: energy > threshold => 1 (speech/foreground), else 0 (background)
            clean_bin = (clean_spec > threshold).int()
            pred_bin = (pred_spec > threshold).int()

            # compute confusion matrix components
            tp += ((clean_bin == 1) & (pred_bin == 1)).sum().item()
            tn += ((clean_bin == 0) & (pred_bin == 0)).sum().item()
            fp += ((clean_bin == 0) & (pred_bin == 1)).sum().item()
            fn += ((clean_bin == 1) & (pred_bin == 0)).sum().item()

    # 5. Final metrics
    eps = 1e-8
    avg_mse = total_mse / max(num_batches, 1)
    avg_mae = total_mae / max(num_batches, 1)

    total = tp + tn + fp + fn
    accuracy = (tp + tn) / max(total, 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, eps)

    # confusion matrix as 2x2
    cm = np.array([[tn, fp],
                   [fn, tp]])

    # 6. Print report
    print("\n===== TEST REPORT =====")
    print(f"Avg MSE: {avg_mse:.6f}")
    print(f"Avg MAE: {avg_mae:.6f}")
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-score:  {f1:.4f}")
    print("\nConfusion Matrix (rows=true, cols=pred):")
    print("          Pred 0    Pred 1")
    print(f"True 0:   {tn:8d} {fp:8d}")
    print(f"True 1:   {fn:8d} {tp:8d}")
    print("========================\n")

    # 7. PLOTS
    # (A) Confusion matrix heatmap
    fig, ax = plt.subplots()
    im = ax.imshow(cm, interpolation="nearest")
    ax.set_title("Confusion Matrix")
    plt.colorbar(im, ax=ax)
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["Pred 0", "Pred 1"])
    ax.set_yticklabels(["True 0", "True 1"])

    # annotate cells
    for i in range(2):
        for j in range(2):
            ax.text(
                j, i, cm[i, j],
                ha="center", va="center", color="white" if cm[i, j] > cm.max() / 2 else "black"
            )
    plt.tight_layout()

    # (B) Metrics bar chart
    fig2, ax2 = plt.subplots()
    metrics_names = ["Accuracy", "Precision", "Recall", "F1"]
    metrics_vals = [accuracy, precision, recall, f1]
    ax2.bar(metrics_names, metrics_vals)
    ax2.set_ylim(0.0, 1.0)
    ax2.set_title("Classification Metrics")
    for i, v in enumerate(metrics_vals):
        ax2.text(i, v + 0.01, f"{v:.2f}", ha="center")
    plt.tight_layout()

    # (C) MSE over batches
    fig3, ax3 = plt.subplots()
    ax3.plot(mse_list)
    ax3.set_title("Batch-wise MSE")
    ax3.set_xlabel("Batch index")
    ax3.set_ylabel("MSE")
    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    test_model()
