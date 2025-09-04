"""
Validation script for Easysuites Web Crawler Service implementation.
This script verifies that all components are properly implemented according to the PRD.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def validate_project_structure():
    """Validate the complete project structure."""
    
    project_root = Path(__file__).parent.parent
    required_files = [
        "src/main.py",
        "src/models/schemas.py",
        "src/services/browser_service.py",
        "src/services/auth_service.py",
        "src/services/field_detection_service.py",
        "src/api/endpoints.py",
        "tests/test_endpoints.py",
        "requirements.txt",
        "README.md",
        ".env.example"
    ]
    
    print("🔍 Validando estrutura do projeto...")
    
    missing_files = []
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Arquivos ausentes: {missing_files}")
        return False
    else:
        print("✅ Todos os arquivos necessários estão presentes")
        return True

def validate_imports():
    """Validate that all modules can be imported correctly."""
    
    print("\n🔍 Validando imports...")
    
    try:
        from src.models.schemas import (
            AuthTestRequest, AuthTestResponse,
            FieldDetectionRequest, FieldDetectionResponse
        )
        print("✅ Models importados com sucesso")
    except ImportError as e:
        print(f"❌ Erro ao importar models: {e}")
        return False
    
    try:
        from src.services.browser_service import BrowserService
        from src.services.auth_service import AuthService
        from src.services.field_detection_service import FieldDetectionService
        print("✅ Services importados com sucesso")
    except ImportError as e:
        print(f"❌ Erro ao importar services: {e}")
        return False
    
    try:
        from src.api.endpoints import router
        print("✅ API endpoints importados com sucesso")
    except ImportError as e:
        print(f"❌ Erro ao importar endpoints: {e}")
        return False
    
    try:
        from src.main import create_app
        print("✅ Main app importado com sucesso")
    except ImportError as e:
        print(f"❌ Erro ao importar main app: {e}")
        return False
    
    return True

def validate_schemas():
    """Validate Pydantic schemas."""
    
    print("\n🔍 Validando schemas...")
    
    try:
        from src.models.schemas import AuthTestRequest, FieldDetectionRequest
        
        # Test AuthTestRequest
        auth_request = AuthTestRequest(
            url="https://example.com",
            credentials={"username": "test", "password": "test"}
        )
        print("✅ AuthTestRequest schema válido")
        
        # Test FieldDetectionRequest
        field_request = FieldDetectionRequest(url="https://example.com")
        print("✅ FieldDetectionRequest schema válido")
        
        return True
    except Exception as e:
        print(f"❌ Erro nos schemas: {e}")
        return False

def main():
    """Main validation function."""
    
    print("🚀 Validando implementação do Easysuites Web Crawler Service\n")
    
    # Validate structure
    structure_valid = validate_project_structure()
    
    # Validate imports
    imports_valid = validate_imports()
    
    # Validate schemas
    schemas_valid = validate_schemas()
    
    # Summary
    print("\n📊 Resumo da Validação:")
    print(f"Estrutura do projeto: {'✅ OK' if structure_valid else '❌ FALHOU'}")
    print(f"Imports: {'✅ OK' if imports_valid else '❌ FALHOU'}")
    print(f"Schemas: {'✅ OK' if schemas_valid else '❌ FALHOU'}")
    
    if all([structure_valid, imports_valid, schemas_valid]):
        print("\n🎉 Implementação validada com sucesso!")
        print("\nPróximos passos:")
        print("1. Configure suas variáveis de ambiente em .env")
        print("2. Instale as dependências: pip install -r requirements.txt")
        print("3. Instale o Playwright: playwright install chromium")
        print("4. Execute os testes: pytest tests/")
        print("5. Inicie o serviço: python -m src.main")
    else:
        print("\n❌ Implementação possui problemas. Revise os erros acima.")
        sys.exit(1)

if __name__ == "__main__":
    main()