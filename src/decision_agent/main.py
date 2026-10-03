"""Production ASGI entry point with deferred lifespan-owned runtime composition."""

from decision_agent.api.public_demo import create_deployment_app
from decision_agent.config import Settings

settings = Settings()
app = create_deployment_app(settings)
