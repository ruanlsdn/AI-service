"""Serviço de autenticação para a funcionalidade do web crawler.
Implementa teste de autenticação e salvamento de sessão conforme estratégia MVP.
"""

import asyncio
from typing import Tuple, Dict, Any, Optional, List
from playwright.async_api import Page, BrowserContext
import logging
import re
from datetime import datetime

from src.models.schemas import AuthCredentials
from src.services.session_service import SessionService

# Configurar logger específico para o serviço de autenticação
logger = logging.getLogger("auth_service")

class AuthService:
    """Serviço para lidar com processos de autenticação web seguindo estratégia MVP."""
    
    def __init__(self):
        """
        Inicializa o serviço de autenticação.
        """
        self.session_service = SessionService()
        logger.info("Serviço de autenticação inicializado")
    
    async def perform_authentication(self, page: Page, context: BrowserContext, url: str, credentials: AuthCredentials) -> Tuple[bool, str, bool]:
        """
        Executa o fluxo completo de autenticação conforme estratégia MVP:
        1. Detecta formulário de login
        2. Preenche credenciais
        3. Submete formulário
        4. Verifica autenticação
        5. Salva sessão se bem-sucedida
        
        Args:
            page: Instância da página Playwright
            context: Contexto do navegador
            url: URL da página de login
            credentials: Credenciais de autenticação
            
        Returns:
            Tuple[bool, str, bool]: (sucesso_auth, mensagem, sessao_salva)
        """
        try:
            logger.info(f"Iniciando processo de autenticação para usuário '{credentials.username}' na URL: {url}")
            
            # Etapa 0: Navegar para a URL
            logger.info(f"Etapa 0/5: Navegando para a URL: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            logger.info(f"Navegação concluída para: {page.url}")
            
            # Etapa 1: Detectar formulário de login
            logger.info("Etapa 1/5: Iniciando detecção de formulário de login")
            form_detected, form_message = await self._detect_login_form(page)
            if not form_detected:
                logger.warning(f"Falha na detecção do formulário: {form_message}")
                return False, f"Formulário de login não detectado: {form_message}", False
            
            logger.info(f"Formulário de login detectado com sucesso: {form_message}")
            
            # Etapa 2: Preencher credenciais
            logger.info("Etapa 2/5: Iniciando preenchimento de credenciais")
            fill_success, fill_message = await self._fill_credentials(page, credentials)
            if not fill_success:
                logger.error(f"Falha no preenchimento de credenciais: {fill_message}")
                return False, f"Erro ao preencher credenciais: {fill_message}", False
            
            logger.info(f"Credenciais preenchidas com sucesso para usuário '{credentials.username}'")
            
            # Etapa 3: Submeter formulário
            logger.info("Etapa 3/5: Iniciando submissão do formulário")
            submit_success, submit_message = await self._submit_form(page)
            if not submit_success:
                logger.error(f"Falha na submissão do formulário: {submit_message}")
                return False, f"Erro ao submeter formulário: {submit_message}", False
            
            logger.info(f"Formulário submetido com sucesso: {submit_message}")
            
            # Etapa 4: Verificar autenticação
            logger.info("Etapa 4/5: Iniciando verificação de autenticação")
            auth_success, auth_message = await self._verify_authentication(page)
            if not auth_success:
                logger.warning("Verificação de autenticação falhou: Invalid credentials")
                return False, "Autenticação falhou: Invalid credentials", False
            
            logger.info(f"Autenticação verificada com sucesso: {auth_message}")
            
            # Etapa 5: Salvar sessão
            logger.info("Etapa 5/5: Iniciando salvamento da sessão")
            session_saved = await self.session_service.save_session(context, url, credentials.username)
            if session_saved:
                logger.info(f"Sessão salva com sucesso para usuário '{credentials.username}' na URL: {url}")
                return True, "Autenticação realizada com sucesso e sessão salva", True
            else:
                logger.warning(f"Autenticação bem-sucedida mas falha ao salvar sessão para usuário '{credentials.username}'")
                return True, "Autenticação realizada com sucesso mas sessão não foi salva", False
            
        except Exception as e:
            logger.error(f"Erro crítico durante processo de autenticação para usuário '{credentials.username}': {str(e)}", exc_info=True)
            return False, f"Erro interno durante autenticação: {str(e)}", False
    
    async def _detect_login_form(self, page: Page) -> Tuple[bool, str]:
        """
        Detecta formulário de login usando heurísticas otimizadas conforme estratégia MVP.
        
        Args:
            page: Instância da página Playwright
            
        Returns:
            Tuple[bool, str]: (formulario_detectado, mensagem)
        """
        try:
            logger.info("Iniciando detecção de formulário de login usando múltiplas estratégias")
            
            # Aguardar carregamento da página
            logger.debug("Aguardando carregamento completo da página")
            await page.wait_for_load_state('networkidle', timeout=10000)
            logger.debug("Carregamento da página concluído")
            
            # Debug: verificar URL atual e título da página
            current_url = page.url
            page_title = await page.title()
            logger.info(f"Página carregada - URL: {current_url}, Título: {page_title}")
            
            # Debug: verificar se há formulários na página
            all_forms = await page.query_selector_all('form')
            logger.info(f"Total de formulários encontrados na página: {len(all_forms)}")
            
            # Debug: verificar se há campos de input
            all_inputs = await page.query_selector_all('input')
            logger.info(f"Total de campos input encontrados na página: {len(all_inputs)}")
            
            # Estratégia 1: Detectar por seletores comuns
            logger.debug("Estratégia 1: Detectando formulário por seletores específicos de login")
            login_selectors = [
                'form[action*="login"]',
                'form[action*="signin"]',
                'form[action*="auth"]',
                'form#login',
                'form#signin',
                'form.login',
                'form.signin',
                '[data-testid*="login"]',
                '[data-testid*="signin"]',
                # Seletores específicos para OrangeHRM
                'input[name="username"]',
                'input[name="password"]',
                'button[type="submit"]',
                '.oxd-form'
            ]
            
            for selector in login_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        logger.info(f"Formulário detectado com sucesso pelo seletor específico: {selector}")
                        return True, f"Formulário encontrado: {selector}"
                    else:
                        logger.debug(f"Seletor {selector} não encontrado na página")
                except Exception as e:
                    logger.debug(f"Erro ao verificar seletor {selector}: {e}")
                    continue
            
            # Estratégia específica para OrangeHRM
            logger.debug("Estratégia específica: Verificando campos específicos do OrangeHRM")
            username_field = await page.query_selector('input[name="username"]')
            password_field = await page.query_selector('input[name="password"]')
            
            if username_field and password_field:
                logger.info("Formulário OrangeHRM detectado pelos campos username e password")
                return True, "Formulário OrangeHRM detectado (campos username/password)"
            else:
                logger.debug(f"Campos OrangeHRM - username: {bool(username_field)}, password: {bool(password_field)}")
            
            # Estratégia 2: Detectar por estrutura de formulário
            logger.debug("Estratégia 2: Analisando estrutura de formulários na página")
            forms = await page.query_selector_all('form')
            logger.debug(f"Encontrados {len(forms)} formulários na página")
            
            for i, form in enumerate(forms):
                try:
                    # Verificar se o formulário contém campos de usuário e senha
                    username_field = await form.query_selector('input[type="text"], input[type="email"], input[name*="user"], input[name*="email"], input[id*="user"], input[id*="email"]')
                    password_field = await form.query_selector('input[type="password"]')
                    
                    if username_field and password_field:
                        logger.info(f"Formulário de login detectado por estrutura no formulário {i+1} (campos usuário + senha)")
                        return True, "Formulário com campos de usuário e senha encontrado"
                    else:
                        logger.debug(f"Formulário {i+1} não possui estrutura de login (usuário: {bool(username_field)}, senha: {bool(password_field)})")
                except Exception as e:
                    logger.debug(f"Erro ao analisar formulário {i+1}: {e}")
                    continue
            
            # Estratégia 3: Detectar por palavras-chave no texto
            logger.debug("Estratégia 3: Detectando por palavras-chave de login na página")
            page_text = await page.inner_text('body')
            login_keywords = ['login', 'entrar', 'sign in', 'log in', 'acesso', 'autenticação']
            
            for keyword in login_keywords:
                if keyword.lower() in page_text.lower():
                    logger.debug(f"Palavra-chave '{keyword}' encontrada na página")
                    # Verificar se há campos de entrada próximos
                    inputs = await page.query_selector_all('input[type="text"], input[type="email"], input[type="password"]')
                    if len(inputs) >= 2:
                        logger.info(f"Formulário de login detectado por palavra-chave '{keyword}' com {len(inputs)} campos de entrada")
                        return True, f"Formulário detectado pela palavra-chave: {keyword}"
                    else:
                        logger.debug(f"Palavra-chave '{keyword}' encontrada mas apenas {len(inputs)} campos de entrada disponíveis")
            
            logger.warning("Nenhum formulário de login detectado após aplicar todas as estratégias")
            return False, "Formulário de login não encontrado"
            
        except Exception as e:
            logger.error(f"Erro crítico durante detecção de formulário de login: {str(e)}", exc_info=True)
            return False, f"Erro na detecção: {str(e)}"
    
    async def _fill_credentials(self, page: Page, credentials: AuthCredentials) -> Tuple[bool, str]:
        """
        Preenche as credenciais nos campos detectados usando heurísticas.
        
        Args:
            page: Instância da página Playwright
            credentials: Credenciais de autenticação
            
        Returns:
            Tuple[bool, str]: (preenchimento_sucesso, mensagem)
        """
        try:
            logger.info(f"Iniciando preenchimento de credenciais para usuário '{credentials.username}'")
            
            # Detectar campo de usuário
            logger.debug("Procurando campo de usuário/email")
            username_selectors = [
                'input[name="username"]',
                'input[name="user"]',
                'input[name="email"]',
                'input[name="login"]',
                'input[id="username"]',
                'input[id="user"]',
                'input[id="email"]',
                'input[id="login"]',
                'input[type="email"]',
                'input[placeholder*="usuário"]',
                'input[placeholder*="email"]',
                'input[placeholder*="user"]'
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    field = await page.query_selector(selector)
                    if field:
                        username_field = field
                        logger.info(f"Campo de usuário encontrado com seletor: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Seletor de usuário {selector} falhou: {e}")
                    continue
            
            if not username_field:
                # Fallback: primeiro campo de texto que não seja senha
                logger.debug("Aplicando fallback: procurando primeiro campo de texto disponível")
                text_inputs = await page.query_selector_all('input[type="text"], input[type="email"]')
                if text_inputs:
                    username_field = text_inputs[0]
                    logger.info(f"Campo de usuário detectado como primeiro campo de texto (fallback) - {len(text_inputs)} campos disponíveis")
                else:
                    logger.debug("Nenhum campo de texto encontrado no fallback")
            
            if not username_field:
                logger.error("Campo de usuário não encontrado após todas as tentativas")
                return False, "Campo de usuário não encontrado"
            
            # Detectar campo de senha
            logger.debug("Procurando campo de senha")
            password_field = await page.query_selector('input[type="password"]')
            if not password_field:
                logger.error("Campo de senha não encontrado na página")
                return False, "Campo de senha não encontrado"
            
            logger.debug("Campos de usuário e senha localizados com sucesso")
            
            # Preencher campos
            logger.debug("Limpando e preenchendo campo de usuário")
            await username_field.click()
            await username_field.fill('')  # Limpar campo
            await username_field.fill(credentials.username)
            logger.info(f"Campo de usuário preenchido com '{credentials.username}'")
            
            logger.debug("Limpando e preenchendo campo de senha")
            await password_field.click()
            await password_field.fill('')  # Limpar campo
            await password_field.fill(credentials.password)
            logger.info("Campo de senha preenchido com sucesso")
            
            return True, "Credenciais preenchidas com sucesso"
            
        except Exception as e:
            logger.error(f"Erro crítico ao preencher credenciais para usuário '{credentials.username}': {str(e)}", exc_info=True)
            return False, f"Erro no preenchimento: {str(e)}"
    
    async def _submit_form(self, page: Page) -> Tuple[bool, str]:
        """
        Submete o formulário de login.
        
        Args:
            page: Instância da página Playwright
            
        Returns:
            Tuple[bool, str]: (submissao_sucesso, mensagem)
        """
        try:
            logger.info("Iniciando submissão do formulário de login")
            
            # Estratégia 1: Procurar botão de submit
            logger.debug("Estratégia 1: Procurando botão de submissão específico")
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Entrar")',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'button:has-text("Acessar")',
                '[data-testid*="login"]',
                '[data-testid*="submit"]'
            ]
            
            for selector in submit_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        logger.debug(f"Botão de submissão encontrado: {selector}")
                        await button.click()
                        logger.info(f"Formulário submetido via botão: {selector}")
                        
                        # Aguardar navegação ou resposta
                        logger.debug("Aguardando resposta após submissão")
                        try:
                            await page.wait_for_load_state('networkidle', timeout=5000)
                            logger.debug("Carregamento pós-submissão concluído")
                        except Exception as wait_e:
                            logger.debug(f"Timeout no carregamento pós-submissão: {wait_e}")
                            pass
                        
                        return True, f"Formulário submetido via botão: {selector}"
                except Exception as e:
                    logger.debug(f"Falha ao tentar botão {selector}: {e}")
                    continue
            
            # Estratégia 2: Pressionar Enter no campo de senha
            logger.debug("Estratégia 2: Tentando submissão via tecla Enter")
            password_field = await page.query_selector('input[type="password"]')
            if password_field:
                logger.debug("Pressionando Enter no campo de senha")
                await password_field.press('Enter')
                logger.info("Formulário submetido via tecla Enter no campo de senha")
                
                logger.debug("Aguardando resposta após submissão via Enter")
                try:
                    await page.wait_for_load_state('networkidle', timeout=5000)
                    logger.debug("Carregamento pós-Enter concluído")
                except Exception as wait_e:
                    logger.debug(f"Timeout no carregamento pós-Enter: {wait_e}")
                    pass
                
                return True, "Formulário submetido via Enter"
            
            logger.warning("Nenhum método de submissão funcionou")
            return False, "Botão de submit não encontrado"
            
        except Exception as e:
            logger.error(f"Erro crítico ao submeter formulário: {str(e)}", exc_info=True)
            return False, f"Erro na submissão: {str(e)}"
    
    async def _verify_authentication(self, page: Page) -> Tuple[bool, str]:
        """
        Verifica se a autenticação foi bem-sucedida.
        
        Args:
            page: Instância da página Playwright
            
        Returns:
            Tuple[bool, str]: (autenticacao_sucesso, mensagem)
        """
        try:
            logger.info("Iniciando verificação de autenticação usando múltiplas estratégias")
            
            # Aguardar possível redirecionamento
            logger.debug("Aguardando possível redirecionamento pós-login")
            await asyncio.sleep(2)
            
            current_url = page.url
            logger.info(f"URL atual após tentativa de login: {current_url}")
            
            # Estratégia 1: Verificar mudança de URL
            logger.debug("Estratégia 1: Verificando padrões de URL de sucesso")
            
            # Primeiro verificar se ainda está em página de login
            login_url_patterns = [
                '/login', '/signin', '/auth/login', '/authentication',
                '/entrar', '/acesso'
            ]
            
            is_still_on_login = False
            for login_pattern in login_url_patterns:
                if login_pattern in current_url.lower():
                    logger.info(f"Ainda na página de login: padrão '{login_pattern}' encontrado em {current_url}")
                    is_still_on_login = True
                    break
            
            if not is_still_on_login:
                # Se não está em página de login, verificar padrões de sucesso
                success_url_patterns = [
                    'dashboard', 'home', 'main', 'welcome', 'index.php',
                    'painel', 'inicio', 'principal', '/pim/', '/admin/',
                    '/web/index.php', 'viewPersonalDetails', 'empNumber'
                ]
                
                for pattern in success_url_patterns:
                    if pattern in current_url.lower():
                        logger.info(f"Autenticação verificada por padrão de URL: '{pattern}' encontrado em {current_url}")
                        return True, f"Redirecionamento para página autenticada detectado: {pattern}"
            
            # Estratégia 2: Verificar ausência de mensagens de erro
            logger.debug("Estratégia 2: Verificando presença de mensagens de erro")
            error_selectors = [
                '.error', '.alert-danger', '.alert-error',
                '[class*="error"]', '[class*="invalid"]',
                '[data-testid*="error"]'
            ]
            
            for selector in error_selectors:
                try:
                    error_element = await page.query_selector(selector)
                    if error_element:
                        error_text = await error_element.inner_text()
                        if error_text.strip():
                            logger.warning(f"Mensagem de erro detectada com seletor {selector}: [Erro de autenticação detectado]")
                            return False, "Erro de autenticação: Invalid credentials"
                except Exception as e:
                    logger.debug(f"Erro ao verificar seletor de erro {selector}: {e}")
                    continue
            
            # Estratégia 3: Verificar presença de elementos pós-login
            logger.debug("Estratégia 3: Procurando elementos indicativos de usuário autenticado")
            success_selectors = [
                '[data-testid*="logout"]',
                '[data-testid*="profile"]',
                'button:has-text("Sair")',
                'button:has-text("Logout")',
                'a:has-text("Sair")',
                'a:has-text("Logout")'
            ]
            
            for selector in success_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        logger.info(f"Elemento pós-login detectado com seletor: {selector}")
                        return True, f"Elementos de usuário autenticado detectados: {selector}"
                except Exception as e:
                    logger.debug(f"Erro ao verificar seletor de sucesso {selector}: {e}")
                    continue
            
            # Estratégia 4: Verificar se ainda há formulário de login completo
            logger.debug("Estratégia 4: Verificando se formulário de login ainda está presente")
            password_field = await page.query_selector('input[type="password"]')
            username_field = await page.query_selector('input[name="username"], input[name="user"], input[name="email"], input[type="email"]')
            login_button = await page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Entrar")')
            
            if password_field and username_field:
                logger.info("Formulário de login completo ainda presente - autenticação falhou")
                return False, "Formulário de login ainda está presente na página"
            elif not password_field and not is_still_on_login:
                logger.info("Campo de senha não encontrado e não está em página de login - indicativo de sucesso")
                return True, "Ausência de formulário de login em página não-login indica sucesso"
            
            # Estratégia 5: Verificar se a URL mudou significativamente da URL de login original
            logger.debug("Estratégia 5: Verificando mudança significativa de URL")
            if not is_still_on_login and current_url != page.url:
                logger.info(f"URL mudou significativamente de login para: {current_url}")
                return True, "Redirecionamento significativo detectado após login"
            
            # Se chegou até aqui, assumir falha
            logger.warning("Não foi possível verificar sucesso da autenticação com nenhuma estratégia")
            return False, "Não foi possível confirmar o sucesso da autenticação"
            
        except Exception as e:
            logger.error(f"Erro crítico ao verificar autenticação: {str(e)}", exc_info=True)
            return False, f"Erro na verificação: {str(e)}"
    
    def has_saved_session(self, url: str, username: str) -> bool:
        """
        Verifica se existe uma sessão salva para a URL e usuário.
        
        Args:
            url: URL do site
            username: Nome do usuário
            
        Returns:
            bool: True se existe sessão salva
        """
        logger.info(f"Verificando existência de sessão salva para usuário '{username}' na URL: {url}")
        session_exists = self.session_service.session_exists(url, username)
        logger.info(f"Sessão {'encontrada' if session_exists else 'não encontrada'} para usuário '{username}'")
        return session_exists
    
    async def load_saved_session(self, context: BrowserContext, url: str, username: str) -> bool:
        """
        Carrega uma sessão salva no contexto do navegador.
        
        Args:
            context: Contexto do navegador
            url: URL do site
            username: Nome do usuário
            
        Returns:
            bool: True se a sessão foi carregada com sucesso
        """
        logger.info(f"Iniciando carregamento de sessão salva para usuário '{username}' na URL: {url}")
        try:
            session_loaded = await self.session_service.apply_session_to_context(context, url, username)
            if session_loaded:
                logger.info(f"Sessão carregada com sucesso para usuário '{username}'")
            else:
                logger.warning(f"Falha ao carregar sessão para usuário '{username}'")
            return session_loaded
        except Exception as e:
            logger.error(f"Erro ao carregar sessão para usuário '{username}': {str(e)}", exc_info=True)
            return False
    
    async def test_authentication(self, page: Page, context: BrowserContext, url: str, credentials: AuthCredentials) -> dict:
        """Método wrapper para teste de autenticação que retorna um dicionário."""
        try:
            # Navegar para a URL primeiro
            logger.info(f"Navegando para a URL: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            logger.info(f"Navegação concluída para: {page.url}")
            
            # Detectar se há formulário de login
            form_detected, form_message = await self._detect_login_form(page)
            
            if not form_detected:
                return {
                    'success': False,
                    'message': f"Formulário de login não detectado: {form_message}",
                    'authenticated': False,
                    'login_detected': False,
                    'form_filled': False,
                    'submission_successful': False,
                    'post_login_url': None,
                    'session_saved': False
                }
            
            # Executar autenticação completa
            success, message, session_saved = await self.perform_authentication(page, context, url, credentials)
            
            # Obter URL pós-login se autenticação foi bem-sucedida
            post_login_url = page.url if success else None
            
            # Sanitizar mensagem para evitar exposição de credenciais
            sanitized_message = "Autenticação realizada com sucesso" if success else "Autenticação falhou: Invalid credentials"
            
            return {
                'success': success,
                'message': sanitized_message,
                'authenticated': success,
                'login_detected': True,
                'form_filled': success,
                'submission_successful': success,
                'post_login_url': post_login_url,
                'session_saved': session_saved
            }
            
        except Exception as e:
            logger.error(f"Erro no teste de autenticação: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f"Erro interno durante teste de autenticação: {str(e)}",
                'authenticated': False,
                'login_detected': False,
                'form_filled': False,
                'submission_successful': False,
                'post_login_url': None,
                'session_saved': False
            }