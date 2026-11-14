"""Проверка настроек почты: python test_mail.py ваша@почта.ру"""
import sys, envload  # noqa
from extra import send_mail
import os
if not os.getenv("SMTP_HOST"): sys.exit("SMTP_HOST не задан: создайте файл .env (см. .env.example)")
try: send_mail(sys.argv[1], "123456"); print("Готово: письмо отправлено, проверьте входящие и «Спам».")
except Exception as e: print("Не получилось:", getattr(e, "detail", e))
