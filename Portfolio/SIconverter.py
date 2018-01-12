class SIconverter:
    def __init__(
        self,
        buffer_size = 500,
        trader = None,
        load = None
        ):
        assert trader is not None
        assert buffer_size > 0
        self.buffer_size = buffer_size
        self.SI =  {}
        self.IS = {}
        self.count = {}
        self.life = {}
        self.freq = {}
        self.trader = trader

    def query_S2I(self,scode):
        if scode not in self.SI:
            try:
                self.SI[scode] = self.trader.instruments(scode)[0]['url']
            except:
                return None
            self.IS[self.SI[scode]] = scode
            self.count[scode] = 0
            self.life[scode] = 0
        self.count[scode] += 1
        self.update_all()
        return self.SI[scode]

    def query_I2S(self,instrument):
        if isinstance(instrument,dict):
            instrument = instrument['url']
        if instrument not in self.IS:
            try:
                scode = self.trader.session.get(instrument).json()['symbol']
            except:
                return None
            self.SI[scode] = instrument
            self.IS[instrument] = scode
            self.count[scode] = 0
            self.life[scode] = 0
        scode = self.IS[instrument]
        self.count[scode] += 1
        self.update_all()
        return scode

    def update_all(self):
        for key in self.life:
            self.life[key] += 1
            self.freq[key] = self.count[key]/self.life[key]
        if len(self.freq) > self.buffer_size:
            argmin = min(self.freq,key = self.freq.get)
            self.IS.pop(self.SI[argmin])
            self.SI.pop(argmin)
            self.count.pop(argmin)
            self.life.pop(argmin)
            self.freq.pop(argmin)

    def __call__(self,query):
        if query.find("https:") == 0:
            return self.query_I2S(query)
        return self.query_S2I(query)





