from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class QualificationStatus(StrEnum):
    REJECTED = "REJETE"
    WARM = "WARM"
    HOT = "HOT"


class PipelineStatus(StrEnum):
    NEW = "NOUVEAU"
    CONNECTION_SENT = "DEMANDE_ENVOYEE"
    CONNECTED = "CONNECTE"
    FOLLOW_UP_1 = "RELANCE_1"
    REPLIED = "REPONDU"
    MEETING_BOOKED = "RDV_PRIS"
    DISQUALIFIED = "DISQUALIFIE"
    REJECTED = "REJETE"


CRM_COLUMNS: list[str] = [
    "id",
    "date_ajout",
    "prenom",
    "nom",
    "titre",
    "entreprise",
    "url_linkedin",
    "localisation",
    "secteur",
    "taille_entreprise",
    "statut_qualification",
    "nb_signaux_activite",
    "nb_signaux_intention",
    "priorite_interne",
    "signaux_detectes",
    "dernier_post",
    "statut",
    "date_connexion_envoyee",
    "date_connexion_acceptee",
    "notes",
    "source_run",
]


class ICP(BaseModel):
    titres_cibles: list[str] = Field(default_factory=list)
    seniorite: list[str] = Field(default_factory=list)
    secteurs_activite: list[str] = Field(default_factory=list)
    taille_entreprise: list[str] = Field(default_factory=list)
    localisation: list[str] = Field(default_factory=list)
    technologies_stack: list[str] = Field(default_factory=list)
    annees_experience_min: int | None = None
    signaux_intention_cles: list[str] = Field(default_factory=list)
    titres_a_exclure: list[str] = Field(default_factory=list)
    secteurs_a_exclure: list[str] = Field(default_factory=list)


class Offer(BaseModel):
    nom_offre: str = ""
    probleme_resolu: list[str] = Field(default_factory=list)
    benefice_principal: str = ""
    mots_cles_intention: list[str] = Field(default_factory=list)
    concurrents_ou_alternatives: list[str] = Field(default_factory=list)


class Prospect(BaseModel):
    first_name: str = ""
    last_name: str = ""
    title: str = ""
    company: str = ""
    linkedin_url: str = ""
    location: str = ""
    industry: str = ""
    company_size: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("linkedin_url", mode="before")
    @classmethod
    def normalize_url(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @property
    def full_name(self) -> str:
        return " ".join([self.first_name, self.last_name]).strip()


class ActivitySignal(BaseModel):
    kind: str
    text: str = ""
    created_at: datetime | None = None
    url: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class ScoringResult(BaseModel):
    prospect: Prospect
    status: QualificationStatus
    pipeline_status: PipelineStatus = PipelineStatus.NEW
    nb_signaux_activite: int = 0
    nb_signaux_intention: int = 0
    priorite_interne: int = 0
    signaux_detectes: list[str] = Field(default_factory=list)
    dernier_post: date | None = None
    reject_reason: str = ""
    llm_explanation: str = ""

    @property
    def qualified(self) -> bool:
        return self.status in {QualificationStatus.WARM, QualificationStatus.HOT}


class RunReport(BaseModel):
    run_id: str
    started_at: datetime
    ended_at: datetime | None = None
    found_count: int = 0
    qualified_count: int = 0
    warm_count: int = 0
    hot_count: int = 0
    rejected_count: int = 0
    added_to_crm: int = 0
    deduplicated: int = 0
    connections_sent: int = 0
    connection_errors: int = 0
    weekly_connection_used: int = 0
    weekly_connection_limit: int = 60
    top_prospects: list[ScoringResult] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def qualification_rate(self) -> float:
        return 0.0 if self.found_count == 0 else self.qualified_count / self.found_count
