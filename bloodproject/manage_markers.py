#!/usr/bin/env python3
"""
Script to manage health condition markers in the Django database.
Run this script from the bloodproject directory.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bloodproject.settings')
django.setup()

from bloodapp.models import HealthCondition, Marker
from bloodapp.utils import (
    add_markers_to_condition, 
    remove_markers_from_condition,
    get_condition_markers,
    list_all_conditions_with_markers,
    set_expert_comment
)


def print_menu():
    """Print the main menu"""
    print("\n" + "="*50)
    print("HEALTH CONDITION MARKER MANAGER")
    print("="*50)
    print("1. List all health conditions with markers")
    print("2. View markers for a specific condition")
    print("3. Add markers to a condition")
    print("4. Remove markers from a condition")
    print("5. Set expert comment for markers")
    print("6. List all available markers")
    print("7. Exit")
    print("="*50)


def list_conditions():
    """List all conditions with their markers"""
    conditions = list_all_conditions_with_markers()
    
    if not conditions:
        print("No health conditions found in the database.")
        return
    
    print(f"\nFound {len(conditions)} health condition(s):")
    print("-" * 50)
    
            for condition in conditions:
            print(f"\n{condition['name']} (ID: {condition['condition_id']})")
            
            if condition['low_markers']:
                print(f"  Low markers: {', '.join(condition['low_markers'])}")
            else:
                print("  Low markers: None")
            
            if condition['high_markers']:
                print(f"  High markers: {', '.join(condition['high_markers'])}")
            else:
                print("  High markers: None")
            
            if condition['expert_comment_markers']:
                print(f"  Expert comment: {condition['expert_comment_markers'][:100]}...")


def view_condition_markers():
    """View markers for a specific condition"""
    condition_name = input("\nEnter condition name or ID: ").strip()
    
    if not condition_name:
        print("No condition name provided.")
        return
    
    result = get_condition_markers(condition_name)
    
    if not result['success']:
        print(f"Error: {result['error']}")
        return
    
    print(f"\nMarkers for '{result['condition']}':")
    print("-" * 30)
    
    if result['low_markers']:
        print(f"Low markers: {', '.join(result['low_markers'])}")
    else:
        print("Low markers: None")
    
    if result['high_markers']:
        print(f"High markers: {', '.join(result['high_markers'])}")
    else:
        print("High markers: None")
    
    if result['expert_comment_markers']:
        print(f"Expert comment: {result['expert_comment_markers']}")


def add_markers():
    """Add markers to a condition"""
    condition_name = input("\nEnter condition name or ID: ").strip()
    
    if not condition_name:
        print("No condition name provided.")
        return
    
    marker_type = input("Enter marker type (low/high): ").strip().lower()
    
    if marker_type not in ['low', 'high']:
        print("Invalid marker type. Must be 'low' or 'high'.")
        return
    
    markers_input = input(f"Enter marker names (comma-separated): ").strip()
    
    if not markers_input:
        print("No markers provided.")
        return
    
    markers = [m.strip() for m in markers_input.split(',') if m.strip()]
    
    result = add_markers_to_condition(condition_name, markers, marker_type)
    
    if result['success']:
        print(f"\nSuccessfully added {result['total_added']} marker(s) to '{result['condition']}':")
        print(f"Added: {', '.join(result['added'])}")
        
        if result['not_found']:
            print(f"Not found: {', '.join(result['not_found'])}")
    else:
        print(f"Error: {result['error']}")


def remove_markers():
    """Remove markers from a condition"""
    condition_name = input("\nEnter condition name or ID: ").strip()
    
    if not condition_name:
        print("No condition name provided.")
        return
    
    marker_type = input("Enter marker type (low/high): ").strip().lower()
    
    if marker_type not in ['low', 'high']:
        print("Invalid marker type. Must be 'low' or 'high'.")
        return
    
    markers_input = input(f"Enter marker names to remove (comma-separated): ").strip()
    
    if not markers_input:
        print("No markers provided.")
        return
    
    markers = [m.strip() for m in markers_input.split(',') if m.strip()]
    
    result = remove_markers_from_condition(condition_name, markers, marker_type)
    
    if result['success']:
        print(f"\nSuccessfully removed {result['total_removed']} marker(s) from '{result['condition']}':")
        print(f"Removed: {', '.join(result['removed'])}")
        
        if result['not_found']:
            print(f"Not found: {', '.join(result['not_found'])}")
    else:
        print(f"Error: {result['error']}")


def set_expert_comment():
    """Set expert comment for a condition's markers"""
    condition_name = input("\nEnter condition name or ID: ").strip()
    
    if not condition_name:
        print("No condition name provided.")
        return
    
    print(f"\nEnter expert comment for markers.")
    print("This should be from an IFM CP functional medicine practitioner")
    print("commenting on which markers are most/least important for risk assessment:")
    
    comment = input("Expert comment: ").strip()
    
    if not comment:
        print("No comment provided.")
        return
    
    result = set_expert_comment(condition_name, comment)
    
    if result['success']:
        print(f"\nSuccessfully set expert comment for '{result['condition']}':")
        print(f"Comment: {result['comment']}")
    else:
        print(f"Error: {result['error']}")


def list_markers():
    """List all available markers"""
    markers = Marker.objects.all().order_by('name')
    
    if not markers.exists():
        print("No markers found in the database.")
        return
    
    print(f"\nFound {markers.count()} marker(s):")
    print("-" * 30)
    
    for marker in markers:
        print(f"- {marker.name} ({marker.display_name})")


def main():
    """Main function"""
    while True:
        print_menu()
        
        try:
            choice = input("\nEnter your choice (1-7): ").strip()
            
            if choice == '1':
                list_conditions()
            elif choice == '2':
                view_condition_markers()
            elif choice == '3':
                add_markers()
            elif choice == '4':
                remove_markers()
            elif choice == '5':
                set_expert_comment()
            elif choice == '6':
                list_markers()
            elif choice == '7':
                print("\nGoodbye!")
                break
            else:
                print("Invalid choice. Please enter a number between 1 and 7.")
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
