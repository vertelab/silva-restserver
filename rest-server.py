# -*- coding: utf-8 -*-
from flask import Flask, url_for, request, json, Response
from gevent.wsgi import WSGIServer
import datetime, hashlib
import pymssql
import logging
import traceback
import sys
import codecs

from settings import *

logging.basicConfig(filename=LOGFILE, level=LOGLEVEL, format='%(asctime)s %(levelname)s: %(message)s')

app = Flask(__name__)

def get_appkey(offset=0):
    key = hashlib.sha256(APPKEY + (datetime.datetime.utcnow() - datetime.timedelta(minutes=offset)).strftime("%Y-%m-%d %H:%M")).hexdigest()
    return key

def check_appkey(appkey):
    for offset in [0, -1, 1]:
        if appkey == get_appkey(offset):
            return True
    return False

def get_inventory(articles):
    sql="Declare @Item ISE_TblItemQty;"
    data = []
    for article in articles:
        sql += "INSERT INTO @Item(ItemId,Unit,Quantity,CompanyCode) VALUES (%s,%s,%s,10);"
        data += [article['ItemId'], article.get('Unit'), article['Quantity']]
    sql += "EXEC q_ise_2web_GetItemBalance @Tbl_ItemQty = @Item;"
    inventory = []
    conn = cursor = None
    data = tuple(data)
    logging.debug(sql % data)
    try:
        conn = pymssql.connect(host=MSSQL_SERVER, user=MSSQL_USER, password=MSSQL_PWD, database=MSSQL_DB)
        cursor = conn.cursor(as_dict=True)
        cursor.execute(sql, data)
        res = cursor.fetchone()
        while res:
            item = res
            inventory.append(item)
            res = cursor.fetchone()
    except:
        e = sys.exc_info()
        msg = traceback.format_exception(e[0], e[1], e[2])
        logging.warn(''.join(msg))
        raise Warning('Failure in SQL connection.')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return inventory

def get_order_state(order):
    headers = []
    rows = []
    sql = "EXEC q_ise_2web_GetOrders @CustomerNo = %s, @OrderNo = %s, @OrderIdWeb = %s, @CompanyCode = 10;"
    data = (order.get('CustomerNo'), order.get('OrderNo'), order.get('OrderIdWeb'))
    conn = cursor = None
    logging.debug(sql % data)
    try:
        conn = pymssql.connect(host=MSSQL_SERVER, user=MSSQL_USER, password=MSSQL_PWD, database=MSSQL_DB)
        cursor = conn.cursor()
        cursor.execute(sql, data)
        res = cursor.fetchone()
        while res:
            if len(res) >= 20:
                logging.debug(res)
                head = {
                    'CompanyCode': res[0],
                    'OrderNo': res[1],
                    'OrderIdWeb': res[2],
                    'ExternalOrderId': res[3],
                    'AmountExclTax': res[4],
                    'AmountInclTax': res[5],
                    'Currency': res[6],
                    'StatusCode': res[7],
                    'Status': res[8],
                    'PaymentTermsCode': res[9],
                    'PaymentTerms': res[10],
                    'DeliverytypeCode': res[11],
                    'Deliverytype': res[12],
                    'CustomerRef': res[13],
                    'OrderDate': res[14],
                    'ExpDeliveryDate': res[15],
                    'OurRef': res[16],
                    'OrderTypeCode': res[17],
                    'OrderType': res[18],
                    'CreatedDate': res[19], 
                }
                headers.append(head)
                if order.get('OrderNo') or head.get('OrderNo'):
                    sql = "EXEC q_ise_2web_GetOrderRows  @OrderNo = %s;"
                    data = (order.get('OrderNo') or head.get('OrderNo'))
                    logging.debug(sql % data)
                    cursor.execute(sql, data)
                    res = cursor.fetchone()
                    while res:
                        logging.debug(res)
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
    sys.stdout.flush()
    return headers, rows

def place_order(order):
    head = order['head']
    rows = order['rows']
    sql="""DECLARE @Header ISE_TblOrderHeader;
INSERT INTO @Header(OrderIdWeb,CustomerId,Address1,Address2,Address3,Address4,PostalCode,CountryCode,OrderReference,YourReference,OrderComment,Currency,CompanyCode, Contact, Extra1, Extra2, Extra3) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,10, %s, %s, %s, %s);
DECLARE @Rows ISE_TblOrderRow;"""
    data = [head['OrderIdWeb'], head.get('CustomerId'), head.get('Address1'),
        head.get('Address2'), head.get('Address3'), head.get('Address4'),
        head.get('PostalCode'), head.get('CountryCode'), head.get('OrderReference'),
        head.get('YourReference'), head.get('OrderComment'), head.get('Currency'),
        head.get('Contact'), head.get('Extra1'), head.get('Extra2'), head.get('Extra3')]
    for row in rows:
        sql += "INSERT INTO @Rows(OrderIdWeb,RowIdWeb,ItemId,Quantity,CompanyCode, Extra1, Extra2, Extra3) VALUES (%s,%s,%s,%s,10, %s, %s, %s);"
        data += [head['OrderIdWeb'], row['RowIdWeb'], row['ItemId'], row['Quantity'],
            row.get('Extra1'), row.get('Extra2'), row.get('Extra3')]
    sql += "EXEC q_ISE_Web_IntegrateOrder @tblOrderHeader = @Header, @tblOrderRow = @Rows;"
    conn = cursor = None
    result = "SQL Error"
    logging.debug(sql % data)
    try:
        conn = pymssql.connect(host=MSSQL_SERVER, user=MSSQL_USER, password=MSSQL_PWD, database=MSSQL_DB)
        cursor = conn.cursor()
        cursor.execute(sql, data)
        try:
            conn.commit()
            result = ''
        except:
            e = sys.exc_info()
            msg = traceback.format_exception(e[0], e[1], e[2])
            logging.warn(''.join(msg))
            result = u'Fel vid orderläggning!'
    except:
        e = sys.exc_info()
        msg = traceback.format_exception(e[0], e[1], e[2])
        logging.warn(''.join(msg))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    logging.debug(result)
    return result

@app.route('/inventory', methods = ['POST'])
def api_inventory():
    try:
        if request.headers['Content-Type'] == 'application/json':
            logging.debug(request.json)
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
        e = sys.exc_info()
        msg = traceback.format_exception(e[0], e[1], e[2])
        logging.warn(''.join(msg))
        return Response('400 ERROR', status=400)

@app.route('/order_info', methods = ['POST'])
def api_order_info():
    try:
        if request.headers['Content-Type'] == 'application/json':
            logging.debug(request.json)
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
        e = sys.exc_info()
        msg = traceback.format_exception(e[0], e[1], e[2])
        logging.warn(''.join(msg))
        return Response('400 ERROR', status=400)

@app.route('/place_order', methods = ['POST'])
def api_place_order():
    try:
        if request.headers['Content-Type'] == 'application/json':
            logging.debug(request.json)
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
        e = sys.exc_info()
        msg = traceback.format_exception(e[0], e[1], e[2])
        logging.warn(''.join(msg))
        return Response('400 ERROR', status=400)
        

http_server = WSGIServer((HOST, PORT), app)
http_server.serve_forever()
