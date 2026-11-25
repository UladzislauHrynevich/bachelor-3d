"""Video upload and frame extraction.

Metadata is stored in files only (no DB tables):
    storage/projects/<project_id>/videos/<video_id>/source.<ext>
    storage/projects/<project_id>/videos/<video_id>/video.json
    storage/projects/<project_id>/videos/<video_id>/frames.json

Extracted frames go to the project's existing input directory and are
registered as ProjectImage rows, so the rest of the pipeline (input ZIP,
worker) sees them like uploaded images.

extract_frames() does not depend on HTTP and can be called from the worker.
"""

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from uuid import UUID

from backend.database.database import SessionLocal
from backend.database.models import ProjectImage
from backend.project_manager import get_project_directory


DEFAULT_FRAME_COUNT = 300
MIN_FRAME_COUNT = 10
MAX_FRAME_COUNT = 2000
MAX_VIDEO_SIZE = 2 * 1024 ** 3  # 2 GB

CHUNK_SIZE = 1024 * 1024  # 1 MB


class VideoTooLargeError(Exception):
    pass


class InvalidVideoError(Exception):
    pass


# ---------------------------------------------------------------- paths

def get_video_directory(project_id, video_id) -> Path:
    return get_project_directory(project_id) / "videos" / str(video_id)


def frame_filename(video_id, frame_index: int) -> str:
    return f"vid_{str(video_id)[:8]}_f{frame_index:06d}.jpg"


# ---------------------------------------------------------------- metadata

def write_json_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def read_video_metadata(project_id, video_id) -> dict | None:
    path = get_video_directory(project_id, video_id) / "video.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def read_frames(project_id, video_id) -> list[dict]:
    """Contents of frames.json, or [] if frames are not extracted yet."""
    path = get_video_directory(project_id, video_id) / "frames.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def update_video_metadata(project_id, video_id, **fields) -> dict:
    metadata = read_video_metadata(project_id, video_id) or {}
    metadata.update(fields)
    write_json_atomic(
        get_video_directory(project_id, video_id) / "video.json", metadata
    )
    return metadata


# ---------------------------------------------------------------- upload

def save_upload_stream(source_file, destination: Path,
                       max_size: int | None = None) -> int:
    """Copy an uploaded file in chunks. Deletes the partial file and raises
    VideoTooLargeError when max_size is exceeded."""
    if max_size is None:
        max_size = MAX_VIDEO_SIZE

    destination.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    try:
        with open(destination, "wb") as out:
            while True:
                chunk = source_file.read(CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_size:
                    raise VideoTooLargeError(
                        f"Video exceeds maximum size of {max_size} bytes"
                    )
                out.write(chunk)
    except Exception:
        if destination.exists():
            destination.unlink()
        raise
    return written


def _parse_rate(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        rate = Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None
    return float(rate) if rate > 0 else None


def probe_video(path: Path) -> dict:
    """Return duration_s, fps, width, height, total_frames of the first
    video stream. Raises InvalidVideoError if there is no video stream."""
    command = [
        "ffprobe", "-v", "error",
        "-count_packets",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=codec_type,width,height,r_frame_rate,avg_frame_rate,"
        "nb_frames,nb_read_packets,duration:format=duration",
        "-of", "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.replace(str(path), path.name).strip()
        raise InvalidVideoError(
            f"ffprobe could not read file: {stderr[-500:]}"
        )

    info = json.loads(result.stdout or "{}")
    streams = [
        s for s in info.get("streams", []) if s.get("codec_type") == "video"
    ]
    if not streams:
        raise InvalidVideoError("File contains no video stream")
    stream = streams[0]

    total_frames = 0
    for key in ("nb_read_packets", "nb_frames"):
        try:
            total_frames = int(stream.get(key))
            break
        except (TypeError, ValueError):
            continue
    if total_frames <= 0:
        raise InvalidVideoError("Video stream contains no frames")

    fps = _parse_rate(stream.get("avg_frame_rate")) or _parse_rate(
        stream.get("r_frame_rate")
    )

    duration = None
    for value in (info.get("format", {}).get("duration"), stream.get("duration")):
        try:
            duration = float(value)
            break
        except (TypeError, ValueError):
            continue
    if fps is None and duration:
        fps = total_frames / duration

    return {
        "duration_s": duration,
        "fps": fps,
        "width": stream.get("width"),
        "height": stream.get("height"),
        "total_frames": total_frames,
    }


def register_video(project_id, video_id, upload_file,
                   requested_frame_count: int) -> dict:
    """Save the uploaded video, probe it and write video.json (status
    'uploaded'). On any error the video directory is removed."""
    video_directory = get_video_directory(project_id, video_id)
    original_filename = upload_file.filename or ""
    suffix = Path(original_filename).suffix.lower()
    if not suffix[1:].isalnum():
        suffix = ".bin"
    source_path = video_directory / f"source{suffix}"

    try:
        size_bytes = save_upload_stream(upload_file.file, source_path)
        probe = probe_video(source_path)

        metadata = {
            "video_id": str(video_id),
            "project_id": str(project_id),
            "original_filename": original_filename,
            "source_file": source_path.name,
            "size_bytes": size_bytes,
            **probe,
            "requested_frame_count": requested_frame_count,
            "extracted_frame_count": 0,
            "status": "uploaded",
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json_atomic(video_directory / "video.json", metadata)
    except Exception:
        shutil.rmtree(video_directory, ignore_errors=True)
        raise

    return metadata


# ---------------------------------------------------------------- extraction

def select_frame_indices(total_frames: int, frame_count: int) -> list[int]:
    """Exactly min(frame_count, total_frames) unique indices spread evenly
    over the whole video (centre of each of n equal segments)."""
    n = min(frame_count, total_frames)
    if n <= 0:
        return []
    # index_i = floor((i + 0.5) * T / n), in exact integer arithmetic.
    # Step T/n >= 1, so indices are strictly increasing (unique).
    return [((2 * i + 1) * total_frames) // (2 * n) for i in range(n)]


def build_select_expression(total_frames: int, count: int) -> str:
    """ffmpeg select expression that picks exactly the frames returned by
    select_frame_indices(total_frames, count).

    C(k) = floor((2*k*N + T - 1) / (2*T)) is the number of selected indices
    smaller than k, so frame k is selected iff C(k+1) > C(k).
    A constant-size formula is used because listing indices as
    eq(n,a)+eq(n,b)+... exceeds ffmpeg's expression parser depth limit
    (fails already at ~100 terms)."""
    n_sel = min(count, total_frames)
    t2 = 2 * total_frames
    c = total_frames - 1
    return (
        f"lt(n\\,{total_frames})*"
        f"gt(floor((2*(n+1)*{n_sel}+{c})/{t2})\\,"
        f"floor((2*n*{n_sel}+{c})/{t2}))"
    )


def _run_ffmpeg_select(source: Path, total_frames: int, count: int,
                       output_directory: Path) -> None:
    select_expr = build_select_expression(total_frames, count)
    command = [
        "ffmpeg", "-v", "error", "-nostdin", "-y",
        "-i", str(source),
        "-map", "0:v:0",
        "-vf", f"select='{select_expr}'",
        "-fps_mode", "passthrough",
        "-q:v", "2",
        str(output_directory / "%06d.jpg"),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)


def extract_frames(project_id, video_id, session_factory=None) -> dict:
    """Extract evenly spaced frames into <project>/input, write frames.json,
    create ProjectImage rows in one transaction. On failure everything is
    rolled back, created frames are deleted and status becomes 'failed'.
    Returns the final video metadata."""
    if session_factory is None:
        session_factory = SessionLocal

    project_id = UUID(str(project_id))
    video_directory = get_video_directory(project_id, video_id)
    input_directory = get_project_directory(project_id) / "input"
    tmp_directory = video_directory / "_frames_tmp"
    moved_frames: list[Path] = []

    metadata = update_video_metadata(
        project_id, video_id, status="extracting", error=None
    )

    try:
        source = video_directory / metadata["source_file"]
        fps = metadata.get("fps")
        indices = select_frame_indices(
            metadata["total_frames"], metadata["requested_frame_count"]
        )

        shutil.rmtree(tmp_directory, ignore_errors=True)
        tmp_directory.mkdir(parents=True)
        _run_ffmpeg_select(
            source, metadata["total_frames"], len(indices), tmp_directory
        )

        produced = sorted(tmp_directory.glob("*.jpg"))
        if len(produced) != len(indices):
            raise RuntimeError(
                f"ffmpeg produced {len(produced)} frames, "
                f"expected {len(indices)}"
            )

        input_directory.mkdir(parents=True, exist_ok=True)
        frames = []
        for path, frame_index in zip(produced, indices):
            destination = input_directory / frame_filename(video_id, frame_index)
            shutil.move(path, destination)
            moved_frames.append(destination)
            frames.append({
                "filename": destination.name,
                "frame_index": frame_index,
                "timestamp_s": round(frame_index / fps, 6) if fps else None,
            })

        with session_factory() as db:
            try:
                for path in moved_frames:
                    db.add(ProjectImage(
                        project_id=project_id,
                        original_name=path.name,
                        storage_path=str(path),
                        size_bytes=path.stat().st_size,
                    ))
                db.commit()
            except Exception:
                db.rollback()
                raise

        write_json_atomic(video_directory / "frames.json", frames)
        return update_video_metadata(
            project_id, video_id,
            status="done", extracted_frame_count=len(frames), error=None,
        )

    except Exception as error:
        for path in moved_frames:
            if path.exists():
                path.unlink()
        if isinstance(error, subprocess.CalledProcessError):
            message = (error.stderr or "").strip()[-2000:] or str(error)
        else:
            message = str(error)
        return update_video_metadata(
            project_id, video_id,
            status="failed", extracted_frame_count=0, error=message,
        )

    finally:
        shutil.rmtree(tmp_directory, ignore_errors=True)
