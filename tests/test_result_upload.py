
from pathlib import Path
from unittest.mock import Mock

from backend.worker.worker import upload_result


def test_upload_result(tmp_path, monkeypatch):
    archive_path = tmp_path / "result.zip"
    archive_path.write_bytes(b"test archive content")

    response = Mock()
    response.json.return_value = {
        "job_id": "test-job",
        "status": "uploaded",
        "filename": "result.zip",
    }

    def fake_post(url, files, timeout):
        assert url.endswith(
            "/processing-jobs/test-job/result"
        )
        assert files["archive"][0] == "result.zip"
        assert files["archive"][1].read() == b"test archive content"
        return response

    monkeypatch.setattr(
        "backend.worker.worker.httpx.post",
        fake_post
    )

    result = upload_result("test-job", archive_path)

    response.raise_for_status.assert_called_once()
    assert result["status"] == "uploaded"
