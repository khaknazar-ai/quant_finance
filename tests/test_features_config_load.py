import pytest
from pydantic import ValidationError
from src.config.settings import FeaturesFileConfig, load_features_config


def test_load_features_config() -> None:
    config = load_features_config("configs/features.yaml")

    features = config.features

    assert features.price_column == "adjusted_close"
    assert features.return_windows == [1]
    assert features.momentum_windows == [21, 63, 126, 252]
    assert features.volatility_windows == [21, 63, 126]
    assert features.drawdown_windows == [63, 126, 252]
    assert features.ranking.enabled is True
    assert features.ranking.cross_sectional is True
    assert features.leakage_control.shift_features_by_days == 1


def test_features_config_rejects_duplicate_windows() -> None:
    payload = {
        "features": {
            "price_column": "adjusted_close",
            "return_windows": [1],
            "momentum_windows": [21, 21],
            "volatility_windows": [21],
            "drawdown_windows": [63],
            "ranking": {
                "enabled": True,
                "cross_sectional": True,
            },
            "leakage_control": {
                "shift_features_by_days": 1,
                "reason": "Test leakage control.",
            },
        }
    }

    with pytest.raises(ValidationError):
        FeaturesFileConfig.model_validate(payload)
