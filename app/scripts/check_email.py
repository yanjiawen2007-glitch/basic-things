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

# Email configuration
EMAIL_HOST = 'imap.exmail.qq.com'
EMAIL_PORT = 993
EMAIL_USER = 'hr@weilan.com'
EMAIL_PASS = '9wpCjNNcMvj845Fv'
TASKFLOW_API = 'http://localhost:8000/api'

def decode_str(s):
    """Decode string with multiple encoding attempts"""
    if isinstance(s, str):
        return s
    for encoding in ['utf-8', 'gbk', 'gb2312', 'big5', 'latin-1']:
        try:
            return s.decode(encoding)
        except:
            continue
    return s.decode('utf-8', errors='ignore')

def get_email_body(msg):
    """Extract email body with encoding handling"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset()
                    try:
                        if charset:
                            body = payload.decode(charset)
                        else:
                            body = decode_str(payload)
                    except:
                        body = decode_str(payload)
                break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset()
            try:
                if charset:
                    body = payload.decode(charset)
                else:
                    body = decode_str(payload)
            except:
                body = decode_str(payload)
    return body

def check_emails():
    """Check inbox for new emails and create tasks"""
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
            
            # Parse email subject
            subject_header = msg['Subject']
            subject = ""
            if subject_header:
                decoded_header = decode_header(subject_header)
                for part, charset in decoded_header:
                    if isinstance(part, bytes):
                        try:
                            if charset:
                                subject += part.decode(charset)
                            else:
                                subject += decode_str(part)
                        except:
                            subject += decode_str(part)
                    else:
                        subject += part
            
            # Parse from address
            from_header = msg['From']
            from_addr = ""
            if from_header:
                decoded_from = decode_header(from_header)
                for part, charset in decoded_from:
                    if isinstance(part, bytes):
                        try:
                            if charset:
                                from_addr += part.decode(charset)
                            else:
                                from_addr += decode_str(part)
                        except:
                            from_addr += decode_str(part)
                    else:
                        from_addr += part
            
            # Get email body
            body = get_email_body(msg)
            
            print(f"Processing email: {subject[:100]}")
            
            # Create task from email
            task_data = {
                "name": f"邮件任务: {subject[:50]}",
                "description": f"From: {from_addr}\n\n{body[:500]}",
                "task_type": "shell",
                "cron_expression": "0 0 * * *",
                "config": {
                    "command": f"echo 'Processing email: {subject[:100]}'",
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
                    print(f"Created task for: {subject[:50]}")
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
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(check_emails())
