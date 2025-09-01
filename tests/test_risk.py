from app.tools.risk_tool import position_units

def test_position_units_basic():
    u = position_units(10000, 0.005, atr=0.001)
    assert isinstance(u, int) and u > 0
