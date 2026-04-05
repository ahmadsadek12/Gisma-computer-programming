"""Export analysis results to CSV, JSON, and TXT under exports/."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from models.contributor_stats import ContributorStats
from services.conflict_detector import ConflictRisk
from services.repository_analyzer import AnalysisResult


class ReportExporter:
    """CSV, JSON, and text exports under exports/."""

    def __init__(self, exports_dir: Path) -> None:
        self._dir = exports_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    def export_csv(
        self,
        owner: str,
        repo: str,
        contributors: list[ContributorStats],
    ) -> Path:
        path = self._dir / f"{owner}_{repo}_{self._timestamp()}_contributors.csv"
        try:
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(
                    [
                        "github_username",
                        "display_name",
                        "commit_count",
                        "first_commit_date",
                        "last_commit_date",
                        "latest_commit_hash",
                        "latest_commit_message",
                    ]
                )
                for c in contributors:
                    w.writerow(
                        [
                            c.github_username,
                            c.display_name or "",
                            c.commit_count,
                            c.first_commit_date,
                            c.last_commit_date,
                            c.latest_commit_hash,
                            c.latest_commit_message,
                        ]
                    )
        except OSError as e:
            raise RuntimeError(f"Could not write CSV export: {e}") from e
        return path

    def export_json(
        self,
        analysis: AnalysisResult,
        conflicts: Optional[list[ConflictRisk]] = None,
    ) -> Path:
        path = self._dir / f"{analysis.owner}_{analysis.repo_name}_{self._timestamp()}_analysis.json"
        payload: dict[str, Any] = {
            "owner": analysis.owner,
            "repo_name": analysis.repo_name,
            "repo_description": analysis.repo_description,
            "github_contributors_endpoint_count": analysis.github_contributors_endpoint_count,
            "total_commits": analysis.total_commits,
            "total_contributors": analysis.total_contributors,
            "latest_commit_date": analysis.latest_commit_date,
            "latest_commit_hash": analysis.latest_commit_hash,
            "latest_commit_message": analysis.latest_commit_message,
            "most_active_contributor": analysis.most_active_contributor,
            "commits_per_contributor": analysis.commits_per_contributor,
            "commits_per_day": [{"date": d, "count": n} for d, n in analysis.commits_per_day],
            "message_categories": analysis.message_categories,
            "contributors": [
                {
                    "github_username": c.github_username,
                    "display_name": c.display_name,
                    "commit_count": c.commit_count,
                    "first_commit_date": c.first_commit_date,
                    "last_commit_date": c.last_commit_date,
                    "latest_commit_hash": c.latest_commit_hash,
                    "latest_commit_message": c.latest_commit_message,
                }
                for c in analysis.contributor_stats
            ],
            "commits": [
                {
                    "sha": c.sha,
                    "short_sha": c.short_sha,
                    "author": c.author_login,
                    "message": c.message,
                    "date": c.committed_at,
                }
                for c in analysis.commits
            ],
        }
        if conflicts is not None:
            payload["conflict_risks"] = [
                {
                    "file_path": x.file_path,
                    "contributor_a": x.contributor_a,
                    "contributor_b": x.contributor_b,
                    "commit_hash_a": x.commit_hash_a,
                    "commit_hash_b": x.commit_hash_b,
                    "date_a": x.date_a,
                    "date_b": x.date_b,
                    "risk_level": x.risk_level,
                    "explanation": x.explanation,
                    "recommendation": x.recommendation,
                }
                for x in conflicts
            ]

        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise RuntimeError(f"Could not write JSON export: {e}") from e
        return path

    def export_txt(
        self,
        analysis: AnalysisResult,
        conflicts: Optional[list[ConflictRisk]] = None,
    ) -> Path:
        path = self._dir / f"{analysis.owner}_{analysis.repo_name}_{self._timestamp()}_summary.txt"
        lines = [
            "GitHub Repository Analyzer — Summary Report",
            "=" * 50,
            f"Repository: {analysis.owner}/{analysis.repo_name}",
        ]
        if analysis.repo_description:
            lines.append(f"Description: {analysis.repo_description}")
        if analysis.github_contributors_endpoint_count is not None:
            lines.append(
                f"GitHub contributors (API list length): "
                f"{analysis.github_contributors_endpoint_count}"
            )
        lines.extend(
            [
            f"Total commits analyzed: {analysis.total_commits}",
            f"Distinct contributors: {analysis.total_contributors}",
            f"Most active contributor: {analysis.most_active_contributor}",
            f"Latest commit: {analysis.latest_commit_hash[:7] if analysis.latest_commit_hash else '—'}",
            f"Latest commit date: {analysis.latest_commit_date}",
            f"Latest message: {analysis.latest_commit_message}",
            "",
            "Message categories (heuristic):",
            ]
        )
        for k, v in sorted(analysis.message_categories.items()):
            lines.append(f"  {k}: {v}")
        lines.extend(["", "Top contributors:"])
        for c in analysis.contributor_stats[:10]:
            lines.append(
                f"  {c.github_username}: {c.commit_count} commits "
                f"(last: {c.last_commit_date[:10] if c.last_commit_date else '—'})"
            )
        if conflicts:
            lines.extend(["", "Potential conflict risks (heuristic):"])
            for x in conflicts[:50]:
                lines.append(
                    f"  [{x.risk_level}] {x.file_path} — {x.contributor_a} vs {x.contributor_b}"
                )
                lines.append(f"      {x.explanation}")
        try:
            with path.open("w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except OSError as e:
            raise RuntimeError(f"Could not write TXT export: {e}") from e
        return path
