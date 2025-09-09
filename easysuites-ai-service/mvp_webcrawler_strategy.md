# MVP Web Crawler

## 1. Serviço de Teste de Autenticação
**Objetivo:** validar credenciais antes de tentar extrair campos.

- **Input:** URL + usuário + senha (via frontend/CRUD).
- **Tecnologia:** Playwright (Python)
  - Abrir a página de login.
  - Preencher usuário e senha.
  - Submeter formulário.
  - Esperar redirecionamento / verificar mensagem de erro.
- **Output:** status `success` / `failure` + mensagens de erro.
- **Extra:** salvar sessão (`storageState.json`) para uso posterior no serviço de detecção de campos.

**Benefício:** garante que o usuário tem acesso antes de gastar recursos extraindo campos.

---

## 2. Serviço de Detecção de Campos
**Objetivo:** detectar automaticamente os campos que podem ser scrapeados.

- **Input:** URL (ou páginas internas) + sessão do login (opcional).
- **Tecnologias:**
  - **Playwright** → abre página autenticada.
  - **Heurísticas + Regex** → detecta inputs, selects, textareas, tabelas, listas.
  - **BeautifulSoup / lxml** → parse do HTML final.
- **Output (exemplo JSON):**
```json
[
  {"label": "Nome", "selector": "#empName", "type": "texto"},
  {"label": "Email", "selector": "#empEmail", "type": "email"},
  {"label": "CPF", "selector": "#empCPF", "type": "cpf"},
  {"label": "Departamento", "selector": "#empDept", "type": "tabela"}
]
```

**Benefício:** usuário não precisa identificar manualmente os campos; o serviço entrega sugestões estruturadas.

---

## 3. Integração entre os Serviços
1. **Login/teste de autenticação** → retorna sessão autenticada.
2. **Detecção de campos usando sessão** → abre páginas internas privadas e aplica heurísticas.

---

## 4. Tecnologias recomendadas por etapa

| Etapa                        | Tecnologias recomendadas                    |
|-------------------------------|--------------------------------------------|
| Teste de autenticação/login   | Playwright (ou Browser-Use se gerenciar múltiplas sessões) |
| Gerenciamento de sessão       | Playwright `storageState.json` ou cookies |
| Navegação de páginas privadas | Playwright                                   |
| Detecção de campos (heurística)| Playwright DOM query + BeautifulSoup + Regex |
| Classificação de tipo         | Regex / heurística                          |  
| Retorno dos dados            | JSON                                          |

---

## 5. Fluxograma simplificado
```mermaid
flowchart TD
    A[Frontend: usuário fornece URL + credenciais] --> B[Teste de Autenticação]
    B -->|Sucesso| C[Salvar sessão (cookies / storageState)]
    C --> D[Detecção de campos nas páginas internas]
    D --> E[Heurísticas + Regex + ML/NLP]
    E --> F{Confiável?}
    F -->|Sim| G[Retornar JSON de campos detectados]
    F -->|Não| H[Retornar JSON com status e mensagem amigavel]
    H --> G
    G --> I[Frontend: usuário seleciona campos que quer manter para scraping no futuro]
```

---

## 6. Observações importantes
1. **Browser-Use** é útil para múltiplas sessões simultâneas, mas não obrigatório.
2. **Heurísticas** devem ser o principal método → rápido e confiável.
3. **Persistência da sessão** é crucial para não logar toda vez que detectar campos.
4. **Logs** são essencias para acompanhamento dos fluxos.
5. **Docsstrings** são essencias para entedimento do código.
6. **PT-BR** para melhor compreensão.

---

**Resumo:**
- Primeiro validar login e salvar sessão.
- Depois usar sessão para detectar campos automaticamente.
- JSON retornado serve para o frontend permitir seleção dos campos.
- Scraper final extrai apenas os campos selecionados.

Este fluxo contempla tanto o teste de autenticação quanto a detecção automática de campos, pronto para ser aplicado ao OrangeHRM Open Source Demo e outros sites similares.

