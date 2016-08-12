from flask import Flask, url_for, request, json
import datetime, hashlib
app = Flask(__name__)

@app.route('/messages', methods = ['POST'])
def api_message():

    if request.headers['Content-Type'] == 'application/json':
        appkey = hashlib.sha1('Min Hemliga Nyckel' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M")).hexdigest()
        if appkey == request.json['appkey']:
            return json.dumps({'return': '200 OK', 'message': 'Hejsan'})
        else:
            return '400 ERROR'
    else:
        return "415 Unsupported Media Type!"

if __name__ == '__main__':
    app.run()
