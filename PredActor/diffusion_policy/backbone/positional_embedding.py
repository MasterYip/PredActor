import math
import torch
import torch.nn as nn

class SinusoidalPosEmb(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, x):
        # x.shape = (B,T)
        half_dim = self.dim // 2
        exponent = math.log(10000) / (half_dim - 1)
        indices = torch.cumsum(
            torch.ones_like(x[0, 0]).expand(half_dim), dim=0
        ) - 1
        frequency = torch.exp(indices * -exponent)
        emb = x[:,:,None]*frequency[None, None, :]
        emb = torch.cat((emb.sin(), emb.cos()), dim=-1)
        return emb
