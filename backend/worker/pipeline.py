from pathlib import Path
import subprocess
import time


def run_command(command: list[str]):
    print()
    print("=" * 80)
    print("Running:")
    print(" ".join(command))
    print("=" * 80)

    subprocess.run(
        command,
        check=True,
    )


def run_colmap(
    input_directory: Path,
    output_directory: Path,
):
    database_path = output_directory / "database.db"
    sparse_directory = output_directory / "sparse"

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    sparse_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("Starting COLMAP")
    print(f"Images: {input_directory}")
    print(f"Output: {output_directory}")

    start_time = time.perf_counter()

    # 1. Extract local image features
    run_command([
        "colmap",
        "feature_extractor",
        "--database_path",
        str(database_path),
        "--image_path",
        str(input_directory),
        "--SiftExtraction.use_gpu",
        "0",
    ])

    # 2. Find matches between images
    run_command([
        "colmap",
        "exhaustive_matcher",
        "--database_path",
        str(database_path),
        "--SiftMatching.use_gpu",
        "0",
    ])

    # 3. Sparse 3D reconstruction
    run_command([
        "colmap",
        "mapper",
        "--database_path",
        str(database_path),
        "--image_path",
        str(input_directory),
        "--output_path",
        str(sparse_directory),
    ])

    elapsed = time.perf_counter() - start_time

    print()
    print("=" * 80)
    print("COLMAP finished")
    print(f"Time: {elapsed:.2f} seconds")
    print(f"Result: {sparse_directory}")
    print("=" * 80)

    return sparse_directory


def run_pipeline(
    input_directory: Path,
    job_directory: Path,
):
    print()
    print("Starting processing pipeline")

    colmap_directory = job_directory / "colmap"

    sparse_directory = run_colmap(
        input_directory=input_directory,
        output_directory=colmap_directory,
    )

    return {
        "colmap_sparse": sparse_directory,
    }