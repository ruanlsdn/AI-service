# PRD – Easysuites Web Crawler Service

## 1. Contexto
Este serviço faz parte do ecossistema **Easysuites** e será responsável por automação de interações web e extração de informações utilizando **Python**, **Playwright**, **Browser-use** e **LLM (gpt-4o-mini)**.  
Ele fornecerá endpoints REST para integração com o **conector-web**, permitindo autenticação e mapeamento de campos em páginas web.

---

## 2. Objetivos
- Permitir que o sistema valide fluxos de login em páginas com autenticação.  
- Mapear automaticamente campos relevantes de páginas web para configurar crawlers de forma genérica.  
- Suportar fallback em casos de falha na estratégia principal de detecção.  
- Expor serviços REST documentados e logados, prontos para execução em ambiente containerizado.  

---

## 3. Escopo

### Serviços expostos
Os endpoints estarão sob o namespace:

```
api/v1/web-crawlers
```

### 3.1. Teste de Autenticação
#### Descrição
Valida o processo de login em páginas que exigem autenticação.  

#### Request
**Endpoint:**  
```
POST /api/v1/web-crawlers/auth-test
```

**Payload:**
```json
{
  "url": "https://example.com/login",
  "username": "user123",
  "password": "secret"
}
```

#### Response
**Sucesso:**
```json
{
  "success": true,
  "message": "Login realizado com sucesso"
}
```

**Falha:**
```json
{
  "success": false,
  "message": "Falha na autenticação: credenciais inválidas"
}
```

---

### 3.2. Detecção de Campos
#### Descrição
Detecta e retorna os campos relevantes da página, possibilitando configuração do crawler.  
O fluxo deve:  
1. Verificar se a página exige login.  
2. Autenticar se necessário.  
3. Mapear inputs, botões, menus, tabelas e listas.  
4. Retornar os campos em formato estruturado.  
5. Utilizar fallback em caso de erro.  

#### Request
**Endpoint:**  
```
POST /api/v1/web-crawlers/field-detection
```

**Payload:**
```json
{
  "url": "https://example.com/dashboard",
  "username": "user123",
  "password": "secret"
}
```

#### Response
**Exemplo de sucesso:**
```json
{
  "success": true,
  "fields": [
    {
      "name": "employee_name",
      "type": "text",
      "selector": "#employeeName"
    },
    {
      "name": "search_button",
      "type": "button",
      "selector": "button.search"
    },
    {
      "name": "results_table",
      "type": "table",
      "selector": "#resultsTable",
      "columns": ["ID", "Name", "Department"]
    }
  ]
}
```

**Exemplo de falha com fallback:**
```json
{
  "success": false,
  "message": "Detecção avançada falhou. Retornando resultado simplificado.",
  "fields": [
    {
      "name": "generic_table",
      "type": "table",
      "selector": "table"
    }
  ]
}
```

---

## 4. Requisitos Não Funcionais
- **Logs:**  
  - `INFO`: etapas principais (login iniciado, página acessada, campos detectados).  
  - `WARNING`: lentidão, detecções incompletas.  
  - `ERROR`: falhas de autenticação ou extração.  

- **Documentação:**  
  - Docstrings obrigatórias nos métodos.

- **Resiliência:**  
  - Estratégia de fallback em caso de falhas.

---

## 5. Fluxo Resumido

### Teste de Autenticação
1. Receber request com `url`, `username` e `password`.  
2. Navegar até a página de login.  
3. Detectar automaticamente campos de usuário e senha.  
4. Submeter credenciais.  
5. Retornar resultado da tentativa.  

### Detecção de Campos
1. Receber request com `url` (+ credenciais opcionais).  
2. Se necessário, efetuar login.  
3. Detectar elementos da página:  
   - Inputs, selects, botões, menus.  
   - Tabelas e listas.  
4. Retornar JSON estruturado com seletores e metadados.  
5. Se falhar → aplicar fallback simples.  

---

## 6. Integração com Conector-Web
- Os serviços serão consumidos pelo **conector-web**.  
- O **teste de autenticação** será utilizado na fase de configuração do crawler.  
- A **detecção de campos** será utilizada posteriormente para execução diária (cronjob).  
