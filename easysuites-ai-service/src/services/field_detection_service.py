"""Serviço de detecção de campos para a funcionalidade do web crawler.
Implementa detecção de campos interativos conforme estratégia MVP.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from playwright.async_api import Page, BrowserContext
import logging
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from src.models.schemas import DetectedField, AuthCredentials
from src.services.session_service import SessionService

# Configurar logger específico para o serviço de detecção de campos
logger = logging.getLogger("field_detection_service")

class FieldDetectionService:
    """Serviço para detectar campos interativos em páginas web seguindo estratégia MVP."""
    
    def __init__(self):
        """
        Inicializa o serviço de detecção de campos.
        """
        self.session_service = SessionService()
        logger.info("Serviço de detecção de campos inicializado")
    
    async def detect_fields(self, page: Page, context: BrowserContext, url: str, credentials: Optional['AuthCredentials'] = None) -> Tuple[List[DetectedField], str, bool]:
        """
        Executa o fluxo completo de detecção de campos conforme estratégia MVP:
        1. Carrega sessão salva se disponível
        2. Navega para a URL
        3. Detecta se foi redirecionado para página de login
        4. Se redirecionado, executa autenticação automática
        5. Navega para URL original após autenticação
        6. Detecta campos interativos usando heurísticas
        7. Retorna lista de campos detectados
        
        Args:
            page: Instância da página Playwright
            context: Contexto do navegador
            url: URL da página para detecção
            credentials: Credenciais para autenticação automática (opcional)
            
        Returns:
            Tuple[List[DetectedField], str, bool]: (campos_detectados, metodo_deteccao, sessao_usada)
        """
        session_used = False
        domain = urlparse(url).netloc
        original_url = url
        
        logger.info(f"Iniciando detecção de campos para URL: {url}")
        username = credentials.username if credentials else None
        if username:
            logger.info(f"Usuário especificado: '{username}' - tentando carregar sessão salva")
        
        try:
            # Etapa 1: Carregar sessão salva se disponível
            if username and self.session_service.session_exists(url, username):
                logger.info(f"Verificando sessão salva para usuário '{username}' no domínio '{domain}'")
                session_loaded = await self.session_service.apply_session_to_context(context, url, username)
                if session_loaded:
                    logger.info(f"Sessão salva carregada com sucesso para usuário '{username}'")
                    session_used = True
                else:
                    logger.warning(f"Falha ao carregar sessão salva para usuário '{username}'")
            elif username:
                logger.warning(f"Nenhuma sessão salva encontrada para usuário '{username}' no domínio '{domain}'")
            
            # Etapa 2: Navegar para a URL
            logger.info(f"Navegando para URL: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            current_url = page.url
            logger.info(f"Navegação concluída. URL atual: {current_url}")
            
            # Aguardar carregamento completo
            logger.debug("Aguardando carregamento adicional da página")
            await asyncio.sleep(2)
            
            # Etapa 3: Verificar se foi redirecionado para página de login
            is_login_page = await self._is_login_page(page, original_url, current_url)
            if is_login_page:
                logger.warning(f"Detectado redirecionamento para página de login. URL original: {original_url}, URL atual: {current_url}")
                
                # Etapa 4: Tentar autenticação automática se credenciais fornecidas
                if credentials:
                    logger.info("Credenciais fornecidas. Tentando autenticação automática...")
                    auth_success = await self._perform_auto_authentication(page, credentials)
                    
                    if auth_success:
                        logger.info("Autenticação automática bem-sucedida. Redirecionando para URL original...")
                        # Etapa 5: Navegar para URL original após autenticação
                        await page.goto(original_url, wait_until='networkidle', timeout=30000)
                        final_url = page.url
                        logger.info(f"Redirecionamento pós-autenticação concluído. URL final: {final_url}")
                        
                        # Atualizar variáveis para refletir o estado pós-autenticação
                        current_url = final_url
                        is_login_page = await self._is_login_page(page, original_url, final_url)
                        
                        # Verificar se ainda estamos na página de login
                        if is_login_page:
                            logger.error("Ainda na página de login após autenticação. Autenticação pode ter falhado.")
                            return [], "Erro: Autenticação falhou - ainda na página de login", session_used
                        else:
                            logger.info(f"Autenticação bem-sucedida! Agora na URL de destino: {final_url}")
                    else:
                        logger.error("Falha na autenticação automática. Detectando campos da página de login.")
                        # Continuar com detecção na página de login para mostrar campos disponíveis
                else:
                    logger.warning("Redirecionado para login mas credenciais não foram fornecidas na requisição. Detectando campos da página de login.")
                    # Continuar com detecção na página de login
            
            # Etapa 6: Detectar campos usando heurísticas
            current_detection_url = page.url
            
            # Se estamos na página de login sem credenciais, detectar campos de login
            if is_login_page and not credentials:
                logger.info(f"Detectando campos de login na URL: {current_detection_url}")
            else:
                logger.info(f"Iniciando detecção de campos usando heurísticas baseadas em Playwright na URL: {current_detection_url}")
            
            detected_fields, detection_method = await self._detect_interactive_fields(page)
            
            # Adicionar informação sobre redirecionamento ao método de detecção
            if is_login_page:
                detection_method += " (página de login detectada)"
            
            logger.info(f"Detecção concluída: {len(detected_fields)} campos encontrados usando {detection_method}")
            
            # Log detalhado dos campos encontrados
            if detected_fields:
                logger.info("Campos detectados:")
                for i, field in enumerate(detected_fields, 1):
                    logger.info(f"  {i}. {field.name} ({field.type}) - Seletor: {field.selector}")
            else:
                logger.warning("Nenhum campo interativo foi detectado na página")
            
            return detected_fields, detection_method, session_used
            
        except Exception as e:
            logger.error(f"Erro crítico durante detecção de campos na URL {url}: {str(e)}", exc_info=True)
            return [], f"Erro na detecção: {str(e)}", session_used
    
    async def _is_login_page(self, page: Page, original_url: str, current_url: str) -> bool:
        """
        Verifica se a página atual é uma página de login baseada na URL e conteúdo.
        
        Args:
            page: Instância da página Playwright
            original_url: URL original solicitada
            current_url: URL atual após navegação
            
        Returns:
            bool: True se for uma página de login
        """
        try:
            # Verificar se houve redirecionamento para URL diferente
            url_redirected = original_url != current_url
            
            # Verificar indicadores de login na URL
            login_url_patterns = [
                '/login', '/signin', '/auth', '/authentication',
                'login.', 'signin.', 'auth.', 'sso.',
                'login?', 'signin?', 'auth?'
            ]
            
            url_indicates_login = any(pattern in current_url.lower() for pattern in login_url_patterns)
            
            # Verificar presença de campos típicos de login
            username_field = await page.query_selector('input[name*="user"], input[name*="email"], input[name*="login"], input[id*="user"], input[id*="email"], input[id*="login"]')
            password_field = await page.query_selector('input[type="password"]')
            
            has_login_fields = username_field is not None and password_field is not None
            
            # Verificar palavras-chave de login no conteúdo da página
            try:
                page_text = await page.inner_text('body')
                login_keywords = ['login', 'sign in', 'entrar', 'acesso', 'authentication', 'autenticação']
                has_login_keywords = any(keyword.lower() in page_text.lower() for keyword in login_keywords)
            except:
                has_login_keywords = False
            
            # Verificar título da página
            try:
                page_title = await page.title()
                title_indicates_login = any(keyword.lower() in page_title.lower() for keyword in ['login', 'sign in', 'entrar', 'acesso'])
            except:
                title_indicates_login = False
            
            is_login = (url_redirected and url_indicates_login) or (has_login_fields and (has_login_keywords or title_indicates_login))
            
            logger.info(f"Análise de página de login - Redirecionado: {url_redirected}, URL indica login: {url_indicates_login}, Campos de login: {has_login_fields}, Palavras-chave: {has_login_keywords}, Título indica login: {title_indicates_login}, Resultado: {is_login}")
            
            return is_login
            
        except Exception as e:
            logger.error(f"Erro ao verificar se é página de login: {str(e)}")
            return False
    
    async def _perform_auto_authentication(self, page: Page, credentials: AuthCredentials) -> bool:
        """
        Executa autenticação automática na página de login.
        
        Args:
            page: Instância da página Playwright
            credentials: Objeto AuthCredentials com username e password
            
        Returns:
            bool: True se autenticação foi bem-sucedida
        """
        try:
            logger.info(f"Iniciando autenticação automática para usuário: {credentials.username}")
            
            # Tentar encontrar campo de usuário
            username_selectors = [
                'input[name="username"]',
                'input[name="user"]',
                'input[name="email"]',
                'input[name="login"]',
                'input[id="username"]',
                'input[id="user"]',
                'input[id="email"]',
                'input[id="login"]',
                'input[type="text"]',
                'input[type="email"]'
            ]
            
            username_field = None
            for selector in username_selectors:
                username_field = await page.query_selector(selector)
                if username_field and await username_field.is_visible():
                    logger.debug(f"Campo de usuário encontrado com seletor: {selector}")
                    break
            
            if not username_field:
                logger.error("Campo de usuário não encontrado")
                return False
            
            # Tentar encontrar campo de senha
            password_field = await page.query_selector('input[type="password"]')
            if not password_field or not await password_field.is_visible():
                logger.error("Campo de senha não encontrado")
                return False
            
            # Preencher credenciais
            logger.info("Preenchendo credenciais...")
            await username_field.fill(credentials.username)
            await password_field.fill(credentials.password)
            
            # Tentar encontrar e clicar no botão de submit
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'button:has-text("Entrar")',
                'button:has-text("Acessar")',
                '.oxd-button--main',  # Específico para OrangeHRM
                'form button'
            ]
            
            submit_button = None
            for selector in submit_selectors:
                submit_button = await page.query_selector(selector)
                if submit_button and await submit_button.is_visible():
                    logger.debug(f"Botão de submit encontrado com seletor: {selector}")
                    break
            
            if submit_button:
                logger.info("Clicando no botão de login...")
                await submit_button.click()
            else:
                # Tentar submit via Enter no campo de senha
                logger.info("Botão não encontrado, tentando submit via Enter...")
                await password_field.press('Enter')
            
            # Aguardar navegação ou mudança na página
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except:
                await asyncio.sleep(3)  # Fallback se wait_for_load_state falhar
            
            # Verificar se autenticação foi bem-sucedida
            # (se não há mais campos de login visíveis, provavelmente foi bem-sucedida)
            try:
                current_password_field = await page.query_selector('input[type="password"]')
                if current_password_field:
                    is_visible = await current_password_field.is_visible()
                    auth_success = not is_visible
                else:
                    auth_success = True  # Campo de senha não existe mais
            except Exception as e:
                # Se houve erro ao verificar (ex: contexto destruído por navegação),
                # assumir que autenticação foi bem-sucedida
                logger.debug(f"Erro ao verificar campos pós-autenticação (normal se houve navegação): {str(e)}")
                auth_success = True
            
            logger.info(f"Resultado da autenticação automática: {'Sucesso' if auth_success else 'Falha'}")
            return auth_success
            
        except Exception as e:
            logger.error(f"Erro durante autenticação automática: {str(e)}")
            return False
    
    async def _detect_interactive_fields(self, page: Page) -> Tuple[List[DetectedField], str]:
        """
        Detecta campos interativos usando heurísticas otimizadas conforme estratégia MVP.
        
        Args:
            page: Instância da página Playwright
            
        Returns:
            Tuple[List[DetectedField], str]: (campos_detectados, metodo_usado)
        """
        try:
            logger.debug("Aguardando carregamento completo da página")
            await asyncio.sleep(1)
            
            detected_fields = []
            
            # Estratégia 1: Detectar campos de formulário
            logger.info("Etapa 1/4: Detectando campos de formulário")
            form_fields = await self._detect_form_fields(page)
            detected_fields.extend(form_fields)
            logger.info(f"Campos de formulário detectados: {len(form_fields)}")
            
            # Estratégia 2: Detectar botões interativos (COMENTADO - apenas interativo, não relevante para web-scraping)
            # logger.info("Etapa 2/4: Detectando botões interativos")
            # interactive_buttons = await self._detect_interactive_buttons(page)
            # detected_fields.extend(interactive_buttons)
            # logger.info(f"Botões interativos detectados: {len(interactive_buttons)}")
            
            # Estratégia 3: Detectar links importantes (COMENTADO - apenas interativo, não relevante para web-scraping)
            # logger.debug("Etapa 3/4: Detectando links importantes")
            # important_links = await self._detect_important_links(page)
            # detected_fields.extend(important_links)
            # logger.info(f"Links importantes detectados: {len(important_links)}")
            
            # Estratégia 4: Detectar elementos com eventos (COMENTADO - apenas interativo, não relevante para web-scraping)
            # logger.info("Etapa 4/7: Detectando elementos com eventos JavaScript")
            # event_elements = await self._detect_event_elements(page)
            # detected_fields.extend(event_elements)
            # logger.info(f"Elementos com eventos detectados: {len(event_elements)}")
            
            # Estratégia 2: Detectar elementos com dados estruturados (MANTIDO - relevante para web-scraping)
            # logger.info("Etapa 2/4: Detectando elementos com dados estruturados")
            # data_elements = await self._detect_data_elements(page)
            # detected_fields.extend(data_elements)
            # logger.info(f"Elementos com dados detectados: {len(data_elements)}")
            
            # Estratégia 3: Detectar tabelas e dados tabulares (MANTIDO - relevante para web-scraping)
            # logger.info("Etapa 3/4: Detectando tabelas e dados tabulares")
            # table_elements = await self._detect_table_data(page)
            # detected_fields.extend(table_elements)
            # logger.info(f"Elementos de tabela detectados: {len(table_elements)}")
            
            # Estratégia 4: Detectar listas e elementos repetitivos (MANTIDO - relevante para web-scraping)
            # logger.info("Etapa 4/4: Detectando listas e elementos repetitivos")
            # list_elements = await self._detect_list_data(page)
            # detected_fields.extend(list_elements)
            # logger.info(f"Elementos de lista detectados: {len(list_elements)}")
            
            # Remover duplicatas baseado no seletor
            logger.debug("Removendo campos duplicados")
            unique_fields = self._remove_duplicate_fields(detected_fields)
            
            detection_method = "Heurísticas Playwright"
            
            # Classificar campos por tipo
            interactive_count = len([f for f in unique_fields if f.type in ['input', 'button', 'link', 'select', 'textarea']])
            data_count = len([f for f in unique_fields if f.type in ['data', 'table_header', 'table_cell', 'list_item']])
            
            if len(unique_fields) == 0:
                logger.warning("Nenhum campo detectado após aplicação de todas as estratégias")
                detection_method = "Nenhum campo encontrado"
            else:
                logger.info(f"Detecção de campos concluída: {len(unique_fields)} campos únicos ({interactive_count} interativos, {data_count} com dados)")
            
            return unique_fields, detection_method
            
        except Exception as e:
            logger.error(f"Erro crítico na detecção de campos interativos: {str(e)}", exc_info=True)
            return [], f"Erro: {str(e)}"
    
    async def _detect_form_fields(self, page: Page) -> List[DetectedField]:
        """
        Detecta campos de formulário (inputs, selects, textareas).
        
        Args:
            page: Instância da página Playwright
            
        Returns:
            List[DetectedField]: Lista de campos de formulário detectados
        """
        fields = []
        
        try:
            # Detectar inputs
            input_selectors = [
                'input[type="text"]',
                'input[type="email"]',
                'input[type="password"]',
                'input[type="number"]',
                'input[type="tel"]',
                'input[type="url"]',
                'input[type="search"]',
                'input[type="date"]',
                'input[type="datetime-local"]',
                'input[type="time"]',
                'input[type="checkbox"]',
                'input[type="radio"]',
                'input[type="file"]',
                # Seletores específicos para Angular Material
                'input.mat-datepicker-input',
                'input[matinput]',
                'input.mat-input-element'
            ]
            
            logger.debug(f"Detectando campos de entrada usando {len(input_selectors)} seletores")
            for i, selector in enumerate(input_selectors):
                elements = await page.query_selector_all(selector)
                logger.debug(f"Seletor '{selector}': {len(elements)} elementos encontrados")
                for j, element in enumerate(elements):
                    try:
                        if await element.is_visible():
                            field = await self._create_field_from_element(element, 'input', page)
                            if field:
                                fields.append(field)
                                logger.debug(f"Campo de entrada {j+1} processado: {field.name}")
                    except Exception as e:
                        logger.debug(f"Erro ao processar elemento de entrada {j+1}: {e}")
                        continue
            
            # Detectar selects
            logger.debug("Detectando campos de seleção")
            select_elements = await page.query_selector_all('select')
            logger.debug(f"Encontrados {len(select_elements)} campos de seleção")
            for i, element in enumerate(select_elements):
                try:
                    if await element.is_visible():
                        field = await self._create_field_from_element(element, 'select', page)
                        if field:
                            fields.append(field)
                            logger.debug(f"Campo de seleção {i+1} processado: {field.name}")
                except Exception as e:
                    logger.debug(f"Erro ao processar campo de seleção {i+1}: {e}")
                    continue
            
            # Detectar textareas
            logger.debug("Detectando áreas de texto")
            textarea_elements = await page.query_selector_all('textarea')
            logger.debug(f"Encontradas {len(textarea_elements)} áreas de texto")
            for i, element in enumerate(textarea_elements):
                try:
                    if await element.is_visible():
                        field = await self._create_field_from_element(element, 'textarea', page)
                        if field:
                            fields.append(field)
                            logger.debug(f"Área de texto {i+1} processada: {field.name}")
                except Exception as e:
                    logger.debug(f"Erro ao processar área de texto {i+1}: {e}")
                    continue
            
            logger.info(f"Detecção de campos de formulário concluída: {len(fields)} campos processados")
            
        except Exception as e:
            logger.error(f"Erro crítico ao detectar campos de formulário: {str(e)}", exc_info=True)
        
        return fields
    
    async def _detect_interactive_buttons(self, page: Page) -> List[DetectedField]:
        """
        Detecta botões interativos na página.
        
        Args:
            page: Instância da página Playwright
            
        Returns:
            List[DetectedField]: Lista de botões detectados
        """
        fields = []
        
        try:
            logger.debug("Iniciando detecção de botões interativos")
            
            # Detectar botões
            button_selectors = [
                'button',
                'input[type="button"]',
                'input[type="submit"]',
                'input[type="reset"]'
            ]
            
            logger.debug(f"Detectando botões usando {len(button_selectors)} seletores")
            for i, selector in enumerate(button_selectors):
                elements = await page.query_selector_all(selector)
                logger.debug(f"Seletor '{selector}': {len(elements)} elementos encontrados")
                for j, element in enumerate(elements):
                    try:
                        if await element.is_visible():
                            field = await self._create_field_from_element(element, 'button', page)
                            if field:
                                fields.append(field)
                                logger.debug(f"Botão {j+1} processado: {field.name}")
                    except Exception as e:
                        logger.debug(f"Erro ao processar botão {j+1}: {e}")
                        continue
            
            # Detectar elementos clicáveis com role="button"
            logger.debug("Detectando elementos com role='button'")
            role_buttons = await page.query_selector_all('[role="button"]')
            logger.debug(f"Encontrados {len(role_buttons)} elementos com role='button'")
            for i, element in enumerate(role_buttons):
                try:
                    if await element.is_visible():
                        field = await self._create_field_from_element(element, 'button', page)
                        if field:
                            fields.append(field)
                            logger.debug(f"Elemento role='button' {i+1} processado: {field.name}")
                except Exception as e:
                    logger.debug(f"Erro ao processar elemento role='button' {i+1}: {e}")
                    continue
            
            logger.info(f"Detecção de botões interativos concluída: {len(fields)} botões processados")
            
        except Exception as e:
            logger.error(f"Erro crítico ao detectar botões: {str(e)}", exc_info=True)
        
        return fields
    
    async def _detect_important_links(self, page: Page) -> List[DetectedField]:
        """
        Detecta links importantes na página.
        
        Args:
            page: Instância da página Playwright
            
        Returns:
            List[DetectedField]: Lista de links importantes
        """
        fields = []
        
        try:
            logger.debug("Iniciando detecção de links importantes")
            
            # Palavras-chave para links importantes
            important_keywords = [
                'cadastro', 'registro', 'sign up', 'register',
                'contato', 'contact', 'fale conosco',
                'sobre', 'about', 'quem somos',
                'produtos', 'services', 'serviços',
                'login', 'entrar', 'sign in',
                'carrinho', 'cart', 'comprar', 'buy',
                'perfil', 'profile', 'conta', 'account'
            ]
            
            logger.debug(f"Detectando links usando {len(important_keywords)} palavras-chave")
            link_elements = await page.query_selector_all('a[href]')
            logger.debug(f"Encontrados {len(link_elements)} links na página")
            
            for i, element in enumerate(link_elements):
                try:
                    if await element.is_visible():
                        text = await element.inner_text()
                        href = await element.get_attribute('href')
                        
                        # Verificar se o link contém palavras-chave importantes
                        if text and any(keyword.lower() in text.lower() for keyword in important_keywords):
                            field = await self._create_field_from_element(element, 'link', page)
                            if field:
                                fields.append(field)
                                logger.debug(f"Link importante {len(fields)} detectado por texto: '{text[:50]}...'")
                        elif href and any(keyword.lower() in href.lower() for keyword in important_keywords):
                            field = await self._create_field_from_element(element, 'link', page)
                            if field:
                                fields.append(field)
                                logger.debug(f"Link importante {len(fields)} detectado por href: '{href[:50]}...'")
                except Exception as e:
                    logger.debug(f"Erro ao processar link {i+1}: {e}")
                    continue
            
            logger.info(f"Detecção de links importantes concluída: {len(fields)} links processados")
            
        except Exception as e:
            logger.error(f"Erro crítico ao detectar links: {str(e)}", exc_info=True)
        
        return fields
    
    async def _detect_event_elements(self, page: Page) -> List[DetectedField]:
        """
        Detecta elementos com eventos JavaScript (onclick, etc.).
        
        Args:
            page: Instância da página Playwright
            
        Returns:
            List[DetectedField]: Lista de elementos com eventos
        """
        fields = []
        
        try:
            logger.debug("Iniciando detecção de elementos com eventos JavaScript")
            
            # Detectar elementos com onclick
            logger.debug("Detectando elementos com eventos onclick")
            onclick_elements = await page.query_selector_all('[onclick]')
            logger.debug(f"Encontrados {len(onclick_elements)} elementos com onclick")
            for i, element in enumerate(onclick_elements):
                try:
                    if await element.is_visible():
                        field = await self._create_field_from_element(element, 'clickable', page)
                        if field:
                            fields.append(field)
                            logger.debug(f"Elemento onclick {i+1} processado: {field.name}")
                except Exception as e:
                    logger.debug(f"Erro ao processar elemento onclick {i+1}: {e}")
                    continue
            
            # Detectar elementos com data-* attributes que indicam interatividade
            interactive_selectors = [
                '[data-action]',
                '[data-click]',
                '[data-toggle]',
                '[data-target]',
                '[data-href]'
            ]
            
            logger.debug(f"Detectando elementos com atributos data-* ({len(interactive_selectors)} seletores)")
            for selector in interactive_selectors:
                elements = await page.query_selector_all(selector)
                logger.debug(f"Seletor '{selector}': {len(elements)} elementos encontrados")
                for i, element in enumerate(elements):
                    try:
                        if await element.is_visible():
                            field = await self._create_field_from_element(element, 'interactive', page)
                            if field:
                                fields.append(field)
                                logger.debug(f"Elemento '{selector}' {i+1} processado: {field.name}")
                    except Exception as e:
                        logger.debug(f"Erro ao processar elemento '{selector}' {i+1}: {e}")
                        continue
            
            logger.info(f"Detecção de elementos com eventos concluída: {len(fields)} elementos processados")
            
        except Exception as e:
            logger.error(f"Erro crítico ao detectar elementos com eventos: {str(e)}", exc_info=True)
        
        return fields
    
    async def _create_field_from_element(self, element, field_type: str, page: Page) -> Optional[DetectedField]:
        """
        Cria um objeto DetectedField a partir de um elemento HTML.
        
        Args:
            element: Elemento Playwright
            field_type: Tipo do campo
            page: Instância da página
            
        Returns:
            Optional[DetectedField]: Campo detectado ou None
        """
        try:
            logger.debug(f"Criando campo do tipo '{field_type}' a partir do elemento")
            
            # Obter atributos básicos
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            logger.debug(f"Tag do elemento: '{tag_name}'")
            
            # Gerar seletor CSS único
            css_selector = await self._generate_unique_selector(element)
            if not css_selector:
                logger.warning(f"Não foi possível gerar seletor CSS único para elemento '{tag_name}' do tipo '{field_type}'")
                return None
            
            # Gerar XPath
            xpath = await self._generate_xpath(element)
            logger.debug(f"XPath gerado: '{xpath[:50]}...'")
            
            # Obter texto visível
            text = await element.inner_text() if tag_name not in ['input', 'select'] else ''
            text = text.strip()[:100] if text else ''  # Limitar tamanho
            logger.debug(f"Texto do elemento: '{text[:50]}...'")
            
            # Obter atributos relevantes
            attributes = {}
            
            # Atributos comuns
            common_attrs = ['id', 'name', 'class', 'type', 'placeholder', 'value', 'href', 'title', 'alt']
            for attr in common_attrs:
                try:
                    value = await element.get_attribute(attr)
                    if value:
                        attributes[attr] = value
                        logger.debug(f"Atributo '{attr}': '{value[:50]}...'")
                except:
                    continue
            
            # Obter posição do elemento
            try:
                bounding_box = await element.bounding_box()
                position = {
                    'x': int(bounding_box['x']) if bounding_box else 0,
                    'y': int(bounding_box['y']) if bounding_box else 0,
                    'width': int(bounding_box['width']) if bounding_box else 0,
                    'height': int(bounding_box['height']) if bounding_box else 0
                }
                logger.debug(f"Posição do elemento: x={position['x']}, y={position['y']}, w={position['width']}, h={position['height']}")
            except Exception as e:
                logger.debug(f"Erro ao obter posição do elemento: {e}")
                position = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
            
            # Determinar se é obrigatório
            is_required = False
            try:
                required_attr = await element.get_attribute('required')
                is_required = required_attr is not None
                logger.debug(f"Campo obrigatório: {is_required}")
            except Exception as e:
                logger.debug(f"Erro ao verificar se campo é obrigatório: {e}")
                pass
            
            # Gerar label/descrição
            label = await self._extract_field_label(element, page)
            logger.debug(f"Label extraído: '{label}'")
            
            # Extrair nome do campo
            field_name = attributes.get('name') or attributes.get('id') or f"{field_type}_{css_selector.replace(' ', '_').replace('>', '_').replace(':', '_')[:20]}"
            
            # Extrair placeholder
            placeholder = attributes.get('placeholder')
            
            # Extrair opções para campos select/combobox
            options = None
            if field_type == 'select':
                logger.info(f"Extraindo opções do elemento select: {field_name}")
                options = await self._extract_select_options(element)
                logger.info(f"Opções extraídas: {len(options) if options else 0} opções")
            
            field = DetectedField(
                name=field_name,
                type=field_type,
                css_selector=css_selector,
                xpath=xpath,
                placeholder=placeholder,
                label=label,
                selector=css_selector,  # Manter compatibilidade com versão anterior
                description=text or placeholder or attributes.get('title') or label,
                options=options
            )
            
            logger.debug(f"Campo criado com sucesso: '{label}' ({field_type})")
            return field
            
        except Exception as e:
            logger.error(f"Erro crítico ao criar campo do elemento tipo '{field_type}': {str(e)}", exc_info=True)
            return None
    
    async def _extract_select_options(self, select_element) -> Optional[List[Dict[str, str]]]:
        """
        Extrai todas as opções disponíveis de um elemento select.
        
        Args:
            select_element: Elemento select do Playwright
            
        Returns:
            Optional[List[Dict[str, str]]]: Lista de opções com 'value' e 'text', ou None se erro
        """
        try:
            logger.debug("Iniciando extração de opções do select")
            
            # Buscar todos os elementos option dentro do select
            option_elements = await select_element.query_selector_all('option')
            logger.debug(f"Encontrados {len(option_elements)} elementos option")
            
            if not option_elements:
                logger.debug("Nenhuma opção encontrada no select")
                return None
            
            options = []
            for i, option in enumerate(option_elements):
                try:
                    # Extrair value e text de cada option
                    value = await option.get_attribute('value') or ''
                    text = await option.inner_text()
                    text = text.strip() if text else ''
                    
                    # Se não há text, usar o value como text
                    if not text and value:
                        text = value
                    
                    # Se não há value, usar o text como value
                    if not value and text:
                        value = text
                    
                    # Adicionar apenas se há pelo menos um dos dois
                    if value or text:
                        option_data = {
                            'value': value,
                            'text': text
                        }
                        options.append(option_data)
                        logger.debug(f"Opção {i+1}: value='{value}', text='{text[:50]}...'")
                    else:
                        logger.debug(f"Opção {i+1} ignorada: sem value nem text")
                        
                except Exception as e:
                    logger.debug(f"Erro ao processar opção {i+1}: {str(e)}")
                    continue
            
            logger.debug(f"Extração concluída: {len(options)} opções válidas encontradas")
            return options if options else None
            
        except Exception as e:
            logger.error(f"Erro crítico ao extrair opções do select: {str(e)}", exc_info=True)
            return None
    
    async def _generate_unique_selector(self, element) -> str:
        """
        Gera um seletor único para o elemento.
        
        Args:
            element: Elemento Playwright
            
        Returns:
            str: Seletor CSS único
        """
        try:
            logger.debug("Iniciando geração de seletor único")
            
            # Tentar usar ID primeiro
            element_id = await element.get_attribute('id')
            if element_id:
                selector = f'#{element_id}'
                logger.debug(f"Seletor por ID gerado: '{selector}'")
                return selector
            
            # Tentar usar name
            name = await element.get_attribute('name')
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            if name:
                selector = f'{tag_name}[name="{name}"]'
                logger.debug(f"Seletor por name gerado: '{selector}'")
                return selector
            
            # Usar nth-child como fallback
            logger.debug("Gerando seletor usando nth-child como fallback")
            selector = await element.evaluate('''
                el => {
                    let path = [];
                    while (el.parentElement) {
                        let tagName = el.tagName.toLowerCase();
                        let siblings = Array.from(el.parentElement.children).filter(child => child.tagName === el.tagName);
                        if (siblings.length > 1) {
                            let index = siblings.indexOf(el) + 1;
                            tagName += `:nth-child(${index})`;
                        }
                        path.unshift(tagName);
                        el = el.parentElement;
                        if (path.length > 5) break; // Limitar profundidade
                    }
                    return path.join(' > ');
                }
            ''')
            
            if selector:
                logger.debug(f"Seletor nth-child gerado: '{selector[:100]}...'")
                return selector
            else:
                logger.warning("Não foi possível gerar seletor, usando 'unknown'")
                return 'unknown'
            
        except Exception as e:
            logger.error(f"Erro crítico ao gerar seletor: {str(e)}", exc_info=True)
            return 'unknown'
    
    async def _generate_xpath(self, element) -> str:
        """
        Gera um XPath único para o elemento.
        
        Args:
            element: Elemento Playwright
            
        Returns:
            str: XPath único para o elemento
        """
        try:
            logger.debug("Iniciando geração de XPath")
            
            # Gerar XPath usando JavaScript
            xpath = await element.evaluate('''
                el => {
                    function getElementXPath(element) {
                        // 1. Prioridade: Label associado via 'for' attribute
                        if (element.id) {
                            const label = document.querySelector(`label[for="${element.id}"]`);
                            if (label && label.textContent) {
                                const labelText = label.textContent.trim();
                                return `//label[contains(text(),'${labelText}')]/following::${element.tagName.toLowerCase()}[1]`;
                            }
                        }
                        
                        // 2. Prioridade: Label próximo no DOM (parent/sibling)
                        const parentLabel = element.closest('label');
                        if (parentLabel && parentLabel.textContent) {
                            const labelText = parentLabel.textContent.trim();
                            return `//label[contains(text(),'${labelText}')]//${element.tagName.toLowerCase()}`;
                        }
                        
                        // 3. Prioridade: aria-label quando disponível
                        if (element.getAttribute('aria-label')) {
                            const ariaLabel = element.getAttribute('aria-label');
                            return `//${element.tagName.toLowerCase()}[@aria-label="${ariaLabel}"]`;
                        }
                        
                        // 4. Prioridade: placeholder quando disponível
                        if (element.placeholder) {
                            return `//${element.tagName.toLowerCase()}[@placeholder="${element.placeholder}"]`;
                        }
                        
                        // 5. Fallback: ID se disponível
                        if (element.id) {
                            return `//*[@id="${element.id}"]`;
                        }
                        
                        // 6. Fallback: name se disponível
                        if (element.name) {
                            return `//${element.tagName.toLowerCase()}[@name="${element.name}"]`;
                        }
                        
                        // 7. Último recurso: posição relativa (evitando caminhos absolutos)
                        let path = '';
                        let current = element;
                        
                        while (current && current.nodeType === Node.ELEMENT_NODE && current !== document.body) {
                            let index = 1;
                            let sibling = current.previousElementSibling;
                            
                            while (sibling) {
                                if (sibling.tagName === current.tagName) {
                                    index++;
                                }
                                sibling = sibling.previousElementSibling;
                            }
                            
                            const tagName = current.tagName.toLowerCase();
                            path = `/${tagName}[${index}]${path}`;
                            current = current.parentElement;
                        }
                        
                        return `//${element.tagName.toLowerCase()}${path.substring(path.lastIndexOf('/'))}`;
                    }
                    
                    return getElementXPath(el);
                }
            ''')
            
            if xpath:
                logger.debug(f"XPath gerado: '{xpath[:100]}...'")
                return xpath
            else:
                logger.warning("Não foi possível gerar XPath, usando fallback")
                return '//unknown'
                
        except Exception as e:
            logger.error(f"Erro crítico ao gerar XPath: {str(e)}", exc_info=True)
            return '//unknown'
    
    async def _extract_field_label(self, element, page: Page) -> str:
        """
        Extrai o label/descrição do campo.
        
        Args:
            element: Elemento Playwright
            page: Instância da página
            
        Returns:
            str: Label do campo
        """
        try:
            logger.debug("Iniciando extração de label do campo")
            
            # Tentar encontrar label associado
            element_id = await element.get_attribute('id')
            if element_id:
                logger.debug(f"Procurando label associado ao ID '{element_id}'")
                label_element = await page.query_selector(f'label[for="{element_id}"]')
                if label_element:
                    label_text = await label_element.inner_text()
                    if label_text.strip():
                        label = label_text.strip()[:50]
                        logger.debug(f"Label encontrado por ID: '{label}'")
                        return label
            
            # Tentar encontrar label pai
            try:
                logger.debug("Procurando label pai")
                parent_label = await element.evaluate('''
                    el => {
                        let parent = el.parentElement;
                        while (parent && parent.tagName !== 'BODY') {
                            if (parent.tagName === 'LABEL') {
                                return parent.innerText;
                            }
                            parent = parent.parentElement;
                        }
                        return null;
                    }
                ''')
                if parent_label:
                    label = parent_label.strip()[:50]
                    logger.debug(f"Label encontrado no elemento pai: '{label}'")
                    return label
            except Exception as e:
                logger.debug(f"Erro ao procurar label pai: {e}")
                pass
            
            # Usar placeholder como fallback
            placeholder = await element.get_attribute('placeholder')
            if placeholder:
                label = placeholder.strip()[:50]
                logger.debug(f"Label extraído do placeholder: '{label}'")
                return label
            
            # Usar title como fallback
            title = await element.get_attribute('title')
            if title:
                label = title.strip()[:50]
                logger.debug(f"Label extraído do title: '{label}'")
                return label
            
            # Usar texto do elemento (para botões/links)
            text = await element.inner_text()
            if text and text.strip():
                label = text.strip()[:50]
                logger.debug(f"Label extraído do texto do elemento: '{label}'")
                return label
            
            logger.debug("Nenhum label encontrado, usando padrão")
            return 'Campo sem label'
            
        except Exception as e:
            logger.error(f"Erro crítico ao extrair label: {str(e)}", exc_info=True)
            return 'Campo sem label'
    
    async def _detect_data_elements(self, page) -> List[DetectedField]:
        """
        Detecta elementos que contêm dados estruturados relevantes para web-scraping.
        
        Args:
            page: Instância da página Playwright
            
        Returns:
            List[DetectedField]: Lista de campos com dados detectados
        """
        detected_fields = []
        
        try:
            # Detectar elementos com texto significativo
            text_selectors = [
                'p:not(:empty)',
                'span:not(:empty)',
                'div:not(:empty):not(:has(div)):not(:has(p)):not(:has(span))',
                'h1, h2, h3, h4, h5, h6',
                '[data-value]',
                '[data-text]',
                '.value, .text, .content, .data',
                '*[class*="value"], *[class*="text"], *[class*="content"], *[class*="data"]'
            ]
            
            for selector in text_selectors:
                elements = await page.query_selector_all(selector)
                for element in elements[:20]:  # Limitar para evitar sobrecarga
                    try:
                        text_content = await element.text_content()
                        if text_content and len(text_content.strip()) > 2:
                            # Verificar se contém dados estruturados
                            if self._is_structured_data(text_content.strip()):
                                field_name = await self._generate_field_name(element, text_content[:50])
                                element_selector = await self._get_element_selector(element)
                                
                                detected_fields.append(DetectedField(
                                    name=field_name,
                                    selector=element_selector,
                                    type="data",
                                    description=f"Elemento com dados: {text_content[:100]}..."
                                ))
                    except Exception as e:
                        logger.debug(f"Erro ao processar elemento de dados: {e}")
                        continue
            
            logger.debug(f"Detectados {len(detected_fields)} elementos com dados estruturados")
            
        except Exception as e:
            logger.error(f"Erro na detecção de elementos com dados: {e}")
            
        return detected_fields
    
    async def _detect_table_data(self, page) -> List[DetectedField]:
        """
        Detecta tabelas e dados tabulares.
        
        Args:
            page: Instância da página Playwright
            
        Returns:
            List[DetectedField]: Lista de campos de tabela detectados
        """
        detected_fields = []
        
        try:
            # Detectar tabelas
            tables = await page.query_selector_all('table')
            for i, table in enumerate(tables):
                try:
                    # Detectar cabeçalhos da tabela
                    headers = await table.query_selector_all('th')
                    if headers:
                        for j, header in enumerate(headers):
                            header_text = await header.text_content()
                            if header_text and header_text.strip():
                                header_selector = await self._get_element_selector(header)
                                detected_fields.append(DetectedField(
                                    name=f"Cabeçalho Tabela {i+1} - {header_text.strip()}",
                                    selector=header_selector,
                                    type="table_header",
                                    description=f"Cabeçalho de tabela: {header_text.strip()}"
                                ))
                    
                    # Detectar células de dados
                    cells = await table.query_selector_all('td')
                    for j, cell in enumerate(cells[:10]):  # Limitar células
                        cell_text = await cell.text_content()
                        if cell_text and cell_text.strip():
                            cell_selector = await self._get_element_selector(cell)
                            detected_fields.append(DetectedField(
                                name=f"Célula Tabela {i+1} - {cell_text.strip()[:30]}",
                                selector=cell_selector,
                                type="table_cell",
                                description=f"Célula de tabela: {cell_text.strip()[:100]}"
                            ))
                            
                except Exception as e:
                    logger.debug(f"Erro ao processar tabela {i}: {e}")
                    continue
            
            logger.debug(f"Detectados {len(detected_fields)} elementos de tabela")
            
        except Exception as e:
            logger.error(f"Erro na detecção de tabelas: {e}")
            
        return detected_fields
    
    async def _detect_list_data(self, page) -> List[DetectedField]:
        """
        Detecta listas e elementos repetitivos com dados.
        
        Args:
            page: Instância da página Playwright
            
        Returns:
            List[DetectedField]: Lista de campos de lista detectados
        """
        detected_fields = []
        
        try:
            # Detectar listas ordenadas e não ordenadas
            list_selectors = ['ul li', 'ol li', '.list-item', '*[class*="item"]', '*[class*="list"] > *']
            
            for selector in list_selectors:
                elements = await page.query_selector_all(selector)
                for i, element in enumerate(elements[:15]):  # Limitar itens
                    try:
                        text_content = await element.text_content()
                        if text_content and len(text_content.strip()) > 2:
                            element_selector = await self._get_element_selector(element)
                            field_name = f"Item Lista {i+1} - {text_content.strip()[:30]}"
                            
                            detected_fields.append(DetectedField(
                                name=field_name,
                                selector=element_selector,
                                type="list_item",
                                description=f"Item de lista: {text_content.strip()[:100]}"
                            ))
                    except Exception as e:
                        logger.debug(f"Erro ao processar item de lista {i}: {e}")
                        continue
            
            logger.debug(f"Detectados {len(detected_fields)} elementos de lista")
            
        except Exception as e:
            logger.error(f"Erro na detecção de listas: {e}")
            
        return detected_fields
    
    def _is_structured_data(self, text: str) -> bool:
        """
        Verifica se o texto contém dados estruturados relevantes.
        
        Args:
            text: Texto a ser analisado
            
        Returns:
            bool: True se contém dados estruturados
        """
        import re
        
        # Padrões para identificar dados estruturados
        patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # Datas
            r'\d+[.,]\d+',  # Números decimais
            r'\$\d+|R\$\d+|€\d+|£\d+',  # Valores monetários
            r'\b\d{3,}\b',  # Números grandes
            r'\b[A-Z]{2,}\b',  # Códigos/siglas
            r'\b\w+@\w+\.\w+\b',  # Emails
            r'\b\d{3}[.-]\d{3}[.-]\d{4}\b',  # Telefones
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return True
                
        # Verificar se tem comprimento mínimo e não é apenas espaços
        return len(text.strip()) >= 3 and not text.isspace()
    
    async def _generate_field_name(self, element, text_content: str) -> str:
        """
        Gera um nome para o campo baseado no elemento e conteúdo.
        
        Args:
            element: Elemento Playwright
            text_content: Conteúdo de texto do elemento
            
        Returns:
            str: Nome gerado para o campo
        """
        try:
            # Tentar obter atributos identificadores
            name_attr = await element.get_attribute('name')
            id_attr = await element.get_attribute('id')
            class_attr = await element.get_attribute('class')
            
            if name_attr:
                return f"campo_{name_attr}"
            elif id_attr:
                return f"campo_{id_attr}"
            elif class_attr:
                # Usar primeira classe como base
                first_class = class_attr.split()[0] if class_attr.split() else 'elemento'
                return f"campo_{first_class}"
            else:
                # Usar parte do texto como nome
                clean_text = re.sub(r'[^a-zA-Z0-9]', '_', text_content[:30])
                return f"campo_{clean_text}"
        except Exception:
            return "campo_sem_nome"
    
    async def _get_element_selector(self, element) -> str:
        """
        Gera um seletor CSS para o elemento.
        
        Args:
            element: Elemento Playwright
            
        Returns:
            str: Seletor CSS do elemento
        """
        try:
            # Tentar usar o método existente
            return await self._generate_unique_selector(element)
        except Exception:
            # Fallback para seletor simples
            try:
                tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                return tag_name
            except Exception:
                return "*"
    
    def _remove_duplicate_fields(self, fields: List[DetectedField]) -> List[DetectedField]:
        """
        Remove campos duplicados baseado no seletor.
        
        Args:
            fields: Lista de campos detectados
            
        Returns:
            List[DetectedField]: Lista sem duplicatas
        """
        logger.debug(f"Iniciando remoção de duplicatas de {len(fields)} campos")
        
        seen_selectors = set()
        unique_fields = []
        duplicates_count = 0
        
        for i, field in enumerate(fields):
            if field.selector not in seen_selectors:
                seen_selectors.add(field.selector)
                unique_fields.append(field)
                logger.debug(f"Campo {i+1} mantido: '{field.name}' ({field.selector})")
            else:
                duplicates_count += 1
                logger.debug(f"Campo {i+1} removido como duplicata: '{field.name}' ({field.selector})")
        
        logger.info(f"Remoção de duplicatas concluída: {duplicates_count} duplicatas removidas, {len(unique_fields)} campos únicos mantidos")
        return unique_fields
    
    def has_saved_session(self, url: str, username: str) -> bool:
        """
        Verifica se existe uma sessão salva para a URL e usuário.
        
        Args:
            url: URL do site
            username: Nome do usuário
            
        Returns:
            bool: True se existe sessão salva
        """
        return self.session_service.session_exists(url, username)
    
    async def load_saved_session(self, context, url: str, username: str) -> bool:
        """
        Carrega uma sessão salva no contexto do navegador.
        
        Args:
            context: Contexto do navegador
            url: URL do site
            username: Nome do usuário
            
        Returns:
            bool: True se a sessão foi carregada com sucesso
        """
        return await self.session_service.apply_session_to_context(context, url, username)