# Robinhood Portflio Manager
Tools to create and manage separated portfolios in the same robinhood trading account.

One can apply different trading algorithms on different portfolios with a single account, portfolios wont interfere each other, wights, risks and returns of each portfolio can be calculated separately.

orders executed concurrently, so please make sure there are extra buying power that not belongs to any portoflio. otherwise you need to make buying orders waits for selling orders' completion manaully.

## Current Features 
- market buy orders (`Portfolio.market_buy`)(`TESTED`)
- market sell order (`Portfolio.market_sell`)(`TESTED`)
- get market value of portfolio(`Portfolio.get_market_value`)(`TESTED`)
- confirm orders in queue(`Portfolio.confirm_order`)(`TESTED`)
- transfer equities between portfolios(`Portfolio.transfer_shares`)(`TESTED`)
- transfer buying power between portfolios(`Portfolio.transfer_buying_power`)(`TESTED`)
- cancel all orders havent been executed yet(`Portfolio.cancel_all_orders_in_queue`)(`TESTED`)
- add shares you owned to portfolio(`Portfolio.add_shares_from_pool`)(`TESTED`)
- save portfolio info to hard disk(`Portfolio.save`)(`TESTED`)
- load portfolio into memory('Portfolio.load')(`TESTED`)
- More coming soon

### How To Install:
    TODO
    

### How to Use 
    TODO



------------------

# Related

* [robinhood-python framework](https://github.com/zhhrozhh/Robinhood) - python framework to use data from robinhood
