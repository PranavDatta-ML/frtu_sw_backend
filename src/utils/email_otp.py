import boto3
import secrets
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from fastapi import HTTPException
from typing import Dict, Optional

SES_CONFIG = {
    "fromEmail": "message-noreply@kimbal.io",
    "host": "email-smtp.ap-south-1.amazonaws.com",
    "port": 587,
    "username": "***REMOVED-AWS-ACCESS-KEY***",
    "password": "***REMOVED-AWS-SECRET-KEY***"
}

# In-memory cache (use Redis in production)
OTP_CACHE: Dict[str, Dict] = {}
RESET_TOKENS: Dict[str, Dict] = {}

class EmailService:
    def __init__(self):
        self.client = boto3.client(
            'ses', region_name='ap-south-1',
            aws_access_key_id=SES_CONFIG['username'],
            aws_secret_access_key=SES_CONFIG['password']
        )
    
    async def send_otp(self, email: str, otp: str):
        html = f"""
        <h2>Login OTP</h2>
        <p><strong>{otp}</strong></p>
        <p>Valid for 5 minutes</p>
        """
        self.client.send_email(
            Source=SES_CONFIG['fromEmail'],
            Destination={'ToAddresses': [email]},
            Message={
                'Subject': {'Data': 'Your Login OTP'},
                'Body': {
                    'Html': {'Data': html},
                    'Text': {'Data': f'Your OTP: {otp}'}
                }
            }
        )

    async def send_reset_link(self, email: str, token: str):
        url = f"https://your-frontend.com/reset-password?token={token}"
        html = f"""
        <h2>Reset Password</h2>
        <p>Click <a href="{url}">here</a> to reset password</p>
        """
        self.client.send_email(
            Source=SES_CONFIG['fromEmail'],
            Destination={'ToAddresses': [email]},
            Message={
                'Subject': {'Data': 'Reset Password'},
                'Body': {
                    'Html': {'Data': html},
                    'Text': {'Data': f'Reset URL: {url}'}
                }
            }
        )

email_service = EmailService()

def generate_otp() -> str:
    return secrets.token_hex(3).upper()

def store_otp(email: str, otp: str):
    OTP_CACHE[email] = {
        "otp": otp,
        "expires": datetime.now() + timedelta(minutes=5)
    }

def validate_otp(email: str, otp: str) -> bool:
    data = OTP_CACHE.get(email)
    if not data or datetime.now() > data["expires"]:
        return False
    return data["otp"] == otp

def store_reset_token(email: str, token: str):
    RESET_TOKENS[token] = {
        "email": email,
        "expires": datetime.now() + timedelta(hours=1)
    }

def validate_reset_token(token: str) -> Optional[str]:
    data = RESET_TOKENS.get(token)
    if data and datetime.now() < data["expires"]:
        return data["email"]
    return None
