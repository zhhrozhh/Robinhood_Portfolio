from Robinhood import Robinhood
from .Portfolio import Portfolio
from .SIconverter import SIconverter

import numpy as np
class PortfolioMgr:
    def __init__(
        self,
        robin_un = None,
        robin_pd = None,
        name = None,
        load_from = None
    ):
        assert robin_un is not None
        assert robin_pd is not None
        assert name is not None
        self.trader = Robinhood()
        self.trader.login(robin_un,robin_pd)
        self.name = name
        self.converter = SIconverter(trader = self.trader)
        self.unassigned_bp = float(self.trader.get_account()['margin_balances']['unallocated_margin_cash'])
        self.unassigned_shares = {
            self.converter(d['instrument']):int(float(d['quantity'])) for d in self.trader.securities_owned()['results']
        }
        self.portfolios = {}
        
        
    def add_portfolio(
        self,
        name = None,
        ini_bp = 0,
        load = None,
        cancel_count = np.inf
    ):
        assert name is not None
        assert ini_bp < self.unassigned_bp
        self.portfolios[name] = Portfolio(
            trader = self.trader,
            name = name,
            iniFund = ini_bp,
            cancel_count = np.inf
        )
        self.unassigned_bp -= ini_bp
        
        
    def update_allocatable_buying_power(self):
        allocated = 0
        for k,p in self.portfolios.items():
            allocated += p.bp
        self.unassigned_bp = self.get_bp_owned() - allocated
    
    def update_allocatable_shares(self):
        owned_shares = self.get_securities_owned()
        for k,p in self.portfolios.items():
            p.portfolio_record_lock.acquire()
            for scode in p.portfolio_record.index:
                owned_shares[scode] -= p.portfolio_record.loc[scode]["SHARES"]
            p.portfolio_record_lock.release()
        self.unassigned_shares = owned_shares
    
    def get_securities_owned(self):
        return {
            self.converter(d['instrument']):int(float(d['quantity'])) for d in self.trader.securities_owned()['results']
        }
    
    def get_bp_owned(self):
        return float(self.trader.get_account()['margin_balances']['unallocated_margin_cash'])
    
    def add_bp_to(self,name,amount):
        assert name in self.portfolios
        self.update_allocatable_buying_power()
        assert self.unassigned_bp > amount
        self.portfolios[name].bp += amount
        self.unassigned_bp -= amount
        self.portfolios[name].add_trading_record("None","None",amount,1,"add bp")
    
    def add_shares_to(self,name,scode,amount):
        assert name in self.portfolios
        self.update_allocatable_shares()
        amount = int(amount)
        assert self.unassigned_shares[scode] > amount
        self.portfolios[name].add_shares_from_pool(scode = scode,n = amount)
        self.unassigned_shares[scode] -= amount
        self.portfolios[name].add_trading_record("None",scode,"None",amount,"add share")
        
    
    def draw_bp_from(self,name,amount):
        assert name in self.portfolios
        assert self.portfolios[name].bp >= amount
        self.portfolios[name].bp -= amount
        self.unassigned_bp += amount
        self.portfolios[name].add_trading_record("None","None",amount,1,"draw bp")
    
    def draw_shares_from(self,name,scode,amount):
        assert name in self.portfolios
        amount = int(amount)
        assert self.portfolios[name].shares_owned(scode) >= amount
        self.portfolios[name].portfolio_record_lock.acquire()
        self.portfolios[name].portfolio_record.loc[scode]["SHARES"] -= amount
        if self.portfolios[name].portfolio_record.loc[scode]["SHARES"] == 0:
            self.portfolios[name].portfolio_record = self.portfolios[name].portfolio_record.drop(scode)
        self.portfolios[name].portfolio_record_lock.release()
        self.unassigned_shares[scode] += amount
        self.portfolios[name].add_trading_record("None",scode,"None",amount,"draw share")
        
    
    def transfer_bp(self,from_name,to_name,amount):
        assert from_name in self.portfolios
        assert to_name in self.portfolios
        self.portfolios[from_name].transfer_buying_power(self.portfolios[to_name],amount)
        
        
        
    def transfer_shares(self,from_name,to_name,scode,amount):
        assert from_name in self.portfolios
        assert to_name in self.portfolios
        self.portfolios[from_name].transfer_shares(self.portfolios[to_name],scode,amount)
        