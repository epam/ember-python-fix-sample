##############################################################################
# This is minimalistic sample that illustrates how to submit FIX orders
##############################################################################
import time
import sys
from fix_session import FixSession

if __name__=='__main__':
    if len(sys.argv) < 2:
        print("Please specify config file parameter")
        exit(1)

    config_file = sys.argv[1]

    session = FixSession(config_file)
    session.start()

    # LIMIT BUY
    session.submit_buy_order("AUTOCERT", "BTCUSD", 1.0, 40000.0, "GOLD", {8076: "FILL"})

    # MARKET SELL
    session.submit_sell_order("AUTOCERT", "BTCUSD", 1.0, None, "GOLD", {8076: "FILL"})

    time.sleep(0.5) # wait for events
    session.stop()

