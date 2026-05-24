import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from readpack.config import Config, ConfigError

_WARN_SIZE = 25 * 1024 * 1024  # 25 MB


def send_to_kindle(config: Config, epub_path: Path) -> None:
    size = epub_path.stat().st_size
    if size > _WARN_SIZE:
        mb = size / 1024 / 1024
        raise ConfigError(
            f"File is {mb:.1f} MB — may exceed Kindle attachment limit (25 MB)"
        )

    password = config.smtp_password()
    login = config.email.username or config.email.sender

    msg = MIMEMultipart()
    msg["From"] = config.email.sender
    msg["To"] = config.kindle.address
    msg["Subject"] = "readpack delivery"
    msg.attach(MIMEText("Sent via readpack.", "plain"))

    with open(epub_path, "rb") as f:
        part = MIMEBase("application", "epub+zip")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition", f'attachment; filename="{epub_path.name}"'
    )
    msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP(config.email.smtp_host, config.email.smtp_port) as smtp:
        smtp.starttls(context=context)
        smtp.login(login, password)
        smtp.sendmail(config.email.sender, [config.kindle.address], msg.as_string())
