# experiments/

Результаты экспериментальных прогонов 3DGS. Каждый прогон — отдельная папка
`experiments/<run_id>/`. Содержимое папок прогонов в git не попадает
(см. `.gitignore`), отслеживается только этот README.

## run_id

`<YYYYMMDD>-<scene>-n<num_images>-<short_tag>`, например
`20261115-southbuilding-n100-baseline`.

## Файлы прогона

| Файл | Содержимое |
|---|---|
| `config.json` | Все параметры прогона: сцена, число входных изображений, список train/test кадров (или путь к нему), разрешение, seed, число итераций, гиперпараметры gsplat, параметры COLMAP. |
| `metrics.json` | Результаты: PSNR, SSIM, LPIPS (среднее по held-out видам + по каждому виду), время COLMAP, время обучения, пиковая VRAM, число зарегистрированных камер, число точек COLMAP, число гауссиан, размер модели. |
| `train_log.txt` | Полный лог обучения (stdout/stderr). |
| `env.txt` | Окружение: платформа (Colab/Kaggle), GPU, драйвер/CUDA, версии Python, PyTorch, gsplat, COLMAP, FFmpeg, commit hash репозитория. |

## Пример `metrics.json`

```json
{
  "run_id": "20261115-southbuilding-n100-baseline",
  "test_views": 16,
  "psnr": null,
  "ssim": null,
  "lpips": null,
  "registered_cameras": null,
  "colmap_points": null,
  "num_gaussians": null,
  "colmap_time_s": null,
  "train_time_s": null,
  "peak_vram_mb": null,
  "model_size_mb": null
}
```

## Правила

- Held-out тестовые виды фиксированы для сцены и одинаковы для всех прогонов с разным числом кадров.
- Тестовые кадры не должны быть соседними с тренировочными (нет утечки между соседними кадрами видео).
- Seed, версии ПО и разрешение всегда записываются.
