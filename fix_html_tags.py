#!/usr/bin/env python3
"""
Script to fix HTML tags in existing database entries.
Run this script to clean up <br> tags in existing AI suggestions.
"""
import re
import os
import sys
from app import create_app, db
from app.models.database import AISuggestion

def clean_html_tags(text):
    """Convert HTML <br> tags to newlines and clean up other HTML."""
    if not text or not isinstance(text, str):
        return text
        
    # Replace <br>, <br/>, <br /> with newlines
    text = re.sub(r'<br\s*/?>', '\n', text)
    
    # Remove other HTML tags if present
    text = re.sub(r'<[^>]*>', '', text)
    
    return text

def fix_html_tags():
    """Fix HTML tags in existing database entries."""
    print("Fixing HTML tags in existing AI suggestions...")
    
    # Get all AI suggestions
    suggestions = AISuggestion.query.all()
    print(f"Found {len(suggestions)} AI suggestions")
    
    # Keep track of how many were updated
    updated_count = 0
    
    # Fix each suggestion
    for suggestion in suggestions:
        original_summary = suggestion.summary
        
        # Clean HTML tags from summary
        if '<br>' in original_summary or '<br/>' in original_summary or '<br />' in original_summary:
            cleaned_summary = clean_html_tags(original_summary)
            suggestion.summary = cleaned_summary
            updated_count += 1
            print(f"Updated summary for suggestion {suggestion.id}")
            print(f"  Original: {original_summary[:100]}...")
            print(f"  Cleaned: {cleaned_summary[:100]}...")
    
    # Commit changes
    if updated_count > 0:
        print(f"Committing {updated_count} changes to database...")
        db.session.commit()
        print("Done!")
    else:
        print("No changes needed. All suggestions are clean.")

if __name__ == '__main__':
    # Create app context
    app = create_app()
    with app.app_context():
        fix_html_tags()