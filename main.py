import os
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from dotenv import load_dotenv
from cors_config import add_cors
from routers import auth, webhook, call, display

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="Medical Emergency Webhook API",
    description="API to capture medical webhooks, initiate calls, manage users, and display results.",
    version="1.0.0",
)

# Apply CORS
add_cors(app)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
app.include_router(call.router, prefix="/call", tags=["Call"])
app.include_router(display.router, prefix="/display", tags=["Display"])

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Medical Emergency Webhook API",
        version="1.0.0",
        description="A FastAPI application to process medical webhooks, initiate calls, and display results.",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {"url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"}
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)