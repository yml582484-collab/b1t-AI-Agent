"""
DeepSeek Agent - FastAPI Web Application
Main entry point for the API server
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List

# Load environment variables from .env file (must be before other imports)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path.name}")
except ImportError:
    pass  # python-dotenv not installed, will use system env vars

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from uvicorn import Config, Server
import shutil
import uuid
import base64
import httpx
import os

from src.agent.core import Agent
from src.utils.config import get_config
from src.utils.logger import setup_logger, get_logger


# Pydantic models for API requests/responses
class AttachmentItem(BaseModel):
    """Attachment item model"""
    filename: str
    type: str
    content: Optional[str] = None
    url: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = None
    use_react: bool = Field(default=True, description="Use ReAct planning for complex tasks")
    stream: bool = Field(default=False, description="Enable streaming response")
    attachments: List[AttachmentItem] = Field(default=[], description="List of uploaded file attachments")


class AttachmentInfo(BaseModel):
    """Attachment file info"""
    filename: str
    type: str  # 'text', 'image', 'pdf', etc.
    content: Optional[str] = None  # extracted text content
    url: Optional[str] = None  # file access url


class ChatResponse(BaseModel):
    """Chat response model"""
    session_id: str
    response: str
    success: bool
    reasoning_trace: Optional[list] = None
    token_usage: dict = {}
    metadata: dict = {}


class StatusResponse(BaseModel):
    """Agent status response"""
    status: dict
    sessions: list = []
    tools: list = []


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None


# Global agent instance
agent_instance: Optional[Agent] = None
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler
    
    Manages startup and shutdown events.
    """
    global agent_instance
    
    # Startup
    logger.info("🚀 Starting DeepSeek Agent API Server...")
    
    try:
        # Initialize the agent
        agent_instance = Agent(auto_initialize=False)
        await agent_instance.initialize()
        
        logger.info("✅ Agent ready to serve requests!")
        
        yield  # Application is running
        
    except Exception as e:
        logger.error(f"❌ Failed to start agent: {e}")
        raise RuntimeError(f"Agent initialization failed: {e}")
    
    finally:
        # Shutdown
        logger.info("🛑 Shutting down agent...")
        
        if agent_instance:
            await agent_instance.close()
        
        logger.info("👋 Agent shut down complete")


# Create FastAPI application
app = FastAPI(
    title="DeepSeek Agent API",
    description="""
    🤖 A powerful conversational AI agent powered by DeepSeek with:
    
    - **Memory System**: Short-term and long-term memory for context awareness
    - **Tool Calling**: Built-in tools (search, calculator, code executor, file manager)
    - **ReAct Planning**: Advanced reasoning loop for complex tasks
    - **Streaming Responses**: Real-time token-by-token output
    
    ## Quick Start
    
    Send a POST request to `/api/chat` with your message.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
config = get_config().config.server
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and frontend
frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    # Mount static files
    app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")
    print(f"✅ Static files mounted from {frontend_path / 'static'}")

    @app.get("/", tags=["Root"])
    async def root():
        """Serve b1t-AI frontend"""
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {
            "name": "b1t-AI",
            "version": "1.0.0",
            "status": "running" if agent_instance else "initializing",
            "docs": "/docs",
        }

# 创建上传目录
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Mount uploads directory
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# ==================== Vision API ====================

async def recognize_image(file_path: Path, filename: str) -> Optional[str]:
    """
    使用 SiliconFlow 视觉模型识别图片内容
    
    Returns: 图片描述文本，失败返回 None
    """
    api_key = os.getenv("SILICONFLOW_API_KEY", "")
    model = os.getenv("SILICONFLOW_VISION_MODEL", "Qwen/Qwen3-VL-8B-Instruct")
    
    if not api_key:
        logger.warning("SiliconFlow API key not configured, skipping image recognition")
        return None
    
    try:
        # 读取图片并转base64
        with open(file_path, "rb") as f:
            image_data = f.read()
        
        # 判断图片MIME类型
        ext = file_path.suffix.lower()
        mime_map = {
            '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.gif': 'image/gif', '.webp': 'image/webp',
        }
        mime_type = mime_map.get(ext, 'image/png')
        
        b64_image = base64.b64encode(image_data).decode('utf-8')
        
        # 调用 SiliconFlow 视觉API（兼容OpenAI格式）
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.siliconflow.cn/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{b64_image}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": "请详细描述这张图片的内容，包括文字、物体、场景等信息。"
                                }
                            ]
                        }
                    ],
                    "max_tokens": 1000,
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                logger.info(f"Image recognition success: {filename}, {len(content)} chars")
                return content
            else:
                logger.warning(f"SiliconFlow API error: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Image recognition failed: {e}")
        return None


# ==================== API Routes ====================


@app.post("/api/upload", tags=["Files"])
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file attachment
    
    Supports: txt, md, pdf, doc, docx, png, jpg, jpeg, gif, webp
    Max file size: 10MB
    
    Returns file metadata with extracted content (for text files)
    """
    # 检查文件类型
    allowed_types = {
        'text/plain': 'text',
        'text/markdown': 'text',
        'application/pdf': 'pdf',
        'application/msword': 'doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'image/png': 'image',
        'image/jpeg': 'image',
        'image/jpg': 'image',
        'image/gif': 'image',
        'image/webp': 'image',
    }
    
    content_type = file.content_type or 'application/octet-stream'
    file_type = allowed_types.get(content_type, 'unknown')
    
    # 代码文件扩展名映射
    code_extensions = {
        '.py': 'python', '.js': 'javascript', '.html': 'html', '.css': 'css',
        '.json': 'json', '.xml': 'xml', '.yaml': 'yaml', '.yml': 'yaml',
        '.sql': 'sql', '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.h': 'c',
        '.go': 'go', '.rs': 'rust', '.php': 'php', '.rb': 'ruby',
        '.swift': 'swift', '.kt': 'kotlin', '.ts': 'typescript',
        '.jsx': 'jsx', '.tsx': 'tsx', '.vue': 'vue',
        '.scss': 'scss', '.less': 'less',
        '.sh': 'shell', '.bat': 'batch', '.ps1': 'powershell',
        '.log': 'log', '.csv': 'csv',
    }
    
    if file_type == 'unknown':
        # 尝试从文件名判断
        ext = Path(file.filename).suffix.lower()
        ext_map = {
            '.txt': 'text', '.md': 'text', '.markdown': 'text',
            '.pdf': 'pdf',
            '.doc': 'doc', '.docx': 'docx',
            '.png': 'image', '.jpg': 'image', '.jpeg': 'image',
            '.gif': 'image', '.webp': 'image',
        }
        file_type = ext_map.get(ext, 'unknown')
        
        # 检查是否是代码文件
        if ext in code_extensions:
            file_type = 'code'
    
    if file_type == 'unknown':
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type}")
    
    # 生成唯一文件名
    file_id = str(uuid.uuid4())[:8]
    safe_filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    
    try:
        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 提取文本内容
        extracted_content = None
        
        if file_type == 'text':
            # 文本文件直接读取
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    extracted_content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='gbk') as f:
                    extracted_content = f.read()
        
        elif file_type == 'pdf':
            # PDF文件提取文本
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text_parts = []
                    for page in reader.pages[:10]:  # 最多提取前10页
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    extracted_content = "\n\n".join(text_parts)
                    if len(extracted_content) > 5000:
                        extracted_content = extracted_content[:5000] + "...(内容过长，已截断)"
            except Exception as pdf_error:
                logger.warning(f"PDF extraction failed: {pdf_error}")
                extracted_content = "[PDF文件，无法提取文本内容]"
        
        elif file_type == 'docx':
            # DOCX文件提取文本
            try:
                from docx import Document
                doc = Document(str(file_path))
                text_parts = []
                for para in doc.paragraphs:
                    if para.text.strip():
                        text_parts.append(para.text)
                extracted_content = "\n".join(text_parts)
                if len(extracted_content) > 5000:
                    extracted_content = extracted_content[:5000] + "...(内容过长，已截断)"
            except Exception as docx_error:
                logger.warning(f"DOCX extraction failed: {docx_error}")
                extracted_content = "[Word文档，无法提取文本内容]"
        
        elif file_type == 'code':
            # 代码文件直接读取
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    extracted_content = f.read()
                if len(extracted_content) > 8000:
                    extracted_content = extracted_content[:8000] + "\n\n...(代码过长，已截断，共 " + str(len(extracted_content)) + " 字符)"
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        extracted_content = f.read()
                    if len(extracted_content) > 8000:
                        extracted_content = extracted_content[:8000] + "\n\n...(代码过长，已截断，共 " + str(len(extracted_content)) + " 字符)"
                except Exception as code_error:
                    logger.warning(f"Code file extraction failed: {code_error}")
                    extracted_content = "[代码文件，无法读取内容]"
        
        elif file_type == 'doc':
            # DOC文件（旧格式）暂不支持
            extracted_content = "[Word文档(旧格式)，请转换为docx格式]"
        
        elif file_type == 'image':
            # 图片文件 - 使用视觉模型识别内容
            try:
                image_description = await recognize_image(file_path, file.filename)
                if image_description:
                    extracted_content = f"[图片识别结果]\n{image_description}"
                else:
                    extracted_content = "[图片文件，视觉识别服务未配置或识别失败]"
            except Exception as img_error:
                logger.warning(f"Image recognition error: {img_error}")
                extracted_content = "[图片文件，识别失败]"
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "type": file_type,
            "content": extracted_content,
            "url": f"/api/files/{safe_filename}",
            "size": file_path.stat().st_size,
        }
        
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.get("/api/files/{filename}", tags=["Files"])
async def get_file(filename: str):
    """
    Get uploaded file by filename
    """
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(str(file_path))


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    """
    Send a message to the agent and get a response
    
    - **message**: Your message or question (required)
    - **session_id**: Existing session ID (optional, creates new if not provided)
    - **use_react**: Enable ReAct planning for complex tasks (default: true)
    - **stream**: Enable streaming (use /api/chat/stream instead for true SSE)
    - **attachments**: List of uploaded file attachments with extracted content
    """
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # 构建包含附件内容的完整消息
        full_message = request.message
        
        if request.attachments:
            attachment_context = []
            for att in request.attachments:
                if att.content:
                    # 文本文件或图片识别结果
                    attachment_context.append(f"[文件: {att.filename}]\n{att.content[:2000]}...")
                elif att.type == 'image':
                    attachment_context.append(f"[图片: {att.filename}]")
                else:
                    attachment_context.append(f"[附件: {att.filename}]")
            
            if attachment_context:
                full_message = "附件内容:\n" + "\n\n".join(attachment_context) + "\n\n用户问题:\n" + request.message
        
        if request.use_react:
            # Use ReAct planner for complex tasks
            result = await agent_instance.process(
                input_text=full_message,
                session_id=request.session_id,
                use_react=True,
            )
        else:
            # Simple chat mode
            result = await agent_instance.chat(
                message=full_message,
                session_id=request.session_id,
            )
        
        return ChatResponse(
            session_id=result.session_id,
            response=result.response,
            success=result.success,
            reasoning_trace=result.reasoning_trace,
            token_usage=result.token_usage,
            metadata=result.metadata,
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream", tags=["Chat"])
async def chat_stream_endpoint(request: ChatRequest):
    """
    Stream chat response using Server-Sent Events (SSE)
    
    Returns a streaming response with real-time tokens.
    Use this for better user experience in chat interfaces.
    """
    from fastapi.responses import StreamingResponse
    
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    async def generate():
        try:
            async for chunk in agent_instance.chat_stream(
                message=request.message,
                session_id=request.session_id,
            ):
                yield f"data: {chunk}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            error_data = {"error": str(e)}
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/status", response_model=StatusResponse, tags=["System"])
async def status_endpoint():
    """
    Get comprehensive agent status and statistics
    
    Returns:
    - Agent initialization state
    - Uptime and request statistics
    - Memory usage
    - LLM provider stats
    - Available tools list
    - Active sessions
    """
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return StatusResponse(
        status=agent_instance.get_status(),
        sessions=agent_instance.list_sessions(),
        tools=tool_registry_list(),
    )


@app.get("/api/tools", tags=["Tools"])
async def tools_endpoint():
    """
    List all available tools with their descriptions
    
    Returns information about all registered and enabled tools.
    """
    from src.tools.base import tool_registry
    
    tools_info = tool_registry.list_tools()
    
    return {
        "total_tools": len(tools_info),
        "enabled_count": sum(1 for t in tools_info if t["enabled"]),
        "tools": tools_info,
    }


@app.post("/api/tools/{tool_name}/toggle", tags=["Tools"])
async def toggle_tool_endpoint(tool_name: str, enable: bool = True):
    """
    Enable or disable a specific tool
    
    - **tool_name**: Name of the tool to toggle
    - **enable**: True to enable, False to disable
    """
    from src.tools.base import tool_registry
    
    if enable:
        success = tool_registry.enable_tool(tool_name)
    else:
        success = tool_registry.disable_tool(tool_name)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found"
        )
    
    return {
        "success": True,
        "tool": tool_name,
        "enabled": enable,
        "message": f"Tool '{tool_name}' {'enabled' if enable else 'disabled'}",
    }


@app.get("/api/sessions", tags=["Sessions"])
async def sessions_endpoint():
    """
    List all active conversation sessions
    
    Returns session IDs and basic statistics.
    """
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return {
        "sessions": agent_instance.list_sessions(),
        "active_count": len(agent_instance._sessions),
    }


@app.delete("/api/sessions/{session_id}", tags=["Sessions"])
async def delete_session_endpoint(session_id: str):
    """
    Delete/clear a specific session
    
    - **session_id**: Session ID to clear
    """
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    success = agent_instance.clear_session(session_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found"
        )
    
    return {"success": True, "message": f"Session cleared"}


@app.post("/api/reset", tags=["System"])
async def reset_endpoint():
    """
    Reset the agent completely
    
    Clears all memory, sessions, and resets state.
    Use with caution - this cannot be undone!
    """
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    await agent_instance.reset()
    
    return {
        "success": True,
        "message": "Agent reset successfully",
        "new_session_id": agent_instance._current_session_id[:8] + "...",
    }


@app.get("/api/health", tags=["System"])
async def health_endpoint():
    """
    Health check endpoint
    
    Returns simple OK if the service is running.
    Used by load balancers and monitoring systems.
    """
    return {
        "status": "healthy",
        "agent_ready": agent_instance is not None and agent_instance._initialized,
    }


@app.get("/api/usage", tags=["System"])
async def usage_endpoint():
    """
    Get real-time balance and token usage from DeepSeek platform
    
    Returns actual account balance and local token statistics.
    """
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    import httpx
    import os
    from datetime import datetime
    
    api_key = os.getenv('DEEPSEEK_API_KEY')
    api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com')
    
    stats = {
        "balance": {
            "total_balance": 0.0,
            "topped_up_balance": 0.0,
            "granted_balance": 0.0,
            "currency": "CNY",
        },
        "token_usage": {},
        "api_calls": 0,
        "is_available": False,
        "last_updated": None,
    }
    
    try:
        # 获取真实余额数据（调用 DeepSeek 官方 API）
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{api_base}/user/balance",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                stats["is_available"] = data.get("is_available", False)
                
                # 解析余额信息
                balance_infos = data.get("balance_infos", [])
                for info in balance_infos:
                    if info.get("currency") == "CNY":
                        stats["balance"] = {
                            "total_balance": float(info.get("total_balance", 0)),
                            "topped_up_balance": float(info.get("topped_up_balance", 0)),
                            "granted_balance": float(info.get("granted_balance", 0)),
                            "currency": info.get("currency", "CNY"),
                        }
                        break
                
                logger.info(f"✅ 获取余额成功: ¥{stats['balance']['total_balance']}")
            
            else:
                logger.warning(f"获取余额失败: HTTP {response.status_code}")
        
        # 获取本地 token 使用统计
        if hasattr(agent_instance, "_llm") and hasattr(agent_instance._llm, "stats"):
            llm_stats = agent_instance._llm.stats
            stats["token_usage"] = llm_stats.get("token_usage", {})
            stats["api_calls"] = llm_stats.get("total_calls", 0)
        
        # 更新时间戳
        stats["last_updated"] = datetime.now().isoformat()
        
    except Exception as e:
        logger.error(f"获取使用情况失败: {e}")
        stats["error"] = str(e)
    
    return stats


# ==================== Helper Functions ====================

def tool_registry_list() -> list:
    """Get formatted list of tools from registry"""
    from src.tools.base import tool_registry
    
    return [
        {
            "name": tool.name,
            "description": tool.description,
        }
        for tool in tool_registry.get_all_tools()
    ]


# ==================== Main Entry Point ====================

def run_server(
    host: Optional[str] = None,
    port: Optional[int] = None,
    debug: bool = False,
):
    """
    Run the FastAPI server
    
    Args:
        host: Host to bind to (default from config)
        port: Port to listen to (default from config)
        debug: Enable debug mode
    """
    server_config = get_config().config.server
    
    # Render 平台会设置 PORT 环境变量，优先使用
    render_port = os.environ.get("PORT")
    if render_port:
        port = int(render_port)
        host = "0.0.0.0"  # Render 要求绑定 0.0.0.0
    else:
        host = host or server_config.host
        port = port or server_config.port
    
    print(f"\n{'='*60}")
    print(f"🚀 Starting DeepSeek Agent API Server")
    print(f"{'='*60}")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Debug: {debug}")
    print(f"   Docs: http://{host}:{port}/docs")
    print(f"{'='*60}")
    print(f"\n🔗 Local URL: http://localhost:{port}")
    print(f"   (Ctrl+Click to open in browser)\n")
    
    uvicorn_config = Config(
        app="main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="debug" if debug else "info",
    )
    
    server = Server(config=uvicorn_config)
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="DeepSeek Agent API Server")
    parser.add_argument("--host", type=str, default=None, help="Host to bind to")
    parser.add_argument("--port", type=int, default=None, help="Port to listen to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Setup logging before starting
    setup_logger(log_file="./logs/api.log")
    
    run_server(host=args.host, port=args.port, debug=args.debug)