#!/usr/bin/env python3
"""
Script to create Archon document with the dashboard fix plan
"""

# Import the plan object
from dashboard_fix_plan import dashboard_fix_plan

# Print the object to verify it's imported correctly
print("Imported dashboard_fix_plan object:")
print(f"Type: {type(dashboard_fix_plan)}")
print(f"Keys: {list(dashboard_fix_plan.keys())}")

# This object can now be used with Archon create_document
print("\nObject ready for Archon create_document:")
print(dashboard_fix_plan)
