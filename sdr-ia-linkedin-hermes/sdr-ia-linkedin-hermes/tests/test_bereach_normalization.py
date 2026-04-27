from sdr_ai.bereach import normalize_prospect


def test_normalize_prospect_from_sdk_like_payload():
    prospect = normalize_prospect(
        {
            "fullName": "Grace Hopper",
            "headline": "VP Sales",
            "company": {"name": "Navy SaaS", "size": "51-200", "industry": "Software"},
            "profileUrl": "https://linkedin.com/in/grace",
            "location": "France",
        }
    )
    assert prospect.first_name == "Grace"
    assert prospect.last_name == "Hopper"
    assert prospect.title == "VP Sales"
    assert prospect.company == "Navy SaaS"
    assert prospect.company_size == "51-200"
