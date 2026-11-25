"""Smoke test gsplat na GPU: rasterizácia + backward + 200 krokov optimalizácie.

Spustenie v Colab (Runtime -> GPU):
    !git clone https://github.com/UladzislauHrynevich/bachelor-3d.git && cd bachelor-3d
    !pip install gsplat==1.5.3
    !MAX_JOBS=4 python gpu/smoke_test.py 2>&1 | tee smoke.log

Prvé volanie rasterization() kompiluje CUDA jadrá (niekoľko minút).
MAX_JOBS obmedzuje paralelnú kompiláciu: predtým build padal s kódom 137 (nedostatok RAM).

Princíp podľa príkladu gsplat examples/image_fitting.py: náhodné gaussiány
sa optimalizujú tak, aby ich vykreslenie zodpovedalo pevnému cieľovému obrázku.
Ak loss klesá, funguje rasterizácia aj spätné šírenie gradientu na CUDA.
"""
import json
import math
import platform
import time

import torch
import torch.nn.functional as F

import gsplat
from gsplat import rasterization

STEPS = 200
N = 5000           # počet gaussiánov
H = W = 256        # rozlíšenie obrázka
SEED = 0


def make_target(device):
    """Plynulý farebný prechod + žltý štvorec v strede, hodnoty 0..1."""
    ys, xs = torch.meshgrid(torch.linspace(0, 1, H), torch.linspace(0, 1, W), indexing="ij")
    target = torch.stack([xs, ys, 1 - xs], dim=-1)
    target[H // 4:3 * H // 4, W // 4:3 * W // 4] = torch.tensor([1.0, 0.8, 0.0])
    return target.to(device)


def main():
    assert torch.cuda.is_available(), "CUDA GPU nie je dostupná"
    torch.manual_seed(SEED)
    device = "cuda"
    target = make_target(device)

    # Kamera v počiatku pozerá v smere +z; f = W, takže x/z = ±0.5 pokrýva celý obraz.
    f = float(W)
    Ks = torch.tensor([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]], device=device)[None]
    viewmats = torch.eye(4, device=device)[None]

    means = torch.empty(N, 3, device=device)
    means[:, :2].uniform_(-1, 1)
    means[:, 2].uniform_(2, 3)
    params = {
        "means": means,
        "log_scales": torch.full((N, 3), math.log(0.03), device=device),
        "quats": torch.randn(N, 4, device=device),
        "opacity_logits": torch.zeros(N, device=device),
        "color_logits": torch.randn(N, 3, device=device),
    }
    for p in params.values():
        p.requires_grad_(True)
    optimizer = torch.optim.Adam(params.values(), lr=0.01)

    def render():
        image, _, _ = rasterization(
            params["means"],
            F.normalize(params["quats"], dim=-1),
            torch.exp(params["log_scales"]),
            torch.sigmoid(params["opacity_logits"]),
            torch.sigmoid(params["color_logits"]),
            viewmats, Ks, W, H,
        )
        return image[0]  # [H, W, 3]

    losses = []
    torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    for step in range(STEPS):
        loss = F.mse_loss(render(), target)
        optimizer.zero_grad()
        loss.backward()
        if step == 0:
            torch.cuda.synchronize()
            first_step_s = time.perf_counter() - t0  # vrátane kompilácie CUDA
            grads_ok = all(p.grad is not None and torch.isfinite(p.grad).all() for p in params.values())
            means_grad_nonzero = bool(params["means"].grad.abs().sum() > 0)
            t1 = time.perf_counter()
        optimizer.step()
        losses.append(loss.item())
    torch.cuda.synchronize()
    step_ms = (time.perf_counter() - t1) / (STEPS - 1) * 1000

    result = {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "gsplat": gsplat.__version__,
        "gpu": torch.cuda.get_device_name(0),
        "steps": STEPS,
        "num_gaussians": N,
        "resolution": [W, H],
        "seed": SEED,
        "first_step_s": round(first_step_s, 2),
        "step_ms": round(step_ms, 2),
        "peak_vram_mb": round(torch.cuda.max_memory_allocated() / 2**20, 1),
        "grads_finite": grads_ok,
        "means_grad_nonzero": means_grad_nonzero,
        "loss_first": round(losses[0], 5),
        "loss_last": round(losses[-1], 5),
        "psnr_last_db": round(-10 * math.log10(losses[-1]), 2),
    }
    result["passed"] = grads_ok and means_grad_nonzero and losses[-1] < 0.5 * losses[0]
    print(json.dumps(result, indent=2))
    assert result["passed"], "smoke test zlyhal, pozri hodnoty vyššie"


if __name__ == "__main__":
    main()
