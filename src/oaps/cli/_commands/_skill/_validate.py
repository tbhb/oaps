"""Skill validation functionality."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

# Validation thresholds
MIN_DESCRIPTION_LENGTH = 50
MIN_BODY_WORDS = 100
MAX_BODY_WORDS = 2500
MAX_SECOND_PERSON_OCCURRENCES = 2


class ValidationSeverity(Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(slots=True, frozen=True)
class ValidationIssue:
    """A single validation issue.

    Attributes:
        severity: The severity level of the issue.
        code: A short code identifying the issue type.
        message: A human-readable description of the issue.
        path: Optional path to the file with the issue.
        line: Optional line number where the issue occurs.
    """

    severity: ValidationSeverity
    code: str
    message: str
    path: Path | None = None
    line: int | None = None

    def format(self) -> str:
        """Format the issue for display.

        Returns:
            Formatted string representation of the issue.
        """
        location = ""
        if self.path:
            location = f"{self.path}"
            if self.line:
                location += f":{self.line}"
            location += ": "

        severity_prefix = {
            ValidationSeverity.ERROR: "ERROR",
            ValidationSeverity.WARNING: "WARNING",
            ValidationSeverity.INFO: "INFO",
        }

        return (
            f"{location}{severity_prefix[self.severity]}: [{self.code}] {self.message}"
        )


@dataclass(slots=True)
class ValidationResult:
    """Result of validating a skill.

    Attributes:
        skill_name: Name of the validated skill.
        skill_dir: Path to the skill directory.
        issues: List of validation issues found.
    """

    skill_name: str
    skill_dir: Path
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if the skill passed validation (no errors).

        Returns:
            True if there are no error-level issues.
        """
        return not any(
            issue.severity == ValidationSeverity.ERROR for issue in self.issues
        )

    @property
    def error_count(self) -> int:
        """Count the number of error-level issues."""
        return sum(
            1 for issue in self.issues if issue.severity == ValidationSeverity.ERROR
        )

    @property
    def warning_count(self) -> int:
        """Count the number of warning-level issues."""
        return sum(
            1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING
        )

    def add_error(
        self,
        code: str,
        message: str,
        *,
        path: Path | None = None,
        line: int | None = None,
    ) -> None:
        """Add an error-level issue."""
        self.issues.append(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code=code,
                message=message,
                path=path,
                line=line,
            )
        )

    def add_warning(
        self,
        code: str,
        message: str,
        *,
        path: Path | None = None,
        line: int | None = None,
    ) -> None:
        """Add a warning-level issue."""
        self.issues.append(
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code=code,
                message=message,
                path=path,
                line=line,
            )
        )

    def add_info(
        self,
        code: str,
        message: str,
        *,
        path: Path | None = None,
        line: int | None = None,
    ) -> None:
        """Add an info-level issue."""
        self.issues.append(
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                code=code,
                message=message,
                path=path,
                line=line,
            )
        )


def _count_words(text: str) -> int:
    """Count words in text, excluding code blocks and frontmatter.

    Args:
        text: The markdown text to count.

    Returns:
        Approximate word count.
    """
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)

    # Count words (simple split on whitespace)
    words = text.split()
    return len(words)


def _check_description_quality(description: str) -> list[str]:
    """Check the quality of a skill description.

    Args:
        description: The skill description from frontmatter.

    Returns:
        List of issues found with the description.
    """
    issues: list[str] = []

    # Check for third-person format
    if description.startswith(("Use ", "Load ")):
        issues.append(
            "Description should use third-person (start with 'This skill...')"
        )

    # Check for trigger phrases
    if '"' not in description and "'" not in description:
        msg = (
            "Description should include specific trigger phrases in quotes "
            '(e.g., "create a skill", "add a reference")'
        )
        issues.append(msg)

    # Check minimum length
    if len(description) < MIN_DESCRIPTION_LENGTH:
        issues.append("Description is too short (should be at least 50 characters)")

    # Check for vague descriptions
    vague_patterns = [
        r"^Provides .+ guidance\.?$",
        r"^Helps with .+\.?$",
        r"^For .+ tasks\.?$",
    ]
    for pattern in vague_patterns:
        if re.match(pattern, description, re.IGNORECASE):
            issues.append("Description is too vague; include specific trigger phrases")
            break

    return issues


def _check_writing_style(body: str, skill_md_path: Path) -> list[ValidationIssue]:
    """Check the writing style of SKILL.md body.

    Args:
        body: The markdown body content.
        skill_md_path: Path to SKILL.md for issue reporting.

    Returns:
        List of validation issues.
    """
    issues: list[ValidationIssue] = []

    # Check for second-person usage at sentence starts
    # This is a heuristic - we look for "You should", "You can", etc.
    second_person_patterns = [
        (r"\bYou should\b", "Avoid 'You should'; use imperative form"),
        (r"\bYou can\b", "Avoid 'You can'; use 'To X, do Y' form"),
        (r"\bYou need to\b", "Avoid 'You need to'; use imperative form"),
        (r"\bYou must\b", "Avoid 'You must'; use imperative or 'X is required'"),
    ]

    for pattern, message in second_person_patterns:
        matches = list(re.finditer(pattern, body, re.IGNORECASE))
        # Allow a few occurrences, flag excessive use
        if len(matches) > MAX_SECOND_PERSON_OCCURRENCES:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="style-second-person",
                    message=f"{message} (found {len(matches)} occurrences)",
                    path=skill_md_path,
                )
            )

    return issues


def _normalize_name(name: str) -> str:
    """Normalize a skill name for comparison.

    Converts spaces to hyphens and lowercases for comparison.
    This allows "Skill Development" to match "skill-development".

    Args:
        name: The name to normalize.

    Returns:
        Normalized name.
    """
    return name.lower().replace(" ", "-").replace("_", "-")


def _validate_name_field(
    frontmatter: Mapping[str, object],
    skill_name: str,
    skill_md: Path,
    result: ValidationResult,
) -> None:
    """Validate the 'name' field in frontmatter."""
    if "name" not in frontmatter:
        result.add_error("name-missing", "Missing 'name' in frontmatter", path=skill_md)
    elif not isinstance(frontmatter["name"], str):
        result.add_error("name-invalid", "'name' must be a string", path=skill_md)
    elif _normalize_name(str(frontmatter["name"])) != _normalize_name(skill_name):
        fm_name = frontmatter["name"]
        msg = f"'name' in frontmatter ({fm_name}) differs from directory ({skill_name})"
        result.add_warning("name-mismatch", msg, path=skill_md)


def _validate_description_field(
    frontmatter: Mapping[str, object],
    skill_md: Path,
    result: ValidationResult,
) -> None:
    """Validate the 'description' field in frontmatter."""
    if "description" not in frontmatter:
        result.add_error(
            "description-missing", "Missing 'description' in frontmatter", path=skill_md
        )
    elif not isinstance(frontmatter["description"], str):
        result.add_error(
            "description-invalid", "'description' must be a string", path=skill_md
        )
    else:
        # Check description quality
        desc_issues = _check_description_quality(str(frontmatter["description"]))
        for issue in desc_issues:
            result.add_warning("description-quality", issue, path=skill_md)


def _validate_body_length(
    body: str,
    skill_md: Path,
    result: ValidationResult,
) -> None:
    """Validate SKILL.md body length."""
    word_count = _count_words(body)
    if word_count < MIN_BODY_WORDS:
        msg = f"SKILL.md body is very short ({word_count} words); add more content"
        result.add_warning("body-too-short", msg, path=skill_md)
    elif word_count > MAX_BODY_WORDS:
        msg = f"SKILL.md body is long ({word_count} words); move content to references"
        result.add_warning("body-too-long", msg, path=skill_md)


def validate_skill(skill_dir: Path) -> ValidationResult:
    """Validate a skill directory.

    Checks:
    - Skill directory exists and has correct structure
    - SKILL.md exists with valid frontmatter
    - Required frontmatter fields (name, description)
    - Description quality (third-person, trigger phrases)
    - Body length (1,500-2,000 words target)
    - Writing style (imperative form, not second person)
    - Reference files have valid frontmatter

    Args:
        skill_dir: Path to the skill directory.

    Returns:
        ValidationResult with all issues found.
    """
    from oaps.templating import load_frontmatter_file

    skill_name = skill_dir.name
    result = ValidationResult(skill_name=skill_name, skill_dir=skill_dir)

    # Check skill directory exists
    if not skill_dir.is_dir():
        result.add_error("dir-missing", f"Skill directory not found: {skill_dir}")
        return result

    # Check SKILL.md exists
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        result.add_error("skill-md-missing", "SKILL.md not found", path=skill_dir)
        return result

    # Parse SKILL.md frontmatter
    frontmatter, body = load_frontmatter_file(skill_md)

    if frontmatter is None:
        result.add_error(
            "frontmatter-invalid", "Invalid or missing YAML frontmatter", path=skill_md
        )
        return result

    # Validate required frontmatter fields
    _validate_name_field(frontmatter, skill_name, skill_md, result)
    _validate_description_field(frontmatter, skill_md, result)

    # Validate body length
    _validate_body_length(body, skill_md, result)

    # Check writing style
    style_issues = _check_writing_style(body, skill_md)
    result.issues.extend(style_issues)

    # Validate references
    refs_dir = skill_dir / "references"
    if refs_dir.is_dir():
        for ref_path in refs_dir.glob("*.md"):
            _validate_reference(ref_path, result)

    return result


def _validate_reference(ref_path: Path, result: ValidationResult) -> None:
    """Validate a reference file.

    Args:
        ref_path: Path to the reference markdown file.
        result: ValidationResult to add issues to.
    """
    from oaps.templating import load_frontmatter_file

    frontmatter, _ = load_frontmatter_file(ref_path)

    if frontmatter is None:
        result.add_error(
            "ref-frontmatter-invalid",
            "Invalid or missing YAML frontmatter",
            path=ref_path,
        )
        return

    # Check required fields
    if "name" not in frontmatter:
        result.add_error(
            "ref-name-missing", "Missing 'name' in frontmatter", path=ref_path
        )
    elif not isinstance(frontmatter["name"], str):
        result.add_error("ref-name-invalid", "'name' must be a string", path=ref_path)

    if "description" not in frontmatter:
        result.add_error(
            "ref-description-missing",
            "Missing 'description' in frontmatter",
            path=ref_path,
        )
    elif not isinstance(frontmatter["description"], str):
        result.add_error(
            "ref-description-invalid", "'description' must be a string", path=ref_path
        )


def format_validation_result(result: ValidationResult) -> str:
    """Format a validation result for display.

    Args:
        result: The validation result to format.

    Returns:
        Formatted string output.
    """
    lines: list[str] = []

    lines.append(f"## Validation: {result.skill_name}\n")
    lines.append(f"Path: {result.skill_dir}\n")

    if result.is_valid and result.warning_count == 0:
        lines.append("**Result: PASSED** - No issues found.\n")
        return "\n".join(lines)

    if result.is_valid:
        lines.append(
            f"**Result: PASSED with warnings** - {result.warning_count} warning(s)\n"
        )
    else:
        err = result.error_count
        warn = result.warning_count
        lines.append(f"**Result: FAILED** - {err} error(s), {warn} warning(s)\n")

    lines.append("### Issues\n")
    lines.extend(
        f"- {issue.format()}"
        for issue in sorted(result.issues, key=lambda i: (i.severity.value, i.code))
    )

    return "\n".join(lines)
