import asyncio
import aiohttp
import requests
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
from loguru import logger

class SentimentAnalyzer:
    """Cryptocurrency sentiment analysis from multiple sources"""
    
    def __init__(self):
        self.vader_analyzer = SentimentIntensityAnalyzer()
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def analyze_symbol_sentiment(self, symbol: str) -> float:
        """Analyze sentiment for a specific cryptocurrency symbol"""
        try:
            # Extract base asset (e.g., ETH from ETH-USD)
            base_asset = symbol.split('-')[0].upper()
            
            # Gather sentiment from multiple sources
            sentiment_scores = []
            
            # News sentiment
            news_sentiment = await self.get_news_sentiment(base_asset)
            if news_sentiment is not None:
                sentiment_scores.append(news_sentiment)
            
            # Social media sentiment (placeholder - would need API keys)
            social_sentiment = await self.get_social_sentiment(base_asset)
            if social_sentiment is not None:
                sentiment_scores.append(social_sentiment)
            
            # Reddit sentiment (placeholder)
            reddit_sentiment = await self.get_reddit_sentiment(base_asset)
            if reddit_sentiment is not None:
                sentiment_scores.append(reddit_sentiment)
            
            # Calculate weighted average
            if sentiment_scores:
                final_sentiment = np.mean(sentiment_scores)
                logger.info(f"Sentiment for {symbol}: {final_sentiment:.3f}")
                return final_sentiment
            else:
                logger.warning(f"No sentiment data available for {symbol}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error analyzing sentiment for {symbol}: {e}")
            return 0.0
    
    async def get_news_sentiment(self, symbol: str) -> Optional[float]:
        """Get sentiment from cryptocurrency news"""
        try:
            # This would typically use a news API like NewsAPI, CryptoCompare, etc.
            # For demo purposes, we'll simulate news sentiment
            
            # Placeholder news headlines (in production, fetch from real API)
            sample_headlines = [
                f"{symbol} reaches new all-time high as institutional adoption grows",
                f"Major exchange lists {symbol} for trading, price surges",
                f"{symbol} network upgrade successful, community optimistic",
                f"Regulatory uncertainty affects {symbol} price movement",
                f"{symbol} trading volume increases amid market volatility"
            ]
            
            sentiments = []
            for headline in sample_headlines:
                # TextBlob sentiment analysis
                blob_sentiment = TextBlob(headline).sentiment.polarity
                
                # VADER sentiment analysis
                vader_sentiment = self.vader_analyzer.polarity_scores(headline)['compound']
                
                # Average the two
                combined_sentiment = (blob_sentiment + vader_sentiment) / 2
                sentiments.append(combined_sentiment)
            
            if sentiments:
                avg_sentiment = np.mean(sentiments)
                return float(avg_sentiment)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting news sentiment: {e}")
            return None
    
    async def get_social_sentiment(self, symbol: str) -> Optional[float]:
        """Get sentiment from social media (Twitter, etc.)"""
        try:
            # This would require Twitter API v2 or other social media APIs
            # For demo purposes, we'll simulate social sentiment
            
            # Simulate social media posts
            social_posts = [
                f"{symbol} looking bullish! Great fundamentals 🚀",
                f"Just bought more {symbol}, this dip is a gift 💎",
                f"{symbol} chart analysis shows strong support levels",
                f"Worried about {symbol} price action lately 😰",
                f"{symbol} community is strong, hodling for the long term",
                f"Market manipulation affecting {symbol} price",
                f"{symbol} partnerships announcement coming soon!"
            ]
            
            sentiments = []
            for post in social_posts:
                # Remove emojis for better analysis
                clean_post = ''.join(char for char in post if ord(char) < 127)
                
                # Analyze sentiment
                blob_sentiment = TextBlob(clean_post).sentiment.polarity
                vader_sentiment = self.vader_analyzer.polarity_scores(clean_post)['compound']
                
                combined_sentiment = (blob_sentiment + vader_sentiment) / 2
                sentiments.append(combined_sentiment)
            
            if sentiments:
                # Weight recent posts more heavily
                weights = np.exp(np.linspace(-1, 0, len(sentiments)))
                weighted_sentiment = np.average(sentiments, weights=weights)
                return float(weighted_sentiment)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting social sentiment: {e}")
            return None
    
    async def get_reddit_sentiment(self, symbol: str) -> Optional[float]:
        """Get sentiment from Reddit cryptocurrency discussions"""
        try:
            # This would require Reddit API (PRAW)
            # For demo purposes, we'll simulate Reddit sentiment
            
            reddit_comments = [
                f"{symbol} technical analysis suggests bullish breakout incoming",
                f"DCA into {symbol} has been working great this year",
                f"{symbol} fundamentals are solid, price will follow",
                f"Bearish on {symbol} short term, but long term bullish",
                f"{symbol} whale movements detected, could be accumulating",
                f"Market sentiment for {symbol} seems to be shifting positive",
                f"FUD around {symbol} seems overdone, good buying opportunity"
            ]
            
            sentiments = []
            for comment in reddit_comments:
                # Analyze sentiment
                blob_sentiment = TextBlob(comment).sentiment.polarity
                vader_sentiment = self.vader_analyzer.polarity_scores(comment)['compound']
                
                # Reddit comments tend to be more analytical, so weight them higher
                combined_sentiment = (blob_sentiment + vader_sentiment) / 2
                sentiments.append(combined_sentiment)
            
            if sentiments:
                avg_sentiment = np.mean(sentiments)
                return float(avg_sentiment)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting Reddit sentiment: {e}")
            return None
    
    async def get_fear_greed_index(self) -> Optional[float]:
        """Get cryptocurrency Fear and Greed Index"""
        try:
            # This would fetch from the actual Fear & Greed Index API
            # For demo purposes, we'll simulate it
            
            # Simulate Fear & Greed Index (0 = Extreme Fear, 100 = Extreme Greed)
            # Convert to -1 to 1 scale
            fear_greed_value = np.random.randint(20, 80)  # Simulate current value
            normalized_value = (fear_greed_value - 50) / 50  # Convert to -1 to 1
            
            return float(normalized_value)
            
        except Exception as e:
            logger.error(f"Error getting Fear & Greed Index: {e}")
            return None
    
    def analyze_text_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of a single text using multiple methods"""
        try:
            # TextBlob analysis
            blob = TextBlob(text)
            blob_sentiment = blob.sentiment.polarity
            blob_subjectivity = blob.sentiment.subjectivity
            
            # VADER analysis
            vader_scores = self.vader_analyzer.polarity_scores(text)
            
            return {
                'textblob_sentiment': float(blob_sentiment),
                'textblob_subjectivity': float(blob_subjectivity),
                'vader_compound': float(vader_scores['compound']),
                'vader_positive': float(vader_scores['pos']),
                'vader_neutral': float(vader_scores['neu']),
                'vader_negative': float(vader_scores['neg']),
                'combined_sentiment': float((blob_sentiment + vader_scores['compound']) / 2)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing text sentiment: {e}")
            return {'combined_sentiment': 0.0}
    
    async def get_market_sentiment_indicators(self) -> Dict[str, float]:
        """Get various market sentiment indicators"""
        try:
            indicators = {}
            
            # Fear & Greed Index
            fear_greed = await self.get_fear_greed_index()
            if fear_greed is not None:
                indicators['fear_greed_index'] = fear_greed
            
            # Volume sentiment (placeholder)
            indicators['volume_sentiment'] = self._calculate_volume_sentiment()
            
            # Market momentum sentiment
            indicators['momentum_sentiment'] = self._calculate_momentum_sentiment()
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error getting market sentiment indicators: {e}")
            return {}
    
    def _calculate_volume_sentiment(self) -> float:
        """Calculate sentiment based on volume patterns"""
        # Placeholder implementation
        # In production, this would analyze actual volume data
        return np.random.uniform(-0.3, 0.3)
    
    def _calculate_momentum_sentiment(self) -> float:
        """Calculate sentiment based on price momentum"""
        # Placeholder implementation
        # In production, this would analyze actual price momentum
        return np.random.uniform(-0.2, 0.2)
    
    async def get_comprehensive_sentiment(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Get comprehensive sentiment analysis for multiple symbols"""
        try:
            results = {}
            
            # Get market-wide indicators
            market_indicators = await self.get_market_sentiment_indicators()
            
            # Get sentiment for each symbol
            for symbol in symbols:
                symbol_sentiment = await self.analyze_symbol_sentiment(symbol)
                
                results[symbol] = {
                    'sentiment_score': symbol_sentiment,
                    'market_fear_greed': market_indicators.get('fear_greed_index', 0.0),
                    'volume_sentiment': market_indicators.get('volume_sentiment', 0.0),
                    'momentum_sentiment': market_indicators.get('momentum_sentiment', 0.0),
                    'timestamp': datetime.now().isoformat()
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting comprehensive sentiment: {e}")
            return {}

# Utility functions for advanced sentiment analysis

class SentimentSignalGenerator:
    """Generate trading signals based on sentiment analysis"""
    
    @staticmethod
    def generate_sentiment_signal(sentiment_score: float, threshold: float = 0.3) -> Dict[str, any]:
        """Generate trading signal based on sentiment score"""
        signal = "neutral"
        strength = 0.0
        
        if sentiment_score > threshold:
            signal = "bullish"
            strength = min(sentiment_score / threshold, 1.0)
        elif sentiment_score < -threshold:
            signal = "bearish"
            strength = min(abs(sentiment_score) / threshold, 1.0)
        
        return {
            'signal': signal,
            'strength': strength,
            'sentiment_score': sentiment_score,
            'confidence': strength * 0.7  # Sentiment confidence is typically lower than technical
        }
    
    @staticmethod
    def combine_sentiment_with_technical(sentiment_signal: Dict, technical_signal: Dict) -> Dict:
        """Combine sentiment signal with technical analysis"""
        # Weight sentiment lower than technical analysis
        sentiment_weight = 0.3
        technical_weight = 0.7
        
        # If signals agree, strengthen the combined signal
        if sentiment_signal['signal'] == technical_signal.get('signal', 'neutral'):
            combined_strength = (sentiment_signal['strength'] * sentiment_weight + 
                               technical_signal.get('strength', 0) * technical_weight)
            combined_strength = min(combined_strength * 1.2, 1.0)  # Boost when signals agree
        else:
            # If signals disagree, reduce combined strength
            combined_strength = (sentiment_signal['strength'] * sentiment_weight + 
                               technical_signal.get('strength', 0) * technical_weight) * 0.8
        
        return {
            'signal': technical_signal.get('signal', sentiment_signal['signal']),  # Prefer technical
            'strength': combined_strength,
            'sentiment_component': sentiment_signal['strength'] * sentiment_weight,
            'technical_component': technical_signal.get('strength', 0) * technical_weight
        }