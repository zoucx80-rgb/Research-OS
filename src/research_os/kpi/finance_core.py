def safe_ratio(num,den):
    if num is None or den is None or den==0: return None
    return num/den

def average(a,b):
    return None if a is None or b is None else (a+b)/2

def dupont(revenue,np_parent,assets_begin,assets_end,equity_begin,equity_end):
    aa=average(assets_begin,assets_end); ae=average(equity_begin,equity_end)
    margin=safe_ratio(np_parent,revenue); turnover=safe_ratio(revenue,aa); multiplier=safe_ratio(aa,ae)
    roe=None if None in (margin,turnover,multiplier) else margin*turnover*multiplier
    return {"roe":roe,"net_margin":margin,"asset_turnover":turnover,"equity_multiplier":multiplier}

def turnover_days(begin,end,flow):
    return safe_ratio(average(begin,end),flow)*365 if safe_ratio(average(begin,end),flow) is not None else None
