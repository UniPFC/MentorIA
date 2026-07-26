import secrets
import smtplib
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from config.logger import logger
from config.settings import settings

# Caminho para o template base
TEMPLATE_DIR = Path(__file__).parent / "templates"
BASE_TEMPLATE_PATH = TEMPLATE_DIR / "email_base.html"


class EmailService:
    def __init__(self):
        self.smtp_server = getattr(settings, "SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = getattr(settings, "SMTP_PORT", 587)
        self.smtp_username = getattr(settings, "SMTP_USERNAME", "")
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", "")
        self.from_email = getattr(settings, "FROM_EMAIL", self.smtp_username)
        self.frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

        self._base_template = None

    def _get_base_template(self) -> str:
        if self._base_template is None:
            try:
                with open(BASE_TEMPLATE_PATH, encoding="utf-8") as f:
                    self._base_template = f.read()
            except Exception as e:
                logger.error(f"Failed to read base email template: {e}")
                # Fallback muito simples
                self._base_template = (
                    "<html><body><h1>{{ title }}</h1>{{ content }}</body></html>"
                )
        return self._base_template

    def _render_template(self, title: str, content: str) -> str:
        template = self._get_base_template()
        html = template.replace("{{ title }}", title)
        html = html.replace("{{ content }}", content)
        return html

    def _send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Envia email usando SMTP"""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            html_part = MIMEText(html_body, "html")
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
        """Gera token seguro para reset de senha e verificação de email"""
        return secrets.token_urlsafe(32)

    def send_password_reset_email(
        self, to_email: str, username: str, reset_token: str
    ) -> bool:
        """Envia email de reset de senha apontando para o frontend"""
        reset_link = f"{self.frontend_url}/reset-password?token={reset_token}"

        content = f"""
        <h2>Olá, {username}!</h2>
        <p>Recebemos uma solicitação para redefinir a senha da sua conta no MentorIA.</p>
        <p>Para criar uma nova senha, clique no botão abaixo:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" class="button">Redefinir Minha Senha</a>
        </div>
        <p><strong>Importante:</strong></p>
        <ul>
            <li>Este link expira em 1 hora.</li>
            <li>Se você não solicitou esta alteração, você pode ignorar este email com segurança.</li>
        </ul>
        """

        html_body = self._render_template("Recuperação de Senha", content)
        return self._send_email(to_email, "Recuperação de Senha - MentorIA", html_body)

    def send_password_changed_email(self, to_email: str, username: str) -> bool:
        """Envia email confirmando mudança de senha"""
        content = f"""
        <h2>Senha Alterada com Sucesso</h2>
        <p>Olá <strong>{username}</strong>,</p>
        <p>Sua senha foi alterada com sucesso em nossa plataforma.</p>
        <p>Se você não realizou esta alteração, por favor:</p>
        <ul>
            <li>Entre em contato imediatamente com nosso suporte</li>
            <li>Altere sua senha novamente se ainda tiver acesso</li>
            <li>Verifique se há atividades suspeitas em sua conta</li>
        </ul>
        """

        html_body = self._render_template("Senha Alterada", content)
        return self._send_email(to_email, "Senha Alterada - MentorIA", html_body)

    def send_password_reset_notification(self, to_email: str, username: str) -> bool:
        """Nofifica o usuário sobre o reset de senha."""
        try:
            content = f"""
            <h2>Alerta de Segurança</h2>
            <p>Olá, <strong>{username}</strong>!</p>
            <p>Recebemos uma solicitação para redefinir a senha da sua conta no <strong>MentorIA</strong>.</p>
            <p><strong>Data/Hora:</strong> {datetime.now(UTC).strftime("%d/%m/%Y às %H:%M")} (UTC)</p>
            <div class="alert">
                <p>Se <strong>você fez essa solicitação</strong>, pode ignorar este email — um segundo email com o link de redefinição foi enviado para você.</p>
            </div>
            <p>Se <strong>você NÃO fez essa solicitação</strong>, sua senha ainda está segura, mas recomendamos que você:</p>
            <ul>
                <li>Altere sua senha assim que possível</li>
                <li>Revise os acessos recentes à sua conta</li>
                <li>Entre em contato com o suporte se suspeitar de algo</li>
            </ul>
            """

            html_body = self._render_template(
                "Solicitação de redefinição de senha", content
            )
            return self._send_email(
                to_email, "⚠️ Solicitação de redefinição de senha - MentorIA", html_body
            )

        except Exception as e:
            logger.error(
                f"Failed to send password reset notification to {to_email}: {str(e)}"
            )
            return False

    def send_verification_email(self, to_email: str, username: str, token: str) -> bool:
        """Envia email de verificação de conta"""
        verify_link = f"{self.frontend_url}/verify-email?token={token}"

        content = f"""
        <h2>Bem-vindo(a) ao MentorIA!</h2>
        <p>Olá, <strong>{username}</strong>! Estamos muito felizes em ter você conosco.</p>
        <p>Para começar a usar todos os recursos da plataforma, incluindo o chat e o envio de planilhas, precisamos verificar o seu email.</p>
        <p>Clique no botão abaixo para confirmar seu email:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verify_link}" class="button">Verificar Meu Email</a>
        </div>
        <p>Se você não se cadastrou no MentorIA, por favor ignore este email.</p>
        """

        html_body = self._render_template("Verificação de Email", content)
        return self._send_email(
            to_email, "Bem-vindo ao MentorIA - Verifique seu Email", html_body
        )


# Instância global do serviço
email_service = EmailService()
