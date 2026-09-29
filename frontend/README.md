# Control Tower (React frontend)
npm install && npm run dev      # runs on mock data
Set VITE_USE_MOCK=false in .env to call FastAPI (proxied at /api):
  GET /api/shipments
  GET /api/shipments/{id}/investigate/stream  (SSE events: {type,name,payload}; final {type:"done"})
