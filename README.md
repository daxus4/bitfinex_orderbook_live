This code is made by copying the repository https://github.com/bitfinexcom/bitfinex-api-py and modifying
the files that allowed to be able to download the orderbook updates in live through websocket.

This code is not tested and the author does not take the responsibility for any possible error.

To see the original documentation and license, please visit the link mentioned.

The file enviroment.yml contains the conda environment used to run the websockets files.

The file to download the orderbook live data is examples/websocket/public/order_book.py. Then convert them using the convert_ob_updates_to_timed_ob.ipynb