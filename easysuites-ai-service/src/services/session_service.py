"""Serviço de gerenciamento de sessão para persistir login entre chamadas.
Implementa o salvamento e carregamento de storageState.json conforme estratégia MVP.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from playwright.async_api import Page, BrowserContext

logger = logging.getLogger(__name__)

class SessionService:
    """Serviço para gerenciar sessões de login persistentes usando storageState.json."""
    
    def __init__(self, sessions_dir: str = "sessions"):
        """
        Inicializa o serviço de sessão.
        
        Args:
            sessions_dir: Diretório onde as sessões serão armazenadas
        """
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        logger.info(f"Serviço de sessão inicializado. Diretório: {self.sessions_dir}")
    
    def _get_session_file_path(self, url: str, username: str) -> Path:
        """
        Gera o caminho do arquivo de sessão baseado na URL e usuário.
        
        Args:
            url: URL do site
            username: Nome do usuário
            
        Returns:
            Path: Caminho para o arquivo de sessão
        """
        # Sanitiza a URL para usar como nome de arquivo
        safe_url = url.replace("://", "_").replace("/", "_").replace("?", "_")
        safe_username = username.replace("@", "_at_").replace(".", "_")
        filename = f"{safe_url}_{safe_username}_session.json"
        return self.sessions_dir / filename
    
    async def save_session(self, context: BrowserContext, url: str, username: str) -> bool:
        """
        Salva o estado da sessão atual em um arquivo JSON.
        
        Args:
            context: Contexto do navegador Playwright
            url: URL do site onde foi feito login
            username: Nome do usuário logado
            
        Returns:
            bool: True se a sessão foi salva com sucesso
        """
        try:
            session_file = self._get_session_file_path(url, username)
            
            # Salva o storage state
            storage_state = await context.storage_state()
            
            # Adiciona metadados
            session_data = {
                "url": url,
                "username": username,
                "timestamp": str(datetime.now()),
                "storage_state": storage_state
            }
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Sessão salva com sucesso: {session_file}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar sessão: {e}")
            return False
    
    def load_session(self, url: str, username: str) -> Optional[Dict[str, Any]]:
        """
        Carrega o estado da sessão de um arquivo JSON.
        
        Args:
            url: URL do site
            username: Nome do usuário
            
        Returns:
            Optional[Dict]: Dados da sessão ou None se não encontrada
        """
        try:
            session_file = self._get_session_file_path(url, username)
            
            if not session_file.exists():
                logger.info(f"Arquivo de sessão não encontrado: {session_file}")
                return None
            
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            logger.info(f"Sessão carregada com sucesso: {session_file}")
            return session_data
            
        except Exception as e:
            logger.error(f"Erro ao carregar sessão: {e}")
            return None
    
    def session_exists(self, url: str, username: str) -> bool:
        """
        Verifica se existe uma sessão salva para a URL e usuário.
        
        Args:
            url: URL do site
            username: Nome do usuário
            
        Returns:
            bool: True se a sessão existe
        """
        session_file = self._get_session_file_path(url, username)
        exists = session_file.exists()
        logger.info(f"Verificação de sessão para {url}/{username}: {exists}")
        return exists
    
    def delete_session(self, url: str, username: str) -> bool:
        """
        Remove uma sessão salva.
        
        Args:
            url: URL do site
            username: Nome do usuário
            
        Returns:
            bool: True se a sessão foi removida com sucesso
        """
        try:
            session_file = self._get_session_file_path(url, username)
            
            if session_file.exists():
                session_file.unlink()
                logger.info(f"Sessão removida: {session_file}")
                return True
            else:
                logger.info(f"Sessão não encontrada para remoção: {session_file}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao remover sessão: {e}")
            return False
    
    def list_sessions(self) -> list[Dict[str, str]]:
        """
        Lista todas as sessões salvas.
        
        Returns:
            List[Dict]: Lista de informações das sessões
        """
        sessions = []
        try:
            for session_file in self.sessions_dir.glob("*_session.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    sessions.append({
                        "file": str(session_file),
                        "url": session_data.get("url", "unknown"),
                        "username": session_data.get("username", "unknown"),
                        "timestamp": session_data.get("timestamp", "unknown")
                    })
                except Exception as e:
                    logger.warning(f"Erro ao ler sessão {session_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Erro ao listar sessões: {e}")
        
        logger.info(f"Encontradas {len(sessions)} sessões salvas")
        return sessions
    
    async def apply_session_to_context(self, context: BrowserContext, url: str, username: str) -> bool:
        """
        Aplica uma sessão salva a um contexto do navegador.
        
        Args:
            context: Contexto do navegador Playwright
            url: URL do site
            username: Nome do usuário
            
        Returns:
            bool: True se a sessão foi aplicada com sucesso
        """
        try:
            session_data = self.load_session(url, username)
            if not session_data:
                return False
            
            storage_state = session_data.get("storage_state")
            if not storage_state:
                logger.error("Storage state não encontrado na sessão")
                return False
            
            # Aplica o storage state ao contexto
            await context.add_cookies(storage_state.get("cookies", []))
            
            # Aplica localStorage e sessionStorage se disponíveis
            origins = storage_state.get("origins", [])
            for origin in origins:
                origin_url = origin.get("origin")
                if origin_url:
                    page = await context.new_page()
                    await page.goto(origin_url)
                    
                    # Aplica localStorage
                    local_storage = origin.get("localStorage", [])
                    for item in local_storage:
                        await page.evaluate(f"localStorage.setItem('{item['name']}', '{item['value']}')")
                    
                    # Aplica sessionStorage
                    session_storage = origin.get("sessionStorage", [])
                    for item in session_storage:
                        await page.evaluate(f"sessionStorage.setItem('{item['name']}', '{item['value']}')")
                    
                    await page.close()
            
            logger.info(f"Sessão aplicada com sucesso ao contexto para {url}/{username}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao aplicar sessão ao contexto: {e}")
            return False