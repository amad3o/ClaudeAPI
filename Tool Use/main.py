def greeting():
    print("Hi there!")


def calculate_pi():
    """
    Calculate pi to the 5th decimal digit using the Machin formula.
    Machin's formula: pi/4 = 4*arctan(1/5) - arctan(1/239)
    Returns pi accurate to at least 5 decimal places (3.14159)
    """
    def arctan(x, num_terms=100):
        """Calculate arctan(x) using Taylor series expansion"""
        result = 0
        for n in range(num_terms):
            sign = (-1) ** n
            result += sign * (x ** (2 * n + 1)) / (2 * n + 1)
        return result
    
    # Machin's formula: pi/4 = 4*arctan(1/5) - arctan(1/239)
    pi = 4 * (4 * arctan(1/5, 100) - arctan(1/239, 100))
    
    # Round to 5 decimal places
    return round(pi, 5)