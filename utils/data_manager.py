import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import asyncio
from datetime import datetime, timedelta
from loguru import logger
from hyperliquid.info import Info
from hyperliquid.utils import constants

class DataManager:
    """Manages market data collection and processing"""
    
    def __init__(self, info_client: Info):
        self.info = info_client
        self.data_cache = {}
        self.cache_expiry = {}
        self.cache_duration = timedelta(minutes=1)  # Cache for 1 minute
        
    async def get_market_data(self, symbol: str, timeframe: str = '1m', limit: int = 500) -> pd.DataFrame:
        """Get historical market data for a symbol"""
        try:
            # Check cache first
            cache_key = f"{symbol}_{timeframe}_{limit}"
            if self._is_cached_data_valid(cache_key):
                return self.data_cache[cache_key]
            
            # Convert symbol format for Hyperliquid (e.g., ETH-USD -> ETH)
            hl_symbol = symbol.split('-')[0]
            
            # Get candlestick data
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - (limit * self._timeframe_to_ms(timeframe))
            
            # Fetch candlestick data using correct API method
            candles = self.info.candles_snapshot(
                name=hl_symbol,
                interval=timeframe,
                startTime=start_time,
                endTime=end_time
            )
            
            if not candles:
                logger.warning(f"No data received for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = self._process_candle_data(candles)
            
            # Cache the data
            self.data_cache[cache_key] = df
            self.cache_expiry[cache_key] = datetime.now() + self.cache_duration
            
            logger.info(f"Retrieved {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def get_current_price(self, symbol: str) -> Dict[str, float]:
        """Get current price for a symbol"""
        try:
            # Convert symbol format
            hl_symbol = symbol.split('-')[0]
            
            # Get current price from ticker
            all_mids = self.info.all_mids()
            
            if hl_symbol in all_mids:
                price = float(all_mids[hl_symbol])
                return {
                    'symbol': symbol,
                    'price': price,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.warning(f"Price not found for {symbol}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return {}
    
    async def get_orderbook(self, symbol: str) -> Dict:
        """Get orderbook data for a symbol"""
        try:
            hl_symbol = symbol.split('-')[0]
            
            # Get L2 orderbook
            orderbook = self.info.l2_snapshot(hl_symbol)
            
            if not orderbook:
                return {}
            
            return {
                'symbol': symbol,
                'bids': orderbook.get('levels', [[]])[1],  # Buy orders
                'asks': orderbook.get('levels', [[]])[0],  # Sell orders
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting orderbook for {symbol}: {e}")
            return {}
    
    async def get_market_summary(self, symbol: str) -> Dict:
        """Get market summary including 24h stats"""
        try:
            hl_symbol = symbol.split('-')[0]
            
            # Get 24h statistics
            meta_and_universe = self.info.meta_and_universe()
            
            if not meta_and_universe or 'universe' not in meta_and_universe:
                return {}
            
            universe = meta_and_universe['universe']
            symbol_info = None
            
            for coin_info in universe:
                if coin_info['name'] == hl_symbol:
                    symbol_info = coin_info
                    break
            
            if not symbol_info:
                logger.warning(f"Symbol info not found for {symbol}")
                return {}
            
            # Get current price
            current_price_data = await self.get_current_price(symbol)
            current_price = current_price_data.get('price', 0)
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'market_cap': symbol_info.get('maxLeverage', 0),  # Using maxLeverage as proxy
                'volume_24h': 0,  # Would need separate API call
                'price_change_24h': 0,  # Would need historical comparison
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market summary for {symbol}: {e}")
            return {}
    
    def _process_candle_data(self, candles: List) -> pd.DataFrame:
        """Process raw candle data into DataFrame"""
        try:
            if not candles:
                return pd.DataFrame()
            
            # Expected format: [timestamp, open, high, low, close, volume]
            data = []
            for candle in candles:
                if len(candle) >= 6:  # Ensure we have all required fields
                    data.append({
                        'timestamp': pd.to_datetime(candle['t'], unit='ms'),
                        'open': float(candle['o']),
                        'high': float(candle['h']),
                        'low': float(candle['l']),
                        'close': float(candle['c']),
                        'volume': float(candle['v']) if 'v' in candle else 0.0
                    })
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # Ensure we have numeric data
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove any rows with NaN values
            df.dropna(inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error processing candle data: {e}")
            return pd.DataFrame()
    
    def _timeframe_to_ms(self, timeframe: str) -> int:
        """Convert timeframe string to milliseconds"""
        timeframe_map = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        }
        return timeframe_map.get(timeframe, 60 * 1000)  # Default to 1 minute
    
    def _is_cached_data_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.data_cache or cache_key not in self.cache_expiry:
            return False
        
        return datetime.now() < self.cache_expiry[cache_key]
    
    async def get_multiple_market_data(self, symbols: List[str], timeframe: str = '1m', limit: int = 500) -> Dict[str, pd.DataFrame]:
        """Get market data for multiple symbols"""
        try:
            tasks = []
            for symbol in symbols:
                task = self.get_market_data(symbol, timeframe, limit)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            data_dict = {}
            for i, symbol in enumerate(symbols):
                if isinstance(results[i], pd.DataFrame) and not results[i].empty:
                    data_dict[symbol] = results[i]
                else:
                    logger.warning(f"No data retrieved for {symbol}")
            
            return data_dict
            
        except Exception as e:
            logger.error(f"Error getting multiple market data: {e}")
            return {}
    
    async def get_market_volatility(self, symbol: str, period: int = 20) -> float:
        """Calculate market volatility for a symbol"""
        try:
            market_data = await self.get_market_data(symbol, limit=period * 2)
            
            if market_data.empty or len(market_data) < period:
                return 0.02  # Default 2% volatility
            
            # Calculate returns
            returns = market_data['close'].pct_change().dropna()
            
            # Calculate volatility (standard deviation of returns)
            volatility = returns.std()
            
            # Annualize volatility (assuming daily data)
            annualized_vol = volatility * np.sqrt(365)
            
            return float(annualized_vol)
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return 0.02
    
    def calculate_support_resistance(self, data: pd.DataFrame, window: int = 20) -> Dict[str, List[float]]:
        """Calculate support and resistance levels"""
        try:
            if data.empty or len(data) < window:
                return {'support': [], 'resistance': []}
            
            highs = data['high']
            lows = data['low']
            
            # Find local maxima (resistance)
            resistance_levels = []
            for i in range(window, len(highs) - window):
                if highs.iloc[i] == highs.iloc[i-window:i+window+1].max():
                    resistance_levels.append(highs.iloc[i])
            
            # Find local minima (support)
            support_levels = []
            for i in range(window, len(lows) - window):
                if lows.iloc[i] == lows.iloc[i-window:i+window+1].min():
                    support_levels.append(lows.iloc[i])
            
            # Remove duplicates and sort
            resistance_levels = sorted(list(set(resistance_levels)), reverse=True)
            support_levels = sorted(list(set(support_levels)))
            
            return {
                'support': support_levels[:5],  # Top 5 support levels
                'resistance': resistance_levels[:5]  # Top 5 resistance levels
            }
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {e}")
            return {'support': [], 'resistance': []}
    
    async def get_funding_rates(self, symbol: str) -> Dict:
        """Get funding rates for a symbol"""
        try:
            hl_symbol = symbol.split('-')[0]
            
            # Get meta information which includes funding rates
            meta_and_universe = self.info.meta_and_universe()
            
            if not meta_and_universe or 'universe' not in meta_and_universe:
                return {}
            
            universe = meta_and_universe['universe']
            symbol_info = None
            
            for coin_info in universe:
                if coin_info['name'] == hl_symbol:
                    symbol_info = coin_info
                    break
            
            if not symbol_info:
                return {}
            
            return {
                'symbol': symbol,
                'funding_rate': 0.0,  # Would need specific funding rate endpoint
                'next_funding_time': datetime.now().isoformat(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting funding rates for {symbol}: {e}")
            return {}
    
    def cleanup_cache(self):
        """Clean up expired cache entries"""
        try:
            current_time = datetime.now()
            expired_keys = [
                key for key, expiry_time in self.cache_expiry.items()
                if current_time >= expiry_time
            ]
            
            for key in expired_keys:
                if key in self.data_cache:
                    del self.data_cache[key]
                if key in self.cache_expiry:
                    del self.cache_expiry[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                
        except Exception as e:
            logger.error(f"Error cleaning cache: {e}")
    
    async def validate_symbol(self, symbol: str) -> bool:
        """Validate if a symbol is available for trading"""
        try:
            hl_symbol = symbol.split('-')[0]
            
            # Get available markets
            meta_and_universe = self.info.meta_and_universe()
            
            if not meta_and_universe or 'universe' not in meta_and_universe:
                return False
            
            universe = meta_and_universe['universe']
            
            for coin_info in universe:
                if coin_info['name'] == hl_symbol:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {e}")
            return False