
from pathlib import Path
import zipfile
import json

import httpx


BACKEND_URL = "http://127.0.0.1:8000"
WORKSPACE = Path("worker_data")


def claim_job():
    response = httpx.post(
        f"{BACKEND_URL}/processing-jobs/claim"
    )

    response.raise_for_status()

    print("CLAIM RESPONSE:", response.text)

    return response.json()["job"]


def download_input(project_id: str, destination: Path):
    response = httpx.get(
        f"{BACKEND_URL}/projects/{project_id}/input"
    )

    response.raise_for_status()

    destination.write_bytes(response.content)


def extract_input(archive: Path, destination: Path):
    destination.mkdir(
        parents=True,
        exist_ok=True
    )

    with zipfile.ZipFile(archive, "r") as zip_file:
        zip_file.extractall(destination)


def upload_result(job_id: str, archive_path: Path):
    with archive_path.open("rb") as archive:
        response = httpx.post(
            f"{BACKEND_URL}/processing-jobs/{job_id}/result",
            files={
                "archive": (
                    archive_path.name,
                    archive,
                    "application/zip"
                )
            },
            timeout=120.0
        )

    response.raise_for_status()
    return response.json()


def process_next_job():
    job = claim_job()

    if job is None:
        print("No pending jobs")
        return

    job_id = job["id"]
    project_id = job["project_id"]

    job_directory = WORKSPACE / job_id
    archive_path = job_directory / "input.zip"
    input_directory = job_directory / "input"

    try:
        job_directory.mkdir(parents=True, exist_ok=True)

        print(f"Claimed job: {job_id}")
        print(f"Project: {project_id}")

        download_input(project_id, archive_path)
        extract_input(archive_path, input_directory)

        print("Input downloaded and extracted")

        result_archive = create_test_result(
            input_directory,
            job_directory,
        )

        print(f"Test result created: {result_archive}")

        upload_response = upload_result(job_id, result_archive)
        print(f"Result uploaded: {upload_response}")

        update_job_status(job_id, "complete")
        print(f"Job {job_id} completed successfully")

    except Exception:
        print(f"Job {job_id} failed")

        try:
            update_job_status(job_id, "fail")
        except Exception as status_error:
            print(f"Could not report failure: {status_error}")

        raise


def create_test_result(input_directory: Path, job_directory: Path) -> Path:
    """Temporary pipeline for testing the complete worker workflow."""
    images = sorted(
        p.name for p in input_directory.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )

    if not images:
        raise ValueError("No images found in input directory")

    result_directory = job_directory / "output"
    result_directory.mkdir(parents=True, exist_ok=True)

    metadata = {
        "pipeline": "test",
        "image_count": len(images),
        "images": images,
        "note": "Test result; no 3D reconstruction performed",
    }

    metadata_path = result_directory / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    archive_path = job_directory / "result.zip"

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(metadata_path, arcname="metadata.json")

    return archive_path


def update_job_status(job_id: str, status: str):
    if status not in {"complete", "fail"}:
        raise ValueError(f"Unsupported status action: {status}")

    response = httpx.post(
        f"{BACKEND_URL}/processing-jobs/{job_id}/{status}",
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    process_next_job()
