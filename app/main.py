"""Application entry point for the AIK backend service."""

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="AI Karaoke Backend")


class HealthResponse(BaseModel):
    """Represents the response model for the health-check endpoint."""

    status: str


@app.get("/health", response_model=HealthResponse, summary="Service health-check")
def read_health() -> HealthResponse:
    """Return a simple status payload to confirm the service is healthy."""

    return HealthResponse(status="ok")


__all__ = ["app"]
