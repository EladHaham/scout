"""Tests for aider_mapper filtering logic."""
from __future__ import annotations

from scout.adapters.aider_mapper import (
    _candidate_repo_map_path,
    _filter_repo_map,
    _looks_like_junk_path,
)


# ── _candidate_repo_map_path ──────────────────────────────────────────────────

class TestCandidateRepoMapPath:
    def test_blank_line_returns_none(self):
        assert _candidate_repo_map_path("") is None
        assert _candidate_repo_map_path("   ") is None

    def test_body_line_returns_none(self):
        assert _candidate_repo_map_path("│   def foo():") is None
        assert _candidate_repo_map_path("⋮") is None

    def test_other_box_drawing_prefixes_return_none(self):
        assert _candidate_repo_map_path("╭── header") is None
        assert _candidate_repo_map_path("╰── footer") is None
        assert _candidate_repo_map_path("──────────") is None

    def test_path_with_slash(self):
        assert _candidate_repo_map_path("scout/service.py:") == "scout/service.py"

    def test_path_without_colon(self):
        assert _candidate_repo_map_path("scout/service.py") == "scout/service.py"

    def test_strips_trailing_colon(self):
        result = _candidate_repo_map_path("scout/service.py:")
        assert result == "scout/service.py"
        assert not result.endswith(":")

    def test_dotfile_at_root(self):
        assert _candidate_repo_map_path(".env") == ".env"

    def test_known_extensionless_file_recognized(self):
        assert _candidate_repo_map_path("Makefile") == "Makefile"
        assert _candidate_repo_map_path("Dockerfile:") == "Dockerfile"
        assert _candidate_repo_map_path("LICENSE") == "LICENSE"

    def test_unknown_extensionless_word_returns_none(self):
        # confirms the allowlist is narrow — random words are not paths
        assert _candidate_repo_map_path("randomword") is None
        assert _candidate_repo_map_path("notes") is None

    def test_windows_style_path(self):
        assert _candidate_repo_map_path("scout\\service.py:") == "scout\\service.py"


# ── _looks_like_junk_path ─────────────────────────────────────────────────────

class TestLooksLikeJunkPath:
    def test_pycache(self):
        assert _looks_like_junk_path("scout/__pycache__/models.cpython-311.pyc")

    def test_egg_info(self):
        assert _looks_like_junk_path("scout_repomap.egg-info/PKG-INFO")

    def test_venv(self):
        assert _looks_like_junk_path(".venv/lib/python3.11/site.py")

    def test_pyc_extension(self):
        assert _looks_like_junk_path("scout/models.pyc")

    def test_ds_store(self):
        assert _looks_like_junk_path("some/dir/.DS_Store")

    def test_normal_file_not_junk(self):
        assert not _looks_like_junk_path("scout/service.py")

    def test_nested_normal_file_not_junk(self):
        assert not _looks_like_junk_path("scout/adapters/aider_mapper.py")

    def test_aider_tags_cache(self):
        assert _looks_like_junk_path(".aider.tags.cache.v4/cache.db")

    def test_windows_style_junk_path(self):
        assert _looks_like_junk_path("scout\\__pycache__\\models.pyc")


# ── _filter_repo_map ──────────────────────────────────────────────────────────

SAMPLE_MAP = """\
scout/service.py:
⋮
│def get_repo_map(repo, use_cache, refresh):

scout/__pycache__/service.cpython-311.pyc:
⋮
│(binary)

scout/domain/models.py:
⋮
│class RepoMapResult:
"""


class TestFilterRepoMap:
    def test_removes_pycache_block(self):
        result = _filter_repo_map(SAMPLE_MAP)
        assert "__pycache__" not in result

    def test_keeps_normal_files(self):
        result = _filter_repo_map(SAMPLE_MAP)
        assert "scout/service.py" in result
        assert "scout/domain/models.py" in result

    def test_keeps_body_lines_of_normal_files(self):
        result = _filter_repo_map(SAMPLE_MAP)
        assert "get_repo_map" in result
        assert "RepoMapResult" in result

    def test_preserves_order(self):
        result = _filter_repo_map(SAMPLE_MAP)
        assert result.index("scout/service.py") < result.index("scout/domain/models.py")

    def test_no_double_blank_lines(self):
        text = "scout/a.py:\n\n\n\nscout/b.py:"
        result = _filter_repo_map(text)
        assert "\n\n\n" not in result

    def test_empty_input(self):
        assert _filter_repo_map("") == ""

    def test_only_junk_returns_empty(self):
        junk = "scout/__pycache__/x.pyc:\n⋮\n│(binary)\n"
        result = _filter_repo_map(junk)
        assert result == ""