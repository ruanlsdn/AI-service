"""
Serviço de automação de navegador para a funcionalidade do web crawler.
Lida com a inicialização do navegador, navegação de página e limpeza.
"""

import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import logging

logger = logging.getLogger(__name__)


class BrowserService:
    """Serviço para gerenciar instâncias de navegador e interações de página."""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
    
    async def initialize_browser(self, headless: bool = True) -> bool:
        """
        Inicializa o navegador com configurações otimizadas.
        
        Args:
            headless: Se deve executar o navegador em modo headless
            
        Returns:
            bool: True se a inicialização for bem-sucedida, False caso contrário
        """
        try:
            logger.info("Inicializando o navegador com configurações otimizadas")
            
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-software-rasterizer',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection'
                ]
            )
            
            # Create context with realistic user agent
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='pt-BR'
            )
            
            self.page = await self.context.new_page()
            
            logger.info("Navegador inicializado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Falha ao inicializar o navegador: {e}")
            return False
    
    async def navigate_to_page(self, url: str, wait_until: str = 'networkidle') -> bool:
        """
        Navega para uma URL específica.
        
        Args:
            url: A URL para navegar
            wait_until: Quando considerar a navegação completa
            
        Returns:
            bool: True se a navegação for bem-sucedida, False caso contrário
        """
        try:
            logger.info(f"Navegando para a URL: {url}")
            await self.page.goto(url, wait_until=wait_until, timeout=30000)
            await asyncio.sleep(2)  # Additional wait for dynamic content
            logger.info("Página carregada com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Falha ao navegar para {url}: {e}")
            return False
    
    async def wait_for_element(self, selector: str, timeout: int = 10000) -> bool:
        """
        Espera por um elemento estar presente na página.
        
        Args:
            selector: Seletor CSS para o elemento
            timeout: Tempo máximo de espera em milissegundos
            
        Returns:
            bool: True se o elemento for encontrado, False caso contrário
        """
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False
    
    async def get_page_content(self) -> str:
        """Obtém o conteúdo de texto da página atual."""
        try:
            return await self.page.inner_text('body')
        except Exception as e:
            logger.error(f"Falha ao obter o conteúdo da página: {e}")
            return ""
    
    async def close_browser(self):
        """Fecha o navegador e limpa os recursos."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            logger.info("Navegador fechado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao fechar o navegador: {e}")
    
    async def take_screenshot(self, path: str = None) -> Optional[bytes]:
        """
        Tira uma captura de tela da página atual.
        
        Args:
            path: Caminho opcional para salvar a captura de tela
            
        Returns:
            bytes: Dados da captura de tela se bem-sucedida, None caso contrário
        """
        try:
            if path:
                await self.page.screenshot(path=path, full_page=True)
            else:
                return await self.page.screenshot(full_page=True)
        except Exception as e:
            logger.error(f"Falha ao tirar captura de tela: {e}")
            return None
    
    async def get_page_info(self) -> Dict[str, Any]:
        """Obtém informações básicas sobre a página atual."""
        try:
            return {
                'url': self.page.url,
                'title': await self.page.title(),
                'viewport_size': self.page.viewport_size
            }
        except Exception as e:
            logger.error(f"Falha ao obter informações da página: {e}")
            return {}
    
    async def get_page(self) -> Optional[Page]:
        """Retorna a página atual do navegador."""
        return self.page
    
    async def cleanup(self) -> None:
        """Limpa recursos do navegador."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("Recursos do navegador limpos com sucesso")
        except Exception as e:
            logger.error(f"Erro ao limpar recursos do navegador: {e}")