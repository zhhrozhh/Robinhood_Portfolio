from Robinhood import Robinhood
from .Portfolio import Portfolio
from .SIconverter import SIconverter
from time import sleep
import numpy as np
from threading import Thread
from threading import Condition
class PortfolioMgr:
    def __init__(
        self,
        robin_un = None,
        robin_pd = None,
        name = None,
        load_from = None
    ):
        """
        Manager for multiple portfolios in the same account

        robin_un (str): username of robinhood account
        robin_pd (str): password of robinhood account
        name (str): name of the manager
        load_from (str): path to the saving file
        """
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
        self.regisiter = {}
        self.working_now = True
        self.working_cv = Condition()
        
        self.check_work_v = True
        self.check_work_cv = Condition()
        
    def add_portfolio(
        self,
        name = None,
        ini_bp = 0,
        load = None,
        cancel_count = np.inf
    ):
        """
        create a portfolio with the manager

        name (str): name of the portfolio
        ini_bp (float): initial buying power for this portfolio
        load (str): path to the saving file of this portfolio
        cancel_count (int|np.inf) used for specific trading algorithm, 
            order will be canceled if it can not be executed for cancel_count times
        """
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
        """
        update the unassigned_bp variable. should never be used unless the user transfers money between bank and robinhood account.
        """
        allocated = 0
        for k,p in self.portfolios.items():
            allocated += p.bp
        self.unassigned_bp = self.get_bp_owned() - allocated
    
    def update_allocatable_shares(self):
        """
        update the unassigned_shares variable. should never be used unless the user sell/buy shares without using this mgr
        """
        owned_shares = self.get_securities_owned()
        for k,p in self.portfolios.items():
            p.portfolio_record_lock.acquire()
            for scode in p.portfolio_record.index:
                owned_shares[scode] -= p.portfolio_record.loc[scode]["SHARES"]
            p.portfolio_record_lock.release()
        self.unassigned_shares = owned_shares
    
    def get_securities_owned(self):
        """
        get shares owned by the user
        """
        return {
            self.converter(d['instrument']):int(float(d['quantity'])) for d in self.trader.securities_owned()['results']
        }
    
    def get_bp_owned(self):
        """
        get buying power owned by the user
        """
        return float(self.trader.get_account()['margin_balances']['unallocated_margin_cash'])
    
    def add_bp_to(self,name,amount):
        """
        add buying power from mgr to portfolio

        name (str): the name of the portfolio
        amount (float): money in USD to be added
        """
        assert name in self.portfolios
        self.update_allocatable_buying_power()
        assert self.unassigned_bp > amount
        self.portfolios[name].bp += amount
        self.unassigned_bp -= amount
        self.portfolios[name].add_trading_record("None","None",amount,1,"add bp")
    
    def add_shares_to(self,name,scode,amount):
        """
        add shares from mgr to portfolio

        name (str): the name op the portfolio
        scode (str): symbol of the stock
        amount (int): number of shares
        """
        assert name in self.portfolios
        self.update_allocatable_shares()
        amount = int(amount)
        assert self.unassigned_shares[scode] > amount
        self.portfolios[name].add_shares_from_pool(scode = scode,n = amount)
        self.unassigned_shares[scode] -= amount
        self.portfolios[name].add_trading_record("None",scode,"None",amount,"add share")
        
    
    def draw_bp_from(self,name,amount):
        """
        draw bp from a portfolio to mgr

        name (str): name of the portfolio
        amount (float): money in USD to be draw
        """
        assert name in self.portfolios
        assert self.portfolios[name].bp >= amount
        self.portfolios[name].bp -= amount
        self.unassigned_bp += amount
        self.portfolios[name].add_trading_record("None","None",amount,1,"draw bp")
    
    def draw_shares_from(self,name,scode,amount):
        """
        draw shares from a portfolio to mgr

        name (str): name of the portfolio
        scode (str): symbol of the stock
        amount (int): number of shares
        """
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
        """
        transfer buying power between two portfolios
        
        from_name (str): name of the portfolio to send the buying power
        to_name (str): name of the portfolio to receive the buying power
        """
        assert from_name in self.portfolios
        assert to_name in self.portfolios
        self.portfolios[from_name].transfer_buying_power(self.portfolios[to_name],amount)
        
        
        
    def transfer_shares(self,from_name,to_name,scode,amount):
        """
        transfer shares between two portfolios
        
        from_name (str): name of the portfolio to send shares
        to_name (str): name of the portfolio to receive shares
        """
        assert from_name in self.portfolios
        assert to_name in self.portfolios
        self.portfolios[from_name].transfer_shares(self.portfolios[to_name],scode,amount)

    def schedule(
        self,
        algo = None,
        method = None,
        portfolio_name = None,
        freq = None,
        misc = None
        ):
        assert portfolio_name not in self.regisiter
        assert algo is not None
        assert method is not None
        assert freq is not None
        p = self.portfolios[portfolio_name]
        if "cancel_count" in misc:
            p.cancel_count = misc["cancel_count"]
        def worker():
            p.confirm_order(loop = True)
            while self.working_now:
                try:
                    algo.__getattribute__(method)(
                        self,
                        pname = portfolio_name,
                        args = {
                            "call_from_mgr" : True
                        },
                        misc = misc
                        )
                except AssertionError:
                    p.unlock_all()
                    p.log_lock.acquire()
                    p.log.append("{}: Error Operation During Trading".format(Portfolio.get_now()))
                    p.log_lock.release()
                self.working_cv.acquire()
                self.working_cv.wait(freq*60)
                self.working_cv.release()
            p.unlock_all()
            p.stop_confirm()
            p.cancel_all_orders_in_queue()
            self.regisiter[portfolio_name][0] = 'STOPED'
        
        self.regisiter[portfolio_name] = ["PENDING",worker]
        if self.working_now:
            self.regisiter[portfolio_name] = ["STARTED",worker]
            t = Thread(target = worker)
            t.start()

    def cnow(self):
        def worker():
            while self.check_work_v:
                check_work()
                self.check_work_cv.acquire()
                self.check_work_cv.wait(900)
                self.check_work_cv.release()
                
    def dnow(self):
        self.check_work_v = False
        self.check_work_cv.acquire()
        self.check_work_cv.notify()
        self.check_work_cv.release()


    def check_work(self):
        if not len(self.portfolios):
            self.working_now = False
            self.working_cv.acquire()
            self.working_cv.notifyAll()
            self.working_cv.release()
        if list(self.portfolios.values())[0].is_market_open():
            self.working_now = True
            for key in self.regisiter:
                s,w = self.regisiter[key]
                if s != 'STARTED':
                    t = Thread(target = w)
                    t.start()
                    self.regisiter[key][0] = 'STARTED'
        else:
            self.working_now = False
            self.working_cv.acquire()
            self.working_cv.notifyAll()
            self.working_cv.release()

    def save(self,sav = None):
        if sav is None:
            sav = self.name
        sav = sav + '/'
        for k,p in self.portfolios.items():
            p.save(root_name = sav)

    def load(self,sav = None):
        if sav is None:
            sav = self.name
        sav = sav + '/'
        for k,p in self.portfolios.items():
            p.load(root_name = sav)
        