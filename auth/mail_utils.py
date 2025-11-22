import random
import smtplib

def generate_otp():
    return str(random.randint(100000, 999999))

def send_email(to_email, otp):
    sender = "charansakhavarapu@gmail.com"
    
    # IMPORTANT: Use your 16-digit Gmail App Password here (not your normal password)
    password = "shrbagyioztlrqda"

    subject = "Your Password Reset OTP"
    body = f"Your OTP for resetting your password is: {otp}"

    message = f"Subject: {subject}\n\n{body}"

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender, password)
        server.sendmail(sender, to_email, message)
        server.quit()
        print("Email sent successfully!")
        return True

    except Exception as e:
        print("Email Error:", e)
        return False
