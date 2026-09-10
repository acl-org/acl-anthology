import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "bin" / "geocode_affiliations.py"
SPEC = importlib.util.spec_from_file_location("geocode_affiliations", SCRIPT_PATH)
assert SPEC and SPEC.loader
geocode_affiliations = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(geocode_affiliations)


def test_preferred_external_id_uses_unambiguous_ror_link():
    record = {
        "external_ids": [
            {
                "type": "wikidata",
                "all": ["Q49088", "Q123"],
                "preferred": "Q49088",
            }
        ]
    }

    assert geocode_affiliations.preferred_external_id(record, "wikidata") == "Q49088"


def test_coordinate_from_wikidata_entity_prefers_preferred_earth_claim():
    def claim(
        latitude,
        longitude,
        *,
        rank="normal",
        globe="Q2",
        precision=0.00027777777777778,
    ):
        return {
            "rank": rank,
            "mainsnak": {
                "datavalue": {
                    "value": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "globe": f"http://www.wikidata.org/entity/{globe}",
                        "precision": precision,
                    }
                }
            },
        }

    entity = {
        "claims": {
            "P625": [
                claim(40.71427, -74.00597, rank="normal"),
                claim(40.8075, -73.961944444444, rank="preferred"),
                claim(1, 2, rank="deprecated"),
                claim(3, 4, rank="preferred", globe="Q111"),
            ]
        }
    }

    assert geocode_affiliations.coordinate_from_wikidata_entity(entity) == (
        40.8075,
        -73.96194,
    )


def test_coordinate_from_wikidata_entity_rejects_coarse_or_ambiguous_claims():
    def claim(latitude, longitude, precision=0.0001):
        return {
            "rank": "normal",
            "mainsnak": {
                "datavalue": {
                    "value": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "globe": "http://www.wikidata.org/entity/Q2",
                        "precision": precision,
                    }
                }
            },
        }

    assert (
        geocode_affiliations.coordinate_from_wikidata_entity(
            {"claims": {"P625": [claim(40, -73, precision=1)]}}
        )
        is None
    )
    assert (
        geocode_affiliations.coordinate_from_wikidata_entity(
            {"claims": {"P625": [claim(40, -73), claim(41, -74)]}}
        )
        is None
    )


def test_coordinate_sources_keep_ror_identity_and_use_wikidata_point():
    cache = {
        "Columbia University": {
            "name": "Columbia University",
            "ror_id": "https://ror.org/00hj8s172",
            "lat": 40.71427,
            "lon": -74.00597,
        }
    }
    organizations = {
        "https://ror.org/00hj8s172": {
            "coordinate_source": "ror-geonames",
            "country": "US",
            "lat": 40.71427,
            "lon": -74.00597,
            "ror_id": "https://ror.org/00hj8s172",
            "sector": "academic",
            "source": "ror",
            "wikidata_id": "Q49088",
        }
    }

    geocode_affiliations.apply_ror_metadata(cache, organizations)
    sources = geocode_affiliations.apply_wikidata_coordinates(
        cache, {"Q49088": (40.8075, -73.96194)}
    )

    assert cache["Columbia University"] == {
        "coordinate_source": "wikidata",
        "country": "US",
        "lat": 40.8075,
        "lon": -73.96194,
        "name": "Columbia University",
        "ror_id": "https://ror.org/00hj8s172",
        "sector": "academic",
        "source": "ror",
        "wikidata_id": "Q49088",
    }
    assert sources == {"wikidata": 1}


def test_ror_metadata_refresh_removes_stale_wikidata_link():
    cache = {
        "Example University": {
            "name": "Example University",
            "ror_id": "https://ror.org/example",
            "wikidata_id": "Q123",
        }
    }
    organizations = {
        "https://ror.org/example": {
            "coordinate_source": "ror-geonames",
            "lat": 1.0,
            "lon": 2.0,
            "ror_id": "https://ror.org/example",
            "sector": "academic",
            "source": "ror",
        }
    }

    geocode_affiliations.apply_ror_metadata(cache, organizations)

    assert "wikidata_id" not in cache["Example University"]
