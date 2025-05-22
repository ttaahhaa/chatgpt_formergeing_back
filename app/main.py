"""
Main FastAPI application entry point.
Slim main file that only handles app creation and router registration.
"""
from fastapi import FastAPI
import uvicorn

from app.config.lifespan import lifespan
from app.api.middleware import setup_middleware

# Import route modules directly instead of through package
from app.api.routes import auth, chat, documents, conversations, system, admin

# Create FastAPI app
app = FastAPI(
    title="Document QA Assistant API with MongoDB",
    description="A hybrid RAG system with MongoDB backend",
    version="1.0.0",
    lifespan=lifespan
)

# Setup middleware
setup_middleware(app)

# Include all routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(conversations.router)
app.include_router(system.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Document QA Assistant API with MongoDB is running"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)