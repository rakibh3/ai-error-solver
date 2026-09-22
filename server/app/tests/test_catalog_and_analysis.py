"""Catalog visibility and analysis persistence."""
import io
import zipfile

import pytest

from app.tests.conftest import auth_header


def upload(client, token, name="proj"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("app.py", "def main():\n    retrun 1\n")
    buf.seek(0)
    return client.post(
        "/api/v1/submissions",
        data={"display_name": name},
        files={"file": ("p.zip", buf, "application/zip")},
        headers=auth_header(token),
    ).json()["id"]


# --- catalog ---------------------------------------------------------------

def test_ready_branch_is_visible_to_a_user(client, user_token, ready_branch):
    r = client.get("/api/v1/catalog/projects", headers=auth_header(user_token))
    assert r.status_code == 200
    assert [p["name"] for p in r.json()] == ["demo-project"]
    assert r.json()[0]["ready_branch_count"] == 1


def test_pending_branch_is_hidden_from_the_catalog(client, user_token, pending_branch):
    r = client.get("/api/v1/catalog/projects", headers=auth_header(user_token))
    assert r.status_code == 200
    assert r.json() == []


def test_catalog_never_exposes_the_repo_url(client, user_token, ready_branch):
    r = client.get("/api/v1/catalog/projects", headers=auth_header(user_token))
    assert "repo_url" not in r.json()[0]

    pid = r.json()[0]["id"]
    r = client.get(
        f"/api/v1/catalog/projects/{pid}/branches", headers=auth_header(user_token)
    )
    assert r.status_code == 200
    assert "repo_url" not in r.json()[0]
    assert "collection_name" not in r.json()[0]


def test_admin_view_does_show_pending_branches(client, admin_token, pending_branch):
    r = client.get("/api/v1/admin/reference-projects", headers=auth_header(admin_token))
    assert r.status_code == 200
    statuses = [b["status"] for p in r.json() for b in p["branches"]]
    assert "pending" in statuses


def test_branches_endpoint_404s_for_a_project_with_no_ready_branches(
    client, user_token, pending_branch
):
    r = client.get(
        f"/api/v1/catalog/projects/{pending_branch.project_id}/branches",
        headers=auth_header(user_token),
    )
    assert r.status_code == 404


# --- analysis --------------------------------------------------------------

def test_analyze_rejects_a_non_ready_branch(client, user_token, pending_branch):
    sid = upload(client, user_token)
    r = client.post(
        f"/api/v1/submissions/{sid}/analyze",
        json={"branch_id": str(pending_branch.id), "error_message": "boom"},
        headers=auth_header(user_token),
    )
    assert r.status_code == 404


def test_analyze_rejects_an_empty_error_message(client, user_token, ready_branch):
    sid = upload(client, user_token)
    r = client.post(
        f"/api/v1/submissions/{sid}/analyze",
        json={"branch_id": str(ready_branch.id), "error_message": ""},
        headers=auth_header(user_token),
    )
    assert r.status_code == 422


def test_malformed_model_output_is_stored_as_failed(
    client, user_token, ready_branch, monkeypatch
):
    """A bad model response must become a `failed` row, not a 500."""
    from app.rag import analyzer
    from app.services import analysis_service

    def boom(**kwargs):
        raise analyzer.AnalyzerError("Model response was not valid JSON")

    monkeypatch.setattr(analysis_service.analyzer, "analyze_code", boom)

    sid = upload(client, user_token)
    r = client.post(
        f"/api/v1/submissions/{sid}/analyze",
        json={"branch_id": str(ready_branch.id), "error_message": "NameError: retrun"},
        headers=auth_header(user_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "failed"
    assert "not valid JSON" in r.json()["failure_reason"]


def test_successful_analysis_is_persisted_and_listed(
    client, user_token, ready_branch, monkeypatch
):
    from app.schemas.schemas import AnalysisResult
    from app.services import analysis_service

    def fake(**kwargs):
        return {
            "raw": '{"error_explanation":"typo","fix_instructions":{"file":"app.py"}}',
            "result": AnalysisResult.model_validate(
                {
                    "error_explanation": "typo: retrun should be return",
                    "fix_instructions": {
                        "file": "app.py",
                        "line": 2,
                        "change": {"old_code": "retrun 1", "new_code": "return 1"},
                    },
                }
            ),
        }

    monkeypatch.setattr(analysis_service.analyzer, "analyze_code", fake)

    sid = upload(client, user_token)
    r = client.post(
        f"/api/v1/submissions/{sid}/analyze",
        json={"branch_id": str(ready_branch.id), "error_message": "NameError"},
        headers=auth_header(user_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "success"
    assert r.json()["result"]["fix_instructions"]["change"]["new_code"] == "return 1"

    r = client.get(
        f"/api/v1/submissions/{sid}/analyses", headers=auth_header(user_token)
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


# --- analyzer pure functions ----------------------------------------------

def test_extract_paths_finds_traceback_files():
    from app.rag.analyzer import extract_paths

    paths = extract_paths(
        'File "app/services/foo.py", line 12\n  File "src/index.ts", line 3'
    )
    assert "app/services/foo.py" in paths
    assert "src/index.ts" in paths


@pytest.mark.parametrize(
    "raw",
    [
        '{"error_explanation":"x","fix_instructions":{"file":"a.py"}}',
        '```json\n{"error_explanation":"x","fix_instructions":{"file":"a.py"}}\n```',
        'Sure!\n{"error_explanation":"x","fix_instructions":{"file":"a.py"}}\nHope that helps',
    ],
)
def test_parse_model_output_handles_fences_and_prose(raw):
    from app.rag.analyzer import parse_model_output

    result = parse_model_output(raw)
    assert result.error_explanation == "x"
    assert result.fix_instructions.file == "a.py"


@pytest.mark.parametrize("raw", ["", "no json here", "{not json}", '{"wrong":"shape"}'])
def test_parse_model_output_rejects_garbage(raw):
    from app.rag.analyzer import AnalyzerError, parse_model_output

    with pytest.raises(AnalyzerError):
        parse_model_output(raw)
