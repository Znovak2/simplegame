def add_numbers(a, b, c=0.0):
    """
    Add two or three numbers together and return the result.
    
    Args:
        a (int/float): First number
        b (int/float): Second number
        c (int/float, optional): Third number. Defaults to 0.
    
    Returns:
        int/float: Sum of a, b, and c
    """
    return a + b + c

# Example usage
if __name__ == "__main__":
    # Get input from user
    num1 = float(input("Enter first number: "))
    num2 = float(input("Enter second number: "))
    
    # Ask if user wants to add a third number with validation
    while True:
        add_third = input("Do you want to add a third number? (y/n): ").lower()
        if add_third in ['y', 'n']:
            break
        else:
            print("Please enter 'y' for yes or 'n' for no.")
    
    if add_third == 'y':
        num3 = float(input("Enter third number: "))
        result = add_numbers(num1, num2, num3)
    else:
        result = add_numbers(num1, num2)

    print(f"The sum is {result}")
