from twilio.rest import Client


# Your Account Sid and Auth Token from twilio.com/console
# DANGER! This is insecure. See http://twil.io/secure
account_sid = 'AC93e0ce8c7f637352219ab3f6e71bbe34'
auth_token = '3cb28c9d23d966500d856988e9eb911b'
client = Client(account_sid, auth_token)

message = client.messages \
        .create(
             body="This is message from Client-S1",
             from_='+12058102291',
             to='+60198285105' # '+15558675310'
         )

print(message.sid)
