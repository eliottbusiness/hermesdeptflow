from sdr_ai.config import BeReachConfig, ClientConfig
from sdr_ai.models import ICP, Offer
from sdr_ai.quota import QuotaManager


def test_quota_blocks_after_daily_limit(tmp_path):
    cfg = ClientConfig(
        client_name="Acme",
        slug="acme",
        icp=ICP(),
        offre=Offer(),
        bereach=BeReachConfig(daily_connection_limit=1, weekly_connection_limit=10, dry_run=True),
    )
    quota = QuotaManager(cfg, state_dir=tmp_path)
    assert quota.can_connect()
    quota.register_connection()
    assert not quota.can_connect()
