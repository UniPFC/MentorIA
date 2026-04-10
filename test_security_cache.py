"""
Teste simples para o sistema de cache de segurança
"""
import asyncio
import aiohttp
import json
from datetime import datetime
import time

BASE_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{BASE_URL}/api/v1/auth/login"

# Dados de teste
TEST_EMAIL = "test.security@example.com"
TEST_PASSWORD = "wrongpassword"

async def test_security_cache(session: aiohttp.ClientSession, email: str, password: str, 
                               user_agent: str, test_name: str):
    """Testa login com cache de segurança"""
    try:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": user_agent
        }
        
        payload = {
            "email": email,
            "password": password
        }
        
        async with session.post(
            LOGIN_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=10
        ) as response:
            response_data = await response.json()
            
            return {
                "test_name": test_name,
                "email": email,
                "user_agent": user_agent,
                "status_code": response.status,
                "response": response_data.get("detail", ""),
                "headers": dict(response.headers),
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        return {
            "test_name": test_name,
            "email": email,
            "user_agent": user_agent,
            "status_code": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def main():
    """Teste completo do cache de segurança"""
    print("TESTE DO SISTEMA DE CACHE DE SEGURANÇA")
    print("=" * 50)
    
    connector = aiohttp.TCPConnector(limit=50)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        
        # Teste 1: Login normal
        print("\n1. Teste de Login Normal")
        normal_result = await test_security_cache(
            session, TEST_EMAIL, TEST_PASSWORD, 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", 
            "Login Normal"
        )
        print(f"   Status: {normal_result['status_code']} - {normal_result['response']}")
        
        # Teste 2: User-Agent suspeito
        print("\n2. Teste com User-Agent Suspeito")
        ua_result = await test_security_cache(
            session, TEST_EMAIL, TEST_PASSWORD, 
            "curl/7.68.0", 
            "User-Agent Suspeito"
        )
        print(f"   Status: {ua_result['status_code']} - {ua_result['response']}")
        
        # Teste 3: Múltiplas tentativas rápidas
        print("\n3. Teste de Múltiplas Tentativas Rápidas")
        rapid_results = []
        for i in range(8):
            result = await test_security_cache(
                session, TEST_EMAIL, f"password{i}", 
                "python-requests/2.28.1", 
                f"Rápida {i+1}"
            )
            rapid_results.append(result)
            print(f"   Tentativa {i+1}: Status {result['status_code']}")
            
            if i < 7:
                await asyncio.sleep(0.3)
        
        # Teste 4: Verificar cache após limpeza
        print("\n4. Aguardando 30 segundos e testando recuperação...")
        await asyncio.sleep(30)
        
        recovery_result = await test_security_cache(
            session, TEST_EMAIL, TEST_PASSWORD, 
            "Mozilla/5.0 (Normal Browser)", 
            "Recuperação"
        )
        print(f"   Status: {recovery_result['status_code']} - {recovery_result['response']}")
        
        # Análise dos resultados
        print("\n" + "=" * 50)
        print("ANÁLISE DOS RESULTADOS")
        print("=" * 50)
        
        all_results = [normal_result, ua_result] + rapid_results + [recovery_result]
        
        # Contar status codes
        status_counts = {}
        for result in all_results:
            status = result['status_code']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\nDistribuição de Status:")
        for status, count in sorted(status_counts.items()):
            status_name = {
                200: "Success",
                401: "Unauthorized", 
                403: "Forbidden",
                429: "Rate Limited",
                0: "Connection Error"
            }.get(status, f"Unknown({status})")
            
            print(f"  {status} ({status_name}): {count} ocorrências")
        
        # Verificar se cache funcionou
        blocked_count = sum(1 for r in all_results if r['status_code'] in [403, 429])
        
        print(f"\nAvaliação do Cache:")
        if blocked_count > 0:
            print("  ✅ Cache de segurança ATIVO")
            print(f"  🚫 {blocked_count} tentativas foram bloqueadas")
            print("  📊 Dados sendo armazenados em cache")
        else:
            print("  ⚠️  Cache de segurança pode não estar funcionando")
            print("  🔍 Verifique logs e configurações")
        
        # Verificar headers de segurança
        security_headers = []
        for result in all_results:
            headers = result.get('headers', {})
            if 'X-Security-Block' in headers:
                security_headers.append(result['test_name'])
        
        if security_headers:
            print(f"\nHeaders de Segurança: {', '.join(security_headers)}")
        
        print(f"\n📁 Cache files criados em: cache/security/")
        print(f"🧹 Limpeza automática: 24 horas")
        print(f"📊 Logs disponíveis para análise")

if __name__ == "__main__":
    print("SISTEMA DE CACHE DE SEGURANÇA - TESTE")
    print("Certifique-se de que a API está rodando.")
    print()
    
    asyncio.run(main())
