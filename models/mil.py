import torch
import torchvision
import torch.nn as nn
from models.Attention import CrissCrossAttention


class Conv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super(Conv, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.conv(x)


class MIL(nn.Module):
    def __init__(self, w=(0.2, 0.35, 0.45), R=2):
        super(MIL, self).__init__()
        self.stage1 = nn.Sequential(
            Conv(3, 64),
            Conv(64, 64)
        )
        self.stage2 = nn.Sequential(
            Conv(64, 128),
            Conv(128, 128)
        )
        self.stage3 = nn.Sequential(
            Conv(128, 256),
            Conv(256, 256),
            Conv(256, 256)
        )

        self.pool = nn.MaxPool2d(2, 2)
        
        self.cca1 = CrissCrossAttention(64)
        self.cca2 = CrissCrossAttention(128)
        self.cca3 = CrissCrossAttention(256)

        self.decoder1 = nn.Sequential(
            nn.Conv2d(64, 4, 1),
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=True),
            nn.Sigmoid()
        )
        self.decoder2 = nn.Sequential(
            nn.Conv2d(128, 4, 1),
            nn.Upsample(scale_factor=4, mode="bilinear", align_corners=True),
            nn.Sigmoid()
        )
        self.decoder3 = nn.Sequential(
            nn.Conv2d(256, 4, 1),
            nn.Upsample(scale_factor=8, mode="bilinear", align_corners=True),
            nn.Sigmoid()
        )

        self.w = w
        self.R = R
    
    def pretrain(self):
        model_pre = torchvision.models.vgg16(pretrained=True)
        self.stage1[0].conv[0] = model_pre.features[0]
        self.stage1[1].conv[0] = model_pre.features[2]
        self.stage2[0].conv[0] = model_pre.features[5]
        self.stage2[1].conv[0] = model_pre.features[7]
        self.stage3[0].conv[0] = model_pre.features[10]
        self.stage3[1].conv[0] = model_pre.features[12]
        self.stage3[2].conv[0] = model_pre.features[14]

    def forward(self, x):
        x = self.stage1(x)
        for i in range(self.R):
            x = self.cca1(x)
        x = self.pool(x)
        x1 = x

        x = self.stage2(x)
        for i in range(self.R):
            x = self.cca2(x)
        x = self.pool(x)
        x2 = x

        x = self.stage3(x)
        for i in range(self.R):
            x = self.cca3(x)
        x = self.pool(x)
        x3 = x


        x1 = self.decoder1(x1)
        x2 = self.decoder2(x2)
        x3 = self.decoder3(x3)


        x = self.w[0] * x1 + self.w[1] * x2 + self.w[2] * x3

        return x, x1, x2, x3



