import quandl
import datetime
import json
import numpy as np
import pandas as pd
import os
from scipy.optimize import minimize
from Robinhood import Order
from Robinhood import WatchList
from Robinhood import Robinhood
from threading import Thread
from threading import Lock



class Portfolio:
    def __init__(
        self,
        trader = None,
        name = None,
        iniFund = None,
        load_from = None,
        cancel_count = np.inf
    ):
        """
        create portfolio or load from save
        trader (Robinhood): robinhood account trader
        name (str): name of this portfolio
        iniFund (float|None): initial buying power for this portfolio
        load_from (str|None): address to save information
        """
        assert trader is not None
        assert name is not None
        self.name = name
        self.trader = trader
        self.bp = iniFund
        self.confirm_signal = True
        self.threads = []
        if iniFund == None or iniFund >= float(trader.get_account()['margin_balances']['unallocated_margin_cash'])*0.7:
            self.bp = float(trader.get_account()['margin_balances']['unallocated_margin_cash'])*0.7
            
            
        self.trading_record = pd.DataFrame(columns = ["SIDE","SCODE","PRICE","AMOUNT","ORDER_TYPE"])
        self.trading_record_lock = Lock()
        
        self.portfolio_record = pd.DataFrame(columns = ['AVG_COST','SHARES'])
        self.portfolio_record_lock = Lock()
        
        self.queue = []
        self.queue_lock = Lock()
        
        self.time_zone = str(datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo)
        
        self.log = []
        self.log_lock = Lock()
        
        self.cancel_count = cancel_count
        if load_from is not None:
            self.load(savdir = load_from)

    def add_trading_record(self,*record):
        assert len(record) == 5
        self.trading_record_lock.acquire()
        self.trading_record.loc[self.get_time()] = record
        self.trading_record_lock.release()

    def get_last_price(self):
        """
        get last trading price for any asset in this portfolio
        """
        self.portfolio_record_lock.acquire()
        res = np.array(
            trader.last_trade_price(','.join(self.portfolio_record.index))
        )[:,0].astype(np.float32)
        self.portfolio_record_lock.release()
        return res
    
    def get_time(self):
        """
        get current time
        """
        return pd.datetime.now()
    
    def get_market_value(self):
        """
        get market value of current portfolio
        """
        self.portfolio_record_lock.acquire()
        res = np.dot(
            self.get_last_price(),
            self.portfolio_record["SHARES"].values
        )+self.bp
        self.portfolio_record_lock.release()
        return res
    
    def market_buy(self,scode,n,force_buy = False,time_in_force = 'gfd'):
        """
        buy stock with market order
        
        scode (str): symbol of stock
        n (int): shares to buy
        force_buy (bool): allow using back up buying power(exception when there isnt any) to buy
        time_in_force (str): gfd ,gtc ,ioc ,fok or opg
        """
        def market_buy_worker():
            if self.bp < float(self.trader.last_trade_price(scode)[0][0])*n*1.005 and not force_buy:
                self.log_lock.acquire()
                self.log.append(
                    "{}: no enough buying power for this portfolio to buy {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return 
            instrument = self.trader.instruments(scode)[0]
            order = self.trader.place_market_buy_order(instrument,n,time_in_force=time_in_force)
            if order is None:
                self.log_lock.acquire()
                self.log.append(
                    "{}: fail to place market buy order {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.queue_lock.acquire()
            self.queue.append([scode,order,0])
            self.queue_lock.release()
        t = Thread(target = market_buy_worker)
        self.threads.append(t)
        t.start()
        
    def market_sell(self,scode,n,time_in_force = 'gfd'):
        """
        sell stock with market order
        
        scode (str): symbol of stock
        n (int): shares to sell
        time_in_force (str): gfd ,gtc ,ioc ,fok or opg
        """
        def market_sell_worker():
            assert scode in self.portfolio_record.index
            self.portfolio_record_lock.acquire()
            if self.portfolio_record.loc[scode]["SHARES"] < n:
                self.portfolio_record_lock.release()
                self.log_lock.acquire()
                self.log.append(
                    "{}: no enough shares for this portfolio to sell {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.portfolio_record_lock.release()
            instrument = self.trader.instruments(scode)[0]
            order = self.trader.place_market_sell_order(instrument,n,time_in_force = time_in_force)
            if order.order is None:
                self.log_lock.acquire()
                self.log.append(
                    "{}: fail to place market sell order {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.queue_lock.acquire()
            self.queue.append([scode,order,0])
            self.queue_lock.release()
        t = Thread(target = market_sell_worker)
        self.threads.append(t)
        t.start()
    
    def stop_loss_buy(self,scode,stop_price,n,force_buy = False,time_in_force = 'gtc'):
        """
        buy stock with stop order
        
        scode (str): symbol of stock to buy
        stop_price (float): stop_price
        force_buy (bool): allow buying with buck up buying power
        time_in_force (str): gfd ,gtc ,ioc ,fok or opg
        """
        def stop_buy_worker():
            if self.bp < float(self.trader.last_trade_price(scode)[0][0])*n*1.005 and not force_buy:
                self.log_lock.acquire()
                self.log.append(
                    "{}: no enough buying power for this portfolio to buy {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return 
            instrument = self.trader.instruments(scode)[0]
            order = self.trader.place_stop_loss_buy_order(
                instrument,
                n,
                stop_price = stop_price,
                time_in_force = time_in_force
            )
            if order is None:
                self.log_lock.acquire()
                self.log.append(
                    "{}: fail to place stop loss buy order {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.queue_lock.acquire()
            self.queue.append([scode,order,0])
            self.queue_lock.release()
        t = Thread(target = stop_buy_worker)
        self.threads.append(t)
        t.start()
    def stop_loss_sell(self,scode,stop_price,n,time_in_force = 'gtc'):
        """
        sell stock with stop order
        
        scode (str): symbol of stock
        n (int): shares to sell
        time_in_force (str): gfd ,gtc ,ioc ,fok or opg
        """
        def stop_sell_worker():
            assert scode in self.portfolio_record.index
            self.portfolio_record_lock.acquire()
            if self.portfolio_record.loc[scode]["SHARES"] < n:
                self.portfolio_record_lock.release()
                self.log_lock.acquire()
                self.log.append(
                    "{}: no enough shares for this portfolio to sell {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.portfolio_record_lock.release()
            instrument = self.trader.instruments(scode)[0]
            order = self.trader.place_stop_loss_sell_order(
                instrument,
                n,
                stop_price = stop_price,
                time_in_force = time_in_force
            )
            if order.order is None:
                self.log_lock.acquire()
                self.log.append(
                    "{}: fail to place stop loss sell order {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.queue_lock.acquire()
            self.queue.append([scode,order,0])
            self.queue_lock.release()
        t = Thread(target = stop_sell_worker)
        self.threads.append(t)
        t.start()
        

    def limit_buy(self,scode,price,n,force_buy = False,time_in_force = 'gtc'):
        """
        buy stock with limit order
        
        scode (str): symbol of stock
        n (int): shares to sell
        time_in_force (str): gfd ,gtc ,ioc ,fok or opg
        """
        def limit_buy_worker():
            if self.bp < float(self.trader.last_trade_price(scode)[0][0])*n*1.005 and not force_buy:
                self.log_lock.acquire()
                self.log.append(
                    "{}: no enough buying power for this portfolio to buy {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return 
            instrument = self.trader.instruments(scode)[0]
            order = self.trader.place_limit_buy_order(
                instrument,
                n,
                price = price,
                time_in_force = time_in_force
            )
            if order is None:
                self.log_lock.acquire()
                self.log.append(
                    "{}: fail to place limit buy order {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.queue_lock.acquire()
            self.queue.append([scode,order,0])
            self.queue_lock.release()
        t = Thread(target = limit_buy_worker)
        self.threads.append(t)
        t.start()
        
    def limit_sell(self,scode,price,n,time_in_force = 'gtc'):
        """
        sell stock with limit order
        
        scode (str): symbol of stock
        n (int): shares to sell
        time_in_force (str): gfd ,gtc ,ioc ,fok or opg
        """
        def limit_sell_worker():
            assert scode in self.portfolio_record.index
            self.portfolio_record_lock.acquire()
            if self.portfolio_record.loc[scode]["SHARES"] < n:
                self.portfolio_record_lock.release()
                self.log_lock.acquire()
                self.log.append(
                    "{}: no enough shares for this portfolio to sell {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.portfolio_record_lock.release()
            instrument = self.trader.instruments(scode)[0]
            order = self.trader.place_limit_sell_order(
                instrument,
                n,
                price = price,
                time_in_force = time_in_force
            )
            if order.order is None:
                self.log_lock.acquire()
                self.log.append(
                    "{}: fail to place limit sell order {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.queue_lock.acquire()
            self.queue.append([scode,order,0])
            self.queue_lock.release()
        t = Thread(target = limit_sell_worker)
        self.threads.append(t)
        t.start()        
        
        
    def stop_limit_buy(self,scode,stop_price,n,force_buy = False,time_in_force = 'gtc'):
        """
        buy stock with stop limit order
        
        scode (str): symbol of stock to buy
        stop_price (float): stop_price
        force_buy (bool): allow buying with buck up buying power
        time_in_force (str): gfd ,gtc ,ioc ,fok or opg
        """
        def stop_limit_buy_worker():
            if self.bp < float(self.trader.last_trade_price(scode)[0][0])*n*1.005 and not force_buy:
                self.log_lock.acquire()
                self.log.append(
                    "{}: no enough buying power for this portfolio to buy {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return 
            instrument = self.trader.instruments(scode)[0]
            order = self.trader.place_stop_limit_buy_order(
                instrument,
                n,
                stop_price = stop_price,
                time_in_force = time_in_force
            )
            if order is None:
                self.log_lock.acquire()
                self.log.append(
                    "{}: fail to place stop loss buy order {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.queue_lock.acquire()
            self.queue.append([scode,order,0])
            self.queue_lock.release()
        t = Thread(target = stop_limit_buy_worker)
        self.threads.append(t)
        t.start()
    def stop_limit_sell(self,scode,stop_price,n,time_in_force = 'gtc'):
        """
        sell stock with stop limit order
        
        scode (str): symbol of stock
        n (int): shares to sell
        time_in_force (str): gfd ,gtc ,ioc ,fok or opg
        """
        def stop_limit_sell_worker():
            assert scode in self.portfolio_record.index
            self.portfolio_record_lock.acquire()
            if self.portfolio_record.loc[scode]["SHARES"] < n:
                self.portfolio_record_lock.release()
                self.log_lock.acquire()
                self.log.append(
                    "{}: no enough shares for this portfolio to sell {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.portfolio_record_lock.release()
            instrument = self.trader.instruments(scode)[0]
            order = self.trader.place_stop_limit_sell_order(
                instrument,
                n,
                stop_price = stop_price,
                time_in_force = time_in_force
            )
            if order.order is None:
                self.log_lock.acquire()
                self.log.append(
                    "{}: fail to place stop limit sell order {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.queue_lock.acquire()
            self.queue.append([scode,order,0])
            self.queue_lock.release()
        t = Thread(target = stop_limit_sell_worker)
        self.threads.append(t)
        t.start()
        
        

    def confirm_order(self,loop = False,gap_time = 5):
        """
        check whether submitted orders had been executed
        
        loop (bool): confirm once or keep on comfirming until signal received
        gap_time (float|int): pause between two confirms, in sec
        """
        gap_time = float(gap_time)
        if not self.confirm_signal:
            self.confirm_signal = True
        assert gap_time > 0
        def confirm_worker():
            if loop:
                self.log_lock.acquire()
                self.log.append("{}: confirm, start".format(self.get_time()))
                self.log_lock.release()
            while self.confirm_signal:
                sleep(gap_time)
                self.queue_lock.acquire()
                if not len(self.queue):
                    self.queue_lock.release()
                    continue
                scode,order,cc = self.queue.pop(0)
                self.queue_lock.release()
                d = order.check()
                if d['state'] in ['rejected','cancelled']:
                    self.log_lock.acquire()
                    self.log.append(
                        "{}: order ({},{} {} {} {}) {} for unknown reason".format(
                            self.get_time(),
                            scode,
                            d['quantity'],
                            d['trigger'],
                            d['type'],
                            d['side'],
                            d['state']
                        )
                    )
                    self.log_lock.release()
                    continue

                if not len(d['executions']):
                    self.queue_lock.acquire()
                    if cc >= self.cancel_count:
                        order.cancel()
                    else:
                        self.queue.append([scode,order,cc+1])
                    self.queue_lock.release()
                    continue

                ex_amount = float(d['executions'][0]['quantity'])
                ex_price = float(d['executions'][0]['price'])
                ex_side = d['side']

                if ex_side == 'sell':
                    ex_amount = - ex_amount

                self.trading_record_lock.acquire()
                self.trading_record.loc[self.get_time()] = [ex_side,scode,ex_price,abs(ex_amount),d['type']]
                self.trading_record_lock.release()

                self.portfolio_record_lock.acquire()
                if scode not in self.portfolio_record.index:
                    hold_amount = 0
                    avg_cost = 0
                else:
                    hold_amount = self.portfolio_record.loc[scode]['SHARES']
                    avg_cost = self.portfolio_record.loc[scode]['AVG_COST']

                total_cost = hold_amount*avg_cost + ex_price*ex_amount
                neo_shares = hold_amount + ex_amount
                self.bp = self.bp - total_cost
                if neo_shares == 0:
                    self.portfolio_record.drop(scode)
                    self.portfolio_record_lock.release()
                    continue

                neo_avg_cost = total_cost/neo_shares
                self.portfolio_record.loc[scode] = [neo_avg_cost,neo_shares]
                self.portfolio_record_lock.release()
                if not loop:
                    break
            if loop:
                self.log_lock.acquire()
                self.log.append("{}: confirm, end".format(self.get_time()))
        t = Thread(target = confirm_worker)
        t.start()

    def stop_confirm(self):
        self.confirm_signal = False

    def transfer_shares(self,oth = None,scode = None,amount = None,direction = 'to'):
        """
        transfer shares from one portfolio to another
        
        oth (Portfolio): another portfolio that shares the same trader as this one
        scode (str): symbol of stock to be transfered
        amount (int): shares of stock to be transfered
        direction (str): the direction of the transfer
        """
        assert oth.trader == self.trader
        assert scode is not None
        assert int(amount) > 0
        assert direction in ['from','to']
        amount = int(amount)
        if direction == 'from':
            oth.portfolio_record_lock.acquire()
            if (oth.portfolio_record.loc[scode]["SHARES"] < amount):
                oth.portfolio_record_lock.release()
                self.log_lock.acquire()
                self.log.append(
                    "{}: target portfolio doesnt have enough shares to transfer ({},{})".format(self.get_time(),scode,amount)
                )
                self.log_lock.release()
                return
            oth.portfolio_record.loc[scode]["SHARES"] -= amount
            transfer_price = oth.portfolio_record.loc[scode]["AVG_COST"]
            if oth.portfolio_record.loc[scode]["SHARES"] == 0:
                oth.portfolio_record = oth.portfolio_record.drop(scode)
            oth.portfolio_record_lock.release()
            
            self.portfolio_record_lock.acquire()
            if scode not in self.portfolio_record.index:
                original_avg_cost = 0
                original_hold = 0
            else:
                original_avg_cost = self.portfolio_record.loc[scode]["AVG_COST"]
                original_hold = self.portfolio_record.loc[scode]["SHARES"]
            neo_avg_cost = (original_avg_cost*original_hold + amount*transfer_price)/(original_hold+amount)
            self.portfolio_record.loc[scode] = [neo_avg_cost,original_hold+amount]
            self.portfolio_record_lock.release()
            self.add_trading_record("None",scode,transfer_price,amount,"transfer in")
            oth.add_trading_record("None",scode,transfer_price,amount,"transfer out")
        if direction == 'to':
            oth.transfer_shares(self,scode,amount,direction = 'from')
            
    def transfer_buying_power(self,oth = None,amount = None,direction = 'to'):
        """
        transfer buying power from one portfolio to another
        oth (Portfolio): the other portfolio that shares the same trader as this one
        amount (float): the amount of money(in USD) to be transfered
        direction (str): the direction of this transfer
        """
        assert self.trader == oth.trader
        assert amount > 0
        assert direction in ['from','to']
        if direction == 'from':
            if oth.bp < amount:
                self.log_lock.acquire()
                self.log.append(
                    "{}: target portfolio doesnt have enough buying power to transfer ({})".format(self.get_time(),amount)
                )
                self.log_lock.release()
                return 
            oth.bp -= amount
            self.bp += amount
        if direction == 'to':
            oth.transfer_buying_power(self,amount,'from')
            
            
    def cancel_all_orders_in_queue(self):
        """
        cancel all orders in the queue that havent been executed yet
        """
        self.queue_lock.acquire()
        while len(self.queue):
            scode,order = self.queue.pop()
            order.cancel()
        self.queue_lock.release()
        
    def add_shares_from_pool(self,scode = None,n = None):
        """
        add share from account equity to portfolio
        currently, one should make sure the sum of # of shares in each portfolio is less than the 
        total holding shares manually when using it. A portfolio manager class will be created 
        to handle this later
        
        scode (str): symbol for the stock to be added
        n (int|float): amount to be added
        """
        owned = self.trader.securities_owned()['results']
        target_ins = self.trader.instruments(scode)[0]["url"]
        d = None
        for ins in owned:
            if ins['instrument'] == target_ins:
                d = ins
                break
        if d is None:
            self.log_lock.acquire()
            self.log.append(
                "{}: dont have {} in your pool".format(self.get_time(),scode)
            )
            self.log_lock.release()
            return
        owned_shares = float(d['quantity'])
        if n > owned_shares:
            self.log_lock.acquire()
            self.log.append(
                "{}: dont have enough shares of {} in you pool".format(self.get_time(),scode)
            )
            self.log_lock.release()
            return
        n_avg_cost = float(d['average_buy_price'])
        self.portfolio_record_lock.acquire()
        if scode not in self.portfolio_record:
            avg_cost = 0
            shares = 0
        else:
            avg_cost = self.portfolio_record.loc[scode]['AVG_COST']
            shares = self.portfolio_record.loc[scode]['SHARES']
        neo_shares = shares + n
        neo_cost = (avg_cost*shares + n_avg_cost*n)/neo_shares
        self.portfolio_record.loc[scode] = [neo_cost,neo_shares]
        self.portfolio_record_lock.release()
        
    def set_bp_HARD(self,bp):
        """
        force buying power to be bp, by default, the maximum buying power of a portforlio cannot exceed 70%
        of total buying power in case the buying order thread processed before a concurrent selling order.
        when a market buying order goes with a market selling order at the same time, set the force_buy parameter
        of market_buy if the buying power for buying order comes from the selling order's return.
        
        bp (float): buying power
        """
        total_bp = float(self.trader.get_account()['margin_balances']['unallocated_margin_cash'])
        self.bp = min(bp,total_bp)
        
    def is_market_open(self):
        """
        check if a market is open,
        
        have no clue what timezone did robinhood use for market hour,
        official api says it is US/Eastern, but the market hour returned from api is obviously not US/Eastern
        
        so to check the current time with the timezone robinhood used,
        a buy order will be placed to see the created time returned by api
        
        the placed order will normally be rejected or this method will cancel it immediately.
        
        shoud not call this method too frequently
        """
        u = self.trader.place_stop_limit_buy_order(
            instrument = self.trader.instruments('BAC')[0],
            quantity=1,
            stop_price=0.01
        )
        now = datetime.datetime.strptime(u.check()['created_at'],"%Y-%m-%dT%H:%M:%S.%fZ")
        u.cancel()
        y = now.year
        m = now.month
        d = now.day
        info = self.trader.session.get('https://api.robinhood.com/markets/XNAS/hours/{}-{}-{}/'.format(y,m,d)).json()
        if not info['is_open']:
            return False
        opens_at = datetime.datetime.strptime(info['opens_at'],"%Y-%m-%dT%H:%M:%SZ")
        closes_at = datetime.datetime.strptime(info['closes_at'],"%Y-%m-%dT%H:%M:%SZ")
        return now<=closes_at and now >=opens_at
        
    def shares_owned(self,scode):
        """
        get number of shares of a stock in this portfolio
        
        scode (str): symbol of stock
        """
        self.portfolio_record_lock.acquire()
        if scode not in self.portfolio_record.index:
            self.portfolio_record_lock.release()
            return 0
        res = self.portfolio_record.loc[scode]["SHARES"]
        self.portfolio_record_lock.release()
        return res
             
    def save(self,savdir = None,root_name = ''):
        """
        save portfolio to files
        """
        for t in self.threads:
            t.join()
        if savdir is None:
            savdir = self.name
        
        fdir = root_name+savdir+'/'
        if not os.path.exists(fdir):
            os.mkdir(fdir)
        self.trading_record.to_csv(fdir+"trading.csv")
        self.portfolio_record.to_csv(fdir+"portfolio.csv")
        pd.DataFrame([[self.bp]]).to_csv(fdir+"bp")
        with open(fdir+"log{}.log".format(self.get_time()).replace(' ','').replace(':','.'),'w') as f:
            for log in self.log:
                f.write(log+"\n")
                
    def load(self,savdir = None,root_name = ''):
        """
        load portfolio info from files
        """
        if savdir is None:
            savdir = self.name
        fdir = root_name + savdir + '/'
        assert os.path.exists(fdir)
        self.trading_record = pd.DataFrame.from_csv(fdir+"trading.csv")
        self.portfolio_record = pd.DataFrame.from_csv(fdir+"portfolio.csv")
        self.bp = pd.DataFrame.from_csv(fdir+"bp").values[0][0]
        
        
                
