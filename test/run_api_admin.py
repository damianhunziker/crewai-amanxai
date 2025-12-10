#!/usr/bin/env python3
"""
API Registry Administration Script

Startet das Konsolen-Interface für API-Management
"""

import sys
import os

# Pfad zur core hinzufügen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from core.api_admin import main

if __name__ == "__main__":
    main()