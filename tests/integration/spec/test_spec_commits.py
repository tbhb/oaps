# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
"""Integration tests verifying spec operations create proper git commits.

These tests verify that SpecManager, RequirementManager, and SpecTestManager
operations result in actual git commits when used with OapsRepository.
"""

import subprocess
from pathlib import Path

import pytest

from oaps.repository import OapsRepository
from oaps.spec import RequirementManager, SpecManager, TestManager as SpecTestManager
from oaps.spec._models import (
    RequirementType,
    SpecType,
    TestMethod as SpecTestMethod,
)


def _run_git(cwd: Path, *args: str) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(  # noqa: S603 - Safe: running git in tests
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed: {result.stderr}"
        raise RuntimeError(msg)
    return result.stdout


@pytest.fixture
def oaps_git_repo(tmp_path: Path) -> Path:
    """Create a real .oaps git repository for testing."""
    oaps_dir = tmp_path / ".oaps"
    oaps_dir.mkdir()

    # Initialize git repo
    _run_git(oaps_dir, "init")
    _run_git(oaps_dir, "config", "user.name", "Test User")
    _run_git(oaps_dir, "config", "user.email", "test@example.com")
    _run_git(oaps_dir, "config", "commit.gpgsign", "false")

    # Create initial commit with README
    readme = oaps_dir / "README.md"
    readme.write_text("# OAPS Test Repository\n")
    _run_git(oaps_dir, "add", "README.md")
    _run_git(oaps_dir, "commit", "-m", "Initial commit")

    # Create specs directory structure
    specs_dir = oaps_dir / "docs" / "specs"
    specs_dir.mkdir(parents=True)

    return tmp_path


class TestSpecCreateCommits:
    def test_spec_create_commits_files(self, oaps_git_repo: Path) -> None:
        """Verify SpecManager.create_spec creates a git commit."""
        specs_dir = oaps_git_repo / ".oaps" / "docs" / "specs"

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            manager = SpecManager(base_path=specs_dir, oaps_repo=repo)

            spec = manager.create_spec(
                slug="test-feature",
                title="Test Feature Specification",
                spec_type=SpecType.FEATURE,
                summary="A test feature for integration testing",
                tags=["integration", "testing"],
                actor="test-user",
                session_id="test-session",
            )

        # Verify spec was created
        assert spec.id == "0001"
        assert spec.slug == "test-feature"

        # Verify commit was created
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "-1", "--format=%s")
        assert "oaps(spec): create 0001" in log_output

        # Verify spec directory exists
        assert (specs_dir / "0001-test-feature").exists()
        assert (specs_dir / "0001-test-feature" / "index.json").exists()

    def test_spec_create_with_dependencies_commits(self, oaps_git_repo: Path) -> None:
        """Verify creating a spec with dependencies creates proper commits."""
        specs_dir = oaps_git_repo / ".oaps" / "docs" / "specs"

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            manager = SpecManager(base_path=specs_dir, oaps_repo=repo)

            # Create first spec
            spec1 = manager.create_spec(
                slug="base-feature",
                title="Base Feature",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

            # Create second spec that depends on first
            spec2 = manager.create_spec(
                slug="dependent-feature",
                title="Dependent Feature",
                spec_type=SpecType.FEATURE,
                depends_on=[spec1.id],
                actor="test-user",
            )

        # Verify both specs exist
        assert spec1.id == "0001"
        assert spec2.id == "0002"
        assert spec1.id in spec2.relationships.depends_on

        # Verify two commits were created (one per spec)
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "--oneline")
        lines = log_output.strip().split("\n")
        # Initial + 2 spec creates
        assert len(lines) >= 3


class TestSpecUpdateCommits:
    def test_spec_update_commits(self, oaps_git_repo: Path) -> None:
        """Verify SpecManager.update_spec creates a git commit."""
        specs_dir = oaps_git_repo / ".oaps" / "docs" / "specs"

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            manager = SpecManager(base_path=specs_dir, oaps_repo=repo)

            # Create spec
            spec = manager.create_spec(
                slug="update-test",
                title="Original Title",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

            # Update spec
            updated = manager.update_spec(
                spec.id,
                title="Updated Title",
                summary="New summary",
                actor="test-user",
            )

        assert updated.title == "Updated Title"
        assert updated.summary == "New summary"

        # Verify update commit was created
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "-1", "--format=%s")
        assert f"oaps(spec): update {spec.id}" in log_output


class TestRequirementAddCommits:
    def test_add_requirement_commits(self, oaps_git_repo: Path) -> None:
        """Verify RequirementManager.add_requirement creates a git commit."""
        specs_dir = oaps_git_repo / ".oaps" / "docs" / "specs"

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            spec_manager = SpecManager(base_path=specs_dir, oaps_repo=repo)
            req_manager = RequirementManager(spec_manager, oaps_repo=repo)

            # Create spec first
            spec = spec_manager.create_spec(
                slug="req-test",
                title="Requirement Test Spec",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

            # Add requirement
            req = req_manager.add_requirement(
                spec_id=spec.id,
                req_type=RequirementType.FUNCTIONAL,
                title="Test Requirement",
                description="A test requirement for integration testing",
                actor="test-user",
                session_id="test-session",
            )

        # Verify requirement was created
        assert req.id.startswith("FR-")
        assert req.title == "Test Requirement"

        # Verify commit was created
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "-1", "--format=%s")
        assert "oaps(spec): add requirement" in log_output

    def test_add_multiple_requirements_commits(self, oaps_git_repo: Path) -> None:
        """Verify adding multiple requirements creates separate commits."""
        specs_dir = oaps_git_repo / ".oaps" / "docs" / "specs"

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            spec_manager = SpecManager(base_path=specs_dir, oaps_repo=repo)
            req_manager = RequirementManager(spec_manager, oaps_repo=repo)

            spec = spec_manager.create_spec(
                slug="multi-req",
                title="Multi-Requirement Spec",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

            # Add multiple requirements
            reqs = []
            for i in range(3):
                req = req_manager.add_requirement(
                    spec_id=spec.id,
                    req_type=RequirementType.FUNCTIONAL,
                    title=f"Requirement {i + 1}",
                    description=f"Test requirement {i + 1}",
                    actor="test-user",
                )
                reqs.append(req)

        # Verify all requirements were created
        assert len(reqs) == 3
        assert all(r.id.startswith("FR-") for r in reqs)

        # Verify commits were created
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "--oneline")
        lines = log_output.strip().split("\n")
        # Initial + create spec + 3 add requirements
        assert len(lines) >= 5


class TestRequirementUpdateCommits:
    def test_update_requirement_commits(self, oaps_git_repo: Path) -> None:
        """Verify RequirementManager.update_requirement creates a git commit."""
        specs_dir = oaps_git_repo / ".oaps" / "docs" / "specs"

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            spec_manager = SpecManager(base_path=specs_dir, oaps_repo=repo)
            req_manager = RequirementManager(spec_manager, oaps_repo=repo)

            spec = spec_manager.create_spec(
                slug="update-req",
                title="Update Requirement Spec",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

            req = req_manager.add_requirement(
                spec_id=spec.id,
                req_type=RequirementType.FUNCTIONAL,
                title="Original Title",
                description="Original description",
                actor="test-user",
            )

            # Update requirement
            updated = req_manager.update_requirement(
                spec_id=spec.id,
                req_id=req.id,
                title="Updated Title",
                description="Updated description",
                actor="test-user",
            )

        assert updated.title == "Updated Title"
        assert updated.description == "Updated description"

        # Verify commit was created
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "-1", "--format=%s")
        assert f"oaps(spec): update requirement {spec.id}:{req.id}" in log_output


class TestAddTestCommits:
    def test_add_test_commits(self, oaps_git_repo: Path) -> None:
        """Verify SpecTestManager.add_test creates a git commit."""
        specs_dir = oaps_git_repo / ".oaps" / "docs" / "specs"

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            spec_manager = SpecManager(base_path=specs_dir, oaps_repo=repo)
            req_manager = RequirementManager(spec_manager, oaps_repo=repo)
            test_mgr = SpecTestManager(spec_manager, req_manager, oaps_repo=repo)

            spec = spec_manager.create_spec(
                slug="test-spec",
                title="Test Spec",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

            req = req_manager.add_requirement(
                spec_id=spec.id,
                req_type=RequirementType.FUNCTIONAL,
                title="Testable Requirement",
                description="A requirement to test",
                actor="test-user",
            )

            # Add test
            test = test_mgr.add_test(
                spec_id=spec.id,
                method=SpecTestMethod.UNIT,
                title="Unit Test for Requirement",
                tests_requirements=[req.id],
                description="Tests the requirement",
                file="tests/test_feature.py",
                function="test_requirement",
                actor="test-user",
            )

        # Verify test was created
        assert test.id.startswith("UT-")
        assert req.id in test.tests_requirements

        # Verify commit was created
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "-1", "--format=%s")
        assert "oaps(spec): add test" in log_output

    def test_add_multiple_tests_commits(self, oaps_git_repo: Path) -> None:
        """Verify adding multiple tests creates proper commits."""
        specs_dir = oaps_git_repo / ".oaps" / "docs" / "specs"

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            spec_manager = SpecManager(base_path=specs_dir, oaps_repo=repo)
            req_manager = RequirementManager(spec_manager, oaps_repo=repo)
            test_mgr = SpecTestManager(spec_manager, req_manager, oaps_repo=repo)

            spec = spec_manager.create_spec(
                slug="multi-test",
                title="Multi-Test Spec",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

            req = req_manager.add_requirement(
                spec_id=spec.id,
                req_type=RequirementType.FUNCTIONAL,
                title="Multi-Test Requirement",
                description="A requirement with multiple tests",
                actor="test-user",
            )

            # Add multiple tests
            tests = []
            methods = [
                SpecTestMethod.UNIT,
                SpecTestMethod.INTEGRATION,
                SpecTestMethod.MANUAL,
            ]
            for i, method in enumerate(methods):
                test = test_mgr.add_test(
                    spec_id=spec.id,
                    method=method,
                    title=f"Test {i + 1}",
                    tests_requirements=[req.id],
                    actor="test-user",
                )
                tests.append(test)

        # Verify all tests were created
        assert len(tests) == 3

        # Verify commits were created
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "--oneline")
        lines = log_output.strip().split("\n")
        # Initial + create spec + add req + 3 add tests
        assert len(lines) >= 6


class TestSequentialOperations:
    def test_full_spec_workflow_commits(self, oaps_git_repo: Path) -> None:
        """Verify a complete spec workflow creates proper commit history."""
        specs_dir = oaps_git_repo / ".oaps" / "docs" / "specs"

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            spec_manager = SpecManager(base_path=specs_dir, oaps_repo=repo)
            req_manager = RequirementManager(spec_manager, oaps_repo=repo)
            test_mgr = SpecTestManager(spec_manager, req_manager, oaps_repo=repo)

            # 1. Create spec
            spec = spec_manager.create_spec(
                slug="workflow-spec",
                title="Workflow Spec",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

            # 2. Add requirement
            req1 = req_manager.add_requirement(
                spec_id=spec.id,
                req_type=RequirementType.FUNCTIONAL,
                title="First Requirement",
                description="First requirement",
                actor="test-user",
            )

            # 3. Add another requirement
            req2 = req_manager.add_requirement(
                spec_id=spec.id,
                req_type=RequirementType.QUALITY,
                title="Second Requirement",
                description="Second requirement",
                actor="test-user",
            )

            # 4. Update first requirement
            req_manager.update_requirement(
                spec_id=spec.id,
                req_id=req1.id,
                title="Updated First Requirement",
                actor="test-user",
            )

            # 5. Add test for first requirement
            _ = test_mgr.add_test(
                spec_id=spec.id,
                method=SpecTestMethod.UNIT,
                title="Test for First Req",
                tests_requirements=[req1.id],
                actor="test-user",
            )

            # 6. Add test covering both requirements
            _ = test_mgr.add_test(
                spec_id=spec.id,
                method=SpecTestMethod.INTEGRATION,
                title="Integration Test",
                tests_requirements=[req1.id, req2.id],
                actor="test-user",
            )

            # 7. Update spec
            spec_manager.update_spec(
                spec.id,
                summary="Complete workflow spec",
                actor="test-user",
            )

        # Verify commit history
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "--format=%s")

        # All operations should have commits
        assert "oaps(spec): create 0001" in log_output
        assert "oaps(spec): add requirement" in log_output
        assert "oaps(spec): update requirement" in log_output
        assert "oaps(spec): add test" in log_output
        assert "oaps(spec): update 0001" in log_output

        # Count total commits
        commit_count = len(log_output.strip().split("\n"))
        # Initial + create spec + 2 add reqs + update req + 2 add tests + update spec
        assert commit_count >= 8

    def test_spec_operations_with_session_id(self, oaps_git_repo: Path) -> None:
        """Verify session ID is included in commit trailers."""
        specs_dir = oaps_git_repo / ".oaps" / "docs" / "specs"
        session_id = "test-session-12345"

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            spec_manager = SpecManager(base_path=specs_dir, oaps_repo=repo)
            req_manager = RequirementManager(spec_manager, oaps_repo=repo)

            spec = spec_manager.create_spec(
                slug="session-spec",
                title="Session Spec",
                spec_type=SpecType.FEATURE,
                actor="test-user",
                session_id=session_id,
            )

            req_manager.add_requirement(
                spec_id=spec.id,
                req_type=RequirementType.FUNCTIONAL,
                title="Session Requirement",
                description="Requirement with session",
                actor="test-user",
                session_id=session_id,
            )

        # Verify session ID in commit trailer
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "-2", "--format=%B")
        assert f"OAPS-Session: {session_id}" in log_output


class TestRepositoryIntegrityAfterOperations:
    def test_repository_valid_after_operations(self, oaps_git_repo: Path) -> None:
        """Verify git repository is valid after multiple operations."""
        specs_dir = oaps_git_repo / ".oaps" / "docs" / "specs"

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            spec_manager = SpecManager(base_path=specs_dir, oaps_repo=repo)
            req_manager = RequirementManager(spec_manager, oaps_repo=repo)
            test_mgr = SpecTestManager(spec_manager, req_manager, oaps_repo=repo)

            # Perform multiple operations
            for i in range(3):
                spec = spec_manager.create_spec(
                    slug=f"integrity-spec-{i}",
                    title=f"Integrity Spec {i}",
                    spec_type=SpecType.FEATURE,
                    actor="test-user",
                )

                req = req_manager.add_requirement(
                    spec_id=spec.id,
                    req_type=RequirementType.FUNCTIONAL,
                    title=f"Requirement {i}",
                    description=f"Requirement {i}",
                    actor="test-user",
                )

                test_mgr.add_test(
                    spec_id=spec.id,
                    method=SpecTestMethod.UNIT,
                    title=f"Test {i}",
                    tests_requirements=[req.id],
                    actor="test-user",
                )

        # Run git fsck to verify repository integrity
        result = subprocess.run(
            ["git", "fsck", "--strict", "--full"],
            cwd=str(oaps_git_repo / ".oaps"),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"git fsck failed: {result.stderr}"

        # Verify we can read status
        with OapsRepository(working_dir=oaps_git_repo) as repo:
            status = repo.get_status()
            # Should be clean after all commits
            assert len(status.modified) == 0
            assert len(status.untracked) == 0

    def test_commit_history_walkable(self, oaps_git_repo: Path) -> None:
        """Verify commit history can be walked after operations."""
        specs_dir = oaps_git_repo / ".oaps" / "docs" / "specs"

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            spec_manager = SpecManager(base_path=specs_dir, oaps_repo=repo)

            for i in range(5):
                spec_manager.create_spec(
                    slug=f"walk-spec-{i}",
                    title=f"Walk Spec {i}",
                    spec_type=SpecType.FEATURE,
                    actor="test-user",
                )

        # Walk commit history
        with OapsRepository(working_dir=oaps_git_repo) as repo:
            commits = repo.get_last_commits(n=10)

        # Should have initial commit + 5 spec creates
        assert len(commits) >= 6

        # All commits should have valid SHAs
        for commit in commits:
            assert len(commit.sha) in (40, 80)
            assert all(c in "0123456789abcdef" for c in commit.sha)
