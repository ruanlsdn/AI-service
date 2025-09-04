"""Endpoints da API para o serviço de web crawler.
Implementa os endpoints de autenticação e detecção de campos seguindo a estratégia MVP.
"""

import asyncio
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
import uuid
import time

from src.models.schemas import (
    AuthTestRequest,
    AuthTestResponse,
    FieldDetectionRequest,
    FieldDetectionResponse,
    ErrorResponse
)
from src.services.browser_service import BrowserService
from src.services.auth_service import AuthService
from src.services.field_detection_service import FieldDetectionService
from src.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/web-crawlers", tags=["web-crawler"])


@router.get("/health")
async def health_check():
    """Endpoint de verificação de saúde do serviço."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@router.get("/status")
async def service_status():
    """Endpoint de status detalhado do serviço."""
    return {
        "service": "easysuites-ai-service",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": [
            "/api/v1/web-crawlers/auth-test",
            "/api/v1/web-crawlers/field-detection"
        ]
    }


@router.post("/auth-test", response_model=AuthTestResponse)
async def test_authentication(request: AuthTestRequest) -> AuthTestResponse:
    """
    Testa a autenticação em uma página web seguindo a estratégia MVP.
    Fluxo: Detecta formulário → Preenche credenciais → Submete → Verifica autenticação → Salva sessão
    
    Args:
        request: Dados da requisição contendo URL e credenciais
        
    Returns:
        AuthTestResponse: Resultado do teste de autenticação com sessão salva
    """
    browser_service = None
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Iniciando teste de autenticação para {request.url}")
        
        # Inicializar serviços
        browser_service = BrowserService()
        browser_initialized = await browser_service.initialize_browser()
        
        if not browser_initialized:
            raise Exception("Falha ao inicializar o navegador")
        
        page = await browser_service.get_page()
        context = browser_service.context
        
        if page is None:
            raise Exception("Falha ao obter página do navegador")
        
        auth_service = AuthService()
        
        # Executar teste de autenticação seguindo estratégia MVP
        auth_result = await auth_service.test_authentication(
            page=page,
            context=context,
            url=request.url,
            credentials=request.credentials
        )
        
        execution_time = time.time() - start_time
        
        logger.info(f"[{request_id}] Teste de autenticação concluído em {execution_time:.2f}s")
        
        return AuthTestResponse(
            success=auth_result['success'],
            message=auth_result['message'],
            authenticated=auth_result['authenticated'],
            login_detected=auth_result['login_detected'],
            form_filled=auth_result['form_filled'],
            submission_successful=auth_result['submission_successful'],
            post_login_url=auth_result.get('post_login_url'),
            session_saved=auth_result['session_saved'],
            execution_time=execution_time,
            request_id=request_id,
            timestamp=datetime.now().isoformat()
        )
            
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"[{request_id}] Erro durante teste de autenticação: {e}")
        
        return AuthTestResponse(
            success=False,
            message=f"Erro interno: {str(e)}",
            authenticated=False,
            login_detected=False,
            form_filled=False,
            submission_successful=False,
            session_saved=False,
            execution_time=execution_time,
            request_id=request_id,
            timestamp=datetime.now().isoformat()
        )
        
    finally:
        if browser_service:
            await browser_service.cleanup()


@router.post("/field-detection", response_model=FieldDetectionResponse)
async def detect_fields(request: FieldDetectionRequest) -> FieldDetectionResponse:
    """
    Detecta campos interativos em uma página web seguindo a estratégia MVP.
    Fluxo: Carrega sessão salva (se disponível) → Navega para URL → Detecta campos com heurísticas
    
    Args:
        request: Dados da requisição contendo URL da página e opcionalmente username
        
    Returns:
        FieldDetectionResponse: Lista de campos detectados com informações de sessão
    """
    browser_service = None
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Iniciando detecção de campos para {request.url}")
        
        # Inicializar serviços
        browser_service = BrowserService()
        browser_initialized = await browser_service.initialize_browser()
        
        if not browser_initialized:
            raise Exception("Falha ao inicializar o navegador")
        
        page = await browser_service.get_page()
        context = browser_service.context
        
        if page is None:
            raise Exception("Falha ao obter página do navegador")
        
        field_service = FieldDetectionService()
        
        # Executar detecção de campos seguindo estratégia MVP
        detected_fields, detection_method, session_used = await field_service.detect_fields(
            page=page,
            context=context,
            url=request.url,
            credentials=request.credentials
        )
        
        execution_time = time.time() - start_time
        
        logger.info(f"[{request_id}] Detecção concluída: {len(detected_fields)} campos encontrados em {execution_time:.2f}s")
        
        return FieldDetectionResponse(
            success=True,
            message=f"Detecção concluída: {len(detected_fields)} campos encontrados",
            fields=detected_fields,
            total_fields=len(detected_fields),
            detection_method=detection_method,
            session_used=session_used,
            execution_time=execution_time,
            request_id=request_id,
            timestamp=datetime.now().isoformat()
        )
            
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"[{request_id}] Erro durante detecção de campos: {e}")
        
        return FieldDetectionResponse(
            success=False,
            message=f"Erro interno: {str(e)}",
            fields=[],
            total_fields=0,
            detection_method="Erro na detecção",
            session_used=False,
            execution_time=execution_time,
            request_id=request_id,
            timestamp=datetime.now().isoformat()
        )
        
    finally:
        if browser_service:
            await browser_service.cleanup()


@router.post("/session/check")
async def check_session(url: str, username: str):
    """
    Verifica se existe uma sessão salva para a URL e usuário especificados.
    
    Args:
        url: URL do site
        username: Nome do usuário
        
    Returns:
        Dict: Status da sessão
    """
    try:
        session_service = SessionService()
        session_exists = session_service.session_exists(url, username)
        
        return {
            "session_exists": session_exists,
            "url": url,
            "username": username,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar sessão: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.delete("/session/clear")
async def clear_session(url: str, username: str):
    """
    Remove uma sessão salva para a URL e usuário especificados.
    
    Args:
        url: URL do site
        username: Nome do usuário
        
    Returns:
        Dict: Resultado da operação
    """
    try:
        session_service = SessionService()
        session_deleted = session_service.delete_session(url, username)
        
        return {
            "session_deleted": session_deleted,
            "url": url,
            "username": username,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao deletar sessão: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/sessions/list")
async def list_sessions():
    """
    Lista todas as sessões salvas disponíveis.
    
    Returns:
        Dict: Lista de sessões
    """
    try:
        session_service = SessionService()
        sessions = session_service.list_sessions()
        
        return {
            "sessions": sessions,
            "total": len(sessions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar sessões: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")