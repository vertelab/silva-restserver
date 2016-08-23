from flask import Flask, url_for, request, json, Response
import datetime, hashlib

APPKEY = "Superhemlig nyckel"
PORT = 5000
app = Flask(__name__)

def get_inventory(article_id, amount):
    if article_id == "1337":
        stock = 42 
    elif article_id == "1338":
        stock = 13
    elif article_id == "1336":
        stock = 2
    elif article_id == "1339":
        stock = 0
    else:
        stock = 0
    print '%s\t%s' % (article_id, amount)
    return amount if amount <= stock else stock

def get_order_state(order):
    if order == 23:
        return "Shipped"
    else:
        return "Processing"

def get_appkey(offset=0):
    print (datetime.datetime.utcnow() + datetime.timedelta(seconds=offset)).strftime("%Y-%m-%d %H:%M:%S")[:-1]
    key = hashlib.sha256(APPKEY + (datetime.datetime.utcnow() - datetime.timedelta(seconds=offset)).strftime("%Y-%m-%d %H:%M:%S")[:-1]).hexdigest()
    print key
    return key

def check_appkey(appkey):
    for offset in [0, -10, 10]:
        if appkey == get_appkey(offset):
            return True
    return False

@app.route('/inventory', methods = ['POST'])
def api_inventory():
    try:
        if request.headers['Content-Type'] == 'application/json':
            if check_appkey(request.json['appkey']):
                result = {}
                articles = request.json.get('articles', {})
                for article_id in articles:
                    result[article_id] = get_inventory(article_id, articles[article_id])
                data = json.dumps({
                    'appkey': get_appkey(),
                    'inventory': result,
                })
                return Response(data, status=200, mimetype='application/json')
            else:
                return Response('500 Permission denied', status=500)
        else:
            return Response("415 Unsupported Media Type!", status=415)
    except:
        return Response('400 ERROR', status=400)

@app.route('/order', methods = ['POST'])
def api_order_state():
    try:
        if request.headers['Content-Type'] == 'application/json':
            if check_appkey(request.json['appkey']):
                order = request.json['order']
                data = json.dumps({
                    'appkey': get_appkey(),
                    'order': order,
                    'state': get_order_state(order),
                })
                return Response(data, status=200, mimetype='application/json')
            else:
                return Response('500 Permission denied', status=500)
        else:
            return Response("415 Unsupported Media Type!", status=415)
    except:
        return Response('400 ERROR', status=400)

if __name__ == '__main__':
    app.run(port=PORT)
