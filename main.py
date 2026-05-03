from fastapi import FastAPI
from fastmcp import FastMCP
from server import mcp

# SSE transport — best compatibility with Foundry AI
mcp_app = mcp.http_app(transport="sse")

app = FastAPI(title="My MCP Server", lifespan=mcp_app.lifespan)

@app.get("/health")
def health():
    return {"status": "ok" , "Zayed-Server": "is doing great dont't worry !"}

app.mount("/mcp", mcp_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)