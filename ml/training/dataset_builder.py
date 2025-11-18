"""
Dataset Builder - Convert executed trades into labeled ML training data
Processes trade logs from data/trades/ → data/model_dataset/
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)


class DatasetBuilder:
    """
    Builds ML training dataset from executed trade logs
    """
    
    def __init__(self, trades_dir: str = 'data/trades', 
                 output_dir: str = 'data/model_dataset'):
        """
        Initialize dataset builder
        
        Args:
            trades_dir: Directory containing trade logs
            output_dir: Output directory for ML dataset
        """
        self.trades_dir = Path(trades_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("📊 Dataset Builder initialized")
        logger.info(f"   Trades dir: {self.trades_dir}")
        logger.info(f"   Output dir: {self.output_dir}")
    
    def load_trade_logs(self) -> List[Dict[str, Any]]:
        """
        Load all trade logs from JSONL files
        
        Returns:
            List of trade records
        """
        trades = []
        
        for log_file in self.trades_dir.glob('trades_*.jsonl'):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        trade = json.loads(line.strip())
                        trades.append(trade)
            except Exception as e:
                logger.error(f"Error loading {log_file}: {e}")
        
        logger.info(f"📥 Loaded {len(trades)} trade records")
        return trades
    
    def build_dataset(self) -> pd.DataFrame:
        """
        Build complete training dataset
        
        Returns:
            DataFrame with features and labels
        """
        trades = self.load_trade_logs()
        
        if len(trades) < 100:
            logger.warning(f"⚠️  Only {len(trades)} trades - need at least 100 for meaningful training")
        
        # Convert to DataFrame
        records = []
        
        for trade in trades:
            try:
                signal = trade.get('signal', {})
                market = trade.get('market_data', {})
                account = trade.get('account_state', {})
                result = trade.get('result', {})
                
                record = {
                    # Timestamp
                    'timestamp': trade.get('timestamp'),
                    
                    # Signal features
                    'signal_type': 1 if signal.get('signal_type') == 'long' else -1,
                    'entry_price': signal.get('entry_price', 0),
                    'size': signal.get('size', 0),
                    'leverage': signal.get('leverage', 1),
                    'stop_loss': signal.get('stop_loss', 0),
                    'take_profit': signal.get('take_profit', 0),
                    'momentum_pct': signal.get('momentum_pct', 0),
                    
                    # Market features
                    'market_price': market.get('price', 0),
                    
                    # Account features
                    'account_equity': account.get('equity', 0),
                    'session_pnl': account.get('session_pnl', 0),
                    
                    # Result (for labeling)
                    'success': 1 if result.get('success') else 0
                }
                
                # Calculate additional features
                if record['entry_price'] > 0:
                    record['risk_reward_ratio'] = abs((record['take_profit'] - record['entry_price']) / 
                                                     (record['entry_price'] - record['stop_loss']))
                else:
                    record['risk_reward_ratio'] = 0
                
                records.append(record)
                
            except Exception as e:
                logger.error(f"Error processing trade: {e}")
                continue
        
        df = pd.DataFrame(records)
        
        logger.info(f"✅ Dataset built: {len(df)} samples")
        logger.info(f"   Features: {len(df.columns)}")
        logger.info(f"   Success rate: {df['success'].mean()*100:.1f}%")
        
        return df
    
    def save_dataset(self, df: pd.DataFrame, filename: str = 'training_dataset.csv'):
        """
        Save dataset to file
        
        Args:
            df: Dataset DataFrame
            filename: Output filename
        """
        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False)
        logger.info(f"💾 Dataset saved to {output_path}")
    
    def get_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get dataset statistics"""
        return {
            'total_samples': len(df),
            'features': list(df.columns),
            'success_rate': float(df['success'].mean()),
            'long_signals': int((df['signal_type'] == 1).sum()),
            'short_signals': int((df['signal_type'] == -1).sum()),
            'avg_momentum': float(df['momentum_pct'].mean()),
            'avg_size': float(df['size'].mean()),
            'date_range': {
                'start': df['timestamp'].min(),
                'end': df['timestamp'].max()
            }
        }


def main():
    """Main execution"""
    builder = DatasetBuilder()
    
    # Build dataset
    df = builder.build_dataset()
    
    if len(df) > 0:
        # Save dataset
        builder.save_dataset(df)
        
        # Print statistics
        stats = builder.get_statistics(df)
        print("\n" + "="*60)
        print("📊 DATASET STATISTICS")
        print("="*60)
        print(f"Total Samples: {stats['total_samples']}")
        print(f"Success Rate: {stats['success_rate']*100:.1f}%")
        print(f"Long Signals: {stats['long_signals']}")
        print(f"Short Signals: {stats['short_signals']}")
        print(f"Avg Momentum: {stats['avg_momentum']:.2f}%")
        print(f"Avg Size: {stats['avg_size']:.4f}")
        print("="*60 + "\n")
        
        if stats['total_samples'] >= 1000:
            print("✅ Ready for ML training (1,000+ samples)")
        else:
            print(f"⏳ Need {1000 - stats['total_samples']} more trades for training")
    else:
        print("❌ No trades found - run bot first to collect data")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
