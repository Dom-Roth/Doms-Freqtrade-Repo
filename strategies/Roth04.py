
# --- Do not remove these libs ---
import numpy

from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
# --------------------------------

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class Roth04(IStrategy):
    EMA_SHORT_TERM = 5
    EMA_MEDIUM_TERM = 12
    EMA_LONG_TERM = 21

    ###
    # ToDo:
    # 
    # - Code hyperopt
    # - Run hyperopt
    ###

    #*18 / 100: 801 trades. 345 / 430 / 26 Wins / Draws / Losses.Avg profit 0.29 %.Median profit 0.00 %.Total profit 0.11450369 BTC(228.78 Σ %).Avg duration 801.9 min.Objective: -11.40886

    # Buy hyperspace params:
    buy_params = {
        'adx-enabled': True,
        'adx-value': 21,
        'cci-enabled': False,
        'cci-value': -196,
        'fastd-enabled': False,
        'fastd-value': 32,
        'mfi-enabled': False,
        'mfi-value': 20,
        'rsi-enabled': False,
        'rsi-value': 32,
        'trigger': 'bb_lower'
    }

    # Sell hyperspace params:
    sell_params = {
        'sell-adx-enabled': False,
        'sell-adx-value': 55,
        'sell-cci-enabled': True,
        'sell-cci-value': 51,
        'sell-fastd-enabled': False,
        'sell-fastd-value': 95,
        'sell-mfi-enabled': True,
        'sell-mfi-value': 90,
        'sell-rsi-enabled': False,
        'sell-rsi-value': 99,
        'sell-trigger': 'sell-sar_reversal'
    }

    # ROI table:
    minimal_roi = {
        "0": 0.196,
        "25": 0.05188,
        "69": 0.03109,
        "141": 0
    }

    # Stoploss:
    stoploss = -0.27639


    # Optimal timeframe for the strategy
    timeframe = '1m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['cci'] = ta.CCI(dataframe)
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_low'] = bollinger['lower']
        dataframe['bb_mid'] = bollinger['mid']
        dataframe['bb_upper'] = bollinger['upper']
        dataframe['bb_perc'] = (dataframe['close'] - dataframe['bb_low']) / (
                    dataframe['bb_upper'] - dataframe['bb_low'])
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe)
        rsiframe = DataFrame(dataframe['rsi']).rename(columns={'rsi': 'close'})
        dataframe['emarsi'] = numpy.nan_to_num(ta.EMA(rsiframe, timeperiod=5))
        dataframe['sar'] = ta.SAR(dataframe)
        dataframe['mfi'] = ta.MFI(dataframe)
        
        
        
        dataframe['minusdi'] = numpy.nan_to_num(ta.MINUS_DI(dataframe))
        minusdiframe = DataFrame(dataframe['minusdi']).rename(columns={'minusdi': 'close'})
        dataframe['minusdiema'] = numpy.nan_to_num(ta.EMA(minusdiframe, timeperiod=25))
        dataframe['plusdi'] = numpy.nan_to_num(ta.PLUS_DI(dataframe))
        plusdiframe = DataFrame(dataframe['plusdi']).rename(columns={'plusdi': 'close'})
        dataframe['plusdiema'] = numpy.nan_to_num(ta.EMA(plusdiframe, timeperiod=5))
        
        

        # Stoch fast
        stoch_fast = ta.STOCHF(dataframe)
        dataframe['fastd'] = stoch_fast['fastd']
        dataframe['fastk'] = stoch_fast['fastk']
        
        dataframe['ema_{}'.format(self.EMA_SHORT_TERM)] = ta.EMA(
            dataframe, timeperiod=self.EMA_SHORT_TERM
        )
        dataframe['ema_{}'.format(self.EMA_MEDIUM_TERM)] = ta.EMA(
            dataframe, timeperiod=self.EMA_MEDIUM_TERM
        )
        dataframe['ema_{}'.format(self.EMA_LONG_TERM)] = ta.EMA(
            dataframe, timeperiod=self.EMA_LONG_TERM
        )
        
        dataframe['min'] = ta.MIN(dataframe, timeperiod=self.EMA_MEDIUM_TERM)
        dataframe['max'] = ta.MAX(dataframe, timeperiod=self.EMA_MEDIUM_TERM)
        
        
        dataframe['lowsma'] = numpy.nan_to_num(ta.EMA(dataframe, timeperiod=60))
        dataframe['highsma'] = numpy.nan_to_num(ta.EMA(dataframe, timeperiod=120))
        dataframe['fastsma'] = numpy.nan_to_num(ta.SMA(dataframe, timeperiod=120))
        dataframe['slowsma'] = numpy.nan_to_num(ta.SMA(dataframe, timeperiod=240))
        dataframe['bigup'] = dataframe['fastsma'].gt(dataframe['slowsma']) & ((dataframe['fastsma'] - dataframe['slowsma']) > dataframe['close'] / 300)
        dataframe['bigdown'] = ~dataframe['bigup']
        dataframe['trend'] = dataframe['fastsma'] - dataframe['slowsma']
        dataframe['preparechangetrend'] = dataframe['trend'].gt(dataframe['trend'].shift())
        dataframe['preparechangetrendconfirm'] = dataframe['preparechangetrend'] & dataframe['trend'].shift().gt(dataframe['trend'].shift(2))
        dataframe['continueup'] = dataframe['slowsma'].gt(dataframe['slowsma'].shift()) & dataframe['slowsma'].shift().gt(dataframe['slowsma'].shift(2))
        dataframe['delta'] = dataframe['fastsma'] - dataframe['fastsma'].shift()
        dataframe['slowingdown'] = dataframe['delta'].lt(dataframe['delta'].shift())
        
        

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                (dataframe['close'] < dataframe['bb_low']) &
                (dataframe['adx'] > 21)
                # (dataframe['cci'] <= -57.0)
            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                #(dataframe['sar'] > dataframe['close']) &
                # (dataframe['adx'] > 52) &
                # (dataframe['cci'] >= 50.0) &
                # (dataframe['close'] > dataframe['bb_upper'])

                (dataframe['cci'] >= 51) &
                (dataframe['mfi'] > 90) &
                qtpylib.crossed_above(
                    dataframe['sar'], dataframe['close']
                )
            ),
            'sell'] = 1

        return dataframe
