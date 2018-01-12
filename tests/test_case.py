from Robinhood import Robinhood
from Portfolio import PortfolioMgr
with open('robin_un.topse','r') as f:
    un = f.read()
with open('robin_pd.topse','r') as f:
    pd = f.read()
mgr = PortfolioMgr(un,pd,"Default")

total_bp = mgr.get_bp_owned()

mgr.add_portfolio(name = 'First',ini_bp = total_bp * 0.01)

assert abs(mgr.portfolios['First'].bp - total_bp * 0.01) < 1e-5

mgr.portfolios['First'].bp = total_bp*0.02

mgr.update_allocatable_buying_power()

assert abs(mgr.unassigned_bp - total_bp*0.98) < 1e-5

mgr.add_bp_to("First",total_bp*0.01)

assert abs(mgr.portfolios['First'].bp - total_bp*0.03)<1e-5
assert abs(mgr.unassigned_bp - total_bp*0.97)<1e-5
oss = mgr.get_securities_owned()
if not len(oss):
    raise Exception("No shares to test, please add at least one stock to your account")
scode = list(oss.keys())[0]
iniv = oss[scode]

mgr.add_shares_to("First",scode,1)
assert mgr.portfolios["First"].shares_owned(scode) == 1
assert mgr.unassigned_shares[scode] == iniv-1
mgr.draw_bp_from("First",total_bp*0.01)
assert abs(mgr.portfolios['First'].bp - total_bp*0.02)<1e-5
assert abs(mgr.unassigned_bp - total_bp*0.98)<1e-5
mgr.draw_shares_from("First",scode,1)
assert mgr.portfolios["First"].shares_owned(scode) == 0

mgr.add_portfolio(name = 'Second',ini_bp = total_bp * 0.03)
mgr.transfer_bp('Second','First',0.005*total_bp)
assert abs(mgr.portfolios["First"].bp-0.025*total_bp)<1e-5
assert abs(mgr.portfolios["Second"].bp-0.025*total_bp)<1e-5

mgr.add_shares_to('Second',scode,1)
mgr.transfer_shares('Second','First',scode,1)
assert mgr.portfolios['Second'].shares_owned(scode) == 0
assert mgr.portfolios['First'].shares_owned(scode) == 1