"""
Collects low-confidence or ambiguous decisions produced during structural
analysis so the user can review and override them after the fact.

Decision types:
  sheet_type    — classifier confidence < 0.70
  column_type   — dominant type covers < 70 % of non-null values
  similar_sheets — two sheets share > 70 % of columns and similar names
"""
import re
from typing import Optional


class DecisionCollector:
    def __init__(self):
        self._items: list[dict] = []

    # ── Public API ──────────────────────────────────────────────────────────

    def collect_sheet(self, sheet_meta: dict):
        """Call once per analyzed sheet."""
        stype  = sheet_meta.get("sheet_type", "unknown")
        conf   = sheet_meta.get("confidence_score", 0.0)
        name   = sheet_meta.get("sheet_name", "")

        if stype == "empty":
            return

        if conf < 0.70:
            self._sheet_type(sheet_meta, name, stype, conf)

        if stype in ("transactional", "master"):
            for col in sheet_meta.get("columns_meta", []):
                col_conf = col.get("confidence", 1.0)
                ctype    = col.get("type", "text")
                if col_conf < 0.70 and ctype not in ("text", "text_long", "unknown", "null"):
                    self._column_type(name, col, col_conf)

    def collect_workbook(self, sheets_meta: list[dict]):
        """Call once after all sheets have been collected."""
        active = [s for s in sheets_meta if s.get("sheet_type") != "empty"]
        self._similar_sheets(active)

    def to_list(self) -> list[dict]:
        return list(self._items)

    def count(self) -> int:
        return len(self._items)

    # ── Decision builders ───────────────────────────────────────────────────

    def _sheet_type(self, meta: dict, name: str, detected: str, conf: float):
        self._items.append({
            "id": f"sheet_type:{name}",
            "type": "sheet_type",
            "severity": "high" if conf < 0.50 else "medium",
            "confidence": round(conf, 2),
            "title": f"Tipo de hoja ambiguo: «{name}»",
            "description": (
                f"Clasificada como «{detected}» con {int(conf * 100)} % de confianza. "
                "Confirma o corrige para que el DDL sea preciso."
            ),
            "agent_reasoning": (
                f"{meta.get('row_count', 0):,} filas · {meta.get('col_count', 0)} columnas"
                + (" · contiene fórmulas" if meta.get("has_formulas") else "")
                + (" · celdas combinadas" if meta.get("has_merged_cells") else "")
                + f". Confianza del clasificador: {int(conf * 100)} %."
            ),
            "context": {
                "sheet_name":   name,
                "detected":     detected,
                "row_count":    meta.get("row_count"),
                "col_count":    meta.get("col_count"),
                "has_formulas": meta.get("has_formulas"),
            },
            "options": [
                {"value": "transactional", "label": "Tabla transaccional (historial de eventos)"},
                {"value": "master",        "label": "Catálogo maestro (entidad de referencia)"},
                {"value": "dashboard",     "label": "Dashboard / Resumen (no generar tabla)"},
                {"value": "config",        "label": "Configuración (excluir del modelo)"},
                {"value": "ignore",        "label": "Ignorar esta hoja"},
            ],
            "default":     detected,
            "user_choice": None,
            "applied":     False,
        })

    def _column_type(self, sheet_name: str, col: dict, col_conf: float):
        col_name = col.get("name", "")
        detected = col.get("type", "text")
        sql_type = col.get("sql_type", "TEXT")
        samples  = col.get("sample_values", [])[:5]
        dist     = col.get("type_distribution", {})
        dist_str = ", ".join(f"{k}: {int(v*100)}%" for k, v in sorted(
            dist.items(), key=lambda x: -x[1])[:3])

        self._items.append({
            "id": f"column_type:{sheet_name}:{col_name}",
            "type": "column_type",
            "severity": "medium",
            "confidence": round(col_conf, 2),
            "title": f"Tipo de columna mixto: «{col_name}»",
            "description": (
                f"Solo {int(col_conf * 100)} % de los valores son «{detected}» "
                f"en la hoja «{sheet_name}»."
            ),
            "agent_reasoning": (
                f"Distribución: {dist_str}. "
                f"Muestra: {', '.join(str(v) for v in samples)}. "
                "Pueden ser errores de captura o un campo multi-formato."
            ),
            "context": {
                "sheet_name":   sheet_name,
                "column":       col_name,
                "detected":     detected,
                "sql_type":     sql_type,
                "confidence":   round(col_conf, 2),
                "samples":      samples,
                "distribution": dist,
            },
            "options": [
                {"value": "keep",    "label": f"Mantener como {sql_type}"},
                {"value": "text",    "label": "Forzar TEXT (más flexible)"},
                {"value": "integer", "label": "Forzar BIGINT"},
                {"value": "decimal", "label": "Forzar NUMERIC(18,4)"},
            ],
            "default":     "keep",
            "user_choice": None,
            "applied":     False,
        })

    def _similar_sheets(self, sheets: list[dict]):
        seen: set[str] = set()
        for i, sa in enumerate(sheets):
            for j, sb in enumerate(sheets):
                if j <= i:
                    continue
                na = sa.get("sheet_name", "")
                nb = sb.get("sheet_name", "")
                key = f"{na}|{nb}"
                if key in seen:
                    continue
                seen.add(key)

                clean_a = re.sub(r"[^a-z0-9]", "", na.lower())
                clean_b = re.sub(r"[^a-z0-9]", "", nb.lower())
                # Require at least 4 chars to avoid "is" matching "issuance" etc.
                long_enough = len(clean_a) >= 4 and len(clean_b) >= 4
                name_similar = (
                    long_enough and
                    (clean_a in clean_b or clean_b in clean_a or
                     _edit_distance(clean_a, clean_b) <= 2)
                )
                if not name_similar:
                    continue

                cols_a = {c.get("name") for c in sa.get("columns_meta", [])}
                cols_b = {c.get("name") for c in sb.get("columns_meta", [])}
                if not cols_a or not cols_b:
                    continue

                overlap = len(cols_a & cols_b) / max(len(cols_a), len(cols_b))
                if overlap < 0.70:
                    continue

                shared = sorted(cols_a & cols_b)[:8]
                self._items.append({
                    "id": f"similar_sheets:{na}:{nb}",
                    "type": "similar_sheets",
                    "severity": "medium",
                    "confidence": round(overlap, 2),
                    "title": f"Hojas similares: «{na}» y «{nb}»",
                    "description": (
                        f"Comparten {int(overlap * 100)} % de columnas y nombres parecidos. "
                        "Podrían ser la misma entidad en períodos distintos."
                    ),
                    "agent_reasoning": (
                        f"Columnas en común: {', '.join(shared)}."
                        f" «{na}» tiene {sa.get('row_count',0):,} filas,"
                        f" «{nb}» tiene {sb.get('row_count',0):,} filas."
                    ),
                    "context": {
                        "sheet_a": na, "sheet_b": nb,
                        "overlap": round(overlap, 2),
                        "shared_columns": shared,
                        "rows_a": sa.get("row_count"), "rows_b": sb.get("row_count"),
                    },
                    "options": [
                        {"value": "separate", "label": "Mantener como tablas separadas"},
                        {"value": "ignore_b", "label": f"Ignorar «{nb}» (posible duplicado)"},
                    ],
                    "default":     "separate",
                    "user_choice": None,
                    "applied":     False,
                })


def _edit_distance(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            prev, dp[j] = dp[j], prev if a[i-1] == b[j-1] else 1 + min(prev, dp[j], dp[j-1])
    return dp[n]
