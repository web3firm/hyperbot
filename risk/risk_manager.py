import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from loguru import logger

@dataclass
class RiskMetrics:
    """Risk metrics for portfolio management"""
    portfolio_value: float
    total_exposure: float
    daily_pnl: float
    unrealized_pnl: float
    max_drawdown: float
    var_95: float  # Value at Risk 95%
    sharpe_ratio: float
    risk_score: float

class RiskManager:
    """Advanced risk management system"""
    
    def __init__(self, config):
        self.config = config
        self.position_history = []
        self.pnl_history = []
        self.drawdown_history = []
        self.risk_alerts = []
        
    def calculate_position_size(self, 
                              portfolio_value: float,
                              signal_strength: float,
                              volatility: float,
                              correlation_factor: float = 1.0) -> float:
        """Calculate optimal position size using Kelly Criterion and risk management"""
        try:
            # Base position size (percentage of portfolio)
            base_percentage = self.config.initial_portfolio_percentage / 100
            
            # Adjust for signal strength
            signal_adjusted = base_percentage * signal_strength
            
            # Volatility adjustment (reduce size for high volatility)
            vol_adjustment = 1.0 / (1.0 + volatility * 2)
            
            # Correlation adjustment (reduce size if correlated positions exist)
            correlation_adjustment = 1.0 / correlation_factor
            
            # Final position size
            position_percentage = signal_adjusted * vol_adjustment * correlation_adjustment
            
            # Apply maximum position size limit
            max_position_percentage = self.config.risk_per_trade / 100
            position_percentage = min(position_percentage, max_position_percentage)
            
            # Calculate dollar amount
            position_size = portfolio_value * position_percentage
            
            # Apply leverage
            leveraged_size = position_size * self.config.leverage
            
            logger.info(f"Position size calculation: {position_size:.2f} -> {leveraged_size:.2f} (leveraged)")
            
            return leveraged_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def check_risk_limits(self, portfolio_metrics: RiskMetrics) -> Dict[str, bool]:
        """Check if current portfolio exceeds risk limits"""
        risk_violations = {}
        
        try:
            # Maximum drawdown check
            if portfolio_metrics.max_drawdown >= self.config.max_drawdown:
                risk_violations['max_drawdown'] = True
                logger.warning(f"Max drawdown exceeded: {portfolio_metrics.max_drawdown:.2f}%")
            
            # Daily loss limit check
            daily_loss_pct = abs(portfolio_metrics.daily_pnl) / portfolio_metrics.portfolio_value * 100
            if portfolio_metrics.daily_pnl < 0 and daily_loss_pct >= self.config.daily_loss_limit:
                risk_violations['daily_loss_limit'] = True
                logger.warning(f"Daily loss limit exceeded: {daily_loss_pct:.2f}%")
            
            # Portfolio heat check (total exposure vs portfolio value)
            exposure_ratio = portfolio_metrics.total_exposure / portfolio_metrics.portfolio_value
            max_exposure_ratio = (self.config.max_trades * self.config.risk_per_trade) / 100
            
            if exposure_ratio > max_exposure_ratio:
                risk_violations['exposure_limit'] = True
                logger.warning(f"Exposure limit exceeded: {exposure_ratio:.2f}")
            
            # Risk score check
            if portfolio_metrics.risk_score > 8.0:  # High risk threshold
                risk_violations['risk_score'] = True
                logger.warning(f"High risk score: {portfolio_metrics.risk_score:.2f}")
            
            return risk_violations
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return {}
    
    def calculate_portfolio_risk(self, positions: List[Dict], market_data: Dict) -> RiskMetrics:
        """Calculate comprehensive portfolio risk metrics"""
        try:
            if not positions:
                return RiskMetrics(0, 0, 0, 0, 0, 0, 0, 0)
            
            # Calculate portfolio metrics
            total_value = sum(abs(pos.get('position_value', 0)) for pos in positions)
            total_exposure = sum(abs(pos.get('exposure', 0)) for pos in positions)
            unrealized_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
            
            # Daily PnL calculation
            daily_pnl = self._calculate_daily_pnl(positions)
            
            # Maximum drawdown
            max_drawdown = self._calculate_max_drawdown()
            
            # Value at Risk (VaR)
            var_95 = self._calculate_var_95(positions, market_data)
            
            # Sharpe ratio
            sharpe_ratio = self._calculate_sharpe_ratio()
            
            # Overall risk score
            risk_score = self._calculate_risk_score(total_exposure, total_value, max_drawdown, var_95)
            
            return RiskMetrics(
                portfolio_value=total_value,
                total_exposure=total_exposure,
                daily_pnl=daily_pnl,
                unrealized_pnl=unrealized_pnl,
                max_drawdown=max_drawdown,
                var_95=var_95,
                sharpe_ratio=sharpe_ratio,
                risk_score=risk_score
            )
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            return RiskMetrics(0, 0, 0, 0, 0, 0, 0, 0)
    
    def _calculate_daily_pnl(self, positions: List[Dict]) -> float:
        """Calculate daily PnL"""
        try:
            daily_pnl = 0.0
            for position in positions:
                # This would calculate PnL since market open
                unrealized_pnl = position.get('unrealized_pnl', 0)
                # For simplicity, using unrealized PnL as proxy for daily PnL
                daily_pnl += unrealized_pnl
            return daily_pnl
        except:
            return 0.0
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from historical data"""
        try:
            if not self.pnl_history:
                return 0.0
            
            # Calculate cumulative returns
            cumulative_returns = np.cumsum(self.pnl_history)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max * 100
            
            max_drawdown = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0
            return max_drawdown
            
        except:
            return 0.0
    
    def _calculate_var_95(self, positions: List[Dict], market_data: Dict) -> float:
        """Calculate 95% Value at Risk"""
        try:
            if not positions:
                return 0.0
            
            # Simplified VaR calculation
            # In production, would use Monte Carlo or historical simulation
            
            total_exposure = sum(abs(pos.get('exposure', 0)) for pos in positions)
            
            # Estimate portfolio volatility (simplified)
            avg_volatility = 0.02  # 2% daily volatility assumption
            
            # 95% VaR (1.65 standard deviations for normal distribution)
            var_95 = total_exposure * avg_volatility * 1.65
            
            return var_95
            
        except:
            return 0.0
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from historical returns"""
        try:
            if len(self.pnl_history) < 30:  # Need at least 30 days
                return 0.0
            
            returns = np.array(self.pnl_history[-30:])  # Last 30 days
            
            if len(returns) == 0 or np.std(returns) == 0:
                return 0.0
            
            # Assuming risk-free rate of 0 for crypto
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(365)  # Annualized
            
            return sharpe
            
        except:
            return 0.0
    
    def _calculate_risk_score(self, exposure: float, portfolio_value: float, 
                            max_drawdown: float, var_95: float) -> float:
        """Calculate overall risk score (0-10 scale)"""
        try:
            if portfolio_value == 0:
                return 0.0
            
            # Exposure ratio component (0-3 points)
            exposure_ratio = exposure / portfolio_value if portfolio_value > 0 else 0
            exposure_score = min(exposure_ratio * 3, 3.0)
            
            # Drawdown component (0-3 points)
            drawdown_score = min(max_drawdown / 10 * 3, 3.0)
            
            # VaR component (0-2 points)
            var_ratio = var_95 / portfolio_value if portfolio_value > 0 else 0
            var_score = min(var_ratio * 20, 2.0)
            
            # Market volatility component (0-2 points)
            # This would incorporate current market volatility
            market_vol_score = 1.0  # Placeholder
            
            total_score = exposure_score + drawdown_score + var_score + market_vol_score
            return min(total_score, 10.0)
            
        except:
            return 5.0  # Default medium risk
    
    def update_risk_history(self, portfolio_metrics: RiskMetrics):
        """Update risk tracking history"""
        try:
            # Add to PnL history
            self.pnl_history.append(portfolio_metrics.daily_pnl)
            
            # Keep only last 365 days
            if len(self.pnl_history) > 365:
                self.pnl_history = self.pnl_history[-365:]
            
            # Add to drawdown history
            self.drawdown_history.append(portfolio_metrics.max_drawdown)
            if len(self.drawdown_history) > 365:
                self.drawdown_history = self.drawdown_history[-365:]
                
        except Exception as e:
            logger.error(f"Error updating risk history: {e}")
    
    def should_stop_trading(self, portfolio_metrics: RiskMetrics) -> Tuple[bool, str]:
        """Determine if trading should be stopped due to risk"""
        try:
            risk_violations = self.check_risk_limits(portfolio_metrics)
            
            # Critical risk violations that require stopping trading
            critical_violations = ['max_drawdown', 'daily_loss_limit']
            
            for violation in critical_violations:
                if risk_violations.get(violation, False):
                    return True, f"Critical risk violation: {violation}"
            
            # High risk score
            if portfolio_metrics.risk_score >= 9.0:
                return True, "Extremely high risk score"
            
            return False, "Risk levels acceptable"
            
        except Exception as e:
            logger.error(f"Error checking if should stop trading: {e}")
            return False, "Error in risk assessment"
    
    def get_position_correlation(self, symbol1: str, symbol2: str, 
                               price_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate correlation between two positions"""
        try:
            if symbol1 not in price_data or symbol2 not in price_data:
                return 0.0
            
            # Get price data
            prices1 = price_data[symbol1]['close']
            prices2 = price_data[symbol2]['close']
            
            # Calculate returns
            returns1 = prices1.pct_change().dropna()
            returns2 = prices2.pct_change().dropna()
            
            # Align series
            aligned_data = pd.concat([returns1, returns2], axis=1, join='inner')
            
            if len(aligned_data) < 10:  # Need minimum data points
                return 0.0
            
            correlation = aligned_data.iloc[:, 0].corr(aligned_data.iloc[:, 1])
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.0
    
    def calculate_portfolio_correlation_adjustment(self, new_symbol: str, 
                                                 existing_positions: List[str],
                                                 price_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate correlation adjustment factor for new position"""
        try:
            if not existing_positions:
                return 1.0
            
            correlations = []
            for existing_symbol in existing_positions:
                corr = self.get_position_correlation(new_symbol, existing_symbol, price_data)
                correlations.append(abs(corr))
            
            if not correlations:
                return 1.0
            
            # Average correlation with existing positions
            avg_correlation = np.mean(correlations)
            
            # Adjustment factor: higher correlation = larger adjustment factor
            adjustment_factor = 1.0 + avg_correlation
            
            return adjustment_factor
            
        except Exception as e:
            logger.error(f"Error calculating correlation adjustment: {e}")
            return 1.0
    
    def generate_risk_report(self, portfolio_metrics: RiskMetrics) -> Dict[str, any]:
        """Generate comprehensive risk report"""
        try:
            risk_violations = self.check_risk_limits(portfolio_metrics)
            should_stop, stop_reason = self.should_stop_trading(portfolio_metrics)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'portfolio_metrics': {
                    'portfolio_value': portfolio_metrics.portfolio_value,
                    'total_exposure': portfolio_metrics.total_exposure,
                    'daily_pnl': portfolio_metrics.daily_pnl,
                    'unrealized_pnl': portfolio_metrics.unrealized_pnl,
                    'max_drawdown': portfolio_metrics.max_drawdown,
                    'var_95': portfolio_metrics.var_95,
                    'sharpe_ratio': portfolio_metrics.sharpe_ratio,
                    'risk_score': portfolio_metrics.risk_score
                },
                'risk_violations': risk_violations,
                'should_stop_trading': should_stop,
                'stop_reason': stop_reason,
                'risk_level': self._get_risk_level(portfolio_metrics.risk_score),
                'recommendations': self._generate_recommendations(portfolio_metrics, risk_violations)
            }
            
        except Exception as e:
            logger.error(f"Error generating risk report: {e}")
            return {}
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Get risk level description"""
        if risk_score <= 2.0:
            return "Very Low"
        elif risk_score <= 4.0:
            return "Low"
        elif risk_score <= 6.0:
            return "Medium"
        elif risk_score <= 8.0:
            return "High"
        else:
            return "Very High"
    
    def _generate_recommendations(self, portfolio_metrics: RiskMetrics, 
                                risk_violations: Dict[str, bool]) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        try:
            if risk_violations.get('max_drawdown', False):
                recommendations.append("Reduce position sizes to limit drawdown")
            
            if risk_violations.get('daily_loss_limit', False):
                recommendations.append("Stop trading for the day - daily loss limit reached")
            
            if risk_violations.get('exposure_limit', False):
                recommendations.append("Reduce overall portfolio exposure")
            
            if portfolio_metrics.risk_score > 7.0:
                recommendations.append("Consider reducing leverage and position sizes")
            
            if portfolio_metrics.sharpe_ratio < 0.5:
                recommendations.append("Review trading strategies - low risk-adjusted returns")
            
            if not recommendations:
                recommendations.append("Risk levels are within acceptable limits")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["Error generating recommendations"]