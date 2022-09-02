# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.message import EmailMessage

msg = EmailMessage()
msg.set_content('This is just a test.')

msg['Subject'] = 'Test Message'
msg['From'] = "hgk@ieee.org"
msg['To'] = "hgk@ieee.org"

# Send the message via our own SMTP server.
s = smtplib.SMTP('localhost')
s.send_message(msg)
s.quit()
