from pathlib import Path
import zipfile

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

    job_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    print(f"Claimed job: {job_id}")
    print(f"Project: {project_id}")

    download_input(
        project_id,
        archive_path
    )

    print(f"Input downloaded: {archive_path}")

    extract_input(
        archive_path,
        input_directory
    )

    print(f"Input extracted: {input_directory}")

    images = list(input_directory.iterdir())

    print(f"Files received: {len(images)}")


if __name__ == "__main__":
    process_next_job()