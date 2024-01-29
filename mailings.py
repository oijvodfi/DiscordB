import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

smtp_server = "smtp.gmail.com"
smtp_port = 587
smtp_username = os.getenv('smtp_username')
smtp_password = os.getenv('smtp_password')

def send_tasks_email():
    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = ""
    msg['Subject'] = "List All ur Taag"
    task_list = subprocess.check_output(["task", "+sm1lebroofficial", "list"], stderr=subprocess.STDOUT)
    task_list = task_list.decode('utf-8')
    msg.attach(MIMEText(task_list, 'plain'))

    # Отправка сообщения
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_username, smtp_password)
    server.send_message(msg)
    server.quit()

# send_tasks_email()

# 0 6 * * * /usr/bin/python3 /path/to/mailings.py