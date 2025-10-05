"""Demo module created by FileManager."""


def greet(name: str) -> str:
    """
    Generate a greeting message.
    
    Args:
        name: Name to greet
        
    Returns:
        Greeting message
    """
    return f"Hello, {name}! Welcome to the Coding Agent CLI - Your AI Programming Assistant."


def calculate_sum(numbers: list[int]) -> int:
    """
    Calculate the sum of a list of numbers.
    
    Args:
        numbers: List of integers
        
    Returns:
        Sum of all numbers
    """
    return sum(numbers)


if __name__ == "__main__":
    print(greet("Developer"))
    print(f"Sum of [1, 2, 3, 4, 5]: {calculate_sum([1, 2, 3, 4, 5])}")
