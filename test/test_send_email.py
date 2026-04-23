from unittest.mock import MagicMock, patch

from mpylab.tools import util


def test_send_email_success():
    smtp_instance = MagicMock()
    with patch("mpylab.tools.util.smtplib.SMTP", return_value=smtp_instance) as smtp_ctor:
        ok = util.send_email(
            to="dest@example.com",
            fr="src@example.com",
            subj="Test subject",
            msg="Body text",
        )

    assert ok is True
    smtp_ctor.assert_called_once_with("localhost")
    smtp_instance.send_message.assert_called_once()
    sent_message = smtp_instance.send_message.call_args.args[0]
    assert sent_message["Subject"] == "Test subject"
    assert sent_message["From"] == "src@example.com"
    assert sent_message["To"] == "dest@example.com"
    smtp_instance.quit.assert_called_once()


def test_send_email_returns_false_without_addresses():
    with patch("mpylab.tools.util.smtplib.SMTP") as smtp_ctor:
        ok = util.send_email(to=None, fr="src@example.com", subj="x", msg="y")
    assert ok is False
    smtp_ctor.assert_not_called()


def test_send_email_smtp_error_returns_false():
    with patch("mpylab.tools.util.smtplib.SMTP", side_effect=OSError("smtp down")):
        ok = util.send_email(
            to="dest@example.com",
            fr="src@example.com",
            subj="Test subject",
            msg="Body text",
        )
    assert ok is False
