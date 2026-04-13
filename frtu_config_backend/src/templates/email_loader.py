import os
import jinja2 # type: ignore
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import base64

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates', 'email')
IMAGES_DIR = os.path.join(TEMPLATES_DIR, 'images')

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
    trim_blocks=True,
    lstrip_blocks=True
)

def load_template(template_name: str):
    return env.get_template(template_name)

def embed_images(msg: MIMEMultipart, html_content: str):
    for img_file in ['Frame_12.png', 'Frame_11.png']:
        img_path = os.path.join(IMAGES_DIR, img_file)
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                img_data = f.read()
                image = MIMEImage(img_data)
                image.add_header('Content-ID', f'<{os.path.splitext(img_file)[0]}>')
                msg.attach(image)
    
    return html_content.replace('cid:logo_small', 'cid:Frame_12').replace('cid:logo_large', 'cid:Frame_11')
