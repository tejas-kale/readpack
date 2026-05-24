import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from readpack.config import Config, ConfigError, KindleConfig, EmailConfig
from readpack.send import send_to_kindle


@pytest.fixture
def cfg():
    return Config(
        kindle=KindleConfig(address="test@kindle.com"),
        email=EmailConfig(
            sender="me@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="me@example.com",
            password_command="echo testpass",
        ),
    )


def test_send_calls_smtp(tmp_path, cfg):
    epub = tmp_path / "book.epub"
    epub.write_bytes(b"fake epub content")

    smtp_instance = MagicMock()
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__ = MagicMock(return_value=smtp_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        send_to_kindle(cfg, epub)

    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("me@example.com", "testpass")
    smtp_instance.sendmail.assert_called_once()


def test_send_to_correct_address(tmp_path, cfg):
    epub = tmp_path / "book.epub"
    epub.write_bytes(b"fake epub")

    smtp_instance = MagicMock()
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__ = MagicMock(return_value=smtp_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        send_to_kindle(cfg, epub)

    args = smtp_instance.sendmail.call_args
    assert args[0][0] == "me@example.com"
    assert "test@kindle.com" in args[0][1]


def test_send_rejects_oversized_file(tmp_path, cfg):
    epub = tmp_path / "big.epub"
    epub.write_bytes(b"x" * (26 * 1024 * 1024))
    with pytest.raises(ConfigError, match="25 MB"):
        send_to_kindle(cfg, epub)


def test_send_uses_sender_as_login_when_no_username(tmp_path):
    cfg = Config(
        kindle=KindleConfig(address="test@kindle.com"),
        email=EmailConfig(
            sender="me@example.com",
            smtp_host="smtp.example.com",
            password_command="echo pass",
        ),
    )
    epub = tmp_path / "book.epub"
    epub.write_bytes(b"fake")

    smtp_instance = MagicMock()
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__ = MagicMock(return_value=smtp_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        send_to_kindle(cfg, epub)

    smtp_instance.login.assert_called_once_with("me@example.com", "pass")
