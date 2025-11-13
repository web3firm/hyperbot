import numpy as np
import pandas as pd
import talib
from typing import Dict, List, Optional, Tuple
from loguru import logger

class TechnicalIndicators:
    """Technical analysis indicators using TA-Lib"""
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        return talib.RSI(data.values, timeperiod=period)
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD indicator"""
        macd_line, signal_line, histogram = talib.MACD(data.values, fastperiod=fast, slowperiod=slow, signalperiod=signal)
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands"""
        upper, middle, lower = talib.BBANDS(data.values, timeperiod=period, nbdevup=std, nbdevdn=std)
        return upper, middle, lower
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Stochastic oscillator"""
        k, d = talib.STOCH(high.values, low.values, close.values, fastk_period=k_period, slowk_period=d_period, slowd_period=d_period)
        return k, d
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return talib.EMA(data.values, timeperiod=period)
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return talib.SMA(data.values, timeperiod=period)
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        return talib.ATR(high.values, low.values, close.values, timeperiod=period)
    
    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Williams %R"""
        return talib.WILLR(high.values, low.values, close.values, timeperiod=period)

class CandlestickPatterns:
    """Candlestick pattern recognition"""
    
    @staticmethod
    def detect_patterns(open_data: pd.Series, high_data: pd.Series, low_data: pd.Series, close_data: pd.Series) -> Dict[str, int]:
        """Detect various candlestick patterns"""
        patterns = {}
        
        # Convert to numpy arrays
        open_arr = open_data.values
        high_arr = high_data.values
        low_arr = low_data.values
        close_arr = close_data.values
        
        # Bullish patterns
        patterns['hammer'] = talib.CDLHAMMER(open_arr, high_arr, low_arr, close_arr)[-1]
        patterns['morning_star'] = talib.CDLMORNINGSTAR(open_arr, high_arr, low_arr, close_arr)[-1]
        patterns['bullish_engulfing'] = talib.CDLENGULFING(open_arr, high_arr, low_arr, close_arr)[-1]
        patterns['piercing_line'] = talib.CDLPIERCING(open_arr, high_arr, low_arr, close_arr)[-1]
        patterns['three_white_soldiers'] = talib.CDL3WHITESOLDIERS(open_arr, high_arr, low_arr, close_arr)[-1]
        
        # Bearish patterns
        patterns['hanging_man'] = talib.CDLHANGINGMAN(open_arr, high_arr, low_arr, close_arr)[-1]
        patterns['evening_star'] = talib.CDLEVENINGSTAR(open_arr, high_arr, low_arr, close_arr)[-1]
        patterns['bearish_engulfing'] = talib.CDLENGULFING(open_arr, high_arr, low_arr, close_arr)[-1]
        patterns['dark_cloud_cover'] = talib.CDLDARKCLOUDCOVER(open_arr, high_arr, low_arr, close_arr)[-1]
        patterns['three_black_crows'] = talib.CDL3BLACKCROWS(open_arr, high_arr, low_arr, close_arr)[-1]
        
        # Neutral/reversal patterns
        patterns['doji'] = talib.CDLDOJI(open_arr, high_arr, low_arr, close_arr)[-1]
        patterns['spinning_top'] = talib.CDLSPINNINGTOP(open_arr, high_arr, low_arr, close_arr)[-1]
        
        return patterns

class StrategyManager:
    """Manages multiple trading strategies"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.patterns = CandlestickPatterns()
        
    def analyze_all_strategies(self, market_data: pd.DataFrame) -> Dict[str, dict]:
        """Run all trading strategies on market data"""
        try:
            if market_data.empty or len(market_data) < 50:
                return {}
            
            strategies = {}
            
            # Extract OHLCV data
            close = market_data['close']
            high = market_data['high']
            low = market_data['low']
            open_data = market_data['open']
            volume = market_data['volume'] if 'volume' in market_data.columns else None
            
            # RSI Strategy
            strategies['rsi'] = self._rsi_strategy(close)
            
            # MACD Strategy
            strategies['macd'] = self._macd_strategy(close)
            
            # Bollinger Bands Strategy
            strategies['bollinger'] = self._bollinger_strategy(close)
            
            # Moving Average Crossover
            strategies['ma_crossover'] = self._ma_crossover_strategy(close)
            
            # Stochastic Strategy
            strategies['stochastic'] = self._stochastic_strategy(high, low, close)
            
            # Price Action Strategy
            strategies['price_action'] = self._price_action_strategy(open_data, high, low, close)
            
            # Trend Following Strategy
            strategies['trend_following'] = self._trend_following_strategy(close)
            
            # Momentum Strategy
            strategies['momentum'] = self._momentum_strategy(close)
            
            # Support/Resistance Strategy
            strategies['support_resistance'] = self._support_resistance_strategy(high, low, close)
            
            # Candlestick Pattern Strategy
            strategies['candlestick'] = self._candlestick_strategy(open_data, high, low, close)
            
            return strategies
            
        except Exception as e:
            logger.error(f"Error in analyze_all_strategies: {e}")
            return {}
    
    def _rsi_strategy(self, close: pd.Series) -> dict:
        """RSI-based strategy"""
        try:
            rsi = self.indicators.rsi(close)
            current_rsi = rsi[-1] if not np.isnan(rsi[-1]) else 50
            
            signal = "neutral"
            strength = 0.0
            
            if current_rsi < 30:
                signal = "bullish"
                strength = (30 - current_rsi) / 30
            elif current_rsi > 70:
                signal = "bearish"
                strength = (current_rsi - 70) / 30
                
            return {
                "signal": signal,
                "strength": strength,
                "rsi_value": current_rsi,
                "description": f"RSI: {current_rsi:.2f}"
            }
        except:
            return {"signal": "neutral", "strength": 0.0}
    
    def _macd_strategy(self, close: pd.Series) -> dict:
        """MACD strategy"""
        try:
            macd, signal, histogram = self.indicators.macd(close)
            
            current_macd = macd[-1]
            current_signal = signal[-1]
            current_hist = histogram[-1]
            prev_hist = histogram[-2]
            
            signal_type = "neutral"
            strength = 0.0
            
            # MACD bullish crossover
            if current_hist > 0 and prev_hist <= 0:
                signal_type = "bullish"
                strength = min(abs(current_hist) / abs(current_macd) * 2, 1.0) if current_macd != 0 else 0.5
            # MACD bearish crossover
            elif current_hist < 0 and prev_hist >= 0:
                signal_type = "bearish"
                strength = min(abs(current_hist) / abs(current_macd) * 2, 1.0) if current_macd != 0 else 0.5
            
            return {
                "signal": signal_type,
                "strength": strength,
                "macd": current_macd,
                "signal_line": current_signal,
                "histogram": current_hist,
                "description": f"MACD: {current_macd:.4f}"
            }
        except:
            return {"signal": "neutral", "strength": 0.0}
    
    def _bollinger_strategy(self, close: pd.Series) -> dict:
        """Bollinger Bands strategy"""
        try:
            upper, middle, lower = self.indicators.bollinger_bands(close)
            
            current_price = close.iloc[-1]
            current_upper = upper[-1]
            current_lower = lower[-1]
            current_middle = middle[-1]
            
            signal_type = "neutral"
            strength = 0.0
            
            band_width = current_upper - current_lower
            
            # Price near lower band (oversold)
            if current_price <= current_lower + (band_width * 0.1):
                signal_type = "bullish"
                strength = (current_lower - current_price) / band_width + 0.5
            # Price near upper band (overbought)
            elif current_price >= current_upper - (band_width * 0.1):
                signal_type = "bearish"
                strength = (current_price - current_upper) / band_width + 0.5
            
            strength = min(max(strength, 0.0), 1.0)
            
            return {
                "signal": signal_type,
                "strength": strength,
                "position": (current_price - current_lower) / band_width,
                "description": f"BB Position: {((current_price - current_lower) / band_width):.2f}"
            }
        except:
            return {"signal": "neutral", "strength": 0.0}
    
    def _ma_crossover_strategy(self, close: pd.Series) -> dict:
        """Moving Average crossover strategy"""
        try:
            ema_fast = self.indicators.ema(close, 10)
            ema_slow = self.indicators.ema(close, 30)
            
            current_fast = ema_fast[-1]
            current_slow = ema_slow[-1]
            prev_fast = ema_fast[-2]
            prev_slow = ema_slow[-2]
            
            signal_type = "neutral"
            strength = 0.0
            
            # Bullish crossover
            if current_fast > current_slow and prev_fast <= prev_slow:
                signal_type = "bullish"
                strength = min(abs(current_fast - current_slow) / current_slow * 10, 1.0)
            # Bearish crossover
            elif current_fast < current_slow and prev_fast >= prev_slow:
                signal_type = "bearish"
                strength = min(abs(current_fast - current_slow) / current_slow * 10, 1.0)
            
            return {
                "signal": signal_type,
                "strength": strength,
                "fast_ma": current_fast,
                "slow_ma": current_slow,
                "description": f"MA Spread: {((current_fast - current_slow) / current_slow * 100):.2f}%"
            }
        except:
            return {"signal": "neutral", "strength": 0.0}
    
    def _stochastic_strategy(self, high: pd.Series, low: pd.Series, close: pd.Series) -> dict:
        """Stochastic oscillator strategy"""
        try:
            k, d = self.indicators.stochastic(high, low, close)
            
            current_k = k[-1]
            current_d = d[-1]
            
            signal_type = "neutral"
            strength = 0.0
            
            if current_k < 20 and current_d < 20:
                signal_type = "bullish"
                strength = (20 - min(current_k, current_d)) / 20
            elif current_k > 80 and current_d > 80:
                signal_type = "bearish"
                strength = (min(current_k, current_d) - 80) / 20
            
            return {
                "signal": signal_type,
                "strength": strength,
                "k_value": current_k,
                "d_value": current_d,
                "description": f"Stoch: {current_k:.1f}/{current_d:.1f}"
            }
        except:
            return {"signal": "neutral", "strength": 0.0}
    
    def _price_action_strategy(self, open_data: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> dict:
        """Price action based strategy"""
        try:
            # Calculate recent price movements
            recent_closes = close.tail(5)
            price_change = (recent_closes.iloc[-1] - recent_closes.iloc[0]) / recent_closes.iloc[0]
            
            # Volume-weighted average price approximation
            typical_price = (high + low + close) / 3
            vwap_approx = typical_price.rolling(window=20).mean().iloc[-1]
            
            current_price = close.iloc[-1]
            
            signal_type = "neutral"
            strength = 0.0
            
            # Strong upward momentum
            if price_change > 0.02 and current_price > vwap_approx:
                signal_type = "bullish"
                strength = min(price_change * 10, 1.0)
            # Strong downward momentum
            elif price_change < -0.02 and current_price < vwap_approx:
                signal_type = "bearish"
                strength = min(abs(price_change) * 10, 1.0)
            
            return {
                "signal": signal_type,
                "strength": strength,
                "price_change": price_change,
                "vs_vwap": (current_price - vwap_approx) / vwap_approx,
                "description": f"Momentum: {price_change*100:.2f}%"
            }
        except:
            return {"signal": "neutral", "strength": 0.0}
    
    def _trend_following_strategy(self, close: pd.Series) -> dict:
        """Trend following strategy using multiple EMAs"""
        try:
            ema_short = self.indicators.ema(close, 8)
            ema_medium = self.indicators.ema(close, 21)
            ema_long = self.indicators.ema(close, 50)
            
            current_short = ema_short[-1]
            current_medium = ema_medium[-1]
            current_long = ema_long[-1]
            
            signal_type = "neutral"
            strength = 0.0
            
            # Bullish trend alignment
            if current_short > current_medium > current_long:
                signal_type = "bullish"
                spread1 = (current_short - current_medium) / current_medium
                spread2 = (current_medium - current_long) / current_long
                strength = min((spread1 + spread2) * 20, 1.0)
            # Bearish trend alignment
            elif current_short < current_medium < current_long:
                signal_type = "bearish"
                spread1 = (current_medium - current_short) / current_medium
                spread2 = (current_long - current_medium) / current_long
                strength = min((spread1 + spread2) * 20, 1.0)
            
            return {
                "signal": signal_type,
                "strength": strength,
                "trend_alignment": current_short > current_medium > current_long,
                "description": f"Trend: {'Up' if current_short > current_long else 'Down'}"
            }
        except:
            return {"signal": "neutral", "strength": 0.0}
    
    def _momentum_strategy(self, close: pd.Series) -> dict:
        """Momentum-based strategy"""
        try:
            # Rate of change
            roc_short = ((close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]) * 100
            roc_medium = ((close.iloc[-1] - close.iloc[-10]) / close.iloc[-10]) * 100
            
            # RSI for momentum confirmation
            rsi = self.indicators.rsi(close)[-1]
            
            signal_type = "neutral"
            strength = 0.0
            
            # Strong bullish momentum
            if roc_short > 2 and roc_medium > 1 and rsi > 50:
                signal_type = "bullish"
                strength = min((roc_short + roc_medium) / 6, 1.0)
            # Strong bearish momentum
            elif roc_short < -2 and roc_medium < -1 and rsi < 50:
                signal_type = "bearish"
                strength = min(abs(roc_short + roc_medium) / 6, 1.0)
            
            return {
                "signal": signal_type,
                "strength": strength,
                "roc_short": roc_short,
                "roc_medium": roc_medium,
                "description": f"ROC: {roc_short:.2f}%"
            }
        except:
            return {"signal": "neutral", "strength": 0.0}
    
    def _support_resistance_strategy(self, high: pd.Series, low: pd.Series, close: pd.Series) -> dict:
        """Support and resistance based strategy"""
        try:
            current_price = close.iloc[-1]
            
            # Calculate pivot points
            recent_highs = high.tail(20)
            recent_lows = low.tail(20)
            
            resistance_levels = []
            support_levels = []
            
            # Simple pivot calculation
            for i in range(2, len(recent_highs)-2):
                if (recent_highs.iloc[i] > recent_highs.iloc[i-1] and 
                    recent_highs.iloc[i] > recent_highs.iloc[i+1]):
                    resistance_levels.append(recent_highs.iloc[i])
                    
                if (recent_lows.iloc[i] < recent_lows.iloc[i-1] and 
                    recent_lows.iloc[i] < recent_lows.iloc[i+1]):
                    support_levels.append(recent_lows.iloc[i])
            
            signal_type = "neutral"
            strength = 0.0
            
            # Find nearest support/resistance
            if support_levels:
                nearest_support = max([s for s in support_levels if s <= current_price], default=0)
                support_distance = (current_price - nearest_support) / current_price if nearest_support > 0 else 1
                
                if support_distance < 0.02:  # Within 2% of support
                    signal_type = "bullish"
                    strength = (0.02 - support_distance) / 0.02
            
            if resistance_levels:
                nearest_resistance = min([r for r in resistance_levels if r >= current_price], default=float('inf'))
                resistance_distance = (nearest_resistance - current_price) / current_price if nearest_resistance != float('inf') else 1
                
                if resistance_distance < 0.02:  # Within 2% of resistance
                    if signal_type != "bullish" or strength < (0.02 - resistance_distance) / 0.02:
                        signal_type = "bearish"
                        strength = (0.02 - resistance_distance) / 0.02
            
            return {
                "signal": signal_type,
                "strength": strength,
                "support_levels": support_levels,
                "resistance_levels": resistance_levels,
                "description": f"S/R: {len(support_levels)}/{len(resistance_levels)}"
            }
        except:
            return {"signal": "neutral", "strength": 0.0}
    
    def _candlestick_strategy(self, open_data: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> dict:
        """Candlestick pattern strategy"""
        try:
            patterns = self.patterns.detect_patterns(open_data, high, low, close)
            
            signal_type = "neutral"
            strength = 0.0
            detected_patterns = []
            
            # Bullish patterns
            bullish_patterns = ['hammer', 'morning_star', 'bullish_engulfing', 'piercing_line', 'three_white_soldiers']
            bearish_patterns = ['hanging_man', 'evening_star', 'dark_cloud_cover', 'three_black_crows']
            
            bullish_score = 0
            bearish_score = 0
            
            for pattern, value in patterns.items():
                if value != 0:
                    detected_patterns.append(pattern)
                    if pattern in bullish_patterns and value > 0:
                        bullish_score += 1
                    elif pattern in bearish_patterns and value < 0:
                        bearish_score += 1
                    elif pattern == 'bearish_engulfing' and value < 0:
                        bearish_score += 1
            
            if bullish_score > bearish_score:
                signal_type = "bullish"
                strength = min(bullish_score / 3, 1.0)
            elif bearish_score > bullish_score:
                signal_type = "bearish"
                strength = min(bearish_score / 3, 1.0)
            
            return {
                "signal": signal_type,
                "strength": strength,
                "patterns": detected_patterns,
                "description": f"Patterns: {len(detected_patterns)}"
            }
        except:
            return {"signal": "neutral", "strength": 0.0}