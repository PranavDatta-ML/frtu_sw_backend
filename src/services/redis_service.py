from datetime import datetime, timedelta
from email.mime.image import MIMEImage
import json
import os
import random
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import string
from src import HttpStatusCode
from src.core.settings import Settings
from src.models.frtu_users import FRTUUsers
# from src import Settings
import redis.asyncio as redis # type: ignore
import bcrypt # type: ignore
import base64
from src.templates.email_loader import load_template, embed_images
import pytz
from src.utils.security import generate_salt, hash_password
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

settings = Settings()
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,
    socket_connect_timeout=10
)

SES_CONFIG = {
    "host": "email-smtp.ap-south-1.amazonaws.com",
    "port": "587",
    "username": "***REMOVED-AWS-ACCESS-KEY***",
    "password": "***REMOVED-AWS-SECRET-KEY***",
    "from_email": "message-noreply@kimbal.io"
}

async def generate_unique_otp(length=4):
    chars = string.ascii_uppercase + string.digits  # A-Z + 0-9
    while True:
        otp = ''.join(random.choices(chars, k=length))
        exists = await redis_client.exists(f"otp:*:{otp}")
        if not exists:
            return otp

async def test_redis_connection():
    try:
        await redis_client.ping()
        print("Redis ping successful.")
        await redis_client.set("health_check", "OK", ex=60)
        health = await redis_client.get("health_check")
        return health == "OK"
    except Exception:
        return False


async def send_email_otp(email: str, otp: str):
    # html_path = r"D:\KMP FRTU Configurator\frtu_config_backend_v1\src\templates\email\otp_email_template.html"
    html_path = BASE_DIR / "templates" / "email" / "otp_email_template.html"
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    ist = pytz.timezone("Asia/Kolkata")
    expiry_time = (datetime.now(ist) + timedelta(minutes=10)).strftime("%I:%M %p IST")
    html_content = html_content.replace("[EXPIRY_TIME]", expiry_time)
    
    html_content = html_content.replace("[OTP_CODE]", otp)
    
    msg = MIMEMultipart('related')
    msg['Subject'] = 'Your Login OTP - RTU Configurator'
    msg['From'] = SES_CONFIG['from_email']
    msg['To'] = email
    
    images_dir = BASE_DIR / "templates" / "email" / "images"
    image_map = {
        "Frame 12.jpg": "logo_small",
        "Frame 11.jpg": "logo_large"
    }
    
    html_content = html_content.replace('src="images/Frame 12.jpg"', 'src="cid:logo_small"')
    html_content = html_content.replace('src="images/Frame 11.jpg"', 'src="cid:logo_large"')
    
    # Attach HTML first (root part) so Gmail/Outlook show the template; images after for cid: refs
    msg.attach(MIMEText(html_content, 'html'))
    for img_file, cid_name in image_map.items():
        img_path = os.path.join(images_dir, img_file)
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', f'<{cid_name}>')
                img.add_header('Content-Disposition', 'inline', filename=img_file)
                msg.attach(img)
    
    with smtplib.SMTP(SES_CONFIG['host'], SES_CONFIG['port']) as server:
        server.starttls()
        server.login(SES_CONFIG['username'], SES_CONFIG['password'])
        server.send_message(msg)
    print(f"HTML preview: {otp} -> [OTP_CODE] replaced")
    print(f"OTP '{otp}' sent to {email}")


    
async def send_otp(email: str):
    users = await FRTUUsers.select(email=email)
    if not users:
        return HttpStatusCode.NOT_FOUND.response(message="User not found")

    otp = await generate_unique_otp(4)
    await redis_client.setex(f"otp:{email}", 600, otp)
    # await redis_client.setex(f"otp:*:{otp}", 10, "used")
    print(f"Redis: Stored OTP={otp} for {email}")
    
    await send_email_otp(email, otp)
    return {
        "http_code": 200,
        "code": "OK",
        "message": "OTP sent to your email",
        "data": {"email": email}
    }

async def verify_otp(email: str, otp_input: str):
    stored_otp = await redis_client.get(f"otp:{email}")

    if not stored_otp:
        return HttpStatusCode.BAD_REQUEST.response(message="Invalid or expired OTP"), False

    if stored_otp != otp_input:
        return HttpStatusCode.BAD_REQUEST.response(message="Invalid OTP"), False

    await redis_client.delete(f"otp:{email}")
    return None, True



async def generate_reset_token(email: str):
    payload = json.dumps({
        "email": email,
        "ts": str(int(datetime.utcnow().timestamp())),
        "nonce": secrets.token_hex(16)[:32]
    }).encode()[:72]  
    salt = bcrypt.gensalt(rounds=10)
    token = bcrypt.hashpw(payload, salt)
    return base64.urlsafe_b64encode(token).decode().rstrip('=')[:64]


async def send_reset_email(email: str, token: str):
    reset_link = f"http://localhost:3000/reset-password/{token}"

    # html_path = r"D:\KMP FRTU Configurator\frtu_config_backend_v1\src\templates\email\reset_password_email_template.html"
    html_path = BASE_DIR / "templates" / "email" / "reset_password_email_template.html"

    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    html_content = html_content.replace("[RESET_LINK]", reset_link)

    msg = MIMEMultipart('related')
    msg['Subject'] = 'Reset Your Password - RTU Configurator'
    msg['From'] = SES_CONFIG['from_email']
    msg['To'] = email

    # images_dir = r"D:\KMP FRTU Configurator\frtu_config_backend_v1\src\templates\email\images"
    images_dir = BASE_DIR / "templates" / "email" / "images"
    image_map = {
        "Frame 12.jpg": "logo_small",
        "Frame 11.jpg": "logo_large"
    }

    html_content = html_content.replace('src="images/Frame 12.jpg"', 'src="cid:logo_small"')
    html_content = html_content.replace('src="images/Frame 11.jpg"', 'src="cid:logo_large"')

    # Attach HTML first (root part) so Gmail/Outlook show the template; images after for cid: refs
    msg.attach(MIMEText(html_content, 'html'))
    for img_file, cid_name in image_map.items():
        img_path = os.path.join(images_dir, img_file)
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', f'<{cid_name}>')
                img.add_header('Content-Disposition', 'inline', filename=img_file)
                msg.attach(img)

    with smtplib.SMTP(SES_CONFIG['host'], SES_CONFIG['port']) as server:
        server.starttls()
        server.login(SES_CONFIG['username'], SES_CONFIG['password'])
        server.send_message(msg)

    print(f"Reset link sent to {email}")


async def request_password_reset(email: str):
    users = await FRTUUsers.select(email=email)
    if not users:
        return {
            "http_code": 200,
            "code": "OK",
            "message": "If email exists, reset link sent to your email"
        }
    
    token = await generate_reset_token(email)
    await redis_client.setex(f"reset:{token}", 3600, email)
    print(f"Reset token: {token[:12]}... for {email}")
    await send_reset_email(email, token)
    
    return {
        "http_code": 200,
        "code": "OK",
        "message": "Password reset link sent to your email",
        "data": {"email": email}
    }

async def verify_reset_token(token: str):
    email = await redis_client.get(f"reset:{token}")
    if not email:
        return None, HttpStatusCode.BAD_REQUEST.response(message="Invalid or expired token")
    return email, True

async def confirm_password_reset(token: str, new_password: str):
    email, is_valid = await verify_reset_token(token)
    if not is_valid:
        return HttpStatusCode.BAD_REQUEST.response(message="Invalid or expired token")
    
    users = await FRTUUsers.select(email=email)
    if not users:
        return HttpStatusCode.NOT_FOUND.response("User not found")
    
    target_user = users[0]

    new_salt = generate_salt()
    new_password_hash = hash_password(new_password, new_salt)

    await FRTUUsers.update(
        conditions={"id": target_user.id},
        password_hash=new_password_hash,
        salt=new_salt
    )

    await redis_client.delete(f"reset:{token}")

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Password reset successful"
    }