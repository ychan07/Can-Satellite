import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
import os
import glob
from tqdm import tqdm
import copy
from scipy.signal import resample

# --- 1. 모델 아키텍처 (1D U-Net with Dropout) ---
# (변경 없음)
class ConvBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv1d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm1d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv1d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm1d(out_channels),
            nn.ReLU(inplace=True)
        )
    def forward(self, x):
        return self.block(x)

class UNet1D(nn.Module):
    def __init__(self, in_channels=1, out_channels=1, dropout_rate=0.5):
        super().__init__()
        self.enc1 = ConvBlock(in_channels, 64)
        self.enc2 = ConvBlock(64, 128)
        self.enc3 = ConvBlock(128, 256)
        self.pool = nn.MaxPool1d(2)
        self.bottleneck = nn.Sequential(ConvBlock(256, 512), nn.Dropout(dropout_rate))
        self.upconv3 = nn.ConvTranspose1d(512, 256, kernel_size=2, stride=2)
        self.dec3 = ConvBlock(512, 256)
        self.upconv2 = nn.ConvTranspose1d(256, 128, kernel_size=2, stride=2)
        self.dec2 = ConvBlock(256, 128)
        self.upconv1 = nn.ConvTranspose1d(128, 64, kernel_size=2, stride=2)
        self.dec1 = ConvBlock(128, 64)
        self.out_conv = nn.Conv1d(64, out_channels, kernel_size=1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        b = self.bottleneck(self.pool(e3))
        d3 = self.upconv3(b)
        if d3.shape[2] != e3.shape[2]: d3 = nn.functional.pad(d3, (0, e3.shape[2] - d3.shape[2]))
        d3 = torch.cat([d3, e3], dim=1)
        d3 = self.dec3(d3)
        d2 = self.upconv2(d3)
        if d2.shape[2] != e2.shape[2]: d2 = nn.functional.pad(d2, (0, e2.shape[2] - d2.shape[2]))
        d2 = torch.cat([d2, e2], dim=1)
        d2 = self.dec2(d2)
        d1 = self.upconv1(d2)
        if d1.shape[2] != e1.shape[2]: d1 = nn.functional.pad(d1, (0, e1.shape[2] - d1.shape[2]))
        d1 = torch.cat([d1, e1], dim=1)
        d1 = self.dec1(d1)
        return self.out_conv(d1)

# --- 2. 데이터 로더 (안정성 강화) ---

class SpectraDataset(Dataset):
    def __init__(self, file_paths, target_length=1024):
        self.file_paths = file_paths
        self.num_augmentations = 5
        self.target_length = target_length
        if not self.file_paths:
            raise ValueError("데이터 파일을 찾을 수 없습니다. 경로를 확인하세요.")

    def __len__(self):
        return len(self.file_paths) * self.num_augmentations

    def __getitem__(self, idx):
        try:
            file_idx = idx // self.num_augmentations
            aug_idx = idx % self.num_augmentations
            file_path = self.file_paths[file_idx]
            
            data = pd.read_csv(file_path, sep=r'\s+', header=None, comment='#').values.astype(np.float32)

            # --- 안정성 강화 1: 데이터 유효성 검사 (NaN, Inf 확인) ---
            if not np.isfinite(data).all():
                return None

            if data.shape[1] < 8:
                return None

            target_flux = data[:, 1]
            input_flux = data[:, 3 + aug_idx]

            if len(target_flux) != self.target_length:
                target_flux = resample(target_flux, self.target_length)
                input_flux = resample(input_flux, self.target_length)

            input_tensor = torch.from_numpy(input_flux.copy()).unsqueeze(0)
            target_tensor = torch.from_numpy(target_flux.copy()).unsqueeze(0)
            return input_tensor, target_tensor
        except Exception:
            return None

def collate_fn_skip_none(batch):
    batch = list(filter(lambda x: x is not None, batch))
    if not batch:
        return torch.Tensor(), torch.Tensor()
    return torch.utils.data.dataloader.default_collate(batch)

# --- 3. 학습 파이프라인 (안정성 강화) ---

def train_model(data_dirs, model_save_path, epochs=50, batch_size=16, lr=1e-5, validation_split=0.2, patience=7, target_length=1024):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model = UNet1D(in_channels=1, out_channels=1).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    checkpoint_path = os.path.join(model_save_path, 'checkpoint.pth')
    os.makedirs(model_save_path, exist_ok=True)

    all_files = [p for d in data_dirs for p in glob.glob(os.path.join(d, '*.csv'))]
    if not all_files:
        raise ValueError(f"{data_dirs} 에서 데이터 파일을 찾을 수 없습니다.")
    
    np.random.shuffle(all_files)
    split_idx = int(len(all_files) * (1 - validation_split))
    train_files, val_files = all_files[:split_idx], all_files[split_idx:]
    
    train_dataset = SpectraDataset(train_files, target_length=target_length)
    val_dataset = SpectraDataset(val_files, target_length=target_length)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0, collate_fn=collate_fn_skip_none)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0, collate_fn=collate_fn_skip_none)
    
    print(f"Data loaded: {len(train_dataset)} training samples, {len(val_dataset)} validation samples from {len(all_files)} files.")
    print(f"All spectra will be resampled to a length of {target_length}. Invalid files will be skipped.")

    start_epoch = 0
    best_loss = float('inf')
    epochs_no_improve = 0
    if os.path.exists(checkpoint_path):
        print(f"Resuming training from checkpoint: {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        start_epoch = checkpoint['epoch'] + 1
        best_loss = checkpoint['best_loss']
        epochs_no_improve = checkpoint['epochs_no_improve']
        print(f"Resuming from epoch {start_epoch + 1}")

    print("Starting training...")

    for epoch in range(start_epoch, epochs):
        model.train()
        running_loss = 0.0
        train_progress = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs} [Train]")
        for inputs, targets in train_progress:
            if inputs.nelement() == 0: continue
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            
            # --- 안정성 강화 2: 그래디언트 클리핑 ---
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            optimizer.step()
            running_loss += loss.item()
            train_progress.set_postfix(loss=loss.item())
        train_loss = running_loss / len(train_loader)

        model.eval()
        val_loss = 0.0
        val_progress = tqdm(val_loader, desc=f"Epoch {epoch+1}/{epochs} [Val]")
        with torch.no_grad():
            for inputs, targets in val_progress:
                if inputs.nelement() == 0: continue
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                val_loss += loss.item()
                val_progress.set_postfix(loss=loss.item())
        val_loss /= len(val_loader)
        print(f"Epoch {epoch+1}: Train Loss: {train_loss:.6f}, Val Loss: {val_loss:.6f}")

        is_best = val_loss < best_loss
        if is_best:
            print(f"Validation loss decreased ({best_loss:.6f} --> {val_loss:.6f}). Saving best model...")
            best_loss = val_loss
            epochs_no_improve = 0
            torch.save(model.state_dict(), os.path.join(model_save_path, 'best_model.pth'))
        else:
            epochs_no_improve += 1
            print(f"Validation loss did not improve. Counter: {epochs_no_improve}/{patience}")

        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'best_loss': best_loss,
            'epochs_no_improve': epochs_no_improve
        }, checkpoint_path)

        if epochs_no_improve >= patience:
            print("Early stopping triggered.")
            break
            
    print("Finished Training")
    print(f"Best model saved as 'best_model.pth' in '{model_save_path}' with validation loss {best_loss:.6f}")


if __name__ == '__main__':
    AUGMENTED_DATA_DIRS = [
        r'C:\Users\chan2\Desktop\Can-Satellite\predata\dr3',
        r'C:\Users\chan2\Desktop\Can-Satellite\predata\dr4'
    ]
    MODEL_SAVE_DIR = r'C:\Users\chan2\Desktop\Can-Satellite\trained_models'
    
    NUM_EPOCHS = 100
    BATCH_SIZE = 256
    # --- 안정성 강화 3: 학습률 조정 ---
    LEARNING_RATE = 1e-5
    VALIDATION_SPLIT = 0.2
    EARLY_STOPPING_PATIENCE = 7
    TARGET_LENGTH = 1024

    print("--- Denoising U-Net Trainer with Enhanced Stability ---")
    train_model(
        data_dirs=AUGMENTED_DATA_DIRS,
        model_save_path=MODEL_SAVE_DIR,
        epochs=NUM_EPOCHS,
        batch_size=BATCH_SIZE,
        lr=LEARNING_RATE,
        validation_split=VALIDATION_SPLIT,
        patience=EARLY_STOPPING_PATIENCE,
        target_length=TARGET_LENGTH
    )
