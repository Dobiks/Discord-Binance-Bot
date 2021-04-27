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
    if content[0] == "@ABC": #Check if message starts with mentioned role
        symbol = content[1].replace('#', '').replace('/', '')
        buy_prices = content[7].split('-')
        sell_prices = content[12].split('-')
        stop_price = content[-1]
        print(symbol, buy_prices, sell_prices, stop_price)
        return symbol, buy_prices, sell_prices, stop_price
    else:
        return 0


class Signal:
    def __init__(self, symbol, buy_prices, sell_prices, stop_price):
        self.symbol = symbol
        self.min_price = client.get_symbol_info(symbol=self.symbol)['filters'][0][
            'minPrice']  # format(float(client.get_symbol_info(symbol=self.symbol)['filters'][0]['minPrice']), '.9f')
        self.buy_prices = buy_prices
        self.sell_prices = sell_prices
        self.stop_price = stop_price
        self.price = client.get_avg_price(symbol=self.symbol)['price']
        self.avg_price = self.to_satoshi(self.price)  # self.price.replace('0', '').replace('.', '')
        self.precision = self.calc_precision()
        self.buy_quantity = format(0.01 / float(self.avg_price) * 100000000, str(self.precision).join('.f'))
        self.sell_quantity = self.calc_quantity()
        self.stop_limit = self.calc_stop_limit()
        self.adjusted_stop = self.adjust_price(stop_price)

    def to_satoshi(self, price):
        price = price.replace('.', '')
        price = list(price)
        idx = []
        while 1:
            if price[0] == '0':
                price.pop(0)
            else:
                break

        tmp = "".join(price)
        print("Current price in satoshi: ", tmp)
        return tmp

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

    def calc_precision(self):
        min = str(client.get_symbol_info(symbol=self.symbol)['filters'][2]['minQty'])
        print("Min: ", min)
        min = min.replace('.', '')
        precision = min.find('1')
        print("Precision: ", precision)
        return precision

    def calc_quantity(self):
        quan = []
        x = [0.4, 0.3, 0.2, 0.095]
        for a in range(4):
            tmp = str(self.buy_quantity)  # XD
            tmp = float(tmp)  # XD
            tmp = tmp * x[a]
            quan.append(float(round(tmp, self.precision)))

        print(quan)

        return quan

    def calc_stop_limit(self):
        stop_limit = ''
        if self.stop_price[-1] == '9':
            tmp = int(self.stop_price[-2])
            tmp = tmp + 1
            tmp_list = list(stop_price)
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

    def make_order(self):
        if int(self.buy_prices[0]) > int(self.avg_price) > int(self.buy_prices[1]):
            print("CENA OK")
            print("Buy quantity: ", self.buy_quantity)
            order = client.order_market_buy(
                symbol=self.symbol,
                quantity=self.buy_quantity)
            print(order['status'])
            if order['status'] == 'FILLED':
                ocos = []
                adjusted_sell_prices = []
                for a in self.sell_prices:
                    adjusted_sell_prices.append(self.adjust_price(a))
                adjusted_stop_limit = self.adjust_price(self.stop_limit)
                adjusted_stop_price = self.adjust_price(self.stop_price)
                print(adjusted_sell_prices)
                for a in range(4):
                    oco = client.order_oco_sell(
                        symbol=self.symbol,
                        quantity=self.sell_quantity[a],
                        price=adjusted_sell_prices[a],
                        stopPrice=adjusted_stop_price,
                        stopLimitPrice=adjusted_stop_limit,
                        stopLimitTimeInForce='FOK')
                    ocos.append(oco)
                print(ocos)
        else:
            print("CENA NIE OK")


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
        author = ""
        try:
            event = receive_json_response(ws)
        except:
            # print("error")
            ws.connect("wss://gateway.discord.gg/?v=6&encording=json")
            send_json_request(ws, payload)
        try:
            content = event['d']['content']
            channel_id = event['d']['channel_id']
            author = event['d']['author']['username']
        except:
            pass

        if author == "Nickname" and channel_id == "000":
            data = binance(content)
            if data != 0:
                signal = Signal(data[0], data[1], data[2], data[3])
                # signal.make_order()

main()
