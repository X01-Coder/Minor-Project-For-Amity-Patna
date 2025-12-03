import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchaudio
import glob
import numpy as np
import matplotlib.pyplot as plt
import itertools
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
    
    # PATHS
    "input_noisy_folder": r"E:\Test Audio Data\Audio Data\Noisy Data", 
    "input_clean_folder": r"E:\Test Audio Data\Audio Data\Noiseless Data", # REQUIRED for Metrics
    "output_folder": r"E:\Test Audio Data\Denoised Results"      
}

# ==========================================
# METRICS & PLOTTING UTILITIES
# ==========================================
def calculate_metrics(pred_wav, target_wav, threshold_db=-40):
    """
    Calculates SNR, Accuracy, Precision, Recall, F1, and Confusion Matrix components.
    """
    eps = 1e-8
    pred_wav = pred_wav.view(-1)
    target_wav = target_wav.view(-1)
    
    # 1. SNR (Signal-to-Noise Ratio)
    noise = target_wav - pred_wav
    signal_power = torch.mean(target_wav ** 2)
    noise_power = torch.mean(noise ** 2)
    snr = 10 * torch.log10((signal_power + eps) / (noise_power + eps))
    
    # 2. Accuracy (1 - Relative Error)
    l1_err = torch.abs(pred_wav - target_wav).mean()
    accuracy = max(0, (1 - (l1_err / (torch.abs(target_wav).mean() + eps))).item()) * 100

    # 3. Precision / Recall / F1 (Spectral Binary Classification)
    # We treat energy > threshold as "1" (Signal) and < threshold as "0" (Silence)
    def to_binary_mask(wav):
        stft = torch.stft(wav.view(1, -1), n_fft=512, hop_length=128, return_complex=True, window=torch.hann_window(512).to(wav.device))
        mag = torch.abs(stft)
        db = 20 * torch.log10(mag + eps)
        # Dynamic threshold based on peak
        peak = db.max()
        mask = db > (peak + threshold_db)
        return mask.float().view(-1)

    pred_mask = to_binary_mask(pred_wav)
    target_mask = to_binary_mask(target_wav)

    tp = (pred_mask * target_mask).sum().item()
    fp = (pred_mask * (1 - target_mask)).sum().item()
    fn = ((1 - pred_mask) * target_mask).sum().item()
    tn = ((1 - pred_mask) * (1 - target_mask)).sum().item()

    precision = tp / (tp + fp + eps)
    recall = tp / (tp + fn + eps)
    f1 = 2 * (precision * recall) / (precision + recall + eps)

    return {
        "SNR": snr.item(),
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1": f1,
        "TP": tp, "FP": fp, "FN": fn, "TN": tn
    }

def save_plots(noisy, denoised, clean, sample_rate, filename, output_dir):
    """Generates a neat report plot for the audio."""
    fig, axs = plt.subplots(3, 2, figsize=(15, 10))
    fig.suptitle(f"Denoising Report: {filename}", fontsize=16)

    # --- Waveforms ---
    time = np.linspace(0, len(noisy)/sample_rate, num=len(noisy))
    
    axs[0, 0].plot(time, noisy, color='tab:red', alpha=0.7)
    axs[0, 0].set_title("Input (Noisy)")
    axs[0, 0].set_ylim(-1, 1)

    axs[1, 0].plot(time, denoised, color='tab:green', alpha=0.9)
    axs[1, 0].set_title("Output (Denoised)")
    axs[1, 0].set_ylim(-1, 1)

    axs[2, 0].plot(time, clean, color='tab:blue', alpha=0.7)
    axs[2, 0].set_title("Ground Truth (Clean)")
    axs[2, 0].set_ylim(-1, 1)

    # --- Spectrograms ---
    def plot_spec(ax, wav, title):
        ax.specgram(wav, NFFT=1024, Fs=sample_rate, noverlap=512, cmap='inferno')
        ax.set_title(title)
        ax.set_ylabel("Frequency (Hz)")

    plot_spec(axs[0, 1], noisy, "Noisy Spectrogram")
    plot_spec(axs[1, 1], denoised, "Denoised Spectrogram")
    plot_spec(axs[2, 1], clean, "Clean Spectrogram")

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    save_path = os.path.join(output_dir, f"report_{filename}.png")
    plt.savefig(save_path)
    plt.close()

def save_confusion_matrix(cm, output_dir, filename="GLOBAL_CONFUSION_MATRIX.png"):
    """
    Plots a Confusion Matrix.
    cm format: [[TN, FP], [FN, TP]]
    """
    plt.figure(figsize=(8, 6))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title("Confusion Matrix (Spectral Classification)")
    plt.colorbar()
    
    classes = ['Noise/Silence', 'Signal']
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    # Normalize for text labels
    cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, f"{cm[i, j]:,}\n({cm_norm[i, j]:.1%})",
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, filename))
    plt.close()

def save_summary_graph(avg_metrics, output_dir):
    """Plots the overall F1, Accuracy, etc."""
    metrics = ['Accuracy', 'Precision', 'Recall', 'F1']
    values = [avg_metrics[m] for m in metrics]
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(metrics, values, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'])
    
    plt.title("Model Evaluation Summary (Average Scores)", fontsize=14)
    plt.ylim(0, 1.1)  # Since these are 0-1 (except Accuracy which is 0-100 usually, handled below)
    
    for bar in bars:
        yval = bar.get_height()
        label = f"{yval:.2f}"
        if yval > 1: # Accuracy case (0-100)
             label = f"{yval:.1f}%"
        plt.text(bar.get_x() + bar.get_width()/2, yval, label, ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    plt.grid(axis='y', alpha=0.3)
    plt.savefig(os.path.join(output_dir, "FINAL_METRICS_SUMMARY.png"))
    plt.close()

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
        self.enc1 = ResidualBlock(1, 32)
        self.pool1 = nn.MaxPool2d(2)
        self.enc2 = ResidualBlock(32, 64)
        self.pool2 = nn.MaxPool2d(2)
        self.enc3 = ResidualBlock(64, 128)
        self.pool3 = nn.MaxPool2d(2)
        self.bottleneck = ResidualBlock(128, 256)
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
# INFERENCE
# ==========================================
def load_model():
    print(f"Loading model from {CONFIG['model_path']}...")
    model = AdvancedResUNet().to(CONFIG['device'])
    state_dict = torch.load(CONFIG['model_path'], map_location=CONFIG['device'])
    model.load_state_dict(state_dict)
    model.eval()
    return model

def make_loud_and_clear(waveform):
    max_val = torch.abs(waveform).max()
    if max_val > 0:
        waveform = waveform / max_val
    return waveform

def denoise_files():
    if not os.path.exists(CONFIG['output_folder']):
        os.makedirs(CONFIG['output_folder'])

    model = load_model()
    mel_scale = torchaudio.transforms.MelScale(n_mels=CONFIG['n_mels'], sample_rate=CONFIG['sample_rate'], n_stft=CONFIG['n_fft'] // 2 + 1).to(CONFIG['device'])
    inverse_mel = torchaudio.transforms.InverseMelScale(n_stft=CONFIG["n_fft"] // 2 + 1, n_mels=CONFIG["n_mels"], sample_rate=CONFIG["sample_rate"]).to(CONFIG['device'])

    files = glob.glob(os.path.join(CONFIG['input_noisy_folder'], "*.wav"))
    print(f"Found {len(files)} files to process.")

    avg_metrics = {"SNR": 0, "Accuracy": 0, "Precision": 0, "Recall": 0, "F1": 0}
    # Accumulate confusion matrix counts globally
    global_cm = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
    
    count = 0

    for file_path in tqdm(files, desc="Processing & Evaluation"):
        filename = os.path.basename(file_path)
        
        # 1. Load Noisy
        noisy_wav, sr = torchaudio.load(file_path)
        if noisy_wav.shape[0] > 1: noisy_wav = torch.mean(noisy_wav, dim=0, keepdim=True)
        if sr != CONFIG["sample_rate"]:
            resampler = torchaudio.transforms.Resample(sr, CONFIG["sample_rate"])
            noisy_wav = resampler(noisy_wav)
        noisy_wav = noisy_wav.to(CONFIG['device'])

        # 2. Load Clean (Ground Truth) for Metrics
        clean_path = os.path.join(CONFIG['input_clean_folder'], filename)
        clean_wav = None
        if os.path.exists(clean_path):
            clean_wav, csr = torchaudio.load(clean_path)
            if clean_wav.shape[0] > 1: clean_wav = torch.mean(clean_wav, dim=0, keepdim=True)
            if csr != CONFIG["sample_rate"]:
                resampler = torchaudio.transforms.Resample(csr, CONFIG["sample_rate"])
                clean_wav = resampler(clean_wav)
            clean_wav = clean_wav.to(CONFIG['device'])
            
            # Sync lengths
            min_len = min(noisy_wav.shape[1], clean_wav.shape[1])
            noisy_wav = noisy_wav[:, :min_len]
            clean_wav = clean_wav[:, :min_len]

        # 3. Process (Phase Aware)
        window = torch.hann_window(CONFIG['n_fft']).to(CONFIG['device'])
        stft_complex = torch.stft(noisy_wav, n_fft=CONFIG['n_fft'], hop_length=CONFIG['hop_length'], window=window, return_complex=True)
        noisy_phase = torch.angle(stft_complex)
        noisy_mag = torch.abs(stft_complex)
        
        noisy_mel = mel_scale(noisy_mag)
        noisy_log_mel = torch.log1p(noisy_mel + 1e-6).unsqueeze(0)

        with torch.no_grad():
            denoised_log_mel = model(noisy_log_mel).squeeze(0)

        denoised_mel = torch.expm1(denoised_log_mel)
        denoised_mel = torch.clamp(denoised_mel, min=0.0)
        pred_mag = inverse_mel(denoised_mel)
        
        complex_pred = pred_mag * torch.exp(1j * noisy_phase)
        rec_waveform = torch.istft(complex_pred, n_fft=CONFIG['n_fft'], hop_length=CONFIG['hop_length'], window=window, length=noisy_wav.shape[-1])
        rec_waveform = make_loud_and_clear(rec_waveform)

        # 4. Metrics & Reporting
        if clean_wav is not None:
            metrics = calculate_metrics(rec_waveform, clean_wav)
            for k in avg_metrics:
                avg_metrics[k] += metrics[k]
            
            # Accumulate CM counts
            global_cm["TP"] += metrics["TP"]
            global_cm["FP"] += metrics["FP"]
            global_cm["FN"] += metrics["FN"]
            global_cm["TN"] += metrics["TN"]
            
            count += 1
            
            # Save visual report
            save_plots(
                noisy_wav.cpu().numpy().flatten(), 
                rec_waveform.cpu().numpy().flatten(), 
                clean_wav.cpu().numpy().flatten(), 
                CONFIG['sample_rate'], 
                filename, 
                CONFIG['output_folder']
            )

        # Save Audio
        torchaudio.save(os.path.join(CONFIG['output_folder'], f"clean_{filename}"), rec_waveform.cpu(), CONFIG["sample_rate"])

    # 5. Final Summary
    if count > 0:
        print("\n--- Final Evaluation Report ---")
        for k in avg_metrics:
            avg_metrics[k] /= count
            print(f"{k}: {avg_metrics[k]:.4f}")
            
        # Plot Global Summary Graph
        save_summary_graph(avg_metrics, CONFIG['output_folder'])
        
        # Plot Global Confusion Matrix
        # Format: [[TN, FP], [FN, TP]]
        cm_array = np.array([
            [global_cm["TN"], global_cm["FP"]], 
            [global_cm["FN"], global_cm["TP"]]
        ])
        save_confusion_matrix(cm_array, CONFIG['output_folder'])
        
        print(f"Summary graphs, Confusion Matrix, and individual file reports saved to {CONFIG['output_folder']}")
    else:
        print("Done. No matching clean files found for metrics calculation.")

if __name__ == "__main__":
    denoise_files()