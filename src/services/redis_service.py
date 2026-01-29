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

# async def send_email_otp(email: str, otp: str):
#     msg = MIMEMultipart('alternative')
#     msg['Subject'] = 'Your Login OTP'
#     msg['From'] = SES_CONFIG['from_email']
#     msg['To'] = email
    
# #     html = f"""
# #     <!DOCTYPE html>
# # <html lang="en">
# # <head>
# #     <meta charset="UTF-8">
# #     <meta name="viewport" content="width=device-width, initial-scale=1.0">
# #     <title>OTP Email Template</title>
# # </head>
# # <body style="margin: 0; padding: 0; background-color: #FFFFFF; font-family: 'GT Walsheim Pro', Arial, sans-serif;">
# #     <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #FFFFFF; padding: 40px 20px;">
# #         <tr>
# #             <td align="center">
# #                 <!-- Outer Container with Blue Background -->
# #                 <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; background-color: #D7E8F4; padding: 40px 20px;">
# #                     <tr>
# #                         <td align="center">
# #                             <!-- Inner White Card -->
# #                             <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="352" style="width: 352px; background-color: #FFFFFF; border: 1px solid #D7E8F4; border-radius: 12px; padding: 24px; box-sizing: border-box;">
# #                                 <!-- Logo Section -->
# #                                 <tr>
# #                                     <td align="center" style="padding-bottom: 20px;">
# #                                         <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center">
# #                                             <tr>
# #                                                 <td style="padding-right: 8px; vertical-align: middle;">
# #                                                     <svg width="33" height="32" viewBox="0 0 33 32" fill="none" xmlns="http://www.w3.org/2000/svg" style="display: block;">
# #                                                         <path d="M14.9291 31.9995H13.241V27.3115C13.2376 26.6772 13.4144 26.0547 13.7513 25.5144C14.0882 24.974 14.5717 24.5375 15.1473 24.2542L18.3051 22.6462L19.0516 24.0957L15.8937 25.7036C15.5991 25.859 15.3534 26.091 15.1833 26.3746C15.0133 26.658 14.9253 26.9822 14.9291 27.3115V31.9995Z" fill="#1773BE"/>
# #                                                         <path d="M19.5103 14.834H17.8567V32.0003H19.5103V14.834Z" fill="#1773BE"/>
# #                                                         <path d="M3.81288 26.3823L2.66455 25.25L6.02916 21.9322C6.48195 21.483 7.05307 21.1676 7.67805 21.0215C8.30298 20.8755 8.95695 20.9046 9.56605 21.1056L12.9192 22.238L12.3795 23.7779L9.02634 22.6456C8.70532 22.541 8.36105 22.5269 8.03231 22.6049C7.70363 22.683 7.40358 22.85 7.16601 23.0872L3.81288 26.3823Z" fill="#1773BE"/>
# #                                                         <path d="M18.2118 16.2988L5.90845 28.4437L7.07834 29.5961L19.3817 17.4512L18.2118 16.2988Z" fill="#1773BE"/>
# #                                                         <path d="M7.96941 18.7847L6.38473 15.6707C6.22718 15.3802 5.99183 15.1379 5.70431 14.9702C5.4168 14.8026 5.08813 14.7159 4.7541 14.7195H0V13.055H4.7541C5.39733 13.0516 6.02867 13.2259 6.57663 13.5582C7.12459 13.8903 7.56729 14.3672 7.8546 14.9347L9.4393 18.0486L7.96941 18.7847Z" fill="#1773BE"/>
# #                                                         <path d="M17.4087 17.5945H0V19.225H17.4087V17.5945Z" fill="#1773BE"/>
# #                                                         <path d="M9.95531 12.7164L8.39363 12.2069L9.54197 8.90049C9.64803 8.58392 9.66232 8.24449 9.58318 7.92035C9.50403 7.59621 9.33467 7.30034 9.09412 7.06608L5.74097 3.74831L6.8893 2.61597L10.231 5.92242C10.6865 6.3689 11.0064 6.93206 11.1545 7.54834C11.3027 8.16464 11.2731 8.80948 11.0692 9.41007L9.95531 12.7164Z" fill="#1773BE"/>
# #                                                         <path d="M3.61731 5.81934L2.44824 6.97252L14.7602 19.1089L15.9293 17.9556L3.61731 5.81934Z" fill="#1773BE"/>
# #                                                         <path d="M14.1434 9.30786L13.4084 7.8585L16.5664 6.29584C16.8666 6.14408 17.1185 5.91376 17.2947 5.63014C17.471 5.34651 17.5646 5.02053 17.5654 4.68791V0H19.2076V4.68791C19.2109 5.32219 19.0342 5.94473 18.6973 6.48507C18.3604 7.0254 17.8768 7.46193 17.3013 7.74523L14.1434 9.30786Z" fill="#1773BE"/>
# #                                                         <path d="M14.6047 0H12.9512V17.1664H14.6047V0Z" fill="#1773BE"/>
# #                                                         <path d="M24.1177 11.0855C23.7278 11.0959 23.3391 11.0384 22.9694 10.9157L19.5244 9.81732L20.0412 8.27734L23.3943 9.40967C23.7203 9.50973 24.0681 9.51824 24.3987 9.43418C24.7294 9.3502 25.0297 9.17701 25.2661 8.93412L28.7111 5.66162L29.8594 6.79396L26.4144 10.0891C25.8031 10.6941 24.9831 11.0499 24.1177 11.0855Z" fill="#1773BE"/>
# #                                                         <path d="M25.3705 2.40259L13.0671 14.5474L14.237 15.6998L26.5404 3.55498L25.3705 2.40259Z" fill="#1773BE"/>
# #                                                         <path d="M32.4517 18.9424H27.6976C27.0544 18.9458 26.4231 18.7715 25.8751 18.4393C25.3271 18.1071 24.8844 17.6302 24.5971 17.0627L22.9666 13.9488L24.4364 13.2241L26.0211 16.338C26.175 16.634 26.4086 16.8825 26.6962 17.0563C26.9838 17.2301 27.3144 17.3224 27.6517 17.3232H32.4059L32.4517 18.9424Z" fill="#1773BE"/>
# #                                                         <path d="M32.4515 12.7712H15.0427V14.4018H32.4515V12.7712Z" fill="#1773BE"/>
# #                                                         <path d="M25.5846 29.4404L22.2315 26.0433C21.7907 25.6064 21.4787 25.0594 21.329 24.461C21.1793 23.8625 21.1975 23.2353 21.3818 22.6463L22.5301 19.3398L24.0918 19.8494L22.9665 23.0992C22.8607 23.4105 22.8445 23.7444 22.9195 24.0642C22.9945 24.3841 23.1578 24.6771 23.3913 24.911L26.7559 28.308L25.5846 29.4404Z" fill="#1773BE"/>
# #                                                         <path d="M17.7057 12.8879L16.5366 14.0411L28.8486 26.1775L30.0177 25.0243L17.7057 12.8879Z" fill="#1773BE"/>
# #                                                     </svg>
# #                                                 </td>
# #                                                 <td style="vertical-align: middle;">
# #                                                     <svg width="92" height="23" viewBox="0 0 92 23" fill="none" xmlns="http://www.w3.org/2000/svg" style="display: block;">
# #                                                         <path d="M88.9842 4.28012C88.5854 4.28027 88.192 4.18713 87.8361 4.00836C87.499 3.84453 87.2164 3.58919 87.0205 3.27233C86.8168 2.93005 86.7169 2.53683 86.7341 2.13999C86.72 1.74347 86.8191 1.35112 87.0205 1.00764C87.2133 0.688281 87.4966 0.432164 87.8361 0.271618C88.2147 0.0928235 88.6283 0 89.0474 0C89.4673 0 89.881 0.0928235 90.2595 0.271618C90.5936 0.435629 90.8722 0.691177 91.0627 1.00764C91.2679 1.35018 91.371 1.74245 91.3616 2.13999C91.3741 2.53788 91.2711 2.931 91.0627 3.27233C90.8691 3.58605 90.5905 3.84078 90.2595 4.00836C89.8654 4.20688 89.426 4.30057 88.9842 4.28012ZM88.9842 3.67998C89.2894 3.68491 89.593 3.63503 89.8802 3.53277C90.1136 3.4349 90.3071 3.2637 90.4312 3.04586C90.5717 2.77686 90.6396 2.47637 90.6264 2.17396C90.6381 1.86806 90.5709 1.56431 90.4312 1.29073C90.3087 1.07671 90.1136 0.912273 89.8802 0.826467C89.2995 0.62976 88.6689 0.62976 88.089 0.826467C87.8556 0.912273 87.6597 1.07671 87.538 1.29073C87.3928 1.56234 87.3257 1.86757 87.3421 2.17396C87.3241 2.47684 87.3912 2.7788 87.538 3.04586C87.6621 3.2637 87.8556 3.4349 88.089 3.53277C88.3762 3.63503 88.6791 3.68491 88.9842 3.67998ZM88.537 3.03454H88.0312V1.26808H89.1793C89.3768 1.25545 89.5735 1.30289 89.7421 1.40396C89.81 1.45016 89.8638 1.51342 89.8982 1.58712C89.9325 1.66082 89.9458 1.74226 89.938 1.82293C89.9442 1.89242 89.9349 1.96251 89.9083 2.02747C89.8826 2.09243 89.8412 2.15038 89.7881 2.1966C89.6867 2.27638 89.5626 2.32376 89.4322 2.33249C89.5727 2.39836 89.689 2.50508 89.7655 2.63822L90.0067 3.01189H89.4439L89.2254 2.66086C89.1973 2.58914 89.1497 2.52646 89.088 2.47969C89.017 2.45791 88.9405 2.45791 88.8695 2.47969H88.5019L88.537 3.03454ZM88.537 1.7097V2.10601H89.2488C89.3151 2.11179 89.3807 2.09144 89.4322 2.0494C89.4517 2.03025 89.4673 2.00724 89.4767 1.98186C89.4869 1.95649 89.4915 1.92933 89.49 1.9022C89.4939 1.87485 89.4908 1.84688 89.4806 1.82105C89.4712 1.79522 89.4541 1.77245 89.4322 1.75499C89.3729 1.73225 89.3073 1.73225 89.2488 1.75499L88.537 1.7097Z" fill="#1773BE"/>
# #                                                         <path d="M21.5213 4.26978H18.616V7.31582H21.5213V4.26978Z" fill="#1773BE"/>
# #                                                         <path d="M13.6308 4.26978L8.37136 11.8565H2.90529V4.26978H0V22.0363H2.90529V14.6081H8.41733L13.6078 22.0363H17.0528L10.7829 13.0455L17.0757 4.26978H13.6308Z" fill="#1773BE"/>
# #                                                         <path d="M21.5213 8.85522H18.616V22.0357H21.5213V8.85522Z" fill="#1773BE"/>
# #                                                         <path d="M45.5318 9.30786C44.6507 8.8046 43.6438 8.55734 42.6269 8.59449C41.6645 8.55758 40.71 8.77244 39.8593 9.21724C39.1607 9.59843 38.5746 10.1527 38.1594 10.8252C37.7668 11.4763 37.5016 12.1947 37.3786 12.9427H37.2064C37.1245 12.3771 36.9661 11.8249 36.7356 11.3008C36.3772 10.4909 35.7864 9.80206 35.0361 9.31918C34.1724 8.8039 33.1737 8.5518 32.1652 8.59449C31.2118 8.55648 30.265 8.76745 29.4207 9.20593C28.7461 9.57385 28.1803 10.1085 27.7786 10.7572C27.4017 11.3964 27.1486 12.099 27.0322 12.8294H26.8714V8.85494H24.2073V22.0807H27.1126V15.5131C27.0244 14.3583 27.3273 13.2074 27.9738 12.2406C28.3531 11.8362 28.8219 11.5237 29.3437 11.3273C29.8656 11.1309 30.4264 11.0559 30.9825 11.1083C31.4796 11.0611 31.9812 11.1141 32.457 11.264C32.9327 11.4139 33.3725 11.6575 33.7499 11.9802C34.3786 12.7916 34.6775 13.8051 34.5882 14.8224V22.0807H37.459V15.5131C37.3743 14.3571 37.6812 13.206 38.3318 12.2406C38.7112 11.8392 39.1779 11.5286 39.6977 11.3324C40.2167 11.1361 40.7748 11.0594 41.3289 11.1083C41.8316 11.0597 42.3389 11.112 42.8204 11.2618C43.302 11.4117 43.7476 11.656 44.1309 11.9802C44.7592 12.7916 45.0581 13.8051 44.9691 14.8224V22.0807H47.8397V14.1543C47.8554 13.1774 47.6595 12.2086 47.2661 11.3121C46.9016 10.4894 46.2983 9.79176 45.5318 9.30786Z" fill="#1773BE"/>
# #                                                         <path d="M62.5176 9.45591C61.4725 8.8579 60.2792 8.55984 59.0725 8.59535C57.7285 8.52854 56.4033 8.92932 55.3285 9.72768C54.4427 10.4229 53.8199 11.3922 53.56 12.4793H53.3992V4.26978H50.4021V22.0816H53.0667V18.2429H53.2618C53.4741 19.4396 54.1344 20.5143 55.1108 21.2549C56.1972 21.9966 57.4999 22.3664 58.8197 22.3081C60.0762 22.3461 61.3188 22.0446 62.4138 21.4361C63.3839 20.8765 64.1543 20.0338 64.6187 19.0242C65.1299 17.904 65.3812 16.6854 65.3539 15.4573C65.3937 14.2328 65.158 13.0148 64.6647 11.8905C64.2097 10.8867 63.462 10.0393 62.5176 9.45591ZM61.9775 17.9485C61.6388 18.5578 61.0948 19.0307 60.4392 19.2847C59.6446 19.5686 58.8033 19.7031 57.9588 19.681C57.1135 19.7012 56.2737 19.551 55.4893 19.2394C54.8228 18.9667 54.2663 18.4852 53.9049 17.8693C53.5178 17.177 53.3274 16.3946 53.3539 15.6045V15.3894C53.3047 14.8159 53.382 14.2387 53.5802 13.6974C53.7785 13.1561 54.093 12.6633 54.502 12.2528C55.4792 11.4949 56.7061 11.1198 57.9471 11.1998C58.7752 11.1756 59.5994 11.3182 60.3697 11.6187C61.0214 11.8791 61.5646 12.3503 61.9088 12.9548C62.2983 13.7351 62.4802 14.6001 62.4372 15.4686C62.495 16.3201 62.3373 17.1723 61.9775 17.9485Z" fill="#1773BE"/>
# #                                                         <path d="M78.6487 4.26978H70.3116L68.8997 5.66259V6.30797H77.236L78.6487 4.92653V4.26978Z" fill="#1773BE"/>
# #                                                         <path d="M77.3883 9.29558C76.312 8.79716 75.1319 8.55662 73.9432 8.59353C72.6929 8.55943 71.4511 8.79521 70.303 9.28427C69.3758 9.68395 68.5805 10.3311 68.0061 11.1527C67.4699 11.951 67.1897 12.8901 67.2022 13.8476V13.9496H70.0845V13.8476C70.0463 13.4515 70.1087 13.0521 70.2672 12.6862C70.4264 12.3201 70.6753 11.9993 70.9922 11.7528C71.8305 11.2641 72.7998 11.0389 73.7708 11.1074C74.7276 11.0175 75.6861 11.2489 76.4923 11.7641C76.7842 12.0616 77.0067 12.4185 77.1432 12.8097C77.2806 13.2011 77.329 13.6171 77.2845 14.0289V14.7988L71.21 15.4329C70.4225 15.518 69.6498 15.7085 68.9138 15.9991C68.319 16.2325 67.8024 16.6246 67.4207 17.1314C67.0593 17.6375 66.8744 18.2454 66.8923 18.864C66.8736 19.3533 66.9758 19.8397 67.1897 20.2816C67.4035 20.7233 67.7235 21.1073 68.1208 21.4004C69.0871 22.0562 70.2461 22.3787 71.4168 22.3176C72.7507 22.3702 74.0712 22.0399 75.2178 21.3665C76.2035 20.7759 76.9348 19.8491 77.2736 18.762H77.4687V22.0798H80.1325V14.0289C80.1489 13.0529 79.9202 12.0881 79.4668 11.2206C78.9953 10.3801 78.2687 9.70682 77.3883 9.29558ZM74.7932 19.8151C73.9331 20.0902 73.0324 20.2204 72.1286 20.2001C71.4988 20.2484 70.8681 20.1146 70.3148 19.8151C70.1274 19.6907 69.976 19.5215 69.8738 19.3234C69.7708 19.1254 69.7216 18.905 69.7286 18.6827C69.6974 18.4615 69.7325 18.2358 69.8309 18.0343C69.9284 17.8328 70.0853 17.6644 70.2804 17.5504C70.8018 17.2769 71.3778 17.1184 71.9678 17.0862L77.2041 16.4973C77.2439 17.2552 77.0168 18.003 76.5618 18.6148C76.106 19.1791 75.4902 19.5969 74.7932 19.8151Z" fill="#1773BE"/>
# #                                                         <path d="M85.5398 4.26978H82.634V22.0363H85.5398V4.26978Z" fill="#1773BE"/>
# #                                                     </svg>
# #                                                 </td>
# #                                             </tr>
# #                                         </table>
# #                                     </td>
# #                                 </tr>
                                
# #                                 <!-- Main Heading: Verify Login Request -->
# #                                 <tr>
# #                                     <td align="center" style="padding-bottom: 20px;">
# #                                         <h2 style="margin: 0; width: 304px; height: 29px; font-family: 'GT Walsheim Pro', Arial, sans-serif; font-style: normal; font-weight: bold; font-size: 18px; line-height: 160%; text-align: center; color: #27272A; box-sizing: border-box;">Verify Login Request</h2>
# #                                     </td>
# #                                 </tr>
                                
# #                                 <!-- Instructional Text -->
# #                                 <tr>
# #                                     <td align="center" style="padding-bottom: 20px;">
# #                                         <p style="margin: 0; width: 304px; height: 72px; font-family: 'GT Walsheim Pro', Arial, sans-serif; font-style: normal; font-weight: 400; font-size: 16px; line-height: 150%; text-align: center; color: #808089; box-sizing: border-box;">
# #                                             We've received a login request for your<br>
# #                                             RTU Configurator account. Enter the code<br>
# #                                             below to continue.
# #                                         </p>
# #                                     </td>
# #                                 </tr>
                                
# #                                 <!-- OTP Display Box -->
# #                                 <tr>
# #                                     <td align="center" style="padding-bottom: 20px;">
# #                                         <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="304" style="width: 304px; height: 80px; background-color: #ECF4FA; border: 1px solid #D7E8F4; border-radius: 12px; padding: 16px 24px; box-sizing: border-box;">
# #                                             <tr>
# #                                                 <td align="center" valign="middle" style="height: 48px;">
# #                                                     <h1 style="margin: 0; font-family: 'GT Walsheim Pro', Arial, sans-serif; font-size: 48px; color: #000000; font-weight: bold; letter-spacing: 5px;">{otp}</h1>
# #                                                 </td>
# #                                             </tr>
# #                                         </table>
# #                                     </td>
# #                                 </tr>
                                
# #                                 <!-- Validity Message -->
# #                                 <tr>
# #                                     <td align="center" style="padding-bottom: 20px;">
# #                                         <p style="margin: 0; font-family: 'GT Walsheim Pro', Arial, sans-serif; font-style: normal; font-weight: 400; font-size: 16px; line-height: 150%; text-align: center; color: #808089;">
# #                                             The code is valid for 10 minutes only, and<br>
# #                                             it will expire shortly.
# #                                         </p>
# #                                     </td>
# #                                 </tr>
                                
# #                                 <!-- Footer Links -->
# #                                 <tr>
# #                                     <td align="center" style="padding-bottom: 20px; border-top: 1px solid #e0e0e0; padding-top: 20px;">
# #                                         <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="white-space: nowrap;">
# #                                             <tr>
# #                                                 <td style="padding: 0 10px; white-space: nowrap;">
# #                                                     <a href="#" style="color: #666666; text-decoration: none; font-size: 13px; font-family: 'GT Walsheim Pro', Arial, sans-serif; white-space: nowrap;">Terms of Use</a>
# #                                                 </td>
# #                                                 <td style="padding: 0 10px; border-left: 1px solid #e0e0e0; white-space: nowrap;">
# #                                                     <a href="#" style="color: #666666; text-decoration: none; font-size: 13px; font-family: 'GT Walsheim Pro', Arial, sans-serif; white-space: nowrap;">Privacy Policy</a>
# #                                                 </td>
# #                                                 <td style="padding: 0 10px; border-left: 1px solid #e0e0e0; white-space: nowrap;">
# #                                                     <a href="#" style="color: #666666; text-decoration: none; font-size: 13px; font-family: 'GT Walsheim Pro', Arial, sans-serif; white-space: nowrap;">Company</a>
# #                                                 </td>
# #                                             </tr>
# #                                         </table>
# #                                     </td>
# #                                 </tr>
# #                             </table>
                            
# #                             <!-- Disclaimer (Outside Inner Card, Inside Outer Container) -->
# #                             <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="352" style="width: 352px; margin-top: 20px;">
# #                                 <tr>
# #                                     <td align="center">
# #                                         <p style="margin: 0; color: #999999; font-size: 12px; line-height: 1.5; font-family: 'GT Walsheim Pro', Arial, sans-serif;">
# #                                             This is an automated message. Replies are not<br>
# #                                             monitored or answered.
# #                                         </p>
# #                                     </td>
# #                                 </tr>
# #                             </table>
# #                         </td>
# #                     </tr>
# #                 </table>
# #             </td>
# #         </tr>
# #     </table>
# # </body>
# # </html>
# #     """

#     template = load_template('otp_email_template.html')
#     html_content = template.render(otp=otp)
#     html_content = embed_images(msg, html_content)

#     msg.attach(MIMEText(html_content, 'html'))
    
#     with smtplib.SMTP(SES_CONFIG['host'], SES_CONFIG['port']) as server:
#         server.starttls()
#         server.login(SES_CONFIG['username'], SES_CONFIG['password'])
#         server.send_message(msg)

async def send_email_otp(email: str, otp: str):
    html_path = r"D:\KMP FRTU Configurator\frtu_config_backend_v1\src\templates\email\otp_email_template.html"
    
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
    
    images_dir = r"D:\KMP FRTU Configurator\frtu_config_backend_v1\src\templates\email\images"
    image_map = {
        "Frame 12.jpg": "logo_small",
        "Frame 11.jpg": "logo_large"
    }
    
    for img_file, cid_name in image_map.items():
        img_path = os.path.join(images_dir, img_file)
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', f'<{cid_name}>')
                msg.attach(img)
    
    html_content = html_content.replace('src="images/Frame 12.jpg"', 'src="cid:logo_small"')
    html_content = html_content.replace('src="images/Frame 11.jpg"', 'src="cid:logo_large"')
    
    msg.attach(MIMEText(html_content, 'html'))
    
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

# async def send_reset_email(email: str, token: str):
#     msg = MIMEMultipart('alternative')
#     msg['Subject'] = 'Reset Your Password'
#     msg['From'] = SES_CONFIG['from_email']
#     msg['To'] = email
    
#     reset_link = f"http://localhost:3000/reset-password/{token}"
    
#     html = f"""
#     <!DOCTYPE html>
#     <html><body style="margin:0;padding:0;background:#f8f9fa;font-family:Arial,sans-serif;">
#         <table width="100%" style="padding:40px 20px;">
#             <tr><td align="center">
#                 <table style="max-width:600px;background:#fff;border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,0.1);padding:40px;">
#                     <tr><td align="center" style="padding-bottom:30px;">
#                         <h1 style="color:#1773BE;font-size:28px;margin:0;">Reset Password</h1>
#                         <p style="color:#6c757d;font-size:16px;margin:10px 0 0 0;">RTU Configurator</p>
#                     </td></tr>
#                     <tr><td align="center" style="padding-bottom:40px;">
#                         <p style="font-size:16px;color:#495057;line-height:1.6;text-align:center;max-width:400px;">
#                             Click below to reset your password. Link expires in <strong>1 hour</strong>.
#                         </p>
#                     </td></tr>
#                     <tr><td align="center" style="padding-bottom:30px;">
#                         <a href="{reset_link}" style="display:inline-block;background:#1773BE;color:white;padding:18px 50px;text-decoration:none;border-radius:12px;font-size:18px;font-weight:600;box-shadow:0 8px 25px rgba(23,115,190,0.3);">
#                             Reset Password
#                         </a>
#                     </td></tr>
#                     <tr><td align="center" style="padding-bottom:30px;">
#                         <div style="background:#ECF4FA;border:2px solid #D7E8F4;border-radius:12px;padding:20px 30px;display:inline-block;">
#                             <p style="margin:0 0 10px 0;color:#6c757d;font-size:14px;">Direct Link:</p>
#                             <a href="{reset_link}" style="background:#ffffff;border-radius:8px;padding:12px;font-family:monospace;font-size:14px;color:#1773BE;word-break:break-all;text-align:center;max-width:350px;">
#                                 {reset_link}
#                             </a>
#                         </div>
#                     </td></tr>
#                     <tr><td style="padding-top:30px;border-top:1px solid #e9ecef;padding-bottom:20px;">
#                         <p style="color:#adb5bd;font-size:14px;line-height:1.5;margin:0;text-align:center;">
#                             Didn't request this? <strong>Ignore this email</strong>.
#                         </p>
#                     </td></tr>
#                 </table>
#             </td></tr>
#         </table>
#     </body></html>
#     """
    
#     msg.attach(MIMEText(html, 'html'))
    
#     with smtplib.SMTP(SES_CONFIG['host'], SES_CONFIG['port']) as server:
#         server.starttls()
#         server.login(SES_CONFIG['username'], SES_CONFIG['password'])
#         server.send_message(msg)

async def send_reset_email(email: str, token: str):
    reset_link = f"http://localhost:3000/reset-password/{token}"

    html_path = r"D:\KMP FRTU Configurator\frtu_config_backend_v1\src\templates\email\reset_password_email_template.html"

    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    html_content = html_content.replace("[RESET_LINK]", reset_link)

    msg = MIMEMultipart('related')
    msg['Subject'] = 'Reset Your Password - RTU Configurator'
    msg['From'] = SES_CONFIG['from_email']
    msg['To'] = email

    images_dir = r"D:\KMP FRTU Configurator\frtu_config_backend_v1\src\templates\email\images"
    image_map = {
        "Frame 12.jpg": "logo_small",
        "Frame 11.jpg": "logo_large"
    }

    for img_file, cid_name in image_map.items():
        img_path = os.path.join(images_dir, img_file)
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', f'<{cid_name}>')
                msg.attach(img)

    html_content = html_content.replace('src="images/Frame 12.jpg"', 'src="cid:logo_small"')
    html_content = html_content.replace('src="images/Frame 11.jpg"', 'src="cid:logo_large"')

    msg.attach(MIMEText(html_content, 'html'))

    with smtplib.SMTP(SES_CONFIG['host'], SES_CONFIG['port']) as server:
        server.starttls()
        server.login(SES_CONFIG['username'], SES_CONFIG['password'])
        server.send_message(msg)

    print(f"✅ Reset link sent to {email}")


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

