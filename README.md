# Robinhood Portflio Manager
Tools to create and manage separated portfolios in the same robinhood trading account.

One can apply different trading algorithms on different portfolios with a single account, portfolios wont interfere each other, wights, risks and returns of each portfolio can be calculated separately.

orders executed concurrently, so please make sure there are extra buying power that not belongs to any portoflio. otherwise you need to make buying orders waits for selling orders' completion manaully.

## Methods List 
- market buy orders(`Portfolio.market_buy`)
- market sell order(`Portfolio.market_sell`)
- limit buy/sell orders(`Portfolio.limit_buy`)
- stop buy/sell orders(`Portfolio.stop_loss_buy`)
- stop limit buy/sell orders(`Portfolio.stop_limit_buy`)
- get market value of portfolio(`Portfolio.get_market_value`)
- confirm orders in queue(`Portfolio.confirm_order`)
- stop confirm orders(`Portfolio.stop_confirm`)
- cancel all orders havent been executed yet(`Portfolio.cancel_all_orders_in_queue`)
- save portfolio info to hard disk(`Portfolio.save`)
- load portfolio into memory(`Portfolio.load`)
- is market open now(`Portfolio.is_market_open`)

- convert between instrument amd stock symbol(`SIconverter.__call__`)

- add buying power from mgr(`PortfolioMgr.add_bp_to`)
- add shares from mgr(`PortfolioMgr.add_shares_to`)
- transfer bp between portfolios(`PortfolioMgr.transfer_bp`)
- transfer shares between portfolios(`PortfolioMgr.transfer_shares`)

- More coming soon

### TODO:
    add sample trading algorithm demos

### How To Install:
    git clone git@github.com:zhhrozhh/Robinhood.git
    cd Robinhood*
    pip3 install.
    cd ..
    git clone git@github.com:zhhrozhh/Robinhood_Portfolio.git
    cd Robinhood_Portfolio*
    pip3 install .
    

### How to Use 
    from Portfolio import PortfolioMgr
    
    pmgr = PortfolioMgr("robinhood username","robinhood password","name for the manager")
    pmgr.add_portfolio("portfolio name",buying_power)
    pmgr.portfolios['portfolio name'].confirm_orders(loop = True,gap_time = 1)
    while True:
        """your trading algorithms goes here"""
        if buy_condition:
            pmgr.portfolios['portfolio name'].market_buy(stock,amount)
        if sell_condition:
            pmgr.portfolios['portfolio name'].market_sell(stock,amount)



------------------

# Related

* [robinhood-python framework](https://github.com/zhhrozhh/Robinhood) - robinhood api package used for this project
