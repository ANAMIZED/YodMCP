# Glama release — YodMCP

CMD must be stdio: `python -m yodmcp`.
Do not use `yodmcp-api` on the Quality image.

## Admin form

| Field | Value |
| --- | --- |
| Build steps | `["pip install --no-cache-dir ."]` |
| CMD arguments | `["python", "-m", "yodmcp"]` |
| Placeholders | `{}` |
