"""Markdown log generation for pipeline stages."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PipelineLogger:
    """Generate timestamped markdown logs for pipeline stages."""

    def __init__(self, stage_name: str, log_dir: Path = Path("data/logs")):
        """Initialize logger for a pipeline stage.

        Args:
            stage_name: Name of the pipeline stage (e.g., "download", "parse")
            log_dir: Directory to store log files
        """
        self.stage_name = stage_name
        self.log_dir = log_dir
        self.start_time = datetime.now(tz=timezone.utc)

        # Generate timestamped filename: YYYY-MM-DD-HH-MM-stage.md
        timestamp = self.start_time.strftime("%Y-%m-%d-%H-%M")
        self.log_path = log_dir / f"{timestamp}-{stage_name}.md"

        # Storage for log sections
        self.successful: list[str] = []
        self.failed: list[tuple[str, str]] = []
        self.skipped: list[str] = []
        self.details: list[str] = []

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_success(self, item: str, details: str = "") -> None:
        """Log a successful operation.

        Args:
            item: Item identifier (e.g., patch version)
            details: Additional details to display
        """
        self.successful.append(f"- ✅ {item}: {details}" if details else f"- ✅ {item}")

    def log_failure(self, item: str, error: str) -> None:
        """Log a failed operation.

        Args:
            item: Item identifier (e.g., patch version)
            error: Error message
        """
        self.failed.append((item, error))

    def log_skip(self, item: str, reason: str = "") -> None:
        """Log a skipped operation.

        Args:
            item: Item identifier (e.g., patch version)
            reason: Reason for skipping
        """
        self.skipped.append(f"- ⊘ {item}: {reason}" if reason else f"- ⊘ {item}")

    def log_detail(self, message: str) -> None:
        """Log detailed debugging information.

        Args:
            message: Detail message
        """
        self.details.append(message)

    def write(self, additional_summary: dict[str, Any] | None = None) -> Path:
        """Write the complete log to markdown file.

        Args:
            additional_summary: Additional summary statistics to include

        Returns:
            Path to the written log file
        """
        end_time = datetime.now(tz=timezone.utc)
        duration = end_time - self.start_time
        duration_str = f"{int(duration.total_seconds() // 60)}m {int(duration.total_seconds() % 60)}s"

        # Build markdown content
        lines = [
            f"# {self.stage_name.capitalize()} Report - {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
            f"**Started:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"**Duration:** {duration_str}",
            "",
            "## Summary",
            f"- ✅ {len(self.successful)} successful",
            f"- ❌ {len(self.failed)} failed",
            f"- ⊘ {len(self.skipped)} skipped",
        ]

        # Add additional summary items
        if additional_summary:
            for key, value in additional_summary.items():
                lines.append(f"- {key}: {value}")

        lines.append("")

        # Successful operations
        if self.successful:
            lines.append("## Successful")
            lines.extend(self.successful)
            lines.append("")

        # Failed operations
        if self.failed:
            lines.append("## Failed")
            for item, error in self.failed:
                lines.append(f"- ❌ {item}")
                # Indent error message
                for error_line in error.split("\n"):
                    lines.append(f"  {error_line}")
            lines.append("")

        # Skipped operations
        if self.skipped:
            lines.append("## Skipped")
            lines.extend(self.skipped)
            lines.append("")

        # Detailed output
        if self.details:
            lines.append("## Details")
            lines.extend(self.details)
            lines.append("")

        # Write to file
        content = "\n".join(lines)
        self.log_path.write_text(content, encoding="utf-8")

        return self.log_path
