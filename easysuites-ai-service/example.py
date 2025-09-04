import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from playwright.async_api import async_playwright
from browser_use.agent import Agent, ChatOpenAI
# from browser_use.llms import ChatOpenAI

app = FastAPI(title="Crawler API", version="1.0.0")

# ---------- MODELS ----------
class AuthConfig(BaseModel):
    username: str
    password: str

class MappingRequest(BaseModel):
    url: str
    auth: Optional[AuthConfig] = None

class CampoMapeado(BaseModel):
    nome: str
    seletor: str
    tipo: str
    descricao: Optional[str] = None

class ExtractRequest(BaseModel):
    url: str
    auth: Optional[AuthConfig] = None
    campos_mapeados: List[CampoMapeado]


# ---------- SERVIÇO 1: MAPEAMENTO ----------
@app.post("/crawler/mapping")
async def mapear_campos(req: MappingRequest):
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": 1920, "height": 1080})
    page = await context.new_page()

    await page.goto(req.url)

    # Se tiver login, detecta e preenche
    if req.auth:
        llm_login = ChatOpenAI(model="gpt-4o-mini")
        login_agent = Agent(
            task="Detecte automaticamente os campos de login e submeta as credenciais fornecidas.",
            llm=llm_login,
        )
        await login_agent.run_on_page(page, inputs={"username": req.auth.username, "password": req.auth.password})
        await page.wait_for_load_state("networkidle")

    # Agente para mapear campos
    llm_map = ChatOpenAI(model="gpt-4o-mini")
    map_agent = Agent(
        task="""
        Analise a página e retorne os campos que podem ser extraídos.
        Para cada campo encontrado, retorne:
        - nome (texto amigável do campo)
        - seletor CSS
        - tipo (texto, tabela, lista, input, etc.)
        - descricao (explicação do que é o campo)
        """,
        llm=llm_map,
    )
    campos = await map_agent.run_on_page(page)

    await browser.close()
    await playwright.stop()

    return {"campos_detectados": campos}


# ---------- SERVIÇO 2: EXTRAÇÃO ----------
@app.post("/crawler/extract")
async def extrair_dados(req: ExtractRequest):
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": 1920, "height": 1080})
    page = await context.new_page()

    await page.goto(req.url)

    # Se tiver login, detecta e preenche
    if req.auth:
        llm_login = ChatOpenAI(model="gpt-4o-mini")
        login_agent = Agent(
            task="Detecte automaticamente os campos de login e submeta as credenciais fornecidas.",
            llm=llm_login,
        )
        await login_agent.run_on_page(page, inputs={"username": req.auth.username, "password": req.auth.password})
        await page.wait_for_load_state("networkidle")

    # Agente para extrair os campos informados
    llm_extract = ChatOpenAI(model="gpt-4o-mini")
    extract_agent = Agent(
        task=f"""
        Extraia os seguintes campos da página:
        {req.campos_mapeados}

        Para tabelas/lists, retorne como uma lista de objetos.
        Para textos, apenas o valor.
        Responda no formato JSON.
        """,
        llm=llm_extract,
    )
    dados = await extract_agent.run_on_page(page)

    await browser.close()
    await playwright.stop()

    return {"dados_extraidos": dados}
