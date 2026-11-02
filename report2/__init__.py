"""ADY201m Report 2 - Data Collection & Storage (Python + SQL Server).

Pipeline: collect.py (Playwright -> raw JSON) -> clean.py (pandas -> clean CSV
+ quality report) -> storage.py (pyodbc -> SQL Server) -> reconcile.py.
"""
