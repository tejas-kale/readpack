import pytest
from pathlib import Path

from readpack.config import Config, ConfigError, KindleConfig, EmailConfig, load_config, init_config


def _write_config(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_load_config_valid(tmp_path):
    _write_config(tmp_path / "config.toml", """\
[kindle]
address = "user@kindle.com"

[email]
sender = "me@example.com"
smtp_host = "smtp.example.com"
smtp_port = 587
username = "me@example.com"
password_command = "echo secret"
""")
    cfg = load_config(tmp_path)
    assert cfg.kindle.address == "user@kindle.com"
    assert cfg.email.sender == "me@example.com"
    assert cfg.email.smtp_host == "smtp.example.com"
    assert cfg.email.smtp_port == 587


def test_load_config_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="config --init"):
        load_config(tmp_path)


def test_load_config_missing_kindle_address(tmp_path):
    _write_config(tmp_path / "config.toml", """\
[kindle]

[email]
sender = "me@example.com"
smtp_host = "smtp.example.com"
""")
    with pytest.raises(ConfigError, match="kindle"):
        load_config(tmp_path)


def test_load_config_missing_email_sender(tmp_path):
    _write_config(tmp_path / "config.toml", """\
[kindle]
address = "user@kindle.com"

[email]
smtp_host = "smtp.example.com"
""")
    with pytest.raises(ConfigError, match="sender"):
        load_config(tmp_path)


def test_init_config_creates_file(tmp_path):
    path = init_config(tmp_path)
    assert path.exists()
    assert "kindle" in path.read_text()
    assert "email" in path.read_text()


def test_init_config_errors_if_exists(tmp_path):
    init_config(tmp_path)
    with pytest.raises(ConfigError, match="already exists"):
        init_config(tmp_path)


def test_smtp_password_runs_command():
    cfg = Config(
        kindle=KindleConfig(address="t@kindle.com"),
        email=EmailConfig(
            sender="me@example.com",
            smtp_host="smtp.example.com",
            password_command="echo secretpass",
        ),
    )
    assert cfg.smtp_password() == "secretpass"


def test_smtp_password_missing_command():
    cfg = Config(
        kindle=KindleConfig(address="t@kindle.com"),
        email=EmailConfig(sender="me@example.com", smtp_host="smtp.example.com"),
    )
    with pytest.raises(ConfigError, match="password_command"):
        cfg.smtp_password()


def test_smtp_password_bad_command():
    cfg = Config(
        kindle=KindleConfig(address="t@kindle.com"),
        email=EmailConfig(
            sender="me@example.com",
            smtp_host="smtp.example.com",
            password_command="false",
        ),
    )
    with pytest.raises(ConfigError, match="failed"):
        cfg.smtp_password()
