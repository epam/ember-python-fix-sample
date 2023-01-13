###############################################################################
# This is all-in-one sample tht demonstates how to submit orders
###############################################################################

import sys
import time
import argparse
import quickfix as fix
import configparser

class Application(fix.Application):
    exec_id = 0
    sessionID = None
    sessionPwd = None
    logged_out = False

    def setSessionPassword(self, password):
        self.sessionPwd = password

    def gen_exec_id(self):
        new_id = time.time_ns()
        self.exec_id = new_id if self.exec_id < new_id else self.exec_id + 1
        return repr(self.exec_id)

    def onCreate(self, sessionID):
        return

    def onLogon(self, sessionID):
        print("Session %s successfully logged in" % sessionID)
        self.sessionID = sessionID
        self.logged_out = False
        return

    def onLogout(self, sessionID):
        print("Session %s logged out" % sessionID)
        self.sessionID = None
        self.logged_out = True
        return

    def toAdmin(self, message, sessionID):
        msgType = fix.MsgType();
        message.getHeader().getField(msgType)
        if msgType.getValue() == fix.MsgType_Logon :
            message.getHeader().setField(fix.Password(self.sessionPwd))
        return

    def fromAdmin(self, message, sessionID):
        return

    def toApp(self, message, sessionID):
        return

    def fromApp(self, message, sessionID):
        print("Received message: ", end='')
        print_message(message)
        return

    def submit_order(self, symbol, side, order_type, quantity, price, destination, exchange):
        trade = fix.Message()
        trade.getHeader().setField(fix.BeginString(fix.BeginString_FIX44))
        trade.getHeader().setField(fix.MsgType(fix.MsgType_NewOrderSingle))

        order_id = self.gen_exec_id()
        trade.setField(fix.ClOrdID(order_id))
        trade.setField(fix.TimeInForce(fix.TimeInForce_DAY))
        trade.setField(fix.Symbol(symbol))
        trade.setField(fix.Side(side))
        trade.setField(fix.OrdType(order_type))
        trade.setField(fix.OrderQty(quantity))

        if price is not None:
            trade.setField(fix.Price(price))
        elif order_type != fix.OrdType_MARKET:
            raise Exception("Must specify price for LIMIT order")

        if destination is not None:
            trade.setField(fix.ExecBroker(destination))
        if exchange is not None:
            trade.setField(fix.ExDestination(exchange))

        trade.setField(fix.TransactTime())

        side = "BUY" if side == fix.Side_BUY else "SELL"
        order_type = "LIMIT" if order_type == fix.OrdType_LIMIT else "MARKET"
        print("Sending order: OrderID=%s, SessionID=%s, OrderType=%s, Symbol=%s, Side=%s, Quantity=%s, Price=%s, Destination=%s, Exchange=%s" %
              (order_id, self.sessionID, order_type, symbol, side, quantity, price, destination, exchange))
        fix.Session.sendToTarget(trade, self.sessionID)

# End of Application

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
    else:
        msg_str = "OrderID="
        msg_str += get_field_value(fix.ClOrdID(), msg)
        msg_str += ", MessageType="
        msg_str += get_message_type(msg)
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
        msg_str += ", OrderStatus=" #39
        msg_str += get_order_status(msg)

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

def main(config_file):
    try:
        config = configparser.ConfigParser()
        config.read(config_file)
        sender_pwd = config["SESSION"]["SenderPassword"] if "SESSION" in config and "SenderPassword" in config["SESSION"] else None
        if not sender_pwd:
            print("Warning: SESSION SenderPassword is not specified in config file: " + config_file)

        settings = fix.SessionSettings(config_file)
        application = Application()
        application.setSessionPassword(sender_pwd)
        store_factory = fix.FileStoreFactory(settings)
        log_factory = fix.FileLogFactory(settings)
        initiator = fix.SocketInitiator(application, store_factory, settings, log_factory)
        initiator.start()

        parser = argparse.ArgumentParser(description='CLI Command', prog="command", usage="help | exit | {buy,sell} -s SYMBOL -q QUANTITY [-t {LIMIT,MARKET}] [-p PRICE] [-d DESTINATION] [-e EXCHANGE] [-n ORDER_COUNT] [-i INTERVAL]")
        parser.add_argument("command", type=str, choices=["buy", "sell"], help="Command")
        parser.add_argument("-s", "--symbol", type=str, required=True, help="Order instrument symbol")
        parser.add_argument("-q", "--quantity", type=float, required=True, help="Order quantity")
        parser.add_argument("-t", "--order_type", type=str, choices=["LIMIT", "MARKET"], default="MARKET", help="Order type")
        parser.add_argument("-p", "--price", type=float, default=None, help="Order limit price")
        parser.add_argument("-d", "--destination", type=str, default="SIM", help="Destination ID")
        parser.add_argument("-e", "--exchange", type=str, default=None, help="Exchange ID")
        parser.add_argument("-n", "--order_count", type=int,  default=1, help="Number of orders to submit")
        parser.add_argument("-i", "--interval", type=int, default=5, help="Number of seconds between orders")

        # wait for the client to login
        while not application.sessionID and not application.logged_out:
            time.sleep(0.5)

        if not application.sessionID:
            print("Login failed")
            exit(1)

        while 1:
            print("--> ", end='')
            command = input().strip()
            if not command:
                continue

            command_args = command.split(' ') if ' ' in command else [ command ]
            command = command_args[0]

            if command == "buy" or command == "sell":
                try :
                    args = parser.parse_args(command_args)

                    side = fix.Side_BUY if command == "buy" else fix.Side_SELL
                    order_type = fix.OrdType_LIMIT if args.order_type == "LIMIT" else fix.OrdType_MARKET

                    if order_type == fix.OrdType_LIMIT and args.price is None:
                        print("Please specify LIMIT order price")
                        continue

                    for x in range(args.order_count):
                        if x > 0:
                            time.sleep(args.interval)
                        application.submit_order(args.symbol, side, order_type, args.quantity, args.price, args.destination, args.exchange)

                    time.sleep(0.5) # wait a bit for response
                except:
                    print(sys.exc_info()[1])
            elif command == "quit" or command == "exit":
                sys.exit(0)
            elif command == "help":
                parser.print_usage()
            else:
                print("Unknown command: %s" % command)
                parser.print_usage()

    except (fix.ConfigError, fix.RuntimeError) as e:
        print(e)

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='FIX Client')
    parser.add_argument('config_file', type=str, help='Name of configuration file')
    args = parser.parse_args()
    main(args.config_file)
