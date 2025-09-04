import logging
import logging.handlers
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from src.core.config import settings

class JSONFormatter(logging.Formatter):
    """Formatador personalizado para logs em formato JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread
        }
        
        # Adiciona informações de exceção se presente
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Adiciona campos extras se presentes
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)

class ContextFilter(logging.Filter):
    """Filtro para adicionar contexto aos logs"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Adiciona informações de contexto
        record.service_name = settings.app_name
        record.service_version = settings.app_version
        record.environment = settings.environment
        return True

def setup_logging():
    """Configura o sistema de logging da aplicação"""
    
    # Configura o nível de log
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Escolhe o formatador baseado na configuração
    if settings.log_json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt=settings.log_format,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    # Configura o filtro de contexto
    context_filter = ContextFilter()
    
    # Configura o logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)
    root_logger.addHandler(console_handler)
    
    # Handler para arquivo se habilitado
    if settings.log_file_enabled:
        try:
            log_path = settings.get_log_file_path()
            
            # Handler rotativo para arquivo
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=settings.log_file_max_size,
                backupCount=settings.log_file_backup_count,
                encoding="utf-8"
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            file_handler.addFilter(context_filter)
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Erro ao configurar o logging em arquivo: {e}")
    
    # Configura loggers específicos
    
    # Logger para requisições HTTP (reduzir verbosidade)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Logger para Playwright (reduzir verbosidade)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    
    # Logger para Browser-Use
    logging.getLogger("browser_use").setLevel(logging.INFO)
    
    # Logger para LangChain
    logging.getLogger("langchain").setLevel(logging.WARNING)
    
    # Logger da aplicação
    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    
    # Log de inicialização
    app_logger.info(f"Sistema de logging configurado - Nível: {settings.log_level}")
    app_logger.info(f"Modo debug: {settings.debug}")
    
    return app_logger

def get_logger(name: str) -> logging.Logger:
    """Retorna um logger configurado para o módulo especificado"""
    return logging.getLogger(name)