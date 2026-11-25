"""Referenčná rekonštrukcia COLMAP (pycolmap): SIFT -> exhaustive matching -> incremental mapping.

Parametre: jedna spoločná kamera pre všetky snímky (CameraMode.SINGLE), ostatné predvolené.
Výstup v <out_dir>: database.db, sparse/<i>/ (modely), colmap_run.json (verzie, časy, štatistiky).

Použitie:
    pip install pycolmap
    python gpu/colmap_reference.py <images_dir> <out_dir> [num_threads]
"""
import json
import platform
import sys
import time
from pathlib import Path

import pycolmap


def timed(fn, *args, **kwargs):
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, round(time.perf_counter() - t0, 1)


def main(image_dir: Path, out_dir: Path, num_threads: int = -1):
    out_dir.mkdir(parents=True, exist_ok=True)
    database = out_dir / "database.db"
    sparse = out_dir / "sparse"
    sparse.mkdir(exist_ok=True)
    assert not database.exists(), f"{database} už existuje, použi prázdny výstupný priečinok"
    images = sorted(p.name for p in image_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})

    # počet vlákien neovplyvňuje výsledok, iba rýchlosť a RAM (12 vlákien x plné rozlíšenie ~10 GB)
    extraction = pycolmap.FeatureExtractionOptions(num_threads=num_threads)
    _, t_extract = timed(pycolmap.extract_features, database, image_dir,
                         camera_mode=pycolmap.CameraMode.SINGLE,
                         extraction_options=extraction)
    _, t_match = timed(pycolmap.match_exhaustive, database)
    models, t_map = timed(pycolmap.incremental_mapping, database, image_dir, sparse)

    stats = []
    registered = set()
    for idx, rec in models.items():
        rec.write(sparse / str(idx))
        names = {img.name for img in rec.images.values()}
        registered |= names
        stats.append({
            "model": idx,
            "registered_images": len(names),
            "points3D": rec.num_points3D(),
            "mean_reprojection_error_px": round(rec.compute_mean_reprojection_error(), 4),
            "cameras": len(rec.cameras),
        })
        print(rec.summary())

    result = {
        "python": platform.python_version(),
        "pycolmap": pycolmap.__version__,
        "colmap": getattr(pycolmap, "COLMAP_version", "unknown"),
        "image_dir": str(image_dir),
        "input_images": len(images),
        "camera_mode": "SINGLE",
        "other_parameters": "defaults",
        "extraction_options": extraction.todict(),
        "time_s": {"extract": t_extract, "match": t_match, "map": t_map,
                   "total": round(t_extract + t_match + t_map, 1)},
        "num_models": len(models),
        "models": stats,
        "unregistered_images": sorted(set(images) - registered),
    }
    (out_dir / "colmap_run.json").write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps(result, indent=2, default=str))
    assert models, "COLMAP nevytvoril žiadny model"


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else -1)
