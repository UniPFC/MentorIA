#!/usr/bin/env python3
"""
Teste de implementação de CSRF protection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_csrf_middleware_structure():
    """Testa estrutura do middleware CSRF"""
    print("1. TESTE DE ESTRUTURA DO MIDDLEWARE CSRF")
    print("=" * 60)
    
    try:
        from src.middleware.csrf_protection import CSRFProtectionMiddleware, create_csrf_protect
        from fastapi import FastAPI
        
        # Criar app mock
        mock_app = FastAPI()
        
        # Criar CSRF protect
        csrf_protect = create_csrf_protect()
        
        # Adicionar middleware
        mock_app.add_middleware(CSRFProtectionMiddleware, csrf_protect=csrf_protect)
        
        # Verificar middleware registrado
        middleware_classes = [type(m.cls) for m in mock_app.user_middleware]
        
        print(f"Middlewares registrados: {len(middleware_classes)}")
        for i, middleware_class in enumerate(middleware_classes):
            print(f"  {i+1}. {middleware_class.__name__}")
        
        # Verificar se CSRF middleware está presente
        csrf_found = any("CSRFProtectionMiddleware" in str(cls) for cls in middleware_classes)
        
        if csrf_found:
            print("OK: CSRF Protection middleware encontrado")
            return True
        else:
            print("ERRO: CSRF Protection middleware não encontrado")
            return False
            
    except Exception as e:
        print(f"ERRO ao testar estrutura: {e}")
        return False

def test_csrf_needs_protection():
    """Testa lógica de quando CSRF é necessário"""
    print("\n2. TESTE DE LÓGICA DE PROTEÇÃO CSRF")
    print("=" * 60)
    
    try:
        from src.middleware.csrf_protection import CSRFProtectionMiddleware, create_csrf_protect
        from fastapi import Request
        from unittest.mock import Mock
        
        # Criar middleware
        csrf_protect = create_csrf_protect()
        middleware = CSRFProtectionMiddleware(None, csrf_protect)
        
        # Test cases
        test_cases = [
            # (method, path, content_type, headers, esperado)
            ("GET", "/api/v1/chats", "", {}, False),      # GET não precisa
            ("POST", "/api/v1/auth/login", "application/json", {}, False),  # Login não precisa
            ("POST", "/api/v1/auth/register", "application/json", {}, False),  # Register não precisa
            ("POST", "/api/v1/chats", "application/json", {"authorization": "Bearer token"}, False),  # API não precisa
            ("POST", "/api/v1/chats", "application/x-www-form-urlencoded", {}, True),  # Form precisa
            ("POST", "/api/v1/chats", "multipart/form-data", {}, True),  # Form precisa
            ("PUT", "/api/v1/chats/1", "application/json", {}, False),  # API não precisa
            ("POST", "/health", "", {}, False),  # Pública não precisa
        ]
        
        passed = 0
        total = len(test_cases)
        
        for method, path, content_type, headers, expected in test_cases:
            # Criar request mock
            request = Mock(spec=Request)
            request.method = method
            request.url.path = path
            request.headers = headers.copy()
            if content_type:
                request.headers["content-type"] = content_type
            
            # Testar lógica
            result = middleware._needs_csrf_protection(request)
            
            status = "OK" if result == expected else "ERRO"
            print(f"  {method} {path} ({content_type}): {status} (esperado={expected}, obtido={result})")
            
            if result == expected:
                passed += 1
        
        print(f"\nTestes passaram: {passed}/{total}")
        return passed == total
        
    except Exception as e:
        print(f"ERRO ao testar lógica: {e}")
        return False

def test_csrf_config():
    """Testa configuração do CSRF"""
    print("\n3. TESTE DE CONFIGURAÇÃO CSRF")
    print("=" * 60)
    
    try:
        from src.middleware.csrf_protection import create_csrf_protect
        from config.settings import settings
        
        # Criar CSRF protect
        csrf_protect = create_csrf_protect()
        
        # Verificar configurações
        configs = [
            ("secret_key", hasattr(csrf_protect, 'secret_key')),
            ("cookie_name", hasattr(csrf_protect, 'cookie_name')),
            ("header_name", hasattr(csrf_protect, 'header_name')),
        ]
        
        print("Configurações verificadas:")
        for name, has_config in configs:
            status = "OK" if has_config else "FALTANDO"
            print(f"  {name}: {status}")
        
        # Verificar se usa SECRET_KEY do settings
        if hasattr(csrf_protect, 'secret_key'):
            print(f"  Secret key configurado: OK")
        
        return all(has_config for _, has_config in configs)
        
    except Exception as e:
        print(f"ERRO ao testar configuração: {e}")
        return False

def test_csrf_token_generation():
    """Testa geração de token CSRF"""
    print("\n4. TESTE DE GERAÇÃO DE TOKEN CSRF")
    print("=" * 60)
    
    try:
        from src.middleware.csrf_protection import create_csrf_protect
        
        # Criar CSRF protect
        csrf_protect = create_csrf_protect()
        
        # Gerar token
        token = csrf_protect.generate_csrf()
        
        print(f"Token gerado: {token[:20]}...")
        print(f"Token length: {len(token)}")
        
        # Verificar se token é válido
        if token and len(token) > 10:
            print("OK: Token CSRF gerado com sucesso")
            return True
        else:
            print("ERRO: Token CSRF inválido")
            return False
        
    except Exception as e:
        print(f"ERRO ao gerar token: {e}")
        return False

def test_csrf_endpoint():
    """Testa endpoint CSRF token"""
    print("\n5. TESTE DE ENDPOINT CSRF TOKEN")
    print("=" * 60)
    
    try:
        from src.api.routes.auth import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        # Criar app com router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/auth")
        
        # Criar client
        client = TestClient(app)
        
        # Testar endpoint
        response = client.get("/api/v1/auth/csrf-token")
        
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:50]}...")
        
        if response.status_code == 200:
            print("OK: Endpoint CSRF token funcionando")
            return True
        else:
            print(f"ERRO: Endpoint retornou {response.status_code}")
            return False
        
    except Exception as e:
        print(f"ERRO ao testar endpoint: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("TESTE DE IMPLEMENTAÇÃO CSRF PROTECTION")
    print("=" * 60)
    print("Verificando implementação de proteção CSRF")
    print()
    
    tests = [
        ("Estrutura do Middleware", test_csrf_middleware_structure),
        ("Lógica de Proteção", test_csrf_needs_protection),
        ("Configuração CSRF", test_csrf_config),
        ("Geração de Token", test_csrf_token_generation),
        ("Endpoint CSRF", test_csrf_endpoint),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"ERRO em {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo final
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        icon = "OK" if result else "ERRO"
        print(f"{icon} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResultados: {passed}/{total} testes passaram")
    
    if passed == total:
        print("TODOS OS TESTES PASSARAM!")
        print("Implementação de CSRF protection está correta.")
    else:
        print("ALGUNS TESTES FALHARAM!")
        print("Verifique os erros acima e corrija a implementação.")
    
    return passed == total

if __name__ == "__main__":
    main()
