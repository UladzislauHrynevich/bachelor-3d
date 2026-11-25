import json
import shutil
import subprocess
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.main as main
import backend.routers.projects as projects_router
import backend.services.video_service as video_service
from backend.database.database import Base, get_db
from backend.database.models import Project, ProjectImage


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not installed",
)

TOTAL_FRAMES = 120  # 4 s * 30 fps


@pytest.fixture(scope="module")
def test_video(tmp_path_factory):
    path = tmp_path_factory.mktemp("video") / "test.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=4:size=320x240:rate=30",
            "-pix_fmt", "yuv420p",
            str(path),
        ],
        check=True,
    )
    return path


@pytest.fixture
def api(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    main.app.dependency_overrides[get_db] = override_get_db

    def project_directory(project_id):
        return tmp_path / str(project_id)

    monkeypatch.setattr(video_service, "get_project_directory", project_directory)
    monkeypatch.setattr(projects_router, "get_project_directory", project_directory)
    monkeypatch.setattr(video_service, "SessionLocal", sessionmaker(bind=engine))

    try:
        with TestClient(main.app) as client:
            yield client, engine, tmp_path
    finally:
        main.app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def create_project(engine, tmp_path):
    with Session(engine) as db:
        project = Project()
        db.add(project)
        db.commit()
        project_id = str(project.id)
    (tmp_path / project_id / "input").mkdir(parents=True)
    return project_id


def upload(client, project_id, video_path, frame_count=None,
           filename="clip.mp4"):
    data = {} if frame_count is None else {"frame_count": str(frame_count)}
    with open(video_path, "rb") as file:
        return client.post(
            f"/projects/{project_id}/video",
            files={"video": (filename, file, "video/mp4")},
            data=data,
        )


def read_frames_json(tmp_path, project_id, video_id):
    path = tmp_path / project_id / "videos" / video_id / "frames.json"
    return json.loads(path.read_text())


# ------------------------------------------------------------------ unit

@pytest.mark.parametrize("total,count", [(120, 10), (120, 120), (1000, 300),
                                         (2001, 2000), (37, 10)])
def test_select_frame_indices_unique_and_even(total, count):
    indices = video_service.select_frame_indices(total, count)

    assert len(indices) == count
    assert len(set(indices)) == count
    assert indices == sorted(indices)
    assert 0 <= indices[0] and indices[-1] < total
    gaps = [b - a for a, b in zip(indices, indices[1:])]
    step = total / count
    assert all(abs(gap - step) <= 1 for gap in gaps)


def test_select_frame_indices_caps_at_total():
    assert video_service.select_frame_indices(50, 300) == list(range(50))


# ------------------------------------------------------------------ API

def test_extracts_exact_frame_count(api, test_video):
    client, engine, tmp_path = api
    project_id = create_project(engine, tmp_path)

    response = upload(client, project_id, test_video, frame_count=10)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "uploaded"
    video_id = body["video_id"]

    # TestClient runs BackgroundTasks before returning
    metadata = client.get(f"/projects/{project_id}/videos/{video_id}").json()
    assert metadata["status"] == "done", metadata["error"]
    assert metadata["error"] is None
    assert metadata["total_frames"] == TOTAL_FRAMES
    assert metadata["width"] == 320 and metadata["height"] == 240
    assert metadata["fps"] == pytest.approx(30)
    assert metadata["duration_s"] == pytest.approx(4, abs=0.1)
    assert metadata["requested_frame_count"] == 10
    assert metadata["extracted_frame_count"] == 10
    assert metadata["original_filename"] == "clip.mp4"
    assert metadata["size_bytes"] == test_video.stat().st_size

    video_directory = tmp_path / project_id / "videos" / video_id
    assert (video_directory / "source.mp4").exists()

    frames = read_frames_json(tmp_path, project_id, video_id)
    indices = [f["frame_index"] for f in frames]
    assert indices == video_service.select_frame_indices(TOTAL_FRAMES, 10)
    assert len(set(indices)) == 10
    assert all(b - a == 12 for a, b in zip(indices, indices[1:]))
    for frame in frames:
        assert frame["timestamp_s"] == pytest.approx(frame["frame_index"] / 30)

    input_directory = tmp_path / project_id / "input"
    files = sorted(p.name for p in input_directory.iterdir())
    assert files == sorted(f["filename"] for f in frames)
    assert files[0] == f"vid_{video_id[:8]}_f{indices[0]:06d}.jpg"
    with Image.open(input_directory / files[0]) as image:
        assert image.size == (320, 240)  # no resize

    with Session(engine) as db:
        rows = db.scalars(select(ProjectImage)).all()
    assert len(rows) == 10
    assert sorted(r.original_name for r in rows) == files
    assert all(r.size_bytes > 0 for r in rows)


def test_frame_count_above_total_extracts_all(api, test_video):
    client, engine, tmp_path = api
    project_id = create_project(engine, tmp_path)

    video_id = upload(client, project_id, test_video, frame_count=500).json()["video_id"]

    metadata = client.get(f"/projects/{project_id}/videos/{video_id}").json()
    assert metadata["status"] == "done", metadata["error"]
    assert metadata["extracted_frame_count"] == TOTAL_FRAMES

    frames = read_frames_json(tmp_path, project_id, video_id)
    assert [f["frame_index"] for f in frames] == list(range(TOTAL_FRAMES))


def test_default_frame_count(api, test_video):
    client, engine, tmp_path = api
    project_id = create_project(engine, tmp_path)

    video_id = upload(client, project_id, test_video).json()["video_id"]

    metadata = client.get(f"/projects/{project_id}/videos/{video_id}").json()
    assert metadata["requested_frame_count"] == video_service.DEFAULT_FRAME_COUNT
    assert metadata["extracted_frame_count"] == TOTAL_FRAMES


def test_not_a_video_returns_400(api, tmp_path):
    client, engine, _ = api
    project_id = create_project(engine, tmp_path)

    fake = tmp_path / "fake.mp4"
    fake.write_text("this is not a video")

    response = upload(client, project_id, fake, frame_count=10)

    assert response.status_code == 400
    videos_directory = tmp_path / project_id / "videos"
    assert not videos_directory.exists() or not any(videos_directory.iterdir())


def test_image_without_video_stream_returns_400(api, tmp_path):
    client, engine, _ = api
    project_id = create_project(engine, tmp_path)

    audio = tmp_path / "audio.wav"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "sine=duration=1", str(audio)],
        check=True,
    )

    response = upload(client, project_id, audio, frame_count=10,
                      filename="audio.wav")

    assert response.status_code == 400
    assert "no video stream" in response.json()["detail"]


@pytest.mark.parametrize("frame_count", [0, 9, 2001, 5000])
def test_frame_count_out_of_range_returns_422(api, test_video, frame_count):
    client, engine, tmp_path = api
    project_id = create_project(engine, tmp_path)

    response = upload(client, project_id, test_video, frame_count=frame_count)

    assert response.status_code == 422
    assert not (tmp_path / project_id / "videos").exists()


def test_too_large_returns_413_and_removes_file(api, test_video, monkeypatch):
    client, engine, tmp_path = api
    project_id = create_project(engine, tmp_path)
    monkeypatch.setattr(video_service, "MAX_VIDEO_SIZE", 1000)

    response = upload(client, project_id, test_video, frame_count=10)

    assert response.status_code == 413
    videos_directory = tmp_path / project_id / "videos"
    assert not any(videos_directory.rglob("source.*"))


def test_unknown_project_returns_404(api, test_video):
    client, _, _ = api

    response = upload(client, uuid4(), test_video, frame_count=10)

    assert response.status_code == 404


def test_unknown_video_returns_404(api, tmp_path):
    client, engine, _ = api
    project_id = create_project(engine, tmp_path)

    response = client.get(f"/projects/{project_id}/videos/{uuid4()}")

    assert response.status_code == 404


def test_frames_included_in_input_zip(api, test_video):
    client, engine, tmp_path = api
    project_id = create_project(engine, tmp_path)

    video_id = upload(client, project_id, test_video, frame_count=10).json()["video_id"]
    frames = read_frames_json(tmp_path, project_id, video_id)

    response = client.get(f"/projects/{project_id}/input")

    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as archive:
        names = set(archive.namelist())
    assert {f["filename"] for f in frames} <= names


def test_ffmpeg_failure_rolls_back(api, test_video, monkeypatch):
    client, engine, tmp_path = api
    project_id = create_project(engine, tmp_path)

    def broken_session_factory():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(video_service, "SessionLocal", broken_session_factory)

    video_id = upload(client, project_id, test_video, frame_count=10).json()["video_id"]

    metadata = client.get(f"/projects/{project_id}/videos/{video_id}").json()
    assert metadata["status"] == "failed"
    assert "db unavailable" in metadata["error"]
    assert metadata["extracted_frame_count"] == 0
    assert list((tmp_path / project_id / "input").iterdir()) == []
    with Session(engine) as db:
        assert db.scalars(select(ProjectImage)).all() == []


def test_extracted_frames_are_the_selected_frames(api, test_video, tmp_path):
    """Compare extracted JPEGs with frames decoded directly by index."""
    client, engine, _ = api
    project_id = create_project(engine, tmp_path)

    video_id = upload(client, project_id, test_video, frame_count=10).json()["video_id"]
    frames = read_frames_json(tmp_path, project_id, video_id)
    input_directory = tmp_path / project_id / "input"

    for frame in (frames[0], frames[5], frames[-1]):
        reference = tmp_path / f"ref_{frame['frame_index']}.jpg"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(test_video),
             "-vf", f"select=eq(n\\,{frame['frame_index']})",
             "-fps_mode", "passthrough", "-frames:v", "1", "-q:v", "2",
             str(reference)],
            check=True,
        )
        with Image.open(reference) as ref, \
                Image.open(input_directory / frame["filename"]) as got:
            assert ref.tobytes() == got.tobytes()


def test_max_frame_count_2000(api, tmp_path):
    client, engine, _ = api
    project_id = create_project(engine, tmp_path)

    long_video = tmp_path / "long.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc=duration=70:size=64x48:rate=30",
         "-pix_fmt", "yuv420p", str(long_video)],
        check=True,
    )

    video_id = upload(client, project_id, long_video, frame_count=2000).json()["video_id"]

    metadata = client.get(f"/projects/{project_id}/videos/{video_id}").json()
    assert metadata["status"] == "done", metadata["error"]
    assert metadata["total_frames"] == 2100
    assert metadata["extracted_frame_count"] == 2000

    frames = read_frames_json(tmp_path, project_id, video_id)
    indices = [f["frame_index"] for f in frames]
    assert indices == video_service.select_frame_indices(2100, 2000)
    assert len(set(indices)) == 2000
    assert len(list((tmp_path / project_id / "input").iterdir())) == 2000


# ------------------------------------------------------------------ frames API

def upload_done(client, project_id, video_path, frame_count=10):
    video_id = upload(client, project_id, video_path, frame_count).json()["video_id"]
    status = client.get(f"/projects/{project_id}/videos/{video_id}").json()["status"]
    assert status == "done"
    return video_id


def test_list_frames(api, test_video):
    client, engine, tmp_path = api
    project_id = create_project(engine, tmp_path)
    video_id = upload_done(client, project_id, test_video)

    response = client.get(f"/projects/{project_id}/videos/{video_id}/frames")

    assert response.status_code == 200
    assert response.json() == read_frames_json(tmp_path, project_id, video_id)
    assert len(response.json()) == 10


def test_list_frames_unknown_video_404(api, tmp_path):
    client, engine, _ = api
    project_id = create_project(engine, tmp_path)

    response = client.get(f"/projects/{project_id}/videos/{uuid4()}/frames")

    assert response.status_code == 404


def test_list_frames_unknown_project_404(api):
    client, _, _ = api

    response = client.get(f"/projects/{uuid4()}/videos/{uuid4()}/frames")

    assert response.status_code == 404


def test_get_frame_file(api, test_video):
    client, engine, tmp_path = api
    project_id = create_project(engine, tmp_path)
    video_id = upload_done(client, project_id, test_video)
    filename = read_frames_json(tmp_path, project_id, video_id)[3]["filename"]

    response = client.get(
        f"/projects/{project_id}/videos/{video_id}/frames/{filename}"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == (tmp_path / project_id / "input" / filename).read_bytes()


@pytest.mark.parametrize("filename", [
    "..%2Fvideos",
    "..%2F..%2Fvideo.json",
    "%2E%2E%2F%2E%2E%2Fvideo.json",
    "%2E%2E",               # ".." (literal ".." is normalised away by the client)
    "%2Fetc%2Fpasswd",
    "..%5C..%5Cvideo.json",
    "other.jpg",            # exists in input/, but not a frame of this video
    "vid_00000000_f000000.jpg",
])
def test_get_frame_rejects_unlisted_and_traversal(api, test_video, filename):
    client, engine, tmp_path = api
    project_id = create_project(engine, tmp_path)
    video_id = upload_done(client, project_id, test_video)
    (tmp_path / project_id / "input" / "other.jpg").write_bytes(b"not a frame")

    response = client.get(
        f"/projects/{project_id}/videos/{video_id}/frames/{filename}"
    )

    assert response.status_code == 404
    assert b"not a frame" not in response.content
    assert b'"video_id"' not in response.content


def test_get_frame_rejects_traversal_even_if_listed(api, test_video):
    """Defence in depth: a tampered frames.json must not allow escaping input/."""
    client, engine, tmp_path = api
    project_id = create_project(engine, tmp_path)
    video_id = upload_done(client, project_id, test_video)

    frames_path = tmp_path / project_id / "videos" / video_id / "frames.json"
    frames = json.loads(frames_path.read_text())
    frames.append({"filename": "../videos", "frame_index": 0, "timestamp_s": 0})
    frames_path.write_text(json.dumps(frames))

    response = client.get(
        f"/projects/{project_id}/videos/{video_id}/frames/..%2Fvideos"
    )

    assert response.status_code == 404


def test_ui_is_served(api):
    client, _, _ = api

    response = client.get("/ui/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Запустить обработку" in response.text
