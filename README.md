# Python samlple for Ember FIX API

This sample explains how to run a simple Python client that sends trading orders to Deltix FIX Gateway. This sample uses  popular QuickFIX/Python library.

## **Pre-requisites**

* Install Python 3.7+ and pip:

```sh
sudo yum install python3-devel python3-wheel  
```
  
* Install [QuickFIX](https://pypi.org/project/quickfix/) Python library using pip command:  
  
```sh
pip3 install quickfix  
```
  
Windows users: if you have problems with this step simply get quickfix binaries [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#quickfix).  
  
* Setup Deltix FIX Gateway.
* Download sample [fix-client.py](https://github.com/epam/ember-python-fix-sample/blob/main/fix-client.py) and [fix-client.cfg](https://github.com/epam/ember-python-fix-sample/blob/main/fix-client.cfg) files to your work directory.

## **Configure**

Modify fix-client.cfg according to your Ember configuration as follows:

* Point SocketConnectHost and SocketConnectPort to your Deltix FIX Gateway,
* Make sure SenderCompID, TargetCompID, and SenderPassword to match the FIX Session you want to connect as.
* Update FileStorePath and FileLogPath if necessary.

## **Run**

To run the sample client, execute fix-client.py with fix-client.cfg as a parameter on Python 3.x:

```sh
python3 fix-client.py fix-client.cfg
```

If client is able to connect, it will show a message about successful login and then command prompt:

```
Session FIX.4.4:TCLIENT1->DELTIX successfully logged in
Received message: MessageType=News, Sender=DELTIX, HeadLine=Connector Status, Text=SIM:CONNECTED
-->
```

At this point you can enter commands to issue one or more BUY or SELL orders with specified time interval. The client will display any application messages (order events) coming back from the FIX server. To see supported commands and parameters type help:

```
--> help
usage: help | exit | {buy,sell} -s SYMBOL -q QUANTITY [-t {LIMIT,MARKET}] [-p PRICE] [-d DESTINATION] [-e EXCHANGE] [-n ORDER_COUNT] [-i INTERVAL]
```

The last two parameters ORDER_COUNT (1 by default) and INTERVAL (5 sec by default) are for issuing several orders with the interval in seconds between orders. For instance, command to issue 10 LIMIT BUY orders to SOR algorithm to buy 1 BTCUSD coin every 15 sec with limit price 8081 would look like this:

```
--> buy -s BTCUSD -q 1 -t LIMIT -p 8081 -d SOR -n 10 -i 15
```

In this example options set the following fix tags on order request:

```
-s – fix.Symbol
-t - fix.OrdType
-q - fix.OrderQty
-p - fix.Price
-d - fix.ExecBroker (ember destination, this could be simulator, matching engine, execution algo, or exchange connector)  
-e - fix.ExDestination (identifies exchange)
```

## **QuickFIX API**

QuickFIX provides quickfix.Application class that has notification methods called whenever client sends or receives messages from the FIX server. The custom client application is expected to extend this class and override its notification methods. See provided fix-client.py for an example.

For instance, to supply the server with the password during login we override toAdmin() method and add password to the header of FIX Logon message:

```python
def toAdmin(self, message, sessionID):
    msgType = fix.MsgType();
    message.getHeader().getField(msgType)
    if msgType.getValue() == fix.MsgType_Logon :
        message.getHeader().setField(fix.Password(self.sessionPwd))
    return
```

To handle FIX server execution report messages we override Application fromApp() method:

```python
def fromApp(self, message, sessionID):
    print("Received message: ", end='')
    print_message(message)
    return
```

To initialize client session, pass Application instance to SocketInitiator along with the config settings and then start it like this:

```python
settings = quickfix.SessionSettings(config_file)
store_factory = quickfix.FileStoreFactory(settings)
log_factory = quickfix.FileLogFactory(settings)
application = Application()
initiator = quickfix.SocketInitiator(application, store_factory, settings, log_factory)
initiator.start()
```

After the SocketInitiator is started and the session is initialized the client can send order requests using quickfix.Session.sendToTarget() method. Here is a sample code that sends a LIMIT BUY order to SIM algorithm:

```python
   trade = fix.Message()
   trade.getHeader().setField(fix.BeginString(fix.BeginString_FIX44))
   trade.getHeader().setField(fix.MsgType(fix.MsgType_NewOrderSingle))
   trade.setField(fix.ClOrdID("1121212"))
   trade.setField(fix.HandlInst(fix.HandlInst_MANUAL_ORDER_BEST_EXECUTION))
   trade.setField(fix.TimeInForce(fix.TimeInForce_DAY))
   trade.setField(fix.Symbol("BTCUSD"))
   trade.setField(fix.Side(fix.Side_BUY))
   trade.setField(fix.OrdType(fix.OrdType_LIMIT))
   trade.setField(fix.OrderQty(2))
   trade.setField(fix.Price(8081))
   trade.setField(fix.TransactTime())
   trade.setField(fix.ExecBroker("SIM"))
   fix.Session.sendToTarget(trade, self.sessionID)
```


