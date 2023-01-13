#####################################################################################
# Here we illustrate how to use Python QuickFIX library to talk to Deltix FIX Gateway
# fix_sample_order_entry and fix_sample_market_data samples rely on this class 
#####################################################################################

import time
import quickfix as fix
import configparser
import quickfix44 as fixnn


class Application(fix.Application):
    debug = False
    session_id = None
    session_pwd = None
    logged_out = False

    def setSessionPassword(self, password):
        self.session_pwd = password

    def onCreate(self, session_id):
        return

    def onLogon(self, session_id):
        print("Session %s successfully logged in" % session_id)
        self.session_id = session_id
        self.logged_out = False
        return

    def onLogout(self, session_id):
        print("Session %s logged out" % session_id)
        self.session_id = None
        self.logged_out = True
        return

    def toAdmin(self, message, session_id):
        if self.debug:
            print("To Admin message: %s" % message)
        msgType = fix.MsgType()
        message.getHeader().getField(msgType)
        if msgType.getValue() == fix.MsgType_Logon :
            message.getHeader().setField(fix.Password(self.session_pwd))
        return

    def fromAdmin(self, message, session_id):
        if self.debug:
            print("From Admin message: %s" % message)
        return

    def toApp(self, message, session_id):
        if self.debug:
            print("To App message: ", end='')
            print_message(message)
        return

    def fromApp(self, message, session_id):
        print("Received message: ", end='')
        print_message(message)
        return


class FixSession(object) :
    initiator = None
    exec_id = 0

    def __init__(self, config_file):
        self.settings = fix.SessionSettings(config_file)
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        sender_pwd = None
        if "SESSION" in self.config and "SenderPassword" in self.config["SESSION"]:
            sender_pwd = self.config["SESSION"]["SenderPassword"]

        self.application = Application()
        if sender_pwd:
            self.application.setSessionPassword(sender_pwd)
        else:
            print("Warning: SESSION SenderPassword is not specified in config file: " + config_file)

        store_factory = fix.FileStoreFactory(self.settings)
        log_factory = fix.FileLogFactory(self.settings)
        self.initiator = fix.SocketInitiator(self.application, store_factory, self.settings, log_factory)

    def start(self):
        if not self.initiator.isStopped():
            raise Exception("Session is already started")

        self.application.session_id = None
        self.application.logged_out = False
        self.initiator.start()

        # wait for the client to login
        while not self.application.session_id and not self.application.logged_out:
            time.sleep(0.1)

        if not self.application.session_id:
            raise Exception("Login failed")

    def stop(self):
        self.initiator.stop()

    def gen_exec_id(self):
        new_id = time.time_ns()
        self.exec_id = new_id if self.exec_id < new_id else self.exec_id + 1
        return repr(self.exec_id)

    def submit(self, request):
        request.set_id(self.gen_exec_id())

        print("Sending %s" % request)
        fix.Session.sendToTarget(request.get_fix_message(), self.application.session_id)

    def submit_buy_order(self, destination, symbol, quantity, price=None, account=None, custom_fields=None):
        self.submit_order(destination, fix.Side_BUY, symbol, quantity, price, account, custom_fields)

    def submit_sell_order(self, destination, symbol, quantity, price=None, account=None, custom_fields=None):
        self.submit_order(destination, fix.Side_SELL, symbol, quantity, price, account, custom_fields)

    def submit_order(self, destination, side, symbol, quantity, price=None, account=None, custom_fields=None):
        request = OrderRequest()
        request.set_symbol(symbol)
        request.set_destination(destination)
        request.set_side(side)
        request.set_quantity(quantity)
        if price is not None:
            request.set_price(price)
            request.set_order_type(fix.OrdType_LIMIT)
        else:
            request.set_order_type(fix.OrdType_MARKET)

        if account:
            request.set_account(account)

        if custom_fields:
            request.set_custom_fields(custom_fields)

        self.submit(request)


# End of FixSession


class OrderRequest(object) :
    id = None
    symbol = None
    side = fix.Side_BUY
    quantity = None
    price = None
    order_type = fix.OrdType_MARKET
    time_in_force = fix.TimeInForce_DAY
    account = None
    destination = None
    exchange = None
    custom_fields = {}

    def set_id(self, id):
        self.id = id

    def set_symbol(self, symbol):
        self.symbol = symbol

    def set_side(self, side):
        self.side = fix.Side_BUY if side.upper() == "BUY" else fix.Side_SELL

    def set_quantity(self, quantity):
        self.quantity = quantity

    def set_price(self, price):
        self.price = price

    def set_order_type(self, order_type):
        self.order_type = order_type

    def set_time_in_force(self, time_in_force):
        self.time_in_force = time_in_force

    def set_account(self, account):
        self.account = account

    def set_destination(self, destination):
        self.destination = destination

    def set_exchange(self, exchange):
        self.exchange = exchange

    def set_custom_fields(self, custom_fields):
        self.custom_fields = custom_fields

    def get_fix_message(self):
        request = fix.Message()
        request.getHeader().setField(fix.BeginString(fix.BeginString_FIX44))
        request.getHeader().setField(fix.MsgType(fix.MsgType_NewOrderSingle))

        assert self.id
        request.setField(fix.ClOrdID(self.id))

        assert self.symbol
        request.setField(fix.Symbol(self.symbol))

        assert self.side
        request.setField(fix.Side(self.side))

        assert self.quantity
        request.setField(fix.OrderQty(self.quantity))

        if self.price is not None:
            request.setField(fix.Price(self.price))
        elif self.order_type == fix.OrdType_LIMIT:
            raise Exception("Must specify price for LIMIT order")

        assert self.order_type
        request.setField(fix.OrdType(self.order_type))

        assert self.time_in_force
        request.setField(fix.TimeInForce(self.time_in_force))

        if self.account:
            request.setField(fix.Account(self.account))

        if self.destination is not None:
            request.setField(fix.ExecBroker(self.destination))

        if self.exchange is not None:
            request.setField(fix.ExDestination(self.exchange))

        request.setField(fix.TransactTime())

        for key in self.custom_fields:
            request.setField(key, self.custom_fields[key])

        request.setField(fix.SenderCompID("TRADER"))

        return request

    def __str__(self):
        side = "BUY" if self.side == fix.Side_BUY else "SELL"
        order_type = "LIMIT" if self.order_type == fix.OrdType_LIMIT else "MARKET"
        return "OrderRequest: ID=%s, OrderType=%s, Symbol=%s, Side=%s, Quantity=%s, Price=%s, Account=%s, Destination=%s, Exchange=%s" % \
               (self.id, order_type, self.symbol, side, self.quantity, self.price, self.account, self.destination, self.exchange)

# End of ObjectRequest


class MarketDataRequest(object):
    id = None
    symbols = []

    def set_id(self, id):
        self.id = id

    def set_symbols(self, symbols):
        self.symbols = symbols

    def get_fix_message(self):
        request = fix.Message()
        request.getHeader().setField(fix.BeginString(fix.BeginString_FIX44))
        request.getHeader().setField(fix.MsgType(fix.MsgType_MarketDataRequest))

        request.setField(fix.MDReqID(self.id))
        request.setField(fix.SubscriptionRequestType(fix.SubscriptionRequestType_SNAPSHOT_PLUS_UPDATES))
        request.setField(fix.SecurityType(fix.SecurityType_FOREIGN_EXCHANGE_CONTRACT))
        request.setField(fix.MarketDepth(0)) # full book
        request.setField(fix.MDUpdateType(fix.MDUpdateType_FULL_REFRESH)) # fix.MDUpdateType_INCREMENTAL_REFRESH

        group = fixnn.MarketDataRequest().NoMDEntryTypes()
        group.setField(fix.MDEntryType(fix.MDEntryType_BID))
        group.setField(fix.MDEntryType(fix.MDEntryType_OFFER))
        group.setField(fix.MDEntryType(fix.MDEntryType_TRADE))
        request.addGroup(group)

        request.setField(fix.NoRelatedSym(len(self.symbols)))
        group = fixnn.MarketDataRequest().NoRelatedSym()
        for symbol in self.symbols:
            group.setField(fix.Symbol(symbol))
            request.addGroup(group)

        return request

    def __str__(self):
        return "MarketDataRequest: ID=%s, Symbols=%s" % (self.id, self.symbols)

# End of MarketDataRequest


def print_message(msg):
    msg_str = ''
    msg_type = get_field_value(fix.MsgType(), msg.getHeader())
    if msg_type == fix.MsgType_News:
        msg_str = "MessageType=News, Sender="
        msg_str += get_field_value(fix.SenderCompID(), msg.getHeader())
        msg_str += ", HeadLine="
        msg_str += get_field_value(fix.Headline(), msg)
        msg_str += ", Text="
        msg_str += get_field_value(fix.Text(), msg)
    elif msg_type == fix.MsgType_MarketDataRequestReject:
        print("REJECTED")
    elif msg_type == fix.MsgType_MarketDataSnapshotFullRefresh:
        print("SNAPSHOT")
        print(get_field_value(fix.Symbol(), msg))
        print(msg)
        
    else:
        msg_str = "OrderID="
        msg_str += get_field_value(fix.ClOrdID(), msg)
        msg_str += ", MessageType="
        msg_str += get_message_type(msg)
        msg_str += ", OrderStatus=" #39
        msg_str += get_order_status(msg)
        msg_str += ", Sender="
        msg_str += get_field_value(fix.SenderCompID(), msg.getHeader())
        msg_str += ", Target="
        msg_str += get_field_value(fix.TargetCompID(), msg.getHeader())
        msg_str += ", OrderType=" #40 1-Market, 2-Limit
        msg_str += get_order_type(msg)
        msg_str += ", Side=" #54 1-Buy,2-Sell
        msg_str += 'BUY' if get_field_value(fix.Side(), msg) == fix.Side_BUY else 'SELL'
        msg_str += ", Quantity=" #38
        msg_str += str(get_field_value(fix.OrderQty(), msg))
        msg_str += ", Price="
        msg_str += str(get_field_value(fix.Price(), msg))
        msg_str += ", Symbol="
        msg_str += get_field_value(fix.Symbol(), msg)
        msg_str += ", ExecutionType=" #150
        msg_str += get_exec_type(msg)
        if msg.isSetField(fix.Text().getField()):
            msg_str += ", Text="
            msg_str += get_field_value(fix.Text(), msg)
        msg_str += ", ExecutedQuantity=" #14
        msg_str += str(get_field_value(fix.CumQty(), msg))

    print(msg_str)


def get_field_value(fobj, msg):
    if msg.isSetField(fobj.getField()):
        msg.getField(fobj)
        return fobj.getValue()
    else:
        return "None"


def get_message_type(msg) :
    msg_type = get_field_value(fix.MsgType(), msg.getHeader())
    if msg_type == fix.MsgType_ExecutionReport:
        return "ExecutionReport"
    elif msg_type == fix.MsgType_News:
        return "News"
    elif msg_type == fix.MsgType_NewOrderSingle:
        return "NewOrderSingle"
    else:
        return msg_type


def get_order_type(msg):
    ord_type = get_field_value(fix.OrdType(), msg)
    if ord_type == fix.OrdType_LIMIT:
        return "LIMIT"
    elif ord_type == fix.OrdType_MARKET:
        return "MARKET"
    else:
        return ord_type


def get_exec_type(msg):
    rpt = get_field_value(fix.ExecType(), msg)
    if rpt == fix.ExecType_NEW:
        return "NEW"
    elif rpt == fix.ExecType_REJECTED:
        return "REJECTED"
    elif rpt == fix.ExecType_TRADE:
        return "FILLED"
    elif rpt == fix.ExecType_CANCELED:
        return "CANCELED"
    else:
        return rpt


def get_order_status(msg):
    status = get_field_value(fix.OrdStatus(), msg)
    if status == fix.OrdStatus_NEW:
        return "NEW"
    elif status == fix.OrdStatus_FILLED:
        return "FILLED"
    elif status == fix.OrdStatus_REJECTED:
        return "REJECTED"
    elif status == fix.OrdStatus_CANCELED:
        return "CANCELED"
    else:
        return status

