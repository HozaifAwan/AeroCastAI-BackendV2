from mailjet_rest import Client

api_key = '0460478a7d78d90d7b7681a5d775e6b3'
api_secret = 'e1b7f741a7f4b3979a9530ea0dff756f'
mailjet = Client(auth=(api_key, api_secret), version='v3.1')

data = {
  'Messages': [
    {
      "From": {
        "Email": "aerocastai@gmail.com",
        "Name": "AeroCastAI"
      },
      "To": [
        {
          "Email": "hozaifawan@gmail.com",
          "Name": "You"
        }
      ],
      "Subject": "AeroCastAI Test Email",
      "TextPart": "You've now subscribed to AeroCastAI. We will monitor your zipcode 24/7 and let you know if you are in danger of a tornado attack."
    }
  ]
}

result = mailjet.send.create(data=data)
print(result.status_code)
print(result.json())