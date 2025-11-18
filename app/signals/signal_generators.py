"""
Signal Generators
Technical analysis and rule-based trading signal generation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
import numpy as np
import talib

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of trading signals"""
    ENTRY_LONG = "entry_long"
    ENTRY_SHORT = "entry_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


@dataclass
class TradingSignal:
    """Trading signal data structure"""
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    price: Decimal
    timestamp: datetime
    
    # Strategy specific
    strategy_name: str
    confidence: float  # 0.0 to 1.0
    
    # Risk management
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    position_size: Optional[Decimal] = None
    
    # Technical indicators
    indicators: Dict[str, float] = None
    
    # Additional metadata
    reason: str = ""
    expiry_time: Optional[datetime] = None


@dataclass
class MarketCondition:
    """Market condition assessment"""
    symbol: str
    timestamp: datetime
    trend_direction: str  # 'uptrend', 'downtrend', 'sideways'
    volatility: float
    momentum: float
    support_level: Optional[Decimal] = None
    resistance_level: Optional[Decimal] = None
    conditions: Dict[str, Any] = None


class TechnicalIndicators:
    """Technical analysis indicators calculator"""
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return [np.nan] * len(prices)
        
        prices_array = np.array(prices, dtype=float)
        ema = talib.EMA(prices_array, timeperiod=period)
        return ema.tolist()
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return [np.nan] * len(prices)
        
        prices_array = np.array(prices, dtype=float)
        rsi = talib.RSI(prices_array, timeperiod=period)
        return rsi.tolist()
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float], 
        period: int = 20, 
        std_dev: float = 2.0
    ) -> Tuple[List[float], List[float], List[float]]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            nan_list = [np.nan] * len(prices)
            return nan_list, nan_list, nan_list
        
        prices_array = np.array(prices, dtype=float)
        upper, middle, lower = talib.BBANDS(
            prices_array, 
            timeperiod=period, 
            nbdevup=std_dev, 
            nbdevdn=std_dev
        )
        return upper.tolist(), middle.tolist(), lower.tolist()
    
    @staticmethod
    def calculate_macd(
        prices: List[float], 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9
    ) -> Tuple[List[float], List[float], List[float]]:
        """Calculate MACD"""
        if len(prices) < slow:
            nan_list = [np.nan] * len(prices)
            return nan_list, nan_list, nan_list
        
        prices_array = np.array(prices, dtype=float)
        macd, signal_line, histogram = talib.MACD(
            prices_array, 
            fastperiod=fast, 
            slowperiod=slow, 
            signalperiod=signal
        )
        return macd.tolist(), signal_line.tolist(), histogram.tolist()
    
    @staticmethod
    def calculate_stochastic(
        highs: List[float], 
        lows: List[float], 
        closes: List[float],
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[List[float], List[float]]:
        """Calculate Stochastic Oscillator"""
        if len(closes) < k_period:
            nan_list = [np.nan] * len(closes)
            return nan_list, nan_list
        
        high_array = np.array(highs, dtype=float)
        low_array = np.array(lows, dtype=float)
        close_array = np.array(closes, dtype=float)
        
        slowk, slowd = talib.STOCH(
            high_array, low_array, close_array,
            fastk_period=k_period,
            slowk_period=d_period,
            slowd_period=d_period
        )
        return slowk.tolist(), slowd.tolist()
    
    @staticmethod
    def calculate_atr(
        highs: List[float], 
        lows: List[float], 
        closes: List[float],
        period: int = 14
    ) -> List[float]:
        """Calculate Average True Range"""
        if len(closes) < period:
            return [np.nan] * len(closes)
        
        high_array = np.array(highs, dtype=float)
        low_array = np.array(lows, dtype=float)
        close_array = np.array(closes, dtype=float)
        
        atr = talib.ATR(high_array, low_array, close_array, timeperiod=period)
        return atr.tolist()


class BaseSignalGenerator:
    """Base class for all signal generators"""
    
    def __init__(self, symbol: str, config: Dict[str, Any]):
        """
        Initialize signal generator
        
        Args:
            symbol: Trading symbol
            config: Generator configuration
        """
        self.symbol = symbol
        self.config = config
        self.name = self.__class__.__name__
        
        # Price history storage
        self.price_history: List[Dict[str, float]] = []
        self.max_history = config.get('max_history_bars', 500)
        
        # Indicator cache
        self.indicators_cache: Dict[str, Any] = {}
        self.last_update_time = None
        
        # Signal history
        self.signal_history: List[TradingSignal] = []
        
        logger.info(f"📊 Signal generator {self.name} initialized for {symbol}")

    def add_price_data(self, price_data: Dict[str, float]):
        """
        Add new price data point
        
        Args:
            price_data: Dict with 'open', 'high', 'low', 'close', 'volume', 'timestamp'
        """
        self.price_history.append(price_data)
        
        # Maintain history limit
        if len(self.price_history) > self.max_history:
            self.price_history = self.price_history[-self.max_history:]
        
        # Clear indicators cache to force recalculation
        self.indicators_cache.clear()
        self.last_update_time = datetime.now(timezone.utc)

    def get_prices(self, price_type: str = 'close') -> List[float]:
        """Get price series of specified type"""
        if not self.price_history:
            return []
        
        return [bar[price_type] for bar in self.price_history if price_type in bar]

    def get_latest_price(self, price_type: str = 'close') -> Optional[float]:
        """Get latest price of specified type"""
        prices = self.get_prices(price_type)
        return prices[-1] if prices else None

    def calculate_indicators(self) -> Dict[str, Any]:
        """Calculate all technical indicators (to be implemented by subclasses)"""
        raise NotImplementedError("Subclasses must implement calculate_indicators")

    def generate_signals(self) -> List[TradingSignal]:
        """Generate trading signals (to be implemented by subclasses)"""
        raise NotImplementedError("Subclasses must implement generate_signals")

    def assess_market_condition(self) -> MarketCondition:
        """Assess current market conditions"""
        if len(self.price_history) < 20:
            return MarketCondition(
                symbol=self.symbol,
                timestamp=datetime.now(timezone.utc),
                trend_direction='sideways',
                volatility=0.0,
                momentum=0.0
            )
        
        # Calculate basic trend and volatility
        closes = self.get_prices('close')
        
        # Simple trend detection using EMA comparison
        if len(closes) >= 20:
            ema_10 = TechnicalIndicators.calculate_ema(closes, 10)
            ema_20 = TechnicalIndicators.calculate_ema(closes, 20)
            
            if not np.isnan(ema_10[-1]) and not np.isnan(ema_20[-1]):
                if ema_10[-1] > ema_20[-1]:
                    trend = 'uptrend'
                elif ema_10[-1] < ema_20[-1]:
                    trend = 'downtrend'
                else:
                    trend = 'sideways'
            else:
                trend = 'sideways'
        else:
            trend = 'sideways'
        
        # Calculate volatility (standard deviation of returns)
        if len(closes) >= 10:
            returns = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))]
            volatility = np.std(returns) * 100  # Convert to percentage
        else:
            volatility = 0.0
        
        # Calculate momentum (price change over period)
        if len(closes) >= 10:
            momentum = (closes[-1] / closes[-10] - 1) * 100
        else:
            momentum = 0.0
        
        return MarketCondition(
            symbol=self.symbol,
            timestamp=datetime.now(timezone.utc),
            trend_direction=trend,
            volatility=volatility,
            momentum=momentum
        )


class EMASignalGenerator(BaseSignalGenerator):
    """EMA-based signal generator for baseline strategy"""
    
    def __init__(self, symbol: str, config: Dict[str, Any]):
        super().__init__(symbol, config)
        
        # EMA parameters
        self.ema_fast = config.get('ema_fast', 12)
        self.ema_slow = config.get('ema_slow', 26)
        
        # Signal thresholds
        self.min_separation_pct = config.get('min_separation_pct', 0.1)

    def calculate_indicators(self) -> Dict[str, Any]:
        """Calculate EMA indicators"""
        if 'ema_indicators' in self.indicators_cache:
            return self.indicators_cache['ema_indicators']
        
        closes = self.get_prices('close')
        if len(closes) < max(self.ema_fast, self.ema_slow):
            return {}
        
        ema_fast = TechnicalIndicators.calculate_ema(closes, self.ema_fast)
        ema_slow = TechnicalIndicators.calculate_ema(closes, self.ema_slow)
        
        indicators = {
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'ema_fast_current': ema_fast[-1] if not np.isnan(ema_fast[-1]) else None,
            'ema_slow_current': ema_slow[-1] if not np.isnan(ema_slow[-1]) else None
        }
        
        # Calculate EMA separation
        if indicators['ema_fast_current'] and indicators['ema_slow_current']:
            separation_pct = (
                indicators['ema_fast_current'] - indicators['ema_slow_current']
            ) / indicators['ema_slow_current'] * 100
            indicators['separation_pct'] = separation_pct
        
        self.indicators_cache['ema_indicators'] = indicators
        return indicators

    def generate_signals(self) -> List[TradingSignal]:
        """Generate EMA-based signals"""
        signals = []
        
        if len(self.price_history) < max(self.ema_fast, self.ema_slow) + 2:
            return signals
        
        indicators = self.calculate_indicators()
        if not indicators:
            return signals
        
        current_price = self.get_latest_price('close')
        if not current_price:
            return signals
        
        ema_fast_current = indicators.get('ema_fast_current')
        ema_slow_current = indicators.get('ema_slow_current')
        separation_pct = indicators.get('separation_pct', 0)
        
        if not ema_fast_current or not ema_slow_current:
            return signals
        
        # Get previous EMAs for crossover detection
        ema_fast_prev = indicators['ema_fast'][-2] if len(indicators['ema_fast']) > 1 else None
        ema_slow_prev = indicators['ema_slow'][-2] if len(indicators['ema_slow']) > 1 else None
        
        if not ema_fast_prev or not ema_slow_prev:
            return signals
        
        # Check for EMA crossovers
        was_above = ema_fast_prev > ema_slow_prev
        is_above = ema_fast_current > ema_slow_current
        
        # Bullish crossover (Golden Cross)
        if not was_above and is_above and abs(separation_pct) >= self.min_separation_pct:
            signal = TradingSignal(
                symbol=self.symbol,
                signal_type=SignalType.ENTRY_LONG,
                strength=SignalStrength.MEDIUM,
                price=Decimal(str(current_price)),
                timestamp=datetime.now(timezone.utc),
                strategy_name="EMA_Baseline",
                confidence=0.7,
                stop_loss=Decimal(str(current_price * 0.98)),  # 2% stop loss
                take_profit=Decimal(str(current_price * 1.04)), # 4% take profit
                indicators={
                    'ema_fast': ema_fast_current,
                    'ema_slow': ema_slow_current,
                    'separation_pct': separation_pct
                },
                reason=f"EMA Golden Cross: {self.ema_fast}/{self.ema_slow}"
            )
            signals.append(signal)
        
        # Bearish crossover (Death Cross)
        elif was_above and not is_above and abs(separation_pct) >= self.min_separation_pct:
            signal = TradingSignal(
                symbol=self.symbol,
                signal_type=SignalType.ENTRY_SHORT,
                strength=SignalStrength.MEDIUM,
                price=Decimal(str(current_price)),
                timestamp=datetime.now(timezone.utc),
                strategy_name="EMA_Baseline",
                confidence=0.7,
                stop_loss=Decimal(str(current_price * 1.02)),  # 2% stop loss
                take_profit=Decimal(str(current_price * 0.96)), # 4% take profit
                indicators={
                    'ema_fast': ema_fast_current,
                    'ema_slow': ema_slow_current,
                    'separation_pct': separation_pct
                },
                reason=f"EMA Death Cross: {self.ema_fast}/{self.ema_slow}"
            )
            signals.append(signal)
        
        self.signal_history.extend(signals)
        return signals


class RSISignalGenerator(BaseSignalGenerator):
    """RSI-based signal generator"""
    
    def __init__(self, symbol: str, config: Dict[str, Any]):
        super().__init__(symbol, config)
        
        # RSI parameters
        self.rsi_period = config.get('rsi_period', 14)
        self.oversold_threshold = config.get('oversold_threshold', 30)
        self.overbought_threshold = config.get('overbought_threshold', 70)
        self.extreme_oversold = config.get('extreme_oversold', 20)
        self.extreme_overbought = config.get('extreme_overbought', 80)

    def calculate_indicators(self) -> Dict[str, Any]:
        """Calculate RSI indicators"""
        if 'rsi_indicators' in self.indicators_cache:
            return self.indicators_cache['rsi_indicators']
        
        closes = self.get_prices('close')
        if len(closes) < self.rsi_period + 1:
            return {}
        
        rsi = TechnicalIndicators.calculate_rsi(closes, self.rsi_period)
        
        indicators = {
            'rsi': rsi,
            'rsi_current': rsi[-1] if not np.isnan(rsi[-1]) else None
        }
        
        self.indicators_cache['rsi_indicators'] = indicators
        return indicators

    def generate_signals(self) -> List[TradingSignal]:
        """Generate RSI-based signals"""
        signals = []
        
        if len(self.price_history) < self.rsi_period + 2:
            return signals
        
        indicators = self.calculate_indicators()
        if not indicators:
            return signals
        
        current_price = self.get_latest_price('close')
        rsi_current = indicators.get('rsi_current')
        
        if not current_price or not rsi_current:
            return signals
        
        # Get previous RSI for divergence detection
        rsi_prev = indicators['rsi'][-2] if len(indicators['rsi']) > 1 else None
        
        # Oversold condition (potential long entry)
        if rsi_current <= self.oversold_threshold and (rsi_prev is None or rsi_prev > rsi_current):
            strength = SignalStrength.STRONG if rsi_current <= self.extreme_oversold else SignalStrength.MEDIUM
            confidence = 0.8 if rsi_current <= self.extreme_oversold else 0.6
            
            signal = TradingSignal(
                symbol=self.symbol,
                signal_type=SignalType.ENTRY_LONG,
                strength=strength,
                price=Decimal(str(current_price)),
                timestamp=datetime.now(timezone.utc),
                strategy_name="RSI_Mean_Reversion",
                confidence=confidence,
                stop_loss=Decimal(str(current_price * 0.97)),  # 3% stop loss
                take_profit=Decimal(str(current_price * 1.06)), # 6% take profit
                indicators={'rsi': rsi_current},
                reason=f"RSI Oversold: {rsi_current:.1f}"
            )
            signals.append(signal)
        
        # Overbought condition (potential short entry)
        elif rsi_current >= self.overbought_threshold and (rsi_prev is None or rsi_prev < rsi_current):
            strength = SignalStrength.STRONG if rsi_current >= self.extreme_overbought else SignalStrength.MEDIUM
            confidence = 0.8 if rsi_current >= self.extreme_overbought else 0.6
            
            signal = TradingSignal(
                symbol=self.symbol,
                signal_type=SignalType.ENTRY_SHORT,
                strength=strength,
                price=Decimal(str(current_price)),
                timestamp=datetime.now(timezone.utc),
                strategy_name="RSI_Mean_Reversion",
                confidence=confidence,
                stop_loss=Decimal(str(current_price * 1.03)),  # 3% stop loss
                take_profit=Decimal(str(current_price * 0.94)), # 6% take profit
                indicators={'rsi': rsi_current},
                reason=f"RSI Overbought: {rsi_current:.1f}"
            )
            signals.append(signal)
        
        self.signal_history.extend(signals)
        return signals


class ComboSignalGenerator(BaseSignalGenerator):
    """Combined signal generator using multiple indicators"""
    
    def __init__(self, symbol: str, config: Dict[str, Any]):
        super().__init__(symbol, config)
        
        # Initialize sub-generators
        self.ema_generator = EMASignalGenerator(symbol, config)
        self.rsi_generator = RSISignalGenerator(symbol, config)
        
        # Combination parameters
        self.require_confirmation = config.get('require_confirmation', True)
        self.signal_expiry_minutes = config.get('signal_expiry_minutes', 30)

    def add_price_data(self, price_data: Dict[str, float]):
        """Add price data to all sub-generators"""
        super().add_price_data(price_data)
        self.ema_generator.add_price_data(price_data)
        self.rsi_generator.add_price_data(price_data)

    def calculate_indicators(self) -> Dict[str, Any]:
        """Calculate all indicators"""
        ema_indicators = self.ema_generator.calculate_indicators()
        rsi_indicators = self.rsi_generator.calculate_indicators()
        
        return {
            'ema': ema_indicators,
            'rsi': rsi_indicators
        }

    def generate_signals(self) -> List[TradingSignal]:
        """Generate combined signals"""
        signals = []
        
        if len(self.price_history) < 50:  # Need sufficient data
            return signals
        
        # Get signals from sub-generators
        ema_signals = self.ema_generator.generate_signals()
        rsi_signals = self.rsi_generator.generate_signals()
        
        current_price = self.get_latest_price('close')
        if not current_price:
            return signals
        
        # Combine signals if confirmation is required
        if self.require_confirmation:
            # Look for confirming signals
            for ema_signal in ema_signals:
                for rsi_signal in rsi_signals:
                    if (ema_signal.signal_type == rsi_signal.signal_type and
                        abs((ema_signal.timestamp - rsi_signal.timestamp).total_seconds()) < 300):  # Within 5 minutes
                        
                        # Create combined signal
                        combined_confidence = (ema_signal.confidence + rsi_signal.confidence) / 2
                        combined_strength = SignalStrength.STRONG if combined_confidence > 0.75 else SignalStrength.MEDIUM
                        
                        # Use more conservative stop/take profit
                        stop_loss_pct = 0.007 if ema_signal.signal_type in [SignalType.ENTRY_LONG] else -0.007  # 0.7%
                        take_profit_pct = 0.015 if ema_signal.signal_type in [SignalType.ENTRY_LONG] else -0.015  # 1.5%
                        
                        signal = TradingSignal(
                            symbol=self.symbol,
                            signal_type=ema_signal.signal_type,
                            strength=combined_strength,
                            price=Decimal(str(current_price)),
                            timestamp=datetime.now(timezone.utc),
                            strategy_name="EMA_RSI_Combo",
                            confidence=combined_confidence,
                            stop_loss=Decimal(str(current_price * (1 + stop_loss_pct))),
                            take_profit=Decimal(str(current_price * (1 + take_profit_pct))),
                            indicators={
                                'ema': ema_signal.indicators,
                                'rsi': rsi_signal.indicators
                            },
                            reason=f"EMA+RSI Confirmation: {ema_signal.reason} + {rsi_signal.reason}",
                            expiry_time=datetime.now(timezone.utc) + timedelta(minutes=self.signal_expiry_minutes)
                        )
                        signals.append(signal)
        else:
            # Add all individual signals
            signals.extend(ema_signals)
            signals.extend(rsi_signals)
        
        self.signal_history.extend(signals)
        return signals


class ScalpingSignalGenerator(BaseSignalGenerator):
    """High-frequency scalping signal generator"""
    
    def __init__(self, symbol: str, config: Dict[str, Any]):
        super().__init__(symbol, config)
        
        # Scalping parameters
        self.bollinger_period = config.get('bollinger_period', 20)
        self.bollinger_std = config.get('bollinger_std', 2.0)
        self.rsi_period = config.get('rsi_period', 5)  # Shorter period for scalping
        self.min_spread_pct = config.get('min_spread_pct', 0.1)
        
        # Risk parameters
        self.stop_loss_pct = config.get('stop_loss_pct', 0.5)  # Tight stop loss
        self.take_profit_pct = config.get('take_profit_pct', 1.0)  # Quick profits

    def calculate_indicators(self) -> Dict[str, Any]:
        """Calculate scalping indicators"""
        if 'scalping_indicators' in self.indicators_cache:
            return self.indicators_cache['scalping_indicators']
        
        closes = self.get_prices('close')
        if len(closes) < self.bollinger_period:
            return {}
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.calculate_bollinger_bands(
            closes, self.bollinger_period, self.bollinger_std
        )
        
        # Fast RSI
        rsi = TechnicalIndicators.calculate_rsi(closes, self.rsi_period)
        
        indicators = {
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'rsi': rsi,
            'bb_upper_current': bb_upper[-1] if not np.isnan(bb_upper[-1]) else None,
            'bb_middle_current': bb_middle[-1] if not np.isnan(bb_middle[-1]) else None,
            'bb_lower_current': bb_lower[-1] if not np.isnan(bb_lower[-1]) else None,
            'rsi_current': rsi[-1] if not np.isnan(rsi[-1]) else None
        }
        
        self.indicators_cache['scalping_indicators'] = indicators
        return indicators

    def generate_signals(self) -> List[TradingSignal]:
        """Generate scalping signals"""
        signals = []
        
        if len(self.price_history) < self.bollinger_period + 2:
            return signals
        
        indicators = self.calculate_indicators()
        if not indicators:
            return signals
        
        current_price = self.get_latest_price('close')
        bb_upper = indicators.get('bb_upper_current')
        bb_lower = indicators.get('bb_lower_current')
        bb_middle = indicators.get('bb_middle_current')
        rsi = indicators.get('rsi_current')
        
        if not all([current_price, bb_upper, bb_lower, bb_middle, rsi]):
            return signals
        
        # Bollinger Band bounce strategy
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
        
        # Oversold bounce (near lower band + low RSI)
        if bb_position < 0.1 and rsi < 25:
            signal = TradingSignal(
                symbol=self.symbol,
                signal_type=SignalType.ENTRY_LONG,
                strength=SignalStrength.MEDIUM,
                price=Decimal(str(current_price)),
                timestamp=datetime.now(timezone.utc),
                strategy_name="Scalping_BB_RSI",
                confidence=0.7,
                stop_loss=Decimal(str(current_price * (1 - self.stop_loss_pct / 100))),
                take_profit=Decimal(str(current_price * (1 + self.take_profit_pct / 100))),
                indicators={
                    'bb_position': bb_position,
                    'rsi': rsi,
                    'bb_upper': bb_upper,
                    'bb_lower': bb_lower
                },
                reason=f"Scalping Long: BB Position {bb_position:.2f}, RSI {rsi:.1f}",
                expiry_time=datetime.now(timezone.utc) + timedelta(minutes=10)  # Short expiry
            )
            signals.append(signal)
        
        # Overbought reversal (near upper band + high RSI)
        elif bb_position > 0.9 and rsi > 75:
            signal = TradingSignal(
                symbol=self.symbol,
                signal_type=SignalType.ENTRY_SHORT,
                strength=SignalStrength.MEDIUM,
                price=Decimal(str(current_price)),
                timestamp=datetime.now(timezone.utc),
                strategy_name="Scalping_BB_RSI",
                confidence=0.7,
                stop_loss=Decimal(str(current_price * (1 + self.stop_loss_pct / 100))),
                take_profit=Decimal(str(current_price * (1 - self.take_profit_pct / 100))),
                indicators={
                    'bb_position': bb_position,
                    'rsi': rsi,
                    'bb_upper': bb_upper,
                    'bb_lower': bb_lower
                },
                reason=f"Scalping Short: BB Position {bb_position:.2f}, RSI {rsi:.1f}",
                expiry_time=datetime.now(timezone.utc) + timedelta(minutes=10)
            )
            signals.append(signal)
        
        self.signal_history.extend(signals)
        return signals


class MomentumSignalGenerator(BaseSignalGenerator):
    """Momentum-based signal generator"""
    
    def __init__(self, symbol: str, config: Dict[str, Any]):
        super().__init__(symbol, config)
        
        # Momentum parameters
        self.macd_fast = config.get('macd_fast', 12)
        self.macd_slow = config.get('macd_slow', 26)
        self.macd_signal = config.get('macd_signal', 9)
        self.ema_period = config.get('ema_period', 21)
        
        # Volume confirmation
        self.require_volume_confirmation = config.get('require_volume_confirmation', True)
        self.volume_multiplier = config.get('volume_multiplier', 1.5)

    def calculate_indicators(self) -> Dict[str, Any]:
        """Calculate momentum indicators"""
        if 'momentum_indicators' in self.indicators_cache:
            return self.indicators_cache['momentum_indicators']
        
        closes = self.get_prices('close')
        if len(closes) < max(self.macd_slow, self.ema_period):
            return {}
        
        # MACD
        macd, signal_line, histogram = TechnicalIndicators.calculate_macd(
            closes, self.macd_fast, self.macd_slow, self.macd_signal
        )
        
        # EMA for trend
        ema = TechnicalIndicators.calculate_ema(closes, self.ema_period)
        
        # Volume analysis (if available)
        volumes = self.get_prices('volume')
        volume_avg = np.mean(volumes[-20:]) if len(volumes) >= 20 else None
        
        indicators = {
            'macd': macd,
            'signal_line': signal_line,
            'histogram': histogram,
            'ema': ema,
            'macd_current': macd[-1] if not np.isnan(macd[-1]) else None,
            'signal_current': signal_line[-1] if not np.isnan(signal_line[-1]) else None,
            'histogram_current': histogram[-1] if not np.isnan(histogram[-1]) else None,
            'ema_current': ema[-1] if not np.isnan(ema[-1]) else None,
            'volume_avg': volume_avg,
            'volume_current': volumes[-1] if volumes else None
        }
        
        self.indicators_cache['momentum_indicators'] = indicators
        return indicators

    def generate_signals(self) -> List[TradingSignal]:
        """Generate momentum signals"""
        signals = []
        
        if len(self.price_history) < max(self.macd_slow, self.ema_period) + 2:
            return signals
        
        indicators = self.calculate_indicators()
        if not indicators:
            return signals
        
        current_price = self.get_latest_price('close')
        macd_current = indicators.get('macd_current')
        signal_current = indicators.get('signal_current')
        histogram_current = indicators.get('histogram_current')
        ema_current = indicators.get('ema_current')
        
        if not all([current_price, macd_current, signal_current, ema_current]):
            return signals
        
        # Get previous values for crossover detection
        macd_prev = indicators['macd'][-2] if len(indicators['macd']) > 1 else None
        signal_prev = indicators['signal_line'][-2] if len(indicators['signal_line']) > 1 else None
        
        # Volume confirmation
        volume_confirmed = True
        if self.require_volume_confirmation:
            volume_current = indicators.get('volume_current')
            volume_avg = indicators.get('volume_avg')
            if volume_current and volume_avg:
                volume_confirmed = volume_current >= volume_avg * self.volume_multiplier
        
        # MACD bullish crossover + price above EMA
        if (macd_prev and signal_prev and
            macd_prev <= signal_prev and macd_current > signal_current and
            current_price > ema_current and volume_confirmed):
            
            signal = TradingSignal(
                symbol=self.symbol,
                signal_type=SignalType.ENTRY_LONG,
                strength=SignalStrength.STRONG,
                price=Decimal(str(current_price)),
                timestamp=datetime.now(timezone.utc),
                strategy_name="Momentum_MACD",
                confidence=0.8,
                stop_loss=Decimal(str(current_price * 0.98)),  # 2% stop loss
                take_profit=Decimal(str(current_price * 1.06)), # 6% take profit
                indicators={
                    'macd': macd_current,
                    'signal': signal_current,
                    'histogram': histogram_current,
                    'ema': ema_current
                },
                reason="MACD Bullish Crossover + EMA Trend",
                expiry_time=datetime.now(timezone.utc) + timedelta(hours=4)
            )
            signals.append(signal)
        
        # MACD bearish crossover + price below EMA
        elif (macd_prev and signal_prev and
              macd_prev >= signal_prev and macd_current < signal_current and
              current_price < ema_current and volume_confirmed):
            
            signal = TradingSignal(
                symbol=self.symbol,
                signal_type=SignalType.ENTRY_SHORT,
                strength=SignalStrength.STRONG,
                price=Decimal(str(current_price)),
                timestamp=datetime.now(timezone.utc),
                strategy_name="Momentum_MACD",
                confidence=0.8,
                stop_loss=Decimal(str(current_price * 1.02)),  # 2% stop loss
                take_profit=Decimal(str(current_price * 0.94)), # 6% take profit
                indicators={
                    'macd': macd_current,
                    'signal': signal_current,
                    'histogram': histogram_current,
                    'ema': ema_current
                },
                reason="MACD Bearish Crossover + EMA Trend",
                expiry_time=datetime.now(timezone.utc) + timedelta(hours=4)
            )
            signals.append(signal)
        
        self.signal_history.extend(signals)
        return signals


class SignalManager:
    """
    Manages multiple signal generators and aggregates signals
    """
    
    def __init__(self, symbol: str, config: Dict[str, Any]):
        """
        Initialize signal manager
        
        Args:
            symbol: Trading symbol
            config: Configuration for all generators
        """
        self.symbol = symbol
        self.config = config
        
        # Initialize generators based on config
        self.generators: Dict[str, BaseSignalGenerator] = {}
        
        enabled_generators = config.get('enabled_generators', [
            'ema', 'rsi', 'combo', 'scalping', 'momentum'
        ])
        
        if 'ema' in enabled_generators:
            self.generators['ema'] = EMASignalGenerator(symbol, config.get('ema', {}))
        
        if 'rsi' in enabled_generators:
            self.generators['rsi'] = RSISignalGenerator(symbol, config.get('rsi', {}))
        
        if 'combo' in enabled_generators:
            self.generators['combo'] = ComboSignalGenerator(symbol, config.get('combo', {}))
        
        if 'scalping' in enabled_generators:
            self.generators['scalping'] = ScalpingSignalGenerator(symbol, config.get('scalping', {}))
        
        if 'momentum' in enabled_generators:
            self.generators['momentum'] = MomentumSignalGenerator(symbol, config.get('momentum', {}))
        
        # Signal aggregation
        self.all_signals: List[TradingSignal] = []
        self.last_update_time = None
        
        logger.info(f"🎯 Signal manager initialized for {symbol} with {len(self.generators)} generators")

    def add_price_data(self, price_data: Dict[str, float]):
        """Add price data to all generators"""
        for generator in self.generators.values():
            generator.add_price_data(price_data)
        
        self.last_update_time = datetime.now(timezone.utc)

    def generate_all_signals(self) -> List[TradingSignal]:
        """Generate signals from all active generators"""
        all_signals = []
        
        for name, generator in self.generators.items():
            try:
                signals = generator.generate_signals()
                all_signals.extend(signals)
                
                if signals:
                    logger.debug(f"📊 {name} generator produced {len(signals)} signals")
                    
            except Exception as e:
                logger.error(f"❌ Error in {name} generator: {e}")
        
        # Store all signals
        self.all_signals.extend(all_signals)
        
        # Filter expired signals
        now = datetime.now(timezone.utc)
        active_signals = [
            signal for signal in all_signals
            if not signal.expiry_time or signal.expiry_time > now
        ]
        
        return active_signals

    def get_best_signal(self, signal_type: SignalType = None) -> Optional[TradingSignal]:
        """Get the best signal of specified type"""
        recent_signals = [
            signal for signal in self.all_signals
            if (datetime.now(timezone.utc) - signal.timestamp).total_seconds() < 300  # Last 5 minutes
        ]
        
        if signal_type:
            recent_signals = [s for s in recent_signals if s.signal_type == signal_type]
        
        if not recent_signals:
            return None
        
        # Sort by confidence and strength
        def signal_score(signal):
            strength_score = {'weak': 1, 'medium': 2, 'strong': 3}[signal.strength.value]
            return signal.confidence * strength_score
        
        return max(recent_signals, key=signal_score)

    def assess_market_conditions(self) -> Dict[str, MarketCondition]:
        """Get market condition assessments from all generators"""
        conditions = {}
        
        for name, generator in self.generators.items():
            try:
                condition = generator.assess_market_condition()
                conditions[name] = condition
            except Exception as e:
                logger.error(f"❌ Error assessing market conditions in {name}: {e}")
        
        return conditions

    def get_signal_statistics(self) -> Dict[str, Any]:
        """Get signal generation statistics"""
        now = datetime.now(timezone.utc)
        
        # Count signals by type and time period
        recent_signals = [
            s for s in self.all_signals
            if (now - s.timestamp).total_seconds() < 3600  # Last hour
        ]
        
        signal_counts = {}
        for signal in recent_signals:
            key = f"{signal.strategy_name}_{signal.signal_type.value}"
            signal_counts[key] = signal_counts.get(key, 0) + 1
        
        # Calculate average confidence by strategy
        strategy_confidence = {}
        for signal in recent_signals:
            strategy = signal.strategy_name
            if strategy not in strategy_confidence:
                strategy_confidence[strategy] = []
            strategy_confidence[strategy].append(signal.confidence)
        
        avg_confidence = {
            strategy: np.mean(confidences)
            for strategy, confidences in strategy_confidence.items()
        }
        
        return {
            'total_signals': len(self.all_signals),
            'recent_signals': len(recent_signals),
            'signal_counts': signal_counts,
            'average_confidence': avg_confidence,
            'active_generators': list(self.generators.keys()),
            'last_update': self.last_update_time.isoformat() if self.last_update_time else None
        }