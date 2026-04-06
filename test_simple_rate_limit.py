"""
Teste simples para validação do rate limiting
"""
import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{BASE_URL}/api/v1/auth/login"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "wrongpassword"

async def test_login_attempt(session: aiohttp.ClientSession, attempt_id: int):
    """Faz uma tentativa de login"""
    try:
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        async with session.post(
            LOGIN_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            response_data = await response.json()
            
            return {
                "attempt": attempt_id,
                "status": response.status,
                "detail": response_data.get("detail", ""),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            
    except Exception as e:
        return {
            "attempt": attempt_id,
            "status": 0,
            "error": str(e),
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

async def main():
    print("🧪 Teste de Rate Limiting Simplificado")
    print(f"📧 Email: {TEST_EMAIL}")
    print(f"🔐 Senha: {TEST_PASSWORD}")
    print("-" * 40)
    
    async with aiohttp.ClientSession() as session:
        # Testar 7 tentativas (limite é 5)
        print("⚡ Fazendo 7 tentativas de login...")
        tasks = [test_login_attempt(session, i+1) for i in range(7)]
        results = await asyncio.gather(*tasks)
        
        print("\n📊 Resultados:")
        for result in results:
            if result["status"] == 401:
                print(f"  ❌ Tentativa {result['attempt']}: Senha incorreta (401)")
            elif result["status"] == 429:
                print(f"  🚫 Tentativa {result['attempt']}: Bloqueado (429) - {result['detail']}")
            else:
                print(f"  ❓ Tentativa {result['attempt']}: Status {result['status']}")
        
        # Contar resultados
        failed = sum(1 for r in results if r["status"] == 401)
        blocked = sum(1 for r in results if r["status"] == 429)
        
        print(f"\n📈 Resumo:")
        print(f"  - Falhas de autenticação: {failed}")
        print(f"  - Bloqueados por rate limit: {blocked}")
        
        if blocked > 0:
            print(f"\n✅ Rate limiting funcionou! {blocked} tentativas foram bloqueadas.")
        else:
            print(f"\n❌ Rate limiting não funcionou como esperado.")

if __name__ == "__main__":
    print("⚠️  Execute apenas em ambiente de desenvolvimento!")
    print("⚠️  Certifique-se que a API está rodando em localhost:8000")
    print()
    
    asyncio.run(main())
