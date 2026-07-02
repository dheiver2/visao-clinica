"""Relatório agregado e ANONIMIZADO por setor — NR-01.

Consolida várias triagens de bem-estar em um relatório por setor, mostrando a
**distribuição percentual** de colaboradores por faixa de risco em cada fator —
sem identificar indivíduos. É o formato adequado para compor o PGR/GRO.

Armazena apenas os NÍVEIS derivados (baixo/moderado/alto), nunca biometria,
imagem ou identificação — privacidade por design (LGPD).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.clinical.nr01 import PSYCH_PANEL, PsychoIndicator, overall_risk
from app.paths import user_data_dir

STORE_DIR = user_data_dir() / "data" / "nr01"
LEVELS = ("baixo", "moderado", "alto")


@dataclass
class SectorReport:
    setor: str
    n: int
    by_factor: dict = field(default_factory=dict)     # factor -> {nivel: pct}
    overall_dist: dict = field(default_factory=dict)  # nivel -> pct (risco por sessão)
    priority: list = field(default_factory=list)      # fatores priorizados (% alto)

    def to_dict(self) -> dict:
        return {"setor": self.setor, "n": self.n, "by_factor": self.by_factor,
                "overall_dist": self.overall_dist, "priority": self.priority}


def append_session(setor: str, indicators: list[PsychoIndicator]) -> None:
    """Acrescenta uma triagem ANONIMIZADA (só níveis) à amostra do setor."""
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    rec = {"setor": setor, "levels": {i.key: i.level for i in indicators},
           "overall": overall_risk(indicators)}
    with (STORE_DIR / "sessions.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _load(setor: str | None = None) -> list[dict]:
    path = STORE_DIR / "sessions.jsonl"
    if not path.exists():
        return []
    recs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if setor is None or r.get("setor") == setor:
            recs.append(r)
    return recs


def aggregate(setor: str, sessions: list[list[PsychoIndicator]] | None = None) -> SectorReport:
    """Consolida as triagens do setor. Se `sessions` não for dado, lê do store."""
    if sessions is not None:
        recs = [{"levels": {i.key: i.level for i in s}, "overall": overall_risk(s)}
                for s in sessions]
    else:
        recs = _load(setor)
    n = len(recs)
    rep = SectorReport(setor=setor, n=n)
    if n == 0:
        return rep
    names = {k: nm for k, nm, _ in PSYCH_PANEL}
    for key, name in names.items():
        counts = {lv: 0 for lv in LEVELS}
        for r in recs:
            lv = r["levels"].get(key)
            if lv in counts:
                counts[lv] += 1
        total = sum(counts.values()) or 1
        rep.by_factor[name] = {lv: round(100 * counts[lv] / total, 1) for lv in LEVELS}
    od = {lv: 0 for lv in LEVELS}
    for r in recs:
        if r["overall"] in od:
            od[r["overall"]] += 1
    rep.overall_dist = {lv: round(100 * od[lv] / n, 1) for lv in LEVELS}
    # Prioriza fatores com maior % de risco alto
    rep.priority = sorted(rep.by_factor.items(), key=lambda kv: kv[1]["alto"],
                          reverse=True)
    rep.priority = [nm for nm, d in rep.priority if d["alto"] > 0][:3]
    return rep
