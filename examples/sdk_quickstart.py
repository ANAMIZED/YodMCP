"""Minimal SDK example against yodmcp-api."""
from yodmcp.sdk import YodClient

with YodClient("http://localhost:8080") as c:
    print("health:", c.health())
    print("plans:", c.billing_plans())
