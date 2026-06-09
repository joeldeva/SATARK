"""SDRD-side application services.

IMPORTANT — Import boundary contract:
Nothing in this package may import from `app.intelligence.verdict.*`.
The verdict lane runs at collection time; SDRD only writes the rules and graph.
This is enforced by ``apps/api/tests/test_import_boundary.py``.
"""
