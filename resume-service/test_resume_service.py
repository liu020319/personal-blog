import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SERVICE_PATH = Path(__file__).with_name("resume_service.py")


def load_service():
    data_dir = tempfile.mkdtemp(prefix="xiaoliu-blog-test-")
    os.environ["RESUME_DATA_DIR"] = data_dir
    os.environ["RESUME_ADMIN_TOKEN"] = "test-token-" + "a" * 32
    os.environ["BLOG_EMAIL_NOTIFICATIONS"] = "false"
    spec = importlib.util.spec_from_file_location("resume_service_under_test", SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CommentModerationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = load_service()

    def test_normal_comment_is_automatically_approved(self):
        self.assertFalse(
            self.service.comment_requires_review(
                "Java 学习者",
                "这篇文章把部署思路讲得很清楚，我准备照着实践一次。",
            )
        )

    def test_advertising_comment_requires_manual_review(self):
        self.assertTrue(
            self.service.comment_requires_review(
                "访客",
                "需要代写项目可以加微详聊。",
            )
        )

    def test_excessive_repetition_requires_manual_review(self):
        self.assertTrue(self.service.comment_requires_review("访客", "好好好好好好好好好"))

    def test_gmail_smtp_notification_uses_tls_and_login(self):
        service = self.service
        original = {
            "NOTIFY_EMAIL": service.NOTIFY_EMAIL,
            "SMTP_HOST": service.SMTP_HOST,
            "SMTP_PORT": service.SMTP_PORT,
            "SMTP_USERNAME": service.SMTP_USERNAME,
            "SMTP_PASSWORD": service.SMTP_PASSWORD,
            "SMTP_STARTTLS": service.SMTP_STARTTLS,
            "SMTP_SSL": service.SMTP_SSL,
            "EMAIL_NOTIFICATIONS_ENABLED": service.EMAIL_NOTIFICATIONS_ENABLED,
        }
        service.NOTIFY_EMAIL = "owner@example.com"
        service.SMTP_HOST = "smtp.gmail.com"
        service.SMTP_PORT = 587
        service.SMTP_USERNAME = "sender@example.com"
        service.SMTP_PASSWORD = "app-password"
        service.SMTP_STARTTLS = True
        service.SMTP_SSL = False
        service.EMAIL_NOTIFICATIONS_ENABLED = True
        try:
            with mock.patch.object(service.smtplib, "SMTP") as smtp:
                client = smtp.return_value.__enter__.return_value
                service.send_comment_notification(
                    "test-article",
                    "Java 学习者",
                    "评论内容",
                    "approved",
                    "2026-08-13T08:00:00+00:00",
                )
                smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=10)
                client.starttls.assert_called_once()
                client.login.assert_called_once_with("sender@example.com", "app-password")
                client.send_message.assert_called_once()
        finally:
            for name, value in original.items():
                setattr(service, name, value)

    def test_cooperation_lead_email_contains_private_contact_for_owner(self):
        service = self.service
        original = {
            "NOTIFY_EMAIL": service.NOTIFY_EMAIL,
            "SMTP_HOST": service.SMTP_HOST,
            "SMTP_PORT": service.SMTP_PORT,
            "SMTP_USERNAME": service.SMTP_USERNAME,
            "SMTP_PASSWORD": service.SMTP_PASSWORD,
            "SMTP_STARTTLS": service.SMTP_STARTTLS,
            "SMTP_SSL": service.SMTP_SSL,
            "EMAIL_NOTIFICATIONS_ENABLED": service.EMAIL_NOTIFICATIONS_ENABLED,
        }
        service.NOTIFY_EMAIL = "owner@example.com"
        service.SMTP_HOST = "smtp.gmail.com"
        service.SMTP_PORT = 587
        service.SMTP_USERNAME = "sender@example.com"
        service.SMTP_PASSWORD = "app-password"
        service.SMTP_STARTTLS = True
        service.SMTP_SSL = False
        service.EMAIL_NOTIFICATIONS_ENABLED = True
        try:
            with mock.patch.object(service, "deliver_email") as deliver:
                service.send_lead_notification(
                    "张同学",
                    "邮箱",
                    "student@example.com",
                    "需要一个 Java 毕业设计项目并部署上线。",
                    "2026-08-13T08:00:00+00:00",
                )
                sent = deliver.call_args.args[0]
                self.assertEqual("[小刘博客] 收到一条新合作需求", sent["Subject"])
                self.assertIn("student@example.com", sent.get_content())
                self.assertIn("Java 毕业设计", sent.get_content())
        finally:
            for name, value in original.items():
                setattr(service, name, value)

    def test_email_status_masks_recipient(self):
        self.assertEqual("ow***@example.com", self.service.masked_email("owner@example.com"))


if __name__ == "__main__":
    unittest.main()
