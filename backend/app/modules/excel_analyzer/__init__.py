"""Excel analysis core, ported from the excel_platform project.

Pure-python (openpyxl + pandas), no infra coupling. The high-value reuse:
structure detection, type inference, formula parsing, quality scoring.

`analyze_workbook` is the thin entry point used by the API layer; it wraps
ExcelAnalyzer and adds a structural classification (the 4 categories the
upload wizard speaks: clean / multi-header / cross-tab / multi-section).
"""
from .analyzer import ExcelAnalyzer
from .structural_classifier import classify_structure, STRUCTURE_LABELS

__all__ = ["ExcelAnalyzer", "analyze_workbook", "classify_structure", "STRUCTURE_LABELS"]


def analyze_workbook(file_path: str) -> dict:
    """Run the full analysis and annotate each sheet with its structural type."""
    result = ExcelAnalyzer(file_path).analyze(collect_decisions=True)
    for sheet in result["workbook_structure"]["sheets"]:
        structure, reasons = classify_structure(sheet)
        sheet["structure_type"] = structure
        sheet["structure_label"] = STRUCTURE_LABELS[structure]
        sheet["structure_reasons"] = reasons
    return result
