"""Bartender endpoint wrapper"""
from bartender_standalone import bartender

# Re-export for Cloud Functions
__all__ = ['bartender']