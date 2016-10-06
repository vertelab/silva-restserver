from flask import Flask, url_for, request, json, Response
import datetime, hashlib
import pymssql

APPKEY = "Superhemlig nyckel"
PORT = 5000
HOST = "0.0.0.0"
app = Flask(__name__)

MSSQL_SERVER = 'localhost'
MSSQL_USER = ''
MSSQL_PWD = ''
MSSQL_DB = ''
MSSQL_CHARSET = 'ISO-8859-1'

def get_appkey(offset=0):
    key = hashlib.sha256(APPKEY + (datetime.datetime.utcnow() - datetime.timedelta(minutes=offset)).strftime("%Y-%m-%d %H:%M")).hexdigest()
    return key

def check_appkey(appkey):
    for offset in [0, -1, 1]:
        if appkey == get_appkey(offset):
            return True
    return False

def py2sql(val):
    """Prepare value(s) for use in an SQL query."""
    if type(val) == type(()):
        return tuple([py2sql(v) for v in val])
    elif val == None:
        return 'NULL'
    elif type(val) in [type(str()), type(unicode())]:
        return "'%s'" % val
    return val

def get_inventory(articles):
    sql="Declare @Item ISE_TblItemQty;"
    for article in articles:
        sql += "INSERT INTO @Item(ItemId,Unit,Quantity,CompanyCode) VALUES ('%s',%s,%s,10);" % py2sql((article['ItemId'], article.get('Unit'), article['Quantity']))
    sql += "EXEC q_ise_2web_GetItemBalance @Tbl_ItemQty = @Item;"
    inventory = []
    conn = cursor = None
    try:
        conn = pymssql.connect(host=MSSQL_SERVER, user=MSSQL_USER, password=MSSQL_PWD, database=MSSQL_DB, charset=MSSQL_CHARSET)
        cursor = conn.cursor()
        cursor.execute(sql)
        res = cursor.fetchone()
        while res:
            item = {
                'ItemId': res[0],
                'Unit': res[1],
                'Quantity': res[2],
                'QuantityAvailable': res[3],
                'CompanyCode': res[4],
            }
            inventory.append(item)
            res = cursor.fetchone()
    except:
        raise Warning('Failure in SQL connection.')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return inventory

def get_order_state(order):
    headers = []
    sql = "EXEC q_ise_2web_GetOrders @CustomerNo = %s, @OrderNo = %s, @OrderIdWeb = %s, @CompanyCode = 10;" % py2sql((order.get('CustomerNo'), order.get('OrderNo'), order.get('OrderIdWeb')))
    conn = cursor = None
    try:
        conn = pymssql.connect(host=MSSQL_SERVER, user=MSSQL_USER, password=MSSQL_PWD, database=MSSQL_DB, charset=MSSQL_CHARSET)
        cursor = conn.cursor()
        cursor.execute(sql)
        res = cursor.fetchone()
        while res:
            head = {
                'CompanyCode': res[0],
                'OrderNo': res[1],
                'OrderIdWeb': res[2],
                'AmountExclTax': res[3],
                'AmountInclTax': res[4],
                'Currency': res[5],
                'StatusCode': res[6],
                'Status': res[7],
                'PaymentTermsCode': res[8],
                'PaymentTerms': res[9],
                'DeliverytypeCode': res[10],
                'Deliverytype': res[11],
                'CustomerRef': res[12],
                'OrderDate': res[13],
                'ExpDeliveryDate': res[14],
                'OurRef': res[15],
                'OrderTypeCode': res[16],
                'OrderType': res[17],
                'WebOrderNo': res[18],
                'CreatedDate': res[19],
            }
            headers.append[head]
            res = cursor.fetchone()
        rows = []
        if order.get('OrderNo'):
            sql = "EXEC q_GetOrderRows2Web  @OrderNo = %s, @CompanyCode = 10;" % py2sql(order.get('OrderNo'))
            cursor.execute(sql)
            res = cursor.fetchone()
            while res:
                row = {
                    'CompanyCode': res[0],
                    'OrderRowNo': res[1],
                    'RowIdWeb': res[2],
                    'ItemId': res[3],
                    'ItemDescr': res[4],
                    'Quantity': res[5],
                    'Unit': res[6],
                    'AmountExltax': res[7],
                    'TaxCode': res[8],
                    'Tax': res[9],
                    'DeliveredQty': res[10],
                    'RemaningQty': res[11],
                    'InvoicedQty': res[12],
                    'DeliveryDate': res[13],
                    'Discount': res[14],
                    'Note': res[15],
                    'StatusCode': res[16],
                    'Status': res[17],
                }
                rows.append(row)
                res = cursor.fetchone()
    except:
        raise Warning('Failure in SQL connection.')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return headers, rows

def place_order(order):
    head = order['head']
    rows = order['rows']
    sql="""DECLARE @Header ISE_TblOrderHeader;
INSERT INTO @Header(OrderIdWeb,CustomerId,Address1,Address2,Address3,Address4,PostalCode,CountryCode,OrderReference,YourReference,OrderComment,Currency,CompanyCode) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,10);
DECLARE @Rows ISE_TblOrderRow;""" % py2sql(
        (head['OrderIdWeb'], head.get('CustomerId'), head.get('Address1'),
        head.get('Address2'), head.get('Address3'), head.get('Address4'),
        head.get('PostalCode'), head.get('CountryCode'), head.get('OrderReference'),
        head.get('YourReference'), head.get('OrderComment'), head.get('Currency'))
    )
    for row in rows:
        sql += "INSERT INTO @Rows(OrderIdWeb,RowIdWeb,ItemId,Quantity,CompanyCode) VALUES (%s,%s,%s,%s,10);" % py2sql((
            head['OrderIdWeb'], row['RowIdWeb'], row['ItemId'], row['Quantity']))
    sql += "EXEC q_ISE_Web_IntegrateOrder @tblOrderHeader = @Header, @tblOrderRow = @Rows;"
    conn = cursor = None
    res = "SQL Error"
    try:
        conn = pymssql.connect(host=MSSQL_SERVER, user=MSSQL_USER, password=MSSQL_PWD, database=MSSQL_DB, charset=MSSQL_CHARSET)
        cursor = conn.cursor()
        cursor.execute(sql)
        res = cursor.fetchone()[0]
        if res == ' ':
            conn.commit()
    except:
        raise Warning('Failure in SQL connection.')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return res

@app.route('/inventory', methods = ['POST'])
def api_inventory():
    try:
        if request.headers['Content-Type'] == 'application/json':
            if check_appkey(request.json['appkey']):
                data = json.dumps({
                    'appkey': get_appkey(),
                    'inventory': get_inventory(request.json.get('articles', {})),
                })
                return Response(data, status=200, mimetype='application/json')
            else:
                return Response('500 Permission denied', status=500)
        else:
            return Response("415 Unsupported Media Type!", status=415)
    except:
        return Response('400 ERROR', status=400)

@app.route('/order_info', methods = ['POST'])
def api_order_info():
    try:
        if request.headers['Content-Type'] == 'application/json':
            if check_appkey(request.json['appkey']):
                order = request.json['order']
                head, rows = get_order_state(order)
                data = json.dumps({
                    'appkey': get_appkey(),
                    'order': order,
                    'result': {'head': head, 'rows': rows},
                })
                return Response(data, status=200, mimetype='application/json')
            else:
                return Response('500 Permission denied', status=500)
        else:
            return Response("415 Unsupported Media Type!", status=415)
    except:
        return Response('400 ERROR', status=400)

@app.route('/place_order', methods = ['POST'])
def api_place_order():
    try:
        if request.headers['Content-Type'] == 'application/json':
            if check_appkey(request.json['appkey']):
                order = request.json['order']
                data = json.dumps({
                    'appkey': get_appkey(),
                    'order': order,
                    'result': place_order(order),
                })
                return Response(data, status=200, mimetype='application/json')
            else:
                return Response('500 Permission denied', status=500)
        else:
            return Response("415 Unsupported Media Type!", status=415)
    except:
        return Response('400 ERROR', status=400)

if __name__ == '__main__':
    app.run(host=HOST, port=PORT)
