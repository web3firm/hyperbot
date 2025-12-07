"""
Swing Trading Strategy
Institutional-grade strategy with adaptive risk and smart money concepts.

Features:
- ATR-based dynamic TP/SL (not fixed percentages)
- Market regime detection (trending/ranging/volatile)
- Smart Money Concepts (FVG, Order Blocks, Liquidity Sweeps, BoS)
- Multi-timeframe alignment
- Session-aware trading
- Order flow integration
- VWAP confluence (institutional fair value)
- Divergence detection (RSI/MACD)
- Funding rate filter (avoid squeezes)
- Volume confirmation (filter fake moves)
- Adaptive position sizing

Target: 65%+ win rate with 3:1+ R:R in favorable conditions.
"""

import os
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
from collections import deque
from datetime import datetime, timezone

from app.strategies.adaptive.market_regime import MarketRegimeDetector, MarketRegime
from app.strategies.adaptive.smart_money import SmartMoneyAnalyzer
from app.strategies.adaptive.multi_timeframe import MultiTimeframeAnalyzer
from app.strategies.adaptive.order_flow import OrderFlowAnalyzer
from app.strategies.adaptive.session_manager import SessionManager
from app.strategies.adaptive.adaptive_risk import AdaptiveRiskManager
from app.strategies.adaptive.pro_filters import ProTradingFilters
from app.strategies.adaptive.vwap import VWAPCalculator
from app.strategies.adaptive.divergence import DivergenceDetector
from app.strategies.adaptive.funding_rate import FundingRateFilter

logger = logging.getLogger(__name__)


class SwingStrategy:
    """
    Institutional-Grade Swing Trading Strategy
    
    Combines multiple professional trading concepts:
    1. Adaptive Risk (ATR-based TP/SL)
    2. Market Regime Detection
    3. Smart Money Concepts
    4. Multi-Timeframe Analysis
    5. Session-Aware Trading
    6. Order Flow Analysis
    
    Signal Score System (0-10):
    - Technical indicators: 4 points max
    - SMC alignment: 2 points max
    - HTF alignment: 2 points max
    - Order flow: 2 points max
    
    Entry threshold: 6/10 (60%) minimum
    """
    
    def __init__(self, symbol: str, config: Dict[str, Any] = None):
        """Initialize world-class strategy."""
        self.symbol = symbol
        self.config = config or {}
        
        # Core parameters from environment
        self.leverage = int(os.getenv('MAX_LEVERAGE', '5'))
        self.base_position_size = Decimal(os.getenv('POSITION_SIZE_PCT', '50'))
        
        # TP/SL is calculated dynamically by AdaptiveRiskManager using ATR
        # See ATR_SL_MULTIPLIER and ATR_TP_MULTIPLIER in .env
        
        # Signal threshold - BE PATIENT, WAIT FOR A+ SETUPS
        self.min_signal_score = int(os.getenv('MIN_SIGNAL_SCORE', '7'))  # Raised to 7/10
        self.max_signal_score = 10
        
        # Technical indicator periods
        self.rsi_period = 14
        self.ema_fast = 21
        self.ema_slow = 50
        self.adx_period = 14
        self.atr_period = 14
        self.bb_period = 20
        
        # RSI thresholds (adaptive based on regime)
        self.rsi_oversold_base = 30
        self.rsi_overbought_base = 70
        
        # Volume confirmation threshold
        self.volume_multiplier = Decimal(os.getenv('VOLUME_CONFIRMATION_MULT', '1.2'))  # Require 20% above average
        
        # Initialize adaptive components
        self.regime_detector = MarketRegimeDetector()
        self.smc_analyzer = SmartMoneyAnalyzer()
        self.mtf_analyzer = MultiTimeframeAnalyzer()
        self.order_flow = OrderFlowAnalyzer()
        self.session_manager = SessionManager()
        self.risk_manager = AdaptiveRiskManager()
        self.pro_filters = ProTradingFilters(symbol)  # Professional trading filters
        
        # NEW: Pro-level enhancements
        self.vwap_calculator = VWAPCalculator()
        self.divergence_detector = DivergenceDetector()
        self.funding_filter = FundingRateFilter()
        
        # State tracking - BE PATIENT, DON'T OVERTRADE
        self.last_signal_time: Optional[datetime] = None
        self.signal_cooldown_seconds = int(os.getenv('SWING_COOLDOWN', '600'))  # 10 min between signals (was 5)
        self.recent_prices: deque = deque(maxlen=200)
        
        # Indicator cache
        self._indicator_cache = {}
        self._cache_timestamp: Optional[datetime] = None
        
        # RSI smoothing state
        self.rsi_avg_gain: Optional[Decimal] = None
        self.rsi_avg_loss: Optional[Decimal] = None
        
        # RSI/MACD history for divergence detection
        self.rsi_history: deque = deque(maxlen=30)
        self.macd_history: deque = deque(maxlen=30)
        
        # Statistics
        self.signals_generated = 0
        self.trades_taken = 0
        
        # Log initialization
        logger.info(f"🌟 WORLD-CLASS Swing Strategy initialized for {symbol}")
        logger.info(f"   Leverage: {self.leverage}x")
        logger.info(f"   Base Position: {self.base_position_size}%")
        logger.info(f"   Signal Threshold: {self.min_signal_score}/{self.max_signal_score}")
        logger.info(f"   Components: Regime, SMC, MTF, OrderFlow, Sessions, AdaptiveRisk")
    
    async def generate_signal(
        self,
        market_data: Dict[str, Any],
        account_state: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal with full analysis.
        
        Args:
            market_data: Market data containing candles
            account_state: Current account state
        
        Returns:
            Signal dict or None if no trade
        """
        # Extract candles from market_data
        candles = market_data.get('candles', [])
        htf_candles = market_data.get('htf_candles')
        
        if not candles or len(candles) < 100:
            return None
        
        # Check cooldown
        if not self._check_cooldown():
            return None
        
        # Extract prices
        prices = [Decimal(str(c.get('close', c.get('c', 0)))) for c in candles]
        current_price = prices[-1]
        
        # ==================== ANALYSIS LAYERS ====================
        
        # 1. Calculate technical indicators
        indicators = self._calculate_indicators(candles)
        if not indicators:
            return None
        
        # Store indicator history for divergence detection
        rsi = indicators.get('rsi')
        macd = indicators.get('macd', {})
        if rsi:
            self.rsi_history.append(rsi)
        if macd:
            self.macd_history.append(macd)
        
        # 2. Detect market regime
        regime, regime_confidence, regime_params = self.regime_detector.detect_regime(
            candles,
            adx=indicators.get('adx'),
            atr=indicators.get('atr'),
            bb_bandwidth=indicators.get('bb_bandwidth'),
            ema_fast=indicators.get('ema_fast'),
            ema_slow=indicators.get('ema_slow'),
        )
        
        # CRITICAL: Don't trade when regime is UNKNOWN (insufficient data/analysis)
        from app.strategies.adaptive.market_regime import MarketRegime
        if regime == MarketRegime.UNKNOWN:
            logger.debug(f"⏸️ Regime UNKNOWN for {self.symbol} - skipping signal generation")
            return None
        
        # 3. Smart Money Concepts analysis
        smc_analysis = self.smc_analyzer.analyze(candles)
        
        # 4. Multi-timeframe analysis
        if htf_candles:
            for interval, htf_data in htf_candles.items():
                if htf_data:
                    self.mtf_analyzer.analyze_timeframe(htf_data, interval)
        
        # 5. Order flow analysis
        of_analysis = self.order_flow.analyze_from_candles(candles)
        
        # 6. Session parameters
        session_params = self.session_manager.get_session_params()
        
        # ==================== SIGNAL GENERATION ====================
        
        # Calculate directional scores
        long_score = self._calculate_signal_score(
            direction='long',
            indicators=indicators,
            regime=regime,
            regime_params=regime_params,
            smc_analysis=smc_analysis,
            of_analysis=of_analysis,
            current_price=current_price,
        )
        
        short_score = self._calculate_signal_score(
            direction='short',
            indicators=indicators,
            regime=regime,
            regime_params=regime_params,
            smc_analysis=smc_analysis,
            of_analysis=of_analysis,
            current_price=current_price,
        )
        
        # Apply enhanced scoring (VWAP, Divergence, Volume)
        long_enhanced, long_details = self._calculate_enhanced_score('long', candles, indicators, long_score)
        short_enhanced, short_details = self._calculate_enhanced_score('short', candles, indicators, short_score)
        
        # Log both scores for visibility
        logger.debug(f"📊 Scores: LONG={long_enhanced}/12 | SHORT={short_enhanced}/12 | Regime={regime.value}")
        
        # Determine best direction
        if long_enhanced >= self.min_signal_score and long_enhanced > short_enhanced:
            direction = 'long'
            score = long_enhanced
            score_details = long_details
            logger.info(f"✅ LONG wins: {long_enhanced} vs SHORT {short_enhanced}")
        elif short_enhanced >= self.min_signal_score and short_enhanced > long_enhanced:
            direction = 'short'
            score = short_enhanced
            score_details = short_details
            logger.info(f"✅ SHORT wins: {short_enhanced} vs LONG {long_enhanced}")
        else:
            # No valid signal - log why
            if long_enhanced > 0 or short_enhanced > 0:
                logger.debug(f"⏳ No signal: LONG={long_enhanced}/7, SHORT={short_enhanced}/7 (need 7+)")
            return None
        
        # Check HTF alignment
        htf_aligned, htf_score, htf_reason = self.mtf_analyzer.should_take_trade(direction)
        if not htf_aligned and htf_score < 0.4:
            logger.debug(f"❌ Signal rejected: HTF misalignment ({htf_reason})")
            return None
        
        # Check session
        should_trade, session_reason = self.session_manager.should_trade()
        if not should_trade:
            logger.debug(f"❌ Signal rejected: {session_reason}")
            return None
        
        # ==================== PRO TRADING FILTERS ====================
        # Final quality gate - professional-level confirmation
        
        btc_candles = market_data.get('btc_candles')  # BTC correlation check
        pro_result = self.pro_filters.check_all(
            direction=direction,
            candles=candles,
            indicators=indicators,
            btc_candles=btc_candles,
        )
        
        if not pro_result.passed:
            logger.debug(f"❌ Signal rejected by pro filter: {pro_result.reason}")
            return None
        
        logger.info(f"✅ Pro filters passed: {pro_result.reason} (confidence: {pro_result.confidence:.1%})")
        
        # ==================== RISK CALCULATION ====================
        
        atr = indicators.get('atr')
        if atr is None or atr <= 0:
            logger.warning(f"⚠️ Invalid ATR for {self.symbol}, using fallback")
            atr = current_price * Decimal('0.01')  # 1% of price as fallback
        
        # Ensure ATR is Decimal
        atr = Decimal(str(atr)) if not isinstance(atr, Decimal) else atr
        
        # Get adaptive TP/SL levels
        risk_levels = self.risk_manager.calculate_adaptive_levels(
            entry_price=Decimal(str(current_price)),
            direction=direction,
            atr=atr,
            regime_params=regime_params,
            session_params=session_params,
        )
        
        # Apply session aggression to position size
        aggression = Decimal(str(session_params.get('aggression', 1.0)))
        position_size = self.base_position_size * aggression
        
        # Apply regime position size adjustment
        regime_size_mult = Decimal(str(regime_params.get('position_size_mult', 1.0)))
        position_size *= regime_size_mult
        
        # Cap at maximum
        max_size = Decimal(os.getenv('MAX_POSITION_SIZE_PCT', '55'))
        position_size = min(position_size, max_size)
        
        # ==================== BUILD SIGNAL ====================
        
        # Calculate size in tokens (approximate)
        account_value = Decimal(str(account_state.get('account_value', 1000)))
        size_usd = account_value * position_size / 100 * self.leverage
        size_tokens = size_usd / current_price
        
        signal = {
            'symbol': self.symbol,
            'direction': direction,
            'side': 'buy' if direction == 'long' else 'sell',  # For compatibility
            'signal_type': f'{direction.upper()} (Swing)',
            'entry_price': float(current_price),
            'stop_loss': risk_levels['stop_loss'],
            'take_profit': risk_levels['take_profit'],
            'position_size_pct': float(position_size),
            'size': float(size_tokens),  # Token size for order execution
            'leverage': self.leverage,
            
            # Scoring
            'signal_score': score,
            'max_score': self.max_signal_score,
            'score_pct': score / self.max_signal_score * 100,
            
            # Analysis results
            'regime': regime.value,
            'regime_confidence': regime_confidence,
            'htf_alignment': htf_score,
            'htf_reason': htf_reason,
            'smc_bias': smc_analysis.get('bias'),
            'order_flow_bias': of_analysis.get('bias'),
            'session': session_params.get('session'),
            
            # Risk metrics
            'sl_pct': risk_levels['sl_pct'],
            'tp_pct': risk_levels['tp_pct'],
            'rr_ratio': risk_levels['rr_ratio'],
            'atr': float(atr),
            
            # Telegram display
            'reason': f"Regime: {regime.value}, Score: {score}/{self.max_signal_score}",
            
            # Metadata
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'strategy': 'Swing',
        }
        
        # Update state
        self.last_signal_time = datetime.now(timezone.utc)
        self.signals_generated += 1
        
        logger.info(f"🎯 SIGNAL: {direction.upper()} {self.symbol}")
        logger.info(f"   Score: {score}/{self.max_signal_score} ({score/self.max_signal_score*100:.0f}%)")
        logger.info(f"   Entry: ${current_price:.4f}")
        logger.info(f"   SL: ${risk_levels['stop_loss']:.4f} ({risk_levels['sl_pct']:.2f}%)")
        logger.info(f"   TP: ${risk_levels['take_profit']:.4f} ({risk_levels['tp_pct']:.2f}%)")
        logger.info(f"   R:R: {risk_levels['rr_ratio']:.1f}:1")
        logger.info(f"   Regime: {regime.value} | HTF: {htf_score:.0%} | SMC: {smc_analysis.get('bias')}")
        
        return signal
    
    def _calculate_signal_score(
        self,
        direction: str,
        indicators: Dict,
        regime: MarketRegime,
        regime_params: Dict,
        smc_analysis: Dict,
        of_analysis: Dict,
        current_price: Decimal,
    ) -> int:
        """
        Calculate comprehensive signal score.
        
        Scoring (0-10):
        - Technical: 0-4 points
        - SMC: 0-2 points
        - HTF: 0-2 points
        - Order Flow: 0-2 points
        """
        score = 0
        
        # ========== TECHNICAL (0-4 points) ==========
        rsi = indicators.get('rsi')
        ema_fast = indicators.get('ema_fast')
        ema_slow = indicators.get('ema_slow')
        adx = indicators.get('adx')
        macd = indicators.get('macd', {})
        
        if direction == 'long':
            # RSI condition (0-1 point)
            if rsi and rsi < 40:
                score += 1
            elif rsi and rsi < 50:
                score += 0.5
            
            # EMA alignment (0-1 point)
            if ema_fast and ema_slow and ema_fast > ema_slow:
                score += 1
            
            # ADX trend strength (0-1 point)
            if adx and adx > 20:
                if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                    score += 1
                else:
                    score += 0.5
            
            # MACD (0-1 point)
            if macd.get('histogram') and macd['histogram'] > 0:
                score += 1
            elif macd.get('macd') and macd.get('signal') and macd['macd'] > macd['signal']:
                score += 0.5
        
        else:  # short
            # RSI condition
            if rsi and rsi > 60:
                score += 1
            elif rsi and rsi > 50:
                score += 0.5
            
            # EMA alignment
            if ema_fast and ema_slow and ema_fast < ema_slow:
                score += 1
            
            # ADX trend strength
            if adx and adx > 20:
                if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                    score += 1
                else:
                    score += 0.5
            
            # MACD
            if macd.get('histogram') and macd['histogram'] < 0:
                score += 1
            elif macd.get('macd') and macd.get('signal') and macd['macd'] < macd['signal']:
                score += 0.5
        
        # ========== SMART MONEY (0-2 points) ==========
        smc_bias = smc_analysis.get('bias')
        smc_signals = smc_analysis.get('signals', [])
        
        # Bias alignment
        if (direction == 'long' and smc_bias == 'bullish') or \
           (direction == 'short' and smc_bias == 'bearish'):
            score += 1
        
        # SMC signals
        for sig in smc_signals:
            if sig.get('direction') == direction:
                if sig.get('type') == 'liquidity_sweep':
                    score += 1  # Strongest signal
                elif sig.get('type') in ['fvg_fill', 'order_block']:
                    score += 0.5
        
        # Cap SMC at 2
        score = min(score, 6)  # Tech(4) + SMC(2)
        
        # ========== HTF ALIGNMENT (0-2 points) ==========
        htf_score, _ = self.mtf_analyzer.get_alignment_score(direction)
        score += htf_score * 2  # Scale 0-1 to 0-2
        
        # ========== ORDER FLOW (0-2 points) ==========
        of_bias = of_analysis.get('bias')
        
        if (direction == 'long' and of_bias == 'bullish') or \
           (direction == 'short' and of_bias == 'bearish'):
            score += 1
        
        # POC proximity bonus
        if of_analysis.get('poc_distance_pct') is not None:
            poc_dist = abs(of_analysis['poc_distance_pct'])
            if poc_dist < 0.5:  # Within 0.5% of POC
                score += 1
        
        # Whale activity
        whale_bias, buy_count, sell_count = self.order_flow.get_whale_bias()
        if (direction == 'long' and whale_bias == 'bullish') or \
           (direction == 'short' and whale_bias == 'bearish'):
            score += 0.5
        
        # ========== NEW: BREAK OF STRUCTURE (0-1.5 points) ==========
        bos_score, bos_reason = self.smc_analyzer.get_bos_signal(direction)
        if bos_score > 0:
            score += bos_score
            logger.debug(f"   BoS: +{bos_score:.1f} ({bos_reason})")
        elif bos_score < 0:
            score += bos_score  # Penalty
            logger.debug(f"   BoS: {bos_score:.1f} ({bos_reason})")
        
        return int(score)
    
    def _calculate_enhanced_score(
        self,
        direction: str,
        candles: List[Dict],
        indicators: Dict,
        base_score: int,
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate enhanced score with new pro-level features.
        
        Additional Scoring:
        - VWAP confluence: 0-1.5 points
        - Divergence: 0-2 points
        - Volume confirmation: 0-1 point
        
        Args:
            direction: 'long' or 'short'
            candles: OHLCV candles
            indicators: Calculated indicators
            base_score: Score from _calculate_signal_score
            
        Returns:
            Tuple of (enhanced_score, details)
        """
        score = base_score
        details = {'base_score': base_score}
        
        # ========== VWAP CONFLUENCE (0-1.5 points) ==========
        vwap_analysis = self.vwap_calculator.calculate_from_candles(candles)
        vwap_score, vwap_reason = self.vwap_calculator.get_vwap_signal(direction, vwap_analysis)
        if vwap_score != 0:
            score += vwap_score
            details['vwap'] = {'score': vwap_score, 'reason': vwap_reason}
            logger.debug(f"   VWAP: +{vwap_score:.1f} ({vwap_reason})")
        
        # ========== DIVERGENCE (0-2 points) ==========
        if len(self.rsi_history) >= 15 and len(self.macd_history) >= 15:
            div_analysis = self.divergence_detector.detect_all(
                candles, 
                list(self.rsi_history), 
                list(self.macd_history)
            )
            div_score, div_reason = self.divergence_detector.get_divergence_score(direction)
            if div_score != 0:
                score += div_score
                details['divergence'] = {'score': div_score, 'reason': div_reason}
                logger.debug(f"   Divergence: +{div_score:.1f} ({div_reason})")
        
        # ========== VOLUME CONFIRMATION (0-1 point) ==========
        volume_ok, volume_ratio = self._check_volume_confirmation(candles)
        if volume_ok:
            score += 1
            details['volume'] = {'confirmed': True, 'ratio': volume_ratio}
            logger.debug(f"   Volume: +1 (ratio: {volume_ratio:.1f}x)")
        else:
            # Slight penalty for below-average volume
            score -= 0.5
            details['volume'] = {'confirmed': False, 'ratio': volume_ratio}
            logger.debug(f"   Volume: -0.5 (weak: {volume_ratio:.1f}x)")
        
        return int(score), details
    
    def _check_volume_confirmation(self, candles: List[Dict]) -> Tuple[bool, float]:
        """
        Check if current volume is above average (confirms move is real).
        
        VOLUME IS TRUTH: No volume = fake move.
        
        Args:
            candles: OHLCV candles
            
        Returns:
            Tuple of (is_confirmed, volume_ratio)
        """
        if len(candles) < 20:
            return True, 1.0  # Not enough data, pass
        
        volumes = [float(c.get('volume', c.get('v', 0))) for c in candles]
        avg_volume = sum(volumes[-20:]) / 20
        current_volume = volumes[-1]
        
        if avg_volume <= 0:
            return True, 1.0
        
        volume_ratio = current_volume / avg_volume
        is_confirmed = Decimal(str(volume_ratio)) >= self.volume_multiplier
        
        return is_confirmed, volume_ratio
    
    def _calculate_indicators(self, candles: List[Dict]) -> Optional[Dict]:
        """Calculate all technical indicators."""
        prices = [Decimal(str(c.get('close', c.get('c', 0)))) for c in candles]
        
        if len(prices) < 50:
            return None
        
        return {
            'rsi': self._calculate_rsi(prices),
            'ema_fast': self._calculate_ema(prices, self.ema_fast),
            'ema_slow': self._calculate_ema(prices, self.ema_slow),
            'adx': self._calculate_adx(candles),
            'atr': self._calculate_atr(candles),
            'macd': self._calculate_macd(prices),
            'bb_bandwidth': self._calculate_bb_bandwidth(prices),
        }
    
    def _calculate_rsi(self, prices: List[Decimal], period: int = 14) -> Optional[Decimal]:
        """Calculate RSI with Wilder's smoothing."""
        if len(prices) < period + 1:
            return None
        
        current_change = prices[-1] - prices[-2]
        current_gain = max(current_change, Decimal('0'))
        current_loss = abs(min(current_change, Decimal('0')))
        
        if self.rsi_avg_gain is None:
            changes = [prices[i] - prices[i-1] for i in range(-period, 0)]
            gains = [max(c, Decimal('0')) for c in changes]
            losses = [abs(min(c, Decimal('0'))) for c in changes]
            self.rsi_avg_gain = sum(gains) / period
            self.rsi_avg_loss = sum(losses) / period
        else:
            self.rsi_avg_gain = (self.rsi_avg_gain * (period - 1) + current_gain) / period
            self.rsi_avg_loss = (self.rsi_avg_loss * (period - 1) + current_loss) / period
        
        if self.rsi_avg_loss == 0:
            return Decimal('100')
        
        rs = self.rsi_avg_gain / self.rsi_avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_ema(self, prices: List[Decimal], period: int) -> Optional[Decimal]:
        """Calculate EMA."""
        if len(prices) < period:
            return None
        
        multiplier = Decimal('2') / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_macd(self, prices: List[Decimal]) -> Dict:
        """Calculate MACD with proper signal line (EMA of MACD values)."""
        # Need at least 26 + 9 = 35 prices to calculate signal line
        if len(prices) < 35:
            # Fallback: calculate just MACD line without proper signal
            ema_12 = self._calculate_ema(prices, 12)
            ema_26 = self._calculate_ema(prices, 26)
            if not ema_12 or not ema_26:
                return {}
            macd_line = ema_12 - ema_26
            return {
                'macd': macd_line,
                'signal': macd_line,  # No proper signal available
                'histogram': Decimal('0'),
            }
        
        # Calculate MACD values for the last 9 periods to build signal line
        macd_values = []
        for i in range(9):
            # Use prices up to position -(8-i) from the end
            # i=0: prices[:-8], i=1: prices[:-7], ... i=8: prices[:] (all)
            end_idx = len(prices) - (8 - i) if i < 8 else len(prices)
            price_slice = prices[:end_idx]
            
            ema_12 = self._calculate_ema(price_slice, 12)
            ema_26 = self._calculate_ema(price_slice, 26)
            
            if ema_12 and ema_26:
                macd_values.append(ema_12 - ema_26)
        
        if len(macd_values) < 9:
            return {}
        
        # Current MACD line is the last value
        macd_line = macd_values[-1]
        
        # Signal line is EMA(9) of MACD values
        signal_line = self._calculate_ema(macd_values, 9) or macd_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': macd_line - signal_line,
        }
    
    def _calculate_adx(self, candles: List[Dict], period: int = 14) -> Optional[Decimal]:
        """Calculate ADX with proper True Range (using H/L/C, not just close)."""
        if len(candles) < period * 2:
            return None
        
        tr_list, plus_dm_list, minus_dm_list = [], [], []
        
        for i in range(1, len(candles)):
            # Get OHLC data
            high = Decimal(str(candles[i].get('high', candles[i].get('h', 0))))
            low = Decimal(str(candles[i].get('low', candles[i].get('l', 0))))
            prev_close = Decimal(str(candles[i-1].get('close', candles[i-1].get('c', 0))))
            prev_high = Decimal(str(candles[i-1].get('high', candles[i-1].get('h', 0))))
            prev_low = Decimal(str(candles[i-1].get('low', candles[i-1].get('l', 0))))
            
            # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)
            
            # Directional Movement using high/low
            up_move = high - prev_high
            down_move = prev_low - low
            
            # +DM: up move is greater than down move and positive
            plus_dm = up_move if (up_move > down_move and up_move > 0) else Decimal('0')
            # -DM: down move is greater than up move and positive
            minus_dm = down_move if (down_move > up_move and down_move > 0) else Decimal('0')
            
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)
        
        if len(tr_list) < period:
            return None
        
        atr = sum(tr_list[-period:]) / period
        plus_dm = sum(plus_dm_list[-period:]) / period
        minus_dm = sum(minus_dm_list[-period:]) / period
        
        plus_di = (plus_dm / atr * 100) if atr > 0 else Decimal('0')
        minus_di = (minus_dm / atr * 100) if atr > 0 else Decimal('0')
        
        di_sum = plus_di + minus_di
        di_diff = abs(plus_di - minus_di)
        
        return (di_diff / di_sum * 100) if di_sum > 0 else Decimal('0')
    
    def _calculate_atr(self, candles: List[Dict], period: int = 14) -> Optional[Decimal]:
        """Calculate ATR."""
        if len(candles) < period:
            return None
        
        tr_list = []
        for i in range(1, len(candles)):
            high = Decimal(str(candles[i].get('high', candles[i].get('h', 0))))
            low = Decimal(str(candles[i].get('low', candles[i].get('l', 0))))
            prev_close = Decimal(str(candles[i-1].get('close', candles[i-1].get('c', 0))))
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)
        
        return sum(tr_list[-period:]) / period
    
    def _calculate_bb_bandwidth(self, prices: List[Decimal], period: int = 20) -> Optional[Decimal]:
        """Calculate Bollinger Band bandwidth."""
        if len(prices) < period:
            return None
        
        recent = prices[-period:]
        sma = sum(recent) / period
        variance = sum((p - sma) ** 2 for p in recent) / period
        std = variance ** Decimal('0.5')
        
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        
        return ((upper - lower) / sma) * 100
    
    def _check_cooldown(self) -> bool:
        """Check if signal cooldown has passed."""
        if not self.last_signal_time:
            return True
        
        elapsed = (datetime.now(timezone.utc) - self.last_signal_time).total_seconds()
        return elapsed >= self.signal_cooldown_seconds
    
    def invalidate_indicator_cache(self):
        """Invalidate cache when new candle arrives."""
        self._indicator_cache = {}
        self._cache_timestamp = None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics for Telegram /stats command."""
        return {
            'strategy': 'Swing',
            'signals': self.signals_generated,
            'trades': self.signals_generated,  # Approximate
            'current_regime': self.regime_detector.current_regime.value if hasattr(self, 'regime_detector') else 'unknown',
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get strategy status for monitoring."""
        return {
            'strategy': 'Swing',
            'symbol': self.symbol,
            'signals_generated': self.signals_generated,
            'current_regime': self.regime_detector.current_regime.value,
            'regime_confidence': self.regime_detector.regime_confidence,
            'htf_bias': self.mtf_analyzer.get_htf_bias(),
            'session': self.session_manager.get_current_session().value,
            'cooldown_remaining': max(0, self.signal_cooldown_seconds - 
                (datetime.now(timezone.utc) - self.last_signal_time).total_seconds()
                if self.last_signal_time else 0),
        }
    
    def record_trade_execution(self, signal: Dict[str, Any], result: Dict[str, Any]):
        """
        Record a trade execution for strategy performance tracking.
        
        Args:
            signal: The signal that was executed
            result: The execution result from the order manager
        """
        # Track execution
        success = result.get('success', False) or result.get('status') == 'ok'
        
        if success:
            logger.info(f"✅ Trade executed for {signal.get('symbol', self.symbol)}: "
                       f"{signal.get('side', 'unknown').upper()} @ {signal.get('entry_price', 0)}")
        else:
            logger.warning(f"⚠️ Trade execution issue for {signal.get('symbol', self.symbol)}: {result}")
        
        # Could add more tracking here (trade history, performance metrics, etc.)
    
    def revalidate_signal(self, signal: Dict[str, Any], current_price: Decimal) -> bool:
        """
        Revalidate a signal before execution.
        Ensures market conditions haven't changed significantly.
        
        Args:
            signal: The original signal
            current_price: Current market price
            
        Returns:
            True if signal is still valid, False if conditions changed
        """
        entry_price = Decimal(str(signal.get('entry_price', 0)))
        side = signal.get('side', '').lower()
        
        if entry_price <= 0:
            return True  # Can't validate without entry price
        
        # Calculate price deviation
        deviation_pct = abs(current_price - entry_price) / entry_price * 100
        
        # Allow up to 0.5% deviation for swing trades
        max_deviation = Decimal('0.5')
        
        if deviation_pct > max_deviation:
            logger.warning(f"Signal invalidated: price moved {deviation_pct:.2f}% from entry")
            return False
        
        # For buys, price shouldn't have dropped too much (might indicate reversal)
        # For sells, price shouldn't have risen too much
        if side == 'buy' and current_price < entry_price * Decimal('0.995'):
            logger.warning(f"Buy signal invalidated: price dropped below entry")
            return False
        elif side == 'sell' and current_price > entry_price * Decimal('1.005'):
            logger.warning(f"Sell signal invalidated: price rose above entry")
            return False
        
        return True
