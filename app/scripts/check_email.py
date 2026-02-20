#!/usr/bin/env python3
"""
Check email inbox and create tasks from new emails
"""
import os
import sys
import json
import imaplib
import email
from email.header import decode_header
import requests
from datetime import datetime

# Email configuration from environment variables
EMAIL_HOST = os.getenv('EMAIL_HOST', 'imap.exmail.qq.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '993'))
EMAIL_USER = os.getenv('EMAIL_USER', 'hr@weilan.com')
EMAIL_PASS = os.getenv('EMAIL_PASS', '')
TASKFLOW_API = os.getenv('TASKFLOW_API', 'http://localhost:8000/api')

def check_emails():
    """Check inbox for new emails and create tasks"""
    if not EMAIL_PASS:
        print("Error: EMAIL_PASS not set")
        return 1
    
    try:
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(EMAIL_HOST, EMAIL_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('inbox')
        
        # Search for unread emails
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != 'OK':
            print("No new messages")
            return 0
        
        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} new emails")
        
        for email_id in email_ids:
            # Fetch email
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status != 'OK':
                continue
            
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Parse email
            subject = decode_header(msg['Subject'])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
            
            from_addr = decode_header(msg['From'])[0][0]
            if isinstance(from_addr, bytes):
                from_addr = from_addr.decode()
            
            # Get email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()
            
            print(f"Processing email: {subject}")
            
            # Create task from email
            task_data = {
                "name": f"邮件任务: {subject[:50]}",
                "description": f"From: {from_addr}\n\n{body[:500]}",
                "task_type": "shell",
                "cron_expression": "0 0 * * *",
                "config": {
                    "command": f"echo 'Processing email: {subject}'",
                    "timeout": 300
                },
                "is_enabled": True
            }
            
            # Send to TaskFlow API
            try:
                response = requests.post(
                    f"{TASKFLOW_API}/tasks/",
                    json=task_data,
                    timeout=10
                )
                if response.status_code == 200:
                    print(f"Created task for: {subject}")
                    mail.store(email_id, '+FLAGS', '\\Seen')
                else:
                    print(f"Failed to create task: {response.text}")
            except Exception as e:
                print(f"Error creating task: {e}")
        
        mail.close()
        mail.logout()
        print("Email check completed")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(check_emails())
