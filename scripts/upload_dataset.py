from pathlib import Path

import httpx


BACKEND_URL = "http://127.0.0.1:8000"
PROJECT_ID = "33bada16-1eee-49a7-b59f-9ad54612286c"

DATASET = Path(
    "/home/vlad/imagesSTU/south-building/images"
)

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
}


def find_images():
    return sorted(
        path
        for path in DATASET.iterdir()
        if path.is_file()
        and path.suffix.lower() in ALLOWED_EXTENSIONS
    )


def upload_image(image_path: Path):
    url = (
        f"{BACKEND_URL}/projects/"
        f"{PROJECT_ID}/images"
    )

    with image_path.open("rb") as image_file:
        response = httpx.post(
            url,
            files={
                "images": (
                    image_path.name,
                    image_file,
                    "application/octet-stream",
                )
            },
            timeout=120.0,
        )

    response.raise_for_status()
    return response.json()


def main():
    images = find_images()

    print(f"Dataset: {DATASET}")
    print(f"Found {len(images)} images")

    if not images:
        raise RuntimeError("No images found")

    failed = []

    for number, image_path in enumerate(images, start=1):
        try:
            upload_image(image_path)

            print(
                f"[{number}/{len(images)}] "
                f"Uploaded: {image_path.name}"
            )

        except Exception as error:
            failed.append(image_path.name)

            print(
                f"[{number}/{len(images)}] "
                f"FAILED: {image_path.name}"
            )
            print(error)

    print()
    print("Upload finished")
    print(f"Successful: {len(images) - len(failed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("Failed files:")
        for filename in failed:
            print(f"  - {filename}")


if __name__ == "__main__":
    main()