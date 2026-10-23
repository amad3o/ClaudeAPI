import math
from main import calculate_pi


def test_calculate_pi():
    """Test that calculate_pi returns pi accurate to 5 decimal places"""
    calculated_pi = calculate_pi()
    expected_pi = 3.14159  # Pi to 5 decimal places
    
    print(f"Calculated pi: {calculated_pi}")
    print(f"Expected pi:   {expected_pi}")
    print(f"Actual pi (from math module): {math.pi}")
    
    # Test that the calculated value matches expected to 5 decimal places
    assert calculated_pi == expected_pi, f"Expected {expected_pi}, but got {calculated_pi}"
    print("✓ Test passed: Pi calculated correctly to 5 decimal places")
    
    # Additional verification: check it's close to math.pi
    difference = abs(calculated_pi - math.pi)
    print(f"Difference from math.pi: {difference}")
    assert difference < 0.000005, f"Calculated pi differs too much from math.pi"
    print("✓ Test passed: Pi is within acceptable range of math.pi")


def test_pi_value_range():
    """Test that calculate_pi returns a value in the expected range"""
    calculated_pi = calculate_pi()
    
    assert 3.14159 <= calculated_pi <= 3.14160, \
        f"Pi value {calculated_pi} is outside expected range [3.14159, 3.14160]"
    print("✓ Test passed: Pi value is in expected range")


if __name__ == "__main__":
    print("Running tests for calculate_pi()...\n")
    
    try:
        test_calculate_pi()
        print()
        test_pi_value_range()
        print("\n" + "="*50)
        print("All tests passed! ✓")
        print("="*50)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
    except Exception as e:
        print(f"\n✗ Error running tests: {e}")
