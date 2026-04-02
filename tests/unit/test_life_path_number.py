from app.services.result_calculation.life_path_number import compute_life_path_number

def test_compute_life_path_number():
    # 1990-01-01 -> 1+9+9+0 + 0+1 + 0+1 = 21 -> 3
    result = compute_life_path_number(birth_year=1990, birth_month=1, birth_day=1)
    assert result is not None
    assert result["lifePath"] == 3
    
    # 1992-02-29 -> 1+9+9+2 + 0+2 + 2+9 = 34 -> 7
    result2 = compute_life_path_number(birth_year=1992, birth_month=2, birth_day=29)
    assert result2 is not None
    assert result2["lifePath"] == 7
    
    # Master number test: 1989-09-08 -> 1+9+8+9 + 0+9 + 0+8 = 44 -> 8 (since we only keep 11, 22, 33)
    # Let's find an 11: 1990-01-09 -> 1+9+9+0 + 0+1 + 0+9 = 29 -> 11
    result3 = compute_life_path_number(birth_year=1990, birth_month=1, birth_day=9)
    assert result3["lifePath"] == 11
