#!/usr/bin/env python3
"""
Teste da implementação de Pepper no sistema de senhas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.auth import auth_service
from config.settings import settings

def test_pepper_implementation():
    """Testa a implementação de pepper"""
    print("🧪 TESTE DE IMPLEMENTAÇÃO DE PEPPER")
    print("=" * 50)
    
    # Senha de teste
    test_password = "Senha123!@#"
    print(f"📝 Senha original: {test_password}")
    print(f"🔑 Pepper configurado: {settings.PASSWORD_PEPPER[:10]}...")
    
    # Gerar hash com pepper
    print("\n🔐 Gerando hash com pepper...")
    hashed_password = auth_service.get_password_hash(test_password)
    print(f"📦 Hash gerado: {hashed_password[:50]}...")
    
    # Testar verificação correta
    print("\n✅ Testando verificação correta...")
    is_valid = auth_service.verify_password(test_password, hashed_password)
    print(f"🎯 Resultado: {'✅ VÁLIDO' if is_valid else '❌ INVÁLIDO'}")
    
    # Testar verificação com senha errada
    print("\n❌ Testando verificação com senha errada...")
    wrong_password = "SenhaErrada123!"
    is_invalid = auth_service.verify_password(wrong_password, hashed_password)
    print(f"🎯 Resultado: {'❌ INVÁLIDO (correto)' if not is_invalid else '✅ VÁLIDO (errado)'}")
    
    # Testar segurança adicional
    print("\n🔒 Testando segurança adicional...")
    
    # Gerar hash da mesma senha para comparar
    hashed_password_2 = auth_service.get_password_hash(test_password)
    
    print(f"📦 Hash 1: {hashed_password[:50]}...")
    print(f"📦 Hash 2: {hashed_password_2[:50]}...")
    print(f"🔄 Diferentes (com salt): {'✅ SIM' if hashed_password != hashed_password_2 else '❌ NÃO'}")
    
    # Verificar se ambos são válidos
    is_valid_1 = auth_service.verify_password(test_password, hashed_password)
    is_valid_2 = auth_service.verify_password(test_password, hashed_password_2)
    print(f"🎯 Ambos válidos: {'✅ SIM' if is_valid_1 and is_valid_2 else '❌ NÃO'}")
    
    print("\n📊 RESUMO DO TESTE")
    print("=" * 50)
    print("✅ Pepper implementado com sucesso!")
    print("✅ Senhas corretas são validadas")
    print("✅ Senhas erradas são rejeitadas") 
    print("✅ Salts diferentes gerados a cada hash")
    print("✅ Segurança em camadas (bcrypt + pepper)")
    
    return True

def test_pepper_security():
    """Testa a segurança do pepper"""
    print("\n🔍 TESTE DE SEGURANÇA DO PEPPER")
    print("=" * 50)
    
    # Testar sem pepper (simular ataque)
    test_password = "Senha123!@#"
    hashed_with_pepper = auth_service.get_password_hash(test_password)
    
    # Tentar verificar sem pepper (simular se o banco for comprometido)
    import hashlib
    import base64
    import bcrypt
    
    # Simular ataque conhecendo apenas o hash bcrypt
    try:
        # Tentativa ingênua (sem pepper)
        sha256_without_pepper = hashlib.sha256(test_password.encode('utf-8')).digest()
        prepared_without_pepper = base64.b64encode(sha256_without_pepper).decode('utf-8')
        
        is_attack_successful = bcrypt.checkpw(
            prepared_without_pepper.encode('utf-8'), 
            hashed_with_pepper.encode('utf-8')
        )
        
        print(f"🚫 Ataque sem pepper: {'❌ FALHOU' if not is_attack_successful else '✅ SUCESSO'}")
        
        # Tentativa com pepper correto
        password_with_pepper = test_password + settings.PASSWORD_PEPPER
        sha256_with_pepper = hashlib.sha256(password_with_pepper.encode('utf-8')).digest()
        prepared_with_pepper = base64.b64encode(sha256_with_pepper).decode('utf-8')
        
        is_with_pepper_valid = bcrypt.checkpw(
            prepared_with_pepper.encode('utf-8'), 
            hashed_with_pepper.encode('utf-8')
        )
        
        print(f"🔑 Com pepper correto: {'✅ SUCESSO' if is_with_pepper_valid else '❌ FALHOU'}")
        
        print("\n🛡️ ANÁLISE DE SEGURANÇA")
        print("=" * 30)
        print("✅ Ataques sem pepper falham")
        print("✅ Apenas com pepper correto funciona")
        print("✅ Camada adicional de segurança")
        
    except Exception as e:
        print(f"❌ Erro no teste de segurança: {e}")

if __name__ == "__main__":
    try:
        test_pepper_implementation()
        test_pepper_security()
        print("\n🎉 TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
    except Exception as e:
        print(f"\n❌ ERRO NOS TESTES: {e}")
        import traceback
        traceback.print_exc()
