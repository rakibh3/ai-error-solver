"""Run a comparison and persist the result.

The signature takes loaded ORM rows, not loose strings from the request body.
That is what made the old `/compare` able to read any submission directory:
it accepted `student_project_name` and `student_project_id` straight from the
caller with no ownership check.
"""
import logging
import os
from pathlib import Path
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.core import config
from app.models.analysis import Analysis, AnalysisStatus
from app.models.reference import ReferenceBranch
from app.models.submission import Submission
from app.rag import analyzer
from app.rag.analyzer import AnalyzerError

logger = logging.getLogger(__name__)

CODE_EXTENSIONS = (
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".scss", ".vue",
    ".svelte", ".php", ".rb", ".go", ".rs", ".java", ".kt", ".swift", ".cpp",
    ".c", ".h", ".cs", ".dart", ".json", ".yaml", ".yml", ".sql", ".md",
)


def _score(relative_path: str, hinted_paths: List[str]) -> int:
    """Rank a file by how strongly the error message points at it."""
    rel_lower = relative_path.lower().replace("\\", "/")
    basename = os.path.basename(rel_lower)
    score = 0
    for hint in hinted_paths:
        hint_lower = hint.lower().replace("\\", "/")
        if rel_lower == hint_lower or rel_lower.endswith("/" + hint_lower):
            score += 100
        elif os.path.basename(hint_lower) == basename:
            score += 50
        elif hint_lower in rel_lower:
            score += 10
    return score


def collect_context(root: Path, error_message: str) -> Tuple[str, List[str]]:
    """Assemble the submitted-code context under a character budget.

    The previous version concatenated every matching file in the submission and
    used the whole blob both as the prompt and as the retrieval query. Here the
    files the traceback names are preferred, and the budget is explicit.

    Truncation order: highest-scoring files first, then shortest files, so the
    budget buys the most files rather than one enormous one.
    """
    hinted = analyzer.extract_paths(error_message)

    candidates = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if not name.endswith(CODE_EXTENSIONS):
                continue
            full = Path(dirpath) / name
            try:
                size = full.stat().st_size
            except OSError:
                continue
            relative = str(full.relative_to(root))
            candidates.append((_score(relative, hinted), size, relative, full))

    # Highest score first; within a score, smallest file first.
    candidates.sort(key=lambda c: (-c[0], c[1]))

    included: List[str] = []
    chunks: List[str] = []
    budget = config.MAX_STUDENT_CONTEXT_CHARS

    for _, _, relative, full in candidates[: config.MAX_CANDIDATE_FILES]:
        try:
            content = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        block = f"--- File: {relative} ---\n{content}"
        if len(block) > budget:
            if not chunks:  # always include at least one file, truncated
                chunks.append(block[:budget] + "\n... [truncated]")
                included.append(relative)
            break
        chunks.append(block)
        included.append(relative)
        budget -= len(block)

    return "\n\n".join(chunks), included


def run_analysis(
    db: Session,
    submission: Submission,
    branch: ReferenceBranch,
    error_message: str,
) -> Analysis:
    """Compare `submission` against `branch` and persist the outcome.

    A failure is recorded as an `analyses` row with status=failed rather than
    raised, so the user gets a history entry either way.
    """
    root = Path(submission.storage_path)

    analysis = Analysis(
        submission_id=submission.id,
        branch_id=branch.id,
        error_message=error_message,
        status=AnalysisStatus.FAILED,
        # NOT NULL, and this row is written even when the analysis fails --
        # including the failure where ANALYSIS_MODEL itself is unset.
        model=config.ANALYSIS_MODEL or "(unset)",
    )

    if not root.is_dir():
        analysis.failure_reason = "Submission files are missing on disk"
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis

    student_context, included = collect_context(root, error_message)

    if not student_context:
        analysis.failure_reason = "No readable code files found in the submission"
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis

    try:
        outcome = analyzer.analyze_code(
            student_code_context=student_context,
            collection_name=branch.collection_name,
            error_message=error_message,
        )
        analysis.status = AnalysisStatus.SUCCESS
        analysis.result = outcome["result"].model_dump()
        analysis.raw_response = outcome["raw"]
        # OpenRouter may route to a different model than the one requested.
        analysis.model = outcome.get("model") or config.ANALYSIS_MODEL
    except AnalyzerError as e:
        logger.info("Analysis failed for submission %s: %s", submission.id, e)
        analysis.failure_reason = str(e)[:2000]
    except Exception as e:
        logger.exception("Unexpected analysis error for submission %s", submission.id)
        analysis.failure_reason = f"Unexpected error: {e}"[:2000]

    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    logger.info(
        "Analysis %s for submission %s used %d file(s)",
        analysis.status.value, submission.id, len(included),
    )
    return analysis
