###############################################################################
# This is minimalistic sample that illustrates how to subscribe for market data
###############################################################################
import sys

from fix_session import FixSession
from fix_session import MarketDataRequest

if __name__=='__main__':
    if len(sys.argv) < 2:
        print("Please specify config file parameter")
        exit(1)

    config_file = sys.argv[1]

    session = FixSession(config_file)
    session.start()

    request = MarketDataRequest()
    request.set_symbols(["BTCUSD"])
    session.submit(request)

    # wait for user to type something then stop session
    command = input()
    session.stop()

