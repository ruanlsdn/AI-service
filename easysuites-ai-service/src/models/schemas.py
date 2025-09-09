"""Modelos Pydantic para requisições e respostas do serviço de web crawler.
Baseado nas especificações do PRD_Easysuites_WebCrawler.md e estratégia MVP.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AuthCredentials(BaseModel):
    """Modelo para credenciais de autenticação."""
    username: str = Field(..., description="Nome de usuário para autenticação")
    password: str = Field(..., description="Senha para autenticação")


class AuthTestRequest(BaseModel):
    """Modelo de requisição para o endpoint de teste de autenticação."""
    url: str = Field(..., description="URL da página de login")
    credentials: AuthCredentials = Field(..., description="Credenciais de autenticação")


class AuthTestResponse(BaseModel):
    """Modelo de resposta para o endpoint de teste de autenticação."""
    success: bool = Field(..., description="Indica se a autenticação foi bem-sucedida")
    message: str = Field(..., description="Mensagem detalhada sobre o resultado da autenticação")
    authenticated: bool = Field(..., description="Indica se o usuário foi autenticado com sucesso")
    login_detected: bool = Field(..., description="Indica se o formulário de login foi detectado")
    form_filled: bool = Field(..., description="Indica se o formulário foi preenchido com sucesso")
    submission_successful: bool = Field(..., description="Indica se a submissão do formulário foi bem-sucedida")
    post_login_url: Optional[str] = Field(None, description="URL após o login (se disponível)")
    session_saved: bool = Field(default=False, description="Indica se a sessão foi salva com sucesso")
    execution_time: float = Field(..., description="Tempo de execução em segundos")
    request_id: str = Field(..., description="ID único da requisição")
    timestamp: str = Field(..., description="Timestamp da execução em formato ISO")


class FieldDetectionRequest(BaseModel):
    """Modelo de requisição para o endpoint de detecção de campos."""
    url: str = Field(..., description="URL da página a ser analisada")
    credentials: Optional[AuthCredentials] = Field(None, description="Credenciais de autenticação (opcional)")


class DetectedField(BaseModel):
    """Modelo para um campo detectado em uma página web."""
    name: str = Field(..., description="Nome legível do campo")
    type: str = Field(..., description="Tipo de campo (texto, botão, tabela, lista, etc.)")
    css_selector: str = Field(..., description="Seletor CSS específico para o campo")
    xpath: str = Field(..., description="XPath para localizar o campo")
    placeholder: Optional[str] = Field(None, description="Placeholder do campo")
    label: Optional[str] = Field(None, description="Label associado ao campo")
    selector: Optional[str] = Field(None, description="Seletor CSS legado (mantido para compatibilidade)")
    description: Optional[str] = Field(None, description="Descrição do que o campo representa")
    columns: Optional[List[str]] = Field(None, description="Nomes das colunas para tabelas ou listas")
    options: Optional[List[Dict[str, str]]] = Field(None, description="Opções disponíveis para campos select/combobox (value e text)")


class FieldDetectionResponse(BaseModel):
    """Modelo de resposta para o endpoint de detecção de campos."""
    success: bool = Field(..., description="Indica se a detecção de campos foi bem-sucedida")
    message: Optional[str] = Field(None, description="Mensagem opcional sobre o resultado da detecção")
    fields: List[DetectedField] = Field(default_factory=list, description="Lista de campos detectados")
    execution_time: float = Field(..., description="Tempo de execução em segundos")
    request_id: str = Field(..., description="ID único da requisição")
    timestamp: datetime = Field(..., description="Timestamp da execução")
    detection_method: str = Field(..., description="Método usado para detecção (heurística, playwright, etc.)")
    session_used: bool = Field(default=False, description="Indica se foi usada sessão salva do login")


class ErrorResponse(BaseModel):
    """Modelo de resposta de erro genérico."""
    success: bool = Field(False, description="Sempre falso para respostas de erro")
    message: str = Field(..., description="Mensagem de erro")
    details: Optional[Dict[str, Any]] = Field(None, description="Detalhes adicionais do erro")