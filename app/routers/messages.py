"""
Messages Router - Email and message management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models import Message, get_db
from app.models.schemas import MessageCreate, MessageUpdate, MessageResponse

router = APIRouter(prefix="/api/messages", tags=["messages"])

@router.get("/", response_model=List[MessageResponse])
def list_messages(
    source: Optional[str] = None,
    is_processed: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all messages"""
    query = db.query(Message)
    
    if source:
        query = query.filter(Message.source == source)
    if is_processed is not None:
        query = query.filter(Message.is_processed == is_processed)
    
    return query.order_by(Message.received_at.desc()).offset(skip).limit(limit).all()

@router.post("/", response_model=MessageResponse)
def create_message(message: MessageCreate, db: Session = Depends(get_db)):
    """Create a new message"""
    db_message = Message(**message.dict())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

@router.get("/{message_id}", response_model=MessageResponse)
def get_message(message_id: int, db: Session = Depends(get_db)):
    """Get a specific message"""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message

@router.put("/{message_id}", response_model=MessageResponse)
def update_message(message_id: int, update: MessageUpdate, db: Session = Depends(get_db)):
    """Update a message"""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    for field, value in update.dict(exclude_unset=True).items():
        setattr(message, field, value)
    
    db.commit()
    db.refresh(message)
    return message

@router.delete("/{message_id}")
def delete_message(message_id: int, db: Session = Depends(get_db)):
    """Delete a message"""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    db.delete(message)
    db.commit()
    return {"message": "Message deleted"}

@router.post("/import-emails")
def import_emails(db: Session = Depends(get_db)):
    """Import emails from configured email accounts"""
    import os
    import imaplib
    import email
    from email.header import decode_header
    
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'imap.exmail.qq.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '993'))
    EMAIL_USER = os.getenv('EMAIL_USER', 'hr@weilan.com')
    EMAIL_PASS = os.getenv('EMAIL_PASS', '')
    
    if not EMAIL_PASS:
        # Try to get from code
        EMAIL_PASS = '9wpCjNNcMvj845Fv'
    
    def decode_str(s):
        if isinstance(s, str):
            return s
        for encoding in ['utf-8', 'gbk', 'gb2312', 'big5', 'latin-1']:
            try:
                return s.decode(encoding)
            except:
                continue
        return s.decode('utf-8', errors='ignore')
    
    try:
        mail = imaplib.IMAP4_SSL(EMAIL_HOST, EMAIL_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('inbox')
        
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != 'OK':
            return {"imported": 0, "message": "No new emails"}
        
        email_ids = messages[0].split()
        imported = 0
        
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status != 'OK':
                continue
            
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Get message ID for deduplication
            msg_id = msg.get('Message-ID', '') or msg.get('Message-Id', '')
            
            # Check if already imported
            existing = db.query(Message).filter(Message.message_id == msg_id).first()
            if existing:
                continue
            
            # Parse subject
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
            
            # Parse sender
            from_header = msg['From']
            sender = ""
            sender_name = ""
            if from_header:
                decoded_from = decode_header(from_header)
                for part, charset in decoded_from:
                    if isinstance(part, bytes):
                        try:
                            if charset:
                                sender += part.decode(charset)
                            else:
                                sender += decode_str(part)
                        except:
                            sender += decode_str(part)
                    else:
                        sender += part
            
            # Extract sender name and email
            if '<' in sender and '>' in sender:
                sender_name = sender.split('<')[0].strip()
                sender_email = sender.split('<')[1].split('>')[0].strip()
            else:
                sender_email = sender
                sender_name = ""
            
            # Extract organization from sender email domain or name
            organization = ""
            if '@' in sender_email:
                domain = sender_email.split('@')[1]
                if '.' in domain:
                    organization = domain.split('.')[0]
            
            # Extract contact person
            contact_person = sender_name if sender_name else ""
            
            # Create message
            db_message = Message(
                source="email",
                source_account=EMAIL_USER,
                subject=subject[:500],
                sender=sender_email[:200],
                sender_name=sender_name[:100],
                organization=organization[:200],
                contact_person=contact_person[:100],
                message_id=msg_id[:500] if msg_id else None,
                is_read=False,
                is_processed=False
            )
            
            db.add(db_message)
            imported += 1
        
        db.commit()
        mail.close()
        mail.logout()
        
        return {"imported": imported, "message": f"Imported {imported} emails"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
