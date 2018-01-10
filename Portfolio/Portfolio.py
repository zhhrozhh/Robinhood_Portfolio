import quandl
import datetime
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
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
        load_from = None
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
    
    def market_buy(self,scode,n,force_buy = False):
        """
        buy stock with market order
        
        scode (str): symbol of stock
        n (int): shares to buy
        force_buy(bool): allow using back up buying power(exception when there isnt any) to buy
        """
        def market_buy_worker():
            if self.bp < float(self.trader.last_trade_price(scode)[0][0])*n*1.05 and not force_buy:
                self.log_lock.acquire()
                self.log.append(
                    "{}: no enough buying power for this portfolio to buy {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return 
            instrument = self.trader.instruments(scode)[0]
            order = self.trader.place_buy_order(instrument,n)
            if order is None:
                self.log_lock.acquire()
                self.log.append(
                    "{}: fail to place market buy order {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
                return
            self.queue_lock.acquire()
            self.queue.append([scode,order])
            self.queue_lock.release()
        t = Thread(target = market_buy_worker)
        t.start()
        
    def market_sell(self,scode,n):
        """
        sell stock with market order
        
        scode (str): symbol of stock
        n (int): shares to sell
        """
        def market_sell_worker():
            if self.portfolio_record.loc[scode]["SHARES"] < n:
                self.log_lock.acquire()
                self.log.append(
                    "{}: no enough shares for this portfolio to sell {} shares of {}".format(self.now(),n,scode)
                )
                self.log_lock.release()
            instrument = self.trader.instruments(scode)[0]
            order = self.trader.place_sell_order(instrument,n)
            if order.order is None:
                self.log_lock.acquire()
                self.log.append(
                    "{}: fail to place market sell order {} shares of {}".format(self.now(),n,scode)
                )
                return
            self.queue_lock.acquire()
            self.queue.append([scode,order])
            self.queue_lock.release()
        t = Thread(target = market_sell_worker)
        t.start()
    
    def confirm_order(self):
        """
        check whether submitted orders had been executed
        """
        def confirm_worker():
            self.queue_lock.acquire()
            if not len(self.queue):
                self.queue_lock.release()
                return
            scode,order = *self.queue.pop(0)
            self.queue_lock.release()
            d = order.check()
            if not len(d['executions']):
                self.queue_lock.acquire()
                self.queue.append([scode,order])
                self.queue_lock.release()
                return
            
            ex_amount = d['executions']['quantity']
            ex_price = scode,d['executions']['price']
            ex_side = d['side']
            
            if ex_side == 'sell':
                ex_amount = - ex_amount
            
            self.trading_record_lock.acquire()
            self.trading_record.loc[d['executions']['timestamp']] = [ex_side,ex_price,ex_amount,d['type']]
            self.trade_record_lock.release()
        
            self.portfolio_record_lock.acquire()
            if scode not in self.portfolio_record.index:
                hold_amount = 0
                avg_cost = 0
            else:
                hold_amount = self.portfolio_record['SHARES']
                avg_cost = self.portfolio_record['AVG_COST']
            
            
            
            total_cost = hold_amount*avg_cost + ex_price*ex_amount
            neo_shares = hold_amount + ex_amount
            self.bp = self.bp - total_cost
            if neo_shares == 0:
                self.protfolio_record.drop(scode)
                self.protfolio_record_lock.release()
                return
            
            neo_avg_cost = total_cost/neo_shares
            self.protfolio_record.loc[scode] = [neo_avg_cost,neo_shares]
            self.protfolio_record_lock.release()
        t = Thread(target = confirm_worker)
        t.start()

            
            
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
            oth.protfolio_record_lock.acquire()
            if (oth.protfolio_record.loc[scode]["SHARES"] < amount):
                oth.protfolio_record_lock.release()
                self.log_lock.acquire()
                self.log.append(
                    "{}: target portfolio doesnt have enough shares to transfer ({},{})".format(self.now(),scode,amount)
                )
                self.log_lock.release()
                return
            oth.protfolio_record.loc[scode]["SHARES"] -= amount
            transfer_price = oth.protfolio_record.loc[scode]["AVG_COST"]
            if oth.protfolio_record.loc[scode]["SHARES"] == 0:
                oth.protfolio_record.pop(scode)
            oth.protfolio_record_lock.release()
            
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
        if direction == 'to':
            other.transfer(self,scode,amount,direction = 'from')
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
                    "{}: target portfolio doesnt have enough buying power to transfer ({})".format(self.now(),amount)
                )
                self.log_loc.release()
                return 
            oth.bp -= amount
            self.bp += amount
        if direction == 'to':
            other.transfer(self,amount,'from')
            