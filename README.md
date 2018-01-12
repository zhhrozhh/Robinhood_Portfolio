# Robinhood Portflio Manager
Tools to create and manage separated portfolios in the same robinhood trading account.

One can apply different trading algorithms on different portfolios with a single account, portfolios wont interfere each other, wights, risks and returns of each portfolio can be calculated separately.

orders executed concurrently, so please make sure there are extra buying power that not belongs to any portoflio. otherwise you need to make buying orders waits for selling orders' completion manaully.

## Current Features 
- market buy orders(`Portfolio.market_buy`)
- market sell order(`Portfolio.market_sell`)
- limit buy/sell orders(`Portfolio.limit_buy`)
- stop buy/sell orders(`Portfolio.stop_loss_buy`)
- stop limit buy/sell orders(`Portfolio.stop_limit_buy`)
- get market value of portfolio(`Portfolio.get_market_value`)
- confirm orders in queue(`Portfolio.confirm_order`)
- stop confirm orders(`Portfolio.stop_confirm`)
- transfer equities between portfolios(`Portfolio.transfer_shares`)
- transfer buying power between portfolios(`Portfolio.transfer_buying_power`)
- cancel all orders havent been executed yet(`Portfolio.cancel_all_orders_in_queue`)
- add shares you owned to portfolio(`Portfolio.add_shares_from_pool`)
- save portfolio info to hard disk(`Portfolio.save`)
- load portfolio into memory('Portfolio.load')
- is market open now(`Portfolio.is_market_open`)
- More coming soon

### TODO:
    add PortfolioManager class to manage multiple portfolios
    add sample trading algorithm demos

### How To Install:
    install Robinhood from https://github.com/zhhrozhh/Robinhood first
    pip3 install .
    

### How to Use 
    trader = Robinhood(username,password)
    name = 'Default'
    p = Portfolio(trader,name,load_from = 'path to save')
    p.confirm_orders(loop = True,gap_time = 1)
    while True:
        """your trading algorithms goes here"""
        if buy_condition:
            p.market_buy(stock,amount)
        if sell_condition:
            p.market_sell(stock,amount)



------------------

# Related

* [robinhood-python framework](https://github.com/zhhrozhh/Robinhood) - robinhood api package used for this project
