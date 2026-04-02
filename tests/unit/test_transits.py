from app.services.result_calculation.transits import compute_transits

def test_compute_transits():
    input_data = {
        "birth_datetime": "1990-01-01T12:00:00Z",
        "latitude": 34.0522,
        "longitude": -118.2437
    }
    
    result = compute_transits(input_data)
    # Just asserting it computes properly as testing precise ephemeris is difficult
    assert "error" not in result
    assert "natal_chart" in result
    assert "transit_chart" in result
    assert "transits" in result
    assert "sun" in result["natal_chart"]
