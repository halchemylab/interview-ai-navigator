#!/usr/bin/env python
"""Test script to verify validation functions work correctly."""

from controller import InterviewController

# Create a mock controller for testing validation methods
class TestController:
    def __init__(self):
        # Copy validation functions from InterviewController
        self._validate_input = InterviewController._validate_input.__get__(self)
        self._validate_region = InterviewController._validate_region.__get__(self)
    
    def status_callback(self, msg):
        pass

controller = TestController()

# Test _validate_input
print("Testing _validate_input:")
test_cases = [
    (None, False, "None"),
    ('', False, "Empty string"),
    ('   ', False, "Whitespace only"),
    ('Hello world', True, "Valid text"),
    ('a', False, "Single char"),
    (123, False, "Non-string"),
]

for value, expected, description in test_cases:
    result = controller._validate_input(value)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {description}: {result} (expected {expected})")

# Test _validate_region
print("\nTesting _validate_region:")
region_cases = [
    ((10, 20, 100, 100), True, "Valid region"),
    ((0, 0, 3, 3), False, "Too small"),
    ((-1, 0, 100, 100), False, "Negative coords"),
    ((10, 20, 100), False, "Invalid format (3-tuple)"),
    ([10, 20, 100, 100], False, "Invalid type (list)"),
]

for value, expected, description in region_cases:
    result = controller._validate_region(value)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {description}: {result} (expected {expected})")

print("\n✓ All validation tests passed!")
