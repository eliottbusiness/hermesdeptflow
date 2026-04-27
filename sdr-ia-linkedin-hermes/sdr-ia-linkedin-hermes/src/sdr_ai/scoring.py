from __future__ import annotations

from datetime import UTC, timedelta

from .config import ClientConfig
from .llm import LLMIntentAnalyzer
from .models import ActivitySignal, PipelineStatus, Prospect, QualificationStatus, ScoringResult
from .utils import contains_any, normalize_text, now_utc, parse_datetime


SENIORITY_KEYWORDS: dict[str, list[str]] = {
    "c-level": ["ceo", "coo", "cfo", "cto", "cro", "cmo", "chief", "fondateur", "founder"],
    "vp": ["vp", "vice president", "vice-president", "head of", "directeur general"],
    "director": ["director", "directeur", "directrice"],
    "manager": ["manager", "responsable", "lead"],
    "senior": ["senior", "principal", "staff"],
    "entry": ["junior", "assistant", "associate", "entry"],
}


class ProspectScorer:
    def __init__(self, config: ClientConfig, llm: LLMIntentAnalyzer | None = None) -> None:
        self.config = config
        self.llm = llm

    def score(self, prospect: Prospect, activities: list[ActivitySignal]) -> ScoringResult:
        icp_ok, reject_reason, icp_signals = self._check_icp(prospect)
        if not icp_ok:
            return ScoringResult(
                prospect=prospect,
                status=QualificationStatus.REJECTED,
                pipeline_status=PipelineStatus.REJECTED,
                reject_reason=reject_reason,
                signaux_detectes=icp_signals,
            )

        recent_activities = self._recent_activities(activities)
        activity_count = len(recent_activities)
        if activity_count == 0:
            return ScoringResult(
                prospect=prospect,
                status=QualificationStatus.REJECTED,
                pipeline_status=PipelineStatus.REJECTED,
                reject_reason="Aucune activite LinkedIn detectee sur 45 jours",
                signaux_detectes=icp_signals,
            )

        activity_signals = self._activity_signals(recent_activities)
        dernier_post = None
        dated = [s.created_at for s in recent_activities if s.created_at]
        if dated:
            dernier_post = max(dated).date()

        heuristic_intent_count, heuristic_signals = self._heuristic_intent(prospect, recent_activities)
        llm_count = 0
        llm_signals: list[str] = []
        llm_explanation = ""
        if self.llm is not None:
            try:
                llm_count, llm_signals, llm_explanation = self.llm.analyze(
                    prospect, self.config.offre, recent_activities
                )
            except Exception as exc:  # noqa: BLE001 - scoring must degrade gracefully
                llm_explanation = f"LLM indisponible: {exc}"

        intent_signals = list(dict.fromkeys(heuristic_signals + llm_signals))
        intent_count = max(heuristic_intent_count, llm_count, len(intent_signals))
        status = QualificationStatus.HOT if intent_count > 0 else QualificationStatus.WARM
        priority = (intent_count * 3) + activity_count
        return ScoringResult(
            prospect=prospect,
            status=status,
            pipeline_status=PipelineStatus.NEW,
            nb_signaux_activite=activity_count,
            nb_signaux_intention=intent_count,
            priorite_interne=priority,
            signaux_detectes=icp_signals + activity_signals + intent_signals,
            dernier_post=dernier_post,
            llm_explanation=llm_explanation,
        )

    def _check_icp(self, prospect: Prospect) -> tuple[bool, str, list[str]]:
        icp = self.config.icp
        signals: list[str] = []
        title = prospect.title or ""
        text_blob = " ".join(
            [prospect.title, prospect.company, prospect.industry, prospect.location, str(prospect.raw)]
        )

        if contains_any(title, icp.titres_a_exclure):
            return False, "Titre exclu par l'ICP", signals
        if contains_any(prospect.industry, icp.secteurs_a_exclure):
            return False, "Secteur exclu par l'ICP", signals

        if icp.titres_cibles and not contains_any(title, icp.titres_cibles):
            return False, "Titre hors ICP", signals
        signals.append(f"Titre ICP: {title}")

        if icp.seniorite and not self._seniority_match(title, icp.seniorite):
            return False, "Seniorite hors ICP", signals
        if icp.seniorite:
            signals.append("Seniorite compatible ICP")

        if icp.taille_entreprise and not _company_size_match(
            prospect.company_size, icp.taille_entreprise
        ):
            return False, "Taille entreprise hors ICP", signals
        if prospect.company_size:
            signals.append(f"Taille entreprise: {prospect.company_size}")

        if icp.localisation and not contains_any(prospect.location, icp.localisation):
            return False, "Localisation hors ICP", signals
        if prospect.location:
            signals.append(f"Localisation: {prospect.location}")

        # Secteur = indice souple, pas eliminatoire dur.
        if icp.secteurs_activite and contains_any(text_blob, icp.secteurs_activite):
            signals.append("Secteur ou mots-cles secteur compatibles")
        elif icp.secteurs_activite:
            signals.append("Secteur LinkedIn non confirme, conserve comme critere souple")

        if icp.technologies_stack and contains_any(text_blob, icp.technologies_stack):
            signals.append("Technologie stack detectee")
        return True, "", signals

    def _seniority_match(self, title: str, expected: list[str]) -> bool:
        title_norm = normalize_text(title)
        for item in expected:
            key = normalize_text(item)
            keywords = SENIORITY_KEYWORDS.get(key, [key])
            if any(k in title_norm for k in keywords):
                return True
        return False

    def _recent_activities(self, activities: list[ActivitySignal]) -> list[ActivitySignal]:
        cutoff = now_utc() - timedelta(days=45)
        recent: list[ActivitySignal] = []
        for item in activities:
            dt = item.created_at or parse_datetime(item.raw.get("date"))
            if dt is None or dt >= cutoff:
                recent.append(item)
        return recent

    def _activity_signals(self, activities: list[ActivitySignal]) -> list[str]:
        kinds = {normalize_text(a.kind) for a in activities}
        output: list[str] = []
        if any("post" in k or "publish" in k for k in kinds):
            output.append("Activite: a publie sur LinkedIn sur 45 jours")
        if any("comment" in k for k in kinds):
            output.append("Activite: a commente sur LinkedIn sur 45 jours")
        if any("like" in k or "reaction" in k for k in kinds):
            output.append("Activite: a like/reagi sur LinkedIn sur 45 jours")
        if not output:
            output.append("Activite LinkedIn detectee sur 45 jours")
        return output

    def _heuristic_intent(
        self, prospect: Prospect, activities: list[ActivitySignal]
    ) -> tuple[int, list[str]]:
        offer = self.config.offre
        icp = self.config.icp
        keywords = (
            offer.mots_cles_intention
            + offer.probleme_resolu
            + offer.concurrents_ou_alternatives
            + icp.signaux_intention_cles
        )
        signals: list[str] = []
        for activity in activities:
            text = activity.text or ""
            matched = [kw for kw in keywords if kw and normalize_text(kw) in normalize_text(text)]
            if matched:
                signals.append(f"Intention: mention de {', '.join(matched[:3])}")
        title_blob = normalize_text(prospect.title + " " + str(prospect.raw))
        if any(token in title_blob for token in ["new role", "nouveau poste", "started", "a commence"]):
            signals.append("Intention: changement de poste recent probable")
        unique = list(dict.fromkeys(signals))
        return len(unique), unique


def _company_size_match(actual: str, expected: list[str]) -> bool:
    if not expected:
        return True
    actual_norm = normalize_text(actual).replace(" ", "")
    for item in expected:
        exp = normalize_text(item).replace(" ", "")
        if exp in actual_norm or actual_norm in exp:
            return True
    return False
