@echo off
:loop
C:/Users/Admin/miniconda3/envs/bitfinex_api/python.exe c:/Users/Admin/Desktop/phd/hawkes_coe/bitfinex_orderbook_live/examples/websocket/public/order_book.py
if %errorlevel% neq 0 (
    echo Script failed with error %errorlevel%. Restarting in 5 seconds...
    timeout /t 5
)
goto loop
