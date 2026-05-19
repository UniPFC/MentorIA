import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional

from qdrant_client.models import datetime
from config.settings import settings
from config.logger import logger
import secrets
import hashlib


class EmailService:
    def __init__(self):
        self.smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_username = getattr(settings, 'SMTP_USERNAME', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.from_email = getattr(settings, 'FROM_EMAIL', self.smtp_username)
        self.frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

    def _send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Envia email usando SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email

            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def generate_reset_token(self) -> str:
        """Gera token seguro para reset de senha"""
        return secrets.token_urlsafe(32)

    def send_password_reset_email(self, to_email: str, username: str, reset_token: str) -> bool:
        """Envia email de reset de senha"""
        # Para desenvolvimento, usar a API diretamente
        reset_link = f"http://localhost:8000/api/v1/auth/confirm-reset-password"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reset de Senha</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4f46e5; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .token-box {{ background: #e5e7eb; padding: 15px; border-radius: 6px; margin: 20px 0; font-family: monospace; word-break: break-all; }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Reset de Senha</h1>
                </div>
                <div class="content">
                    <p>Olá <strong>{username}</strong>,</p>
                    <p>Recebemos uma solicitação para resetar sua senha. Use o token abaixo:</p>
                    <div class="token-box">{reset_token}</div>
                    <p><strong>Importante:</strong></p>
                    <ul>
                        <li>Este token expira em 1 hora</li>
                        <li>Use-o na API: <code>POST /api/v1/auth/confirm-reset-password</code></li>
                        <li>Se você não solicitou este reset, ignore este email</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>Este é um email automático. Por favor, não responda.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(to_email, "Reset de Senha - MentorIA", html_body)

    def send_password_changed_email(self, to_email: str, username: str) -> bool:
        """Envia email confirmando mudança de senha"""
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Senha Alterada</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #10b981; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Senha Alterada com Sucesso</h1>
                </div>
                <div class="content">
                    <p>Olá <strong>{username}</strong>,</p>
                    <p>Sua senha foi alterada com sucesso em nossa plataforma.</p>
                    <p>Se você não realizou esta alteração, por favor:</p>
                    <ul>
                        <li>Entre em contato imediatamente com nosso suporte</li>
                        <li>Altere sua senha novamente</li>
                        <li>Verifique se há atividades suspeitas em sua conta</li>
                    </ul>
                    <p>Para sua segurança, recomendamos:</p>
                    <ul>
                        <li>Usar senhas fortes e únicas</li>
                        <li>Nunca compartilhar suas credenciais</li>
                        <li>Ativar autenticação de dois fatores quando disponível</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>Este é um email automático. Por favor, não responda.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(to_email, "Senha Alterada - MentorIA", html_body)

    def send_password_reset_notification(self, to_email: str, username:str) -> bool:
        """Nofifica o usuário sobre o reset de senha.
            Envia ANTES do link de reset, serve como alerta de segurança.
        """
        try:
            subject = "⚠️ Solicitação de redefinição de senha - MentorIA"
            html_body = f"""
            <html><body>
            <h2>Olá, {username}!</h2>
            <p>Recebemos uma solicitação para redefinir a senha da sua conta no <strong>MentorIA</strong>.</p>
            <p><strong>Data/Hora:</strong> {datetime.utcnow().strftime('%d/%m/%Y às %H:%M')}
 (UTC)</p>

          <p>Se <strong>você fez essa solicitação</strong>, pode ignorar este email —
          um segundo email com o link de redefinição foi enviado para você.</p>

           <p>Se <strong>você NÃO fez essa solicitação</strong>, sua senha ainda está segura.
           Recomendamos que você:
           <ul>
              <li>Altere sua senha assim que possível</li>
              <li>Revise os acessos recentes à sua conta</li>
               <li>Entre em contato com o suporte se suspeitar de algo</li>
         </ul>

          <p style="color: gray; font-size: 12px;">
               Este é um email automático de segurança. Não responda a este email.
           </p>
           </body></html>
          """
            return self._send_email(to_email, subject, html_body)
    
        except Exception as e:
            logger.error(f"Failed to send password reset notification to {to_email}: {str(e)}")
            return False
    
# Instância global do serviço
email_service = EmailService()
