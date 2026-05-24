import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]


class ConfigError(ValueError):
    pass


@dataclass
class KindleConfig:
    address: str


@dataclass
class EmailConfig:
    sender: str
    smtp_host: str
    smtp_port: int = 587
    username: str = ""
    password_command: str = ""


@dataclass
class Config:
    kindle: KindleConfig
    email: EmailConfig

    def smtp_password(self) -> str:
        if not self.email.password_command:
            raise ConfigError("No password_command set in config")
        result = subprocess.run(
            self.email.password_command,
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise ConfigError(f"password_command failed: {result.stderr.strip()}")
        return result.stdout.strip()


_CONFIG_TEMPLATE = """\
[kindle]
address = "yourname@kindle.com"

[email]
sender = "you@example.com"
smtp_host = "smtp.gmail.com"
smtp_port = 587
username = "you@example.com"
# Retrieve password from keychain; adjust for your OS password manager
password_command = "security find-generic-password -s readpack-smtp -w"
"""


def load_config(config_dir: Path) -> Config:
    path = config_dir / "config.toml"
    if not path.exists():
        raise ConfigError(
            f"Config not found at {path}. Run 'readpack config --init' to create it."
        )
    with open(path, "rb") as f:
        data = tomllib.load(f)

    kindle_data = data.get("kindle", {})
    if not kindle_data.get("address"):
        raise ConfigError("Missing [kindle] address in config")

    email_data = data.get("email", {})
    if not email_data.get("sender"):
        raise ConfigError("Missing [email] sender in config")
    if not email_data.get("smtp_host"):
        raise ConfigError("Missing [email] smtp_host in config")

    return Config(
        kindle=KindleConfig(address=kindle_data["address"]),
        email=EmailConfig(
            sender=email_data["sender"],
            smtp_host=email_data["smtp_host"],
            smtp_port=email_data.get("smtp_port", 587),
            username=email_data.get("username", ""),
            password_command=email_data.get("password_command", ""),
        ),
    )


def init_config(config_dir: Path) -> Path:
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "config.toml"
    if path.exists():
        raise ConfigError(f"Config already exists at {path}")
    path.write_text(_CONFIG_TEMPLATE)
    return path
