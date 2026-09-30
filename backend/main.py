from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# 1. We added routes_briefing to the end of this import line!
from backend.api import routes_shipments, routes_predictions, routes_agent, routes_briefing 

app = FastAPI(
    title="Supply-Chain Disruption Agent API",
    description="Risk prediction and AI investigation orchestration layer",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all modular routers
app.include_router(routes_shipments.router)
app.include_router(routes_predictions.router)
app.include_router(routes_agent.router)  
# 2. We added the new RAG door here!
app.include_router(routes_briefing.router) 

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Backend Orchestration"}