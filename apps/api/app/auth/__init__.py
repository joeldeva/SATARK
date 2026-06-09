"""Authentication and RBAC package for SATARK API.

Public surface:
- password.hash_password / verify_password
- jwt.encode_token / decode_token
- rbac.require_scope (FastAPI dependency factory)
- rbac.get_current_user (FastAPI dependency)
"""
