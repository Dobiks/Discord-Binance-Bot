import websocket
import json
import time
from config import *
from binance.client import Client
from binance.enums import *

client = Client(api_key, api_secret)


def send_json_request(ws, request):
    ws.send(json.dumps(request))


def receive_json_response(ws):
    response = ws.recv()
    if response:
        return json.loads(response)


def binance(content):
    content = content.split()
    print(content[0])
    if content[0] == "Now" and content[1] == "tracking":
        symbol = content[2]
        #buy_prices = 0#content[7].split('-')
        sell_prices = [content[6:10]]
        sell_prices=sell_prices[0]
        for a in range(len(sell_prices)):
            sell_prices[a]=sell_prices[a].replace(",","")
        stop_price = content[-1]
        # print(wolumen, sell_prices, stop_price)
        return symbol, sell_prices, stop_price


class Signal:
    def __init__(self, symbol, sell_prices, stop_price):
        self.symbol = symbol
        self.min_price = client.get_symbol_info(symbol=self.symbol)['filters'][0]['minPrice']
        self.sell_prices = sell_prices
        self.stop_price = stop_price
        self.stop_limit = self.calc_stop_limit()
        self.price = client.get_avg_price(symbol=self.symbol)['price']
        self.precision = self.calc_precision()
        self.buy_quantity = format(float(0.0077/float(self.price)), str(self.precision).join('.f'))
        self.sell_quantity = self.calc_sell_quantity()
        self.ok = 1
    def calc_precision(self):
        min = str(client.get_symbol_info(symbol=self.symbol)['filters'][2]['minQty'])
        print("Min: ", min)
        min = min.replace('.', '')
        precision = min.find('1')
        print("Precision: ", precision)
        return precision

    def adjust_price(self, price):
        if type(price) is str:
            print("------adjust-----")
            tmp = self.min_price
            idx = tmp.find('1')
            tmp = list(tmp)
            x = 0
            for a in range(idx + 1 - len(price), idx + 1):
                tmp[a] = price[x]
                x += 1
            tmp = "".join(tmp)
            print(tmp)
            return tmp
        else:
            return 0

    def calc_stop_limit(self):
        stop_limit = ''
        if self.stop_price[-1] == '9':
            tmp = int(self.stop_price[-2])
            tmp = tmp + 1
            tmp_list = list(self.stop_price)
            tmp_list[-2] = str(tmp)
            tmp_list[-1] = '0'
            stop_limit = stop_limit.join(tmp_list)
        else:
            tmp = int(self.stop_price[-1])
            tmp = tmp + 1
            tmp_list = list(self.stop_price)
            tmp_list[-1] = str(tmp)
            stop_limit = stop_limit.join(tmp_list)
        print("Stop limit: ", stop_limit)
        return stop_limit

    def calc_sell_quantity(self):
        quan = []
        x = [0.4, 0.3, 0.2, 0.095]
        for a in range(4):
            tmp = str(self.buy_quantity)  # XD
            tmp = float(tmp)  # XD
            tmp = tmp * x[a]
            quan.append(float(round(tmp, self.precision)))

        print("Sell quantity: ", quan)
        quan_float = [float(item) for item in quan]
        print("Suma quan: ",sum(quan_float))
        if sum(quan_float) > float(self.buy_quantity):
            print("Suma za duza!")
            signal.ok = 0

        return quan

    def make_order(self):
        if float(self.sell_prices[0]>self.price):
            print("CENA OK")
            print("Buy quantity: ", self.buy_quantity)
            order = client.order_market_buy(
                symbol=self.symbol,
                quantity=self.buy_quantity)
            print(order['status'])
            if order['status'] == 'FILLED':
                ocos = []
                for a in range(4):
                    oco = client.order_oco_sell(
                        symbol=self.symbol,
                        quantity=self.sell_quantity[a],
                        price=self.sell_prices[a],
                        stopPrice=self.stop_price,
                        stopLimitPrice=self.stop_limit,
                        stopLimitTimeInForce='FOK')
                    ocos.append(oco)
                    print("Zlecenie sprzedazy nr: ", a+1, " wystawione.")
                #print(ocos)
            print("Zlecenia wystawione!")
            return 1
        else:
            print("CENA NIE OK")
            return 0

if __name__ == "__main__":
    ws = websocket.WebSocket()
    ws.connect("wss://gateway.discord.gg/?v=6&encording=json")
    heartbeat_interval = receive_json_response(ws)["d"]["heartbeat_interval"]

    payload = {
        "op": 2,
        "d": {
            "token": token,
            "intents": 513,
            "properties": {
                "$os": 'linux',
                "$browser": 'chrome',
                "$device": 'pc'
            }
        }
    }

    send_json_request(ws, payload)

    while True:
        content = None
        try:
            event = receive_json_response(ws)
        except:
            # print("error")
            ws.connect("wss://gateway.discord.gg/?v=6&encording=json")
            send_json_request(ws, payload)
        try:
            content = event['d']['content']
            author = event['d']['author']['username']
        except:
            pass
        if content is not None:
            if author == "Nickname":
                print(f'{author}: {content}')
                data = binance(content)
                print(data)
                if len(data)==3:
                    signal = Signal(data[0], data[1], data[2])
                    if(signal.ok==1):
                        signal.make_order()
                    else:
                        print("Blad, signal ok = 0")

