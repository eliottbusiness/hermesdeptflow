from datetime import UTC, datetime

from sdr_ai.config import BeReachConfig, ClientConfig
from sdr_ai.models import ActivitySignal, ICP, Offer, Prospect, QualificationStatus
from sdr_ai.scoring import ProspectScorer


def make_config() -> ClientConfig:
    return ClientConfig(
        client_name="Acme",
        slug="acme",
        icp=ICP(
            titres_cibles=["Head of Sales"],
            seniorite=["VP", "Director"],
            taille_entreprise=["51-200"],
            localisation=["France"],
            secteurs_activite=["SaaS"],
        ),
        offre=Offer(
            nom_offre="SDR IA",
            probleme_resolu=["prospection manuelle"],
            mots_cles_intention=["pipeline", "cold outreach"],
            concurrents_ou_alternatives=["Waalaxy"],
        ),
        bereach=BeReachConfig(dry_run=True),
    )


def test_hot_when_icp_activity_and_intent_match():
    cfg = make_config()
    prospect = Prospect(
        first_name="Ada",
        last_name="Lovelace",
        title="Head of Sales",
        company="Acme",
        linkedin_url="https://linkedin.com/in/ada",
        location="Paris, France",
        industry="B2B SaaS",
        company_size="51-200",
    )
    activities = [
        ActivitySignal(
            kind="post",
            text="Nous cherchons a ameliorer notre pipeline et notre cold outreach.",
            created_at=datetime.now(tz=UTC),
        )
    ]
    result = ProspectScorer(cfg).score(prospect, activities)
    assert result.status == QualificationStatus.HOT
    assert result.nb_signaux_activite == 1
    assert result.nb_signaux_intention >= 1
    assert result.priorite_interne >= 4


def test_rejects_non_icp_title():
    cfg = make_config()
    prospect = Prospect(
        title="Etudiant marketing",
        linkedin_url="https://linkedin.com/in/nope",
        location="Paris, France",
        company_size="51-200",
    )
    result = ProspectScorer(cfg).score(prospect, [])
    assert result.status == QualificationStatus.REJECTED
    assert "Titre" in result.reject_reason


def test_rejects_no_activity():
    cfg = make_config()
    prospect = Prospect(
        title="Head of Sales",
        linkedin_url="https://linkedin.com/in/no-activity",
        location="Paris, France",
        company_size="51-200",
        industry="SaaS",
    )
    result = ProspectScorer(cfg).score(prospect, [])
    assert result.status == QualificationStatus.REJECTED
    assert "Aucune activite" in result.reject_reason
