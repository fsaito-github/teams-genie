"""Container App entrypoint

Runs the Databricks Genie Teams bot as a regular web service (FastAPI), suitable for Azure Container Apps.
Exposes:
  - POST /api/messages  (Bot Framework webhook)
  - GET  /api/health   (health check)
"""

import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse

logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(title="Databricks Genie Teams Bot", version="1.0")

_bot = None


def get_bot():
    """Lazy initialization of bot and Genie client."""
    global _bot

    if _bot is None:
        from config import Config
        from databricks.genie_client import GenieClient
        from bot.teams_bot import TeamsBot

        Config.validate()
        config = Config()

        genie = GenieClient(
            host=config.DATABRICKS_HOST,
            client_id=config.DATABRICKS_CLIENT_ID,
            client_secret=config.DATABRICKS_CLIENT_SECRET,
            tenant_id=config.DATABRICKS_TENANT_ID,
            space_id=config.DATABRICKS_GENIE_SPACE_ID,
        )

        _bot = TeamsBot(
            app_id=config.MICROSOFT_APP_ID,
            app_password=config.MICROSOFT_APP_PASSWORD,
            genie_client=genie,
            app_tenant_id=config.MICROSOFT_APP_TENANT_ID,
        )

        logger.info("Bot initialized successfully")

    return _bot


@app.post("/api/messages")
async def messages(request: Request):
    logger.info("=== /api/messages called ===")

    try:
        body = await request.json()
        auth_header = request.headers.get("Authorization", "")

        bot = get_bot()
        result = await bot.handle_request(body, auth_header)

        return JSONResponse({"status": "ok", "result": result}, status_code=200)

    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        return JSONResponse({"error": "Invalid request", "details": str(e)}, status_code=400)

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return JSONResponse({"error": "Internal server error", "details": str(e)}, status_code=500)


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "Databricks Genie Teams Bot"}


@app.get("/")
async def root():
    # Keep this lightweight; useful for manual checks.
    try:
        from config import Config

        config = Config()
        host = config.DATABRICKS_HOST or "Not configured"
        space_id = config.DATABRICKS_GENIE_SPACE_ID or "Not configured"
        app_id = config.MICROSOFT_APP_ID or "Not configured"
    except Exception:
        host = "Not configured"
        space_id = "Not configured"
        app_id = "Not configured"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Databricks Genie Teams Bot</title></head>
    <body style='font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto;'>
      <h1>Databricks Genie Teams Bot</h1>
      <p><b>Status:</b> Running</p>
      <h2>Configuration</h2>
      <ul>
        <li><b>Databricks Host:</b> {host}</li>
        <li><b>Genie Space ID:</b> {space_id}</li>
        <li><b>Microsoft App ID:</b> {app_id}</li>
      </ul>
      <h2>Endpoints</h2>
      <ul>
        <li><code>POST /api/messages</code> (Teams webhook)</li>
        <li><code>GET /api/health</code> (health check)</li>
      </ul>
    </body>
    </html>
    """

    return HTMLResponse(html, status_code=200)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("containerapp.app:app", host="0.0.0.0", port=port, log_level=os.getenv("LOG_LEVEL", "info").lower())
