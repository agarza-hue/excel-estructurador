import pandas as pd
import numpy as np
from typing import Any
import structlog
import openpyxl
from pathlib import Path

log = structlog.get_logger()


class DataQualityEngine:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def run(self, workbook_structure: dict) -> dict:
        log.info("quality_check_start", path=str(self.file_path))

        sheets = workbook_structure.get("sheets", [])
        sheet_reports = []
        global_issues = []

        for sheet_meta in sheets:
            if sheet_meta.get("sheet_type") == "empty":
                continue

            report = self._check_sheet(sheet_meta)
            sheet_reports.append(report)
            global_issues.extend(report.get("critical_issues", []))

        overall_score = self._compute_overall_score(sheet_reports)
        risk_score = self._compute_risk_score(sheet_reports, global_issues)

        return {
            "quality_score": round(overall_score, 2),
            "risk_score": round(risk_score, 2),
            "sheet_reports": sheet_reports,
            "global_issues": global_issues,
            "summary": self._build_summary(sheet_reports, overall_score, risk_score),
            "recommendations": self._generate_recommendations(sheet_reports),
        }

    def _check_sheet(self, sheet_meta: dict) -> dict:
        issues = []
        warnings = []
        sheet_name = sheet_meta.get("sheet_name", "unknown")
        cols = sheet_meta.get("columns_meta", [])
        row_count = sheet_meta.get("row_count", 0)

        col_scores = []

        for col in cols:
            col_issues = []
            col_warnings = []
            col_name = col.get("name", "unknown")
            null_rate = col.get("null_rate", 0)
            cardinality = col.get("cardinality", 0)
            total = col.get("total_values", 1)
            col_type = col.get("type", "unknown")
            type_dist = col.get("type_distribution", {})
            is_unique = col.get("is_unique", False)

            # Null rate checks
            if null_rate == 1.0:
                col_issues.append({"type": "empty_column", "column": col_name,
                                   "detail": "Column is 100% empty"})
            elif null_rate > 0.5:
                col_warnings.append({"type": "high_null_rate", "column": col_name,
                                     "detail": f"{null_rate*100:.0f}% null values"})
            elif null_rate > 0.1:
                col_warnings.append({"type": "moderate_null_rate", "column": col_name,
                                     "detail": f"{null_rate*100:.0f}% null values"})

            # Mixed types
            if len(type_dist) > 2 and col_type not in ("null", "unknown"):
                dominant_pct = max(type_dist.values()) if type_dist else 1
                if dominant_pct < 0.85:
                    col_issues.append({
                        "type": "mixed_data_types",
                        "column": col_name,
                        "detail": f"Multiple types detected: {list(type_dist.keys())}",
                        "type_distribution": type_dist,
                    })

            # Duplicate column names (checked at meta level already sanitized)
            # PK candidate with nulls
            if is_unique and null_rate > 0:
                col_issues.append({
                    "type": "pk_has_nulls",
                    "column": col_name,
                    "detail": "Unique column (PK candidate) contains null values",
                })

            # Low cardinality on what might be a numeric measure
            if col_type in ("integer", "decimal") and cardinality <= 3 and total > 10:
                col_warnings.append({
                    "type": "suspicious_low_cardinality",
                    "column": col_name,
                    "detail": f"Numeric column has only {cardinality} distinct values",
                })

            issues.extend(col_issues)
            warnings.extend(col_warnings)

            col_score = self._col_score(null_rate, len(col_issues), len(col_warnings))
            col_scores.append(col_score)

        # Sheet-level checks
        if sheet_meta.get("has_merged_cells"):
            warnings.append({
                "type": "merged_cells",
                "detail": "Sheet has merged cells — may cause data extraction issues",
            })

        if sheet_meta.get("formula_count", 0) > row_count * 0.5:
            warnings.append({
                "type": "formula_heavy_sheet",
                "detail": "Over 50% of cells are formulas — data may be derived, not source",
            })

        sheet_score = sum(col_scores) / max(len(col_scores), 1)
        critical = [i for i in issues if i.get("type") in
                   ("empty_column", "mixed_data_types", "pk_has_nulls")]

        return {
            "sheet_name": sheet_name,
            "sheet_type": sheet_meta.get("sheet_type"),
            "quality_score": round(sheet_score, 2),
            "issues": issues,
            "warnings": warnings,
            "critical_issues": critical,
            "issue_count": len(issues),
            "warning_count": len(warnings),
        }

    def _col_score(self, null_rate: float, issue_count: int, warning_count: int) -> float:
        score = 1.0
        score -= null_rate * 0.5
        score -= issue_count * 0.15
        score -= warning_count * 0.05
        return max(0.0, min(1.0, score))

    def _compute_overall_score(self, reports: list) -> float:
        if not reports:
            return 0.5
        scores = [r["quality_score"] for r in reports]
        return sum(scores) / len(scores)

    def _compute_risk_score(self, reports: list, global_issues: list) -> float:
        base = 1 - self._compute_overall_score(reports)
        critical_penalty = len(global_issues) * 0.05
        return min(1.0, base + critical_penalty)

    def _build_summary(self, reports: list, quality: float, risk: float) -> dict:
        total_issues = sum(r["issue_count"] for r in reports)
        total_warnings = sum(r["warning_count"] for r in reports)

        grade = "A" if quality >= 0.9 else "B" if quality >= 0.75 else "C" if quality >= 0.6 else "D"

        return {
            "total_sheets_analyzed": len(reports),
            "total_issues": total_issues,
            "total_warnings": total_warnings,
            "quality_grade": grade,
            "risk_level": "low" if risk < 0.3 else "medium" if risk < 0.6 else "high",
        }

    def _generate_recommendations(self, reports: list) -> list[dict]:
        recs = []
        for r in reports:
            for issue in r.get("issues", []):
                itype = issue.get("type")
                if itype == "empty_column":
                    recs.append({
                        "priority": "high",
                        "sheet": r["sheet_name"],
                        "action": f"Remove or investigate empty column: {issue.get('column')}",
                    })
                elif itype == "mixed_data_types":
                    recs.append({
                        "priority": "high",
                        "sheet": r["sheet_name"],
                        "action": f"Standardize data type in column: {issue.get('column')}",
                        "detail": issue.get("detail"),
                    })
                elif itype == "pk_has_nulls":
                    recs.append({
                        "priority": "critical",
                        "sheet": r["sheet_name"],
                        "action": f"Fill null values in unique key column: {issue.get('column')}",
                    })

        return sorted(recs, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["priority"], 4))
