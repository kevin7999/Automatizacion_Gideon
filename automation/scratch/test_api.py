import urllib.request, json
data = json.dumps({'query': 'query { mailbox(mailbox: "testecommerce123") { id sender subject } }'}).encode()
req = urllib.request.Request('https://api.maildrop.cc/graphql', data=data, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
try:
    print(urllib.request.urlopen(req).read().decode())
except Exception as e:
    print(e)
