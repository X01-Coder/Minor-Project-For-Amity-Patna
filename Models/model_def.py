# model_def.py
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchaudio

CONFIG = {
    "sample_rate": 16000,
    "n_fft": 1024,
    "hop_length": 256,
    "n_mels": 80,
    "device": "cuda" if torch.cuda.is_available() else "cpu",
}

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


def load_denoiser(model_path: str, device: str = None):
    if device is None:
        device = CONFIG["device"]

    model = AdvancedResUNet().to(device)
    # weights_only=True is safer on new PyTorch versions
    state_dict = torch.load(model_path, map_location=device, weights_only=False)
    model.load_state_dict(state_dict)
    model.eval()
    return model


def build_transforms(device: str = None):
    if device is None:
        device = CONFIG["device"]

    mel = torchaudio.transforms.MelSpectrogram(
        sample_rate=CONFIG["sample_rate"],
        n_fft=CONFIG["n_fft"],
        hop_length=CONFIG["hop_length"],
        n_mels=CONFIG["n_mels"]
    ).to(device)

    inv_mel = torchaudio.transforms.InverseMelScale(
        n_stft=CONFIG["n_fft"] // 2 + 1,
        n_mels=CONFIG["n_mels"],
        sample_rate=CONFIG["sample_rate"]
    ).to(device)

    griffin = torchaudio.transforms.GriffinLim(
        n_fft=CONFIG["n_fft"],
        hop_length=CONFIG["hop_length"]
    ).to(device)

    return mel, inv_mel, griffin
