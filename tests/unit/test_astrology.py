from app.services.result_calculation.astrology import compute_astrology

def test_compute_astrology():
    result = compute_astrology(
        birth_year=1990,
        birth_month=1,
        birth_day=1,
        birth_time="12:00:00",
        birth_place_lat=0.0,
        birth_place_lng=0.0,
        birth_place_timezone="UTC"
    )
    assert result is not None
    assert "sun_sign" in result
    assert "moon_sign" in result
    assert "rising_sign" in result
    assert "element_distribution" in result
    # For 1990-01-01 12:00 UTC at 0,0, Sun is in Capricorn
    assert result["sun_sign"] == "Capricorn"
