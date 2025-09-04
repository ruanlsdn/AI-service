"""
Aplicação FastAPI principal para o Serviço de Web Crawler da Easysuites.
Implementa a funcionalidade de web crawler conforme especificado no PRD.
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.api.endpoints import router as web_crawler_router
from src.core.logging import setup_logging
from src.core.config import settings

# Configurar sistema de logging
logger = setup_logging()
app_logger = logging.getLogger("app")

# Create FastAPI application
def create_app() -> FastAPI:
    """
    Cria e configura a aplicação FastAPI seguindo a estratégia MVP.
    Implementa endpoints para teste de autenticação e detecção de campos.
    """
    app_logger.info("Iniciando criação da aplicação FastAPI")
    
    app = FastAPI(
        title="EasySuites AI Service - Web Crawler MVP",
        description="Serviço de IA para automação web com foco em autenticação e detecção de campos",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None
    )
    
    app_logger.info(f"Aplicação configurada - Debug: {settings.debug}, Ambiente: {settings.environment}")
    
    # Configurar CORS seguindo as configurações do ambiente
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    app_logger.info(f"CORS configurado para origens: {settings.get_cors_origins()}")
    
    # Incluir rotas da API
    app.include_router(web_crawler_router)
    app_logger.info("Rotas da API incluídas com sucesso")
    
    # Registrar manipuladores de exceção personalizados
    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request, exc):
        app_logger.error(f"Exceção HTTP capturada: {exc.status_code} - {exc.detail}")
        return {"error": exc.detail, "status_code": exc.status_code}
    
    @app.exception_handler(Exception)
    async def custom_general_exception_handler(request, exc):
        app_logger.error(f"Exceção geral capturada: {str(exc)}", exc_info=True)
        return {"error": "Erro interno do servidor", "status_code": 500}
    
    app_logger.info("Manipuladores de exceção registrados")
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint providing service information."""
        app_logger.info("Endpoint raiz acessado - serviço funcionando")
        return {
            "message": "EasySuites AI Service - Web Crawler MVP está funcionando!",
            "version": "1.0.0",
            "status": "healthy",
            "environment": settings.environment,
            "endpoints": [
                "/api/v1/web-crawlers/auth-test",
                "/api/v1/web-crawlers/field-detection",
                "/api/v1/web-crawlers/health",
                "/api/v1/web-crawlers/status"
            ]
        }
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup."""
        logger.info("Iniciando o Serviço de Web Crawler da Easysuites")
        logger.info("Endpoints do serviço disponíveis em /docs")
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        logger.info("Encerrando o Serviço de Web Crawler da Easysuites")
    
    return app

# Create the application instance
app = create_app()

# Run the application if executed directly
if __name__ == "__main__":
    app_logger.info("Iniciando servidor da aplicação")
    app_logger.info(f"Configurações: Host={settings.host}, Port={settings.port}, Workers={settings.workers}")
    app_logger.info(f"Modo debug: {settings.debug}, Ambiente: {settings.environment}")
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        workers=1 if settings.debug else settings.workers
    )