"""Submission upload, ownership, and quota."""
import io
import zipfile

import pytest

from app.tests.conftest import auth_header


def make_zip(members=(("app.py", "print(1)"),)):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in members:
            z.writestr(name, content)
    buf.seek(0)
    return buf


def upload(client, token, display_name="My Project", zbuf=None):
    return client.post(
        "/api/v1/submissions",
        data={"display_name": display_name},
        files={"file": ("project.zip", zbuf or make_zip(), "application/zip")},
        headers=auth_header(token),
    )


def test_upload_creates_a_submission(client, user_token):
    r = upload(client, user_token)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["display_name"] == "My Project"
    assert body["file_count"] == 1


def test_display_name_never_reaches_the_filesystem(client, user_token, db_session):
    """Regression: the old service joined the form field into the path."""
    from app.models.submission import Submission

    r = upload(client, user_token, display_name="../../etc/passwd")
    assert r.status_code == 201, r.text

    submission = db_session.query(Submission).first()
    # The directory is named after the UUID; the label is stored as data only.
    assert str(submission.id) in submission.storage_path
    assert ".." not in submission.storage_path
    assert "etc/passwd" not in submission.storage_path
    assert submission.display_name == "../../etc/passwd"


def test_non_zip_upload_is_rejected(client, user_token):
    r = client.post(
        "/api/v1/submissions",
        data={"display_name": "bad"},
        files={"file": ("x.zip", io.BytesIO(b"not a zip"), "application/zip")},
        headers=auth_header(user_token),
    )
    assert r.status_code == 400


def test_zip_slip_upload_is_rejected(client, user_token):
    r = upload(client, user_token, zbuf=make_zip([("../escape.py", "pwned")]))
    assert r.status_code == 400


def test_empty_archive_is_rejected(client, user_token):
    r = upload(client, user_token, zbuf=make_zip([]))
    assert r.status_code == 400


def test_user_sees_only_their_own_submissions(client, user_token, other_user_token):
    upload(client, user_token, "mine")
    upload(client, other_user_token, "theirs")

    r = client.get("/api/v1/submissions", headers=auth_header(user_token))
    assert r.status_code == 200
    names = [s["display_name"] for s in r.json()]
    assert names == ["mine"]


def test_admin_sees_all_submissions(client, user_token, admin_token):
    upload(client, user_token, "theirs")
    r = client.get("/api/v1/submissions", headers=auth_header(admin_token))
    assert r.status_code == 200
    assert any(s["display_name"] == "theirs" for s in r.json())


@pytest.mark.parametrize(
    "method,suffix", [("GET", ""), ("DELETE", ""), ("GET", "/analyses")]
)
def test_other_user_gets_404_not_403(
    client, user_token, other_user_token, method, suffix
):
    """404, not 403 — a 403 would confirm the id exists."""
    sid = upload(client, user_token).json()["id"]
    r = client.request(
        method, f"/api/v1/submissions/{sid}{suffix}", headers=auth_header(other_user_token)
    )
    assert r.status_code == 404


def test_other_user_cannot_analyze_your_submission(
    client, user_token, other_user_token, ready_branch
):
    sid = upload(client, user_token).json()["id"]
    r = client.post(
        f"/api/v1/submissions/{sid}/analyze",
        json={"branch_id": str(ready_branch.id), "error_message": "boom"},
        headers=auth_header(other_user_token),
    )
    assert r.status_code == 404


def test_owner_can_delete_their_submission(client, user_token):
    sid = upload(client, user_token).json()["id"]
    r = client.delete(f"/api/v1/submissions/{sid}", headers=auth_header(user_token))
    assert r.status_code == 200
    r = client.get(f"/api/v1/submissions/{sid}", headers=auth_header(user_token))
    assert r.status_code == 404


def test_admin_can_delete_any_submission(client, user_token, admin_token):
    sid = upload(client, user_token).json()["id"]
    r = client.delete(f"/api/v1/submissions/{sid}", headers=auth_header(admin_token))
    assert r.status_code == 200


def test_submission_quota_is_enforced(client, user_token, monkeypatch):
    from app.services import submission_service

    monkeypatch.setattr(submission_service.config, "USER_SUBMISSION_QUOTA", 2)
    assert upload(client, user_token, "one").status_code == 201
    assert upload(client, user_token, "two").status_code == 201
    assert upload(client, user_token, "three").status_code == 409
