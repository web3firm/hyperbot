import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import asyncio
from loguru import logger

class FeatureEngineer:
    """Feature engineering for ML models"""
    
    @staticmethod
    def create_technical_features(df: pd.DataFrame) -> pd.DataFrame:
        """Create technical indicator features"""
        features = df.copy()
        
        # Price features
        features['price_change'] = features['close'].pct_change()
        features['price_change_2'] = features['close'].pct_change(2)
        features['price_change_5'] = features['close'].pct_change(5)
        features['high_low_pct'] = (features['high'] - features['low']) / features['close']
        features['open_close_pct'] = (features['close'] - features['open']) / features['open']
        
        # Moving averages
        for period in [5, 10, 20, 50]:
            features[f'sma_{period}'] = features['close'].rolling(window=period).mean()
            features[f'ema_{period}'] = features['close'].ewm(span=period).mean()
            features[f'price_vs_sma_{period}'] = features['close'] / features[f'sma_{period}'] - 1
            features[f'price_vs_ema_{period}'] = features['close'] / features[f'ema_{period}'] - 1
        
        # Volatility features
        features['volatility_10'] = features['close'].rolling(window=10).std()
        features['volatility_20'] = features['close'].rolling(window=20).std()
        features['atr_14'] = FeatureEngineer._calculate_atr(features, 14)
        
        # Volume features (if available)
        if 'volume' in features.columns:
            features['volume_sma_10'] = features['volume'].rolling(window=10).mean()
            features['volume_ratio'] = features['volume'] / features['volume_sma_10']
            features['price_volume'] = features['close'] * features['volume']
        
        # Momentum features
        features['rsi_14'] = FeatureEngineer._calculate_rsi(features['close'], 14)
        features['rsi_7'] = FeatureEngineer._calculate_rsi(features['close'], 7)
        
        # MACD features
        ema_12 = features['close'].ewm(span=12).mean()
        ema_26 = features['close'].ewm(span=26).mean()
        features['macd'] = ema_12 - ema_26
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        features['macd_histogram'] = features['macd'] - features['macd_signal']
        
        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        sma_20 = features['close'].rolling(window=bb_period).mean()
        bb_std_dev = features['close'].rolling(window=bb_period).std()
        features['bb_upper'] = sma_20 + (bb_std_dev * bb_std)
        features['bb_lower'] = sma_20 - (bb_std_dev * bb_std)
        features['bb_position'] = (features['close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        
        # Stochastic
        features['stoch_k'], features['stoch_d'] = FeatureEngineer._calculate_stochastic(features, 14, 3)
        
        # Support/Resistance levels
        features['resistance_distance'] = FeatureEngineer._calculate_resistance_distance(features)
        features['support_distance'] = FeatureEngineer._calculate_support_distance(features)
        
        # Time-based features
        if 'timestamp' in features.columns:
            features['hour'] = pd.to_datetime(features['timestamp']).dt.hour
            features['day_of_week'] = pd.to_datetime(features['timestamp']).dt.dayofweek
            features['hour_sin'] = np.sin(2 * np.pi * features['hour'] / 24)
            features['hour_cos'] = np.cos(2 * np.pi * features['hour'] / 24)
            features['dow_sin'] = np.sin(2 * np.pi * features['day_of_week'] / 7)
            features['dow_cos'] = np.cos(2 * np.pi * features['day_of_week'] / 7)
        
        return features
    
    @staticmethod
    def _calculate_atr(df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close_prev = np.abs(df['high'] - df['close'].shift(1))
        low_close_prev = np.abs(df['low'] - df['close'].shift(1))
        true_range = np.maximum(high_low, np.maximum(high_close_prev, low_close_prev))
        return true_range.rolling(window=period).mean()
    
    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def _calculate_stochastic(df: pd.DataFrame, k_period: int, d_period: int) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic oscillator"""
        lowest_low = df['low'].rolling(window=k_period).min()
        highest_high = df['high'].rolling(window=k_period).max()
        k = 100 * (df['close'] - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()
        return k, d
    
    @staticmethod
    def _calculate_resistance_distance(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """Calculate distance to nearest resistance level"""
        rolling_max = df['high'].rolling(window=window).max()
        return (rolling_max - df['close']) / df['close']
    
    @staticmethod
    def _calculate_support_distance(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """Calculate distance to nearest support level"""
        rolling_min = df['low'].rolling(window=window).min()
        return (df['close'] - rolling_min) / df['close']
    
    @staticmethod
    def create_target_variable(df: pd.DataFrame, forward_periods: int = 5, threshold: float = 0.01) -> pd.Series:
        """Create target variable for classification"""
        future_returns = df['close'].shift(-forward_periods) / df['close'] - 1
        
        # Three-class classification: bullish, bearish, neutral
        target = pd.Series(1, index=df.index)  # neutral
        target[future_returns > threshold] = 2  # bullish
        target[future_returns < -threshold] = 0  # bearish
        
        return target

class MLPredictor:
    """Machine learning prediction engine"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        self.is_trained = False
        self.model_dir = "ml/models"
        self.ensure_model_dir()
        
    def ensure_model_dir(self):
        """Ensure model directory exists"""
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
    
    def initialize_models(self) -> Dict[str, Any]:
        """Initialize ML models"""
        models = {
            'random_forest': RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            ),
            'logistic_regression': LogisticRegression(
                random_state=42,
                max_iter=1000,
                solver='liblinear'
            ),
            'svm': SVC(
                kernel='rbf',
                probability=True,
                random_state=42
            )
        }
        return models
    
    async def prepare_data(self, market_data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare data for ML training"""
        try:
            # Feature engineering
            features_df = FeatureEngineer.create_technical_features(market_data)
            
            # Create target variable
            target = FeatureEngineer.create_target_variable(features_df)
            
            # Select feature columns (exclude OHLC and target)
            exclude_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
            feature_cols = [col for col in features_df.columns if col not in exclude_cols]
            
            # Handle missing values
            features_df[feature_cols] = features_df[feature_cols].fillna(method='bfill')
            features_df[feature_cols] = features_df[feature_cols].fillna(method='ffill')
            
            # Remove rows with any remaining NaN values
            valid_idx = ~(features_df[feature_cols].isna().any(axis=1) | target.isna())
            features_df = features_df[valid_idx]
            target = target[valid_idx]
            
            self.feature_columns = feature_cols
            
            return features_df[feature_cols], target
            
        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return pd.DataFrame(), pd.Series()
    
    async def train_models(self, market_data: pd.DataFrame = None) -> bool:
        """Train ML models"""
        try:
            if market_data is None or len(market_data) < 100:
                logger.warning("Insufficient data for training")
                return False
            
            logger.info("Starting ML model training...")
            
            # Prepare data
            X, y = await self.prepare_data(market_data)
            
            if X.empty or len(y) == 0:
                logger.error("No valid data for training")
                return False
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train models
            models = self.initialize_models()
            trained_models = {}
            
            for name, model in models.items():
                try:
                    logger.info(f"Training {name}...")
                    
                    # Train model
                    if name == 'svm':
                        # Use scaled data for SVM
                        model.fit(X_train_scaled, y_train)
                        predictions = model.predict(X_test_scaled)
                    else:
                        model.fit(X_train, y_train)
                        predictions = model.predict(X_test)
                    
                    # Evaluate
                    accuracy = accuracy_score(y_test, predictions)
                    logger.info(f"{name} accuracy: {accuracy:.3f}")
                    
                    # Cross-validation
                    if name != 'svm':  # Skip CV for SVM due to computational cost
                        cv_scores = cross_val_score(model, X_train, y_train, cv=3)
                        logger.info(f"{name} CV score: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
                    
                    trained_models[name] = model
                    
                except Exception as e:
                    logger.error(f"Error training {name}: {e}")
            
            if trained_models:
                self.models = trained_models
                self.scalers['standard'] = scaler
                self.is_trained = True
                
                # Save models
                await self.save_models()
                
                logger.info("ML models trained successfully")
                return True
            else:
                logger.error("No models were successfully trained")
                return False
                
        except Exception as e:
            logger.error(f"Error in train_models: {e}")
            return False
    
    async def predict(self, market_data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Make prediction using ensemble of models"""
        try:
            if not self.is_trained or not self.models:
                # Try to load models
                await self.load_models()
                if not self.is_trained:
                    logger.warning("Models not trained, cannot make prediction")
                    return None
            
            # Prepare features
            features_df = FeatureEngineer.create_technical_features(market_data)
            
            if self.feature_columns:
                X = features_df[self.feature_columns].tail(1)
            else:
                logger.error("Feature columns not defined")
                return None
            
            # Handle missing values
            X = X.fillna(method='bfill').fillna(method='ffill')
            
            if X.isna().any().any():
                logger.warning("Missing values in features, cannot make prediction")
                return None
            
            # Make predictions with each model
            predictions = {}
            probabilities = {}
            
            for name, model in self.models.items():
                try:
                    if name == 'svm' and 'standard' in self.scalers:
                        # Use scaled features for SVM
                        X_scaled = self.scalers['standard'].transform(X)
                        pred = model.predict(X_scaled)[0]
                        prob = model.predict_proba(X_scaled)[0]
                    else:
                        pred = model.predict(X)[0]
                        if hasattr(model, 'predict_proba'):
                            prob = model.predict_proba(X)[0]
                        else:
                            prob = np.array([0.33, 0.33, 0.34])  # Default uniform distribution
                    
                    predictions[name] = pred
                    probabilities[name] = prob
                    
                except Exception as e:
                    logger.error(f"Error predicting with {name}: {e}")
            
            if not predictions:
                return None
            
            # Ensemble prediction (majority vote)
            prediction_counts = {}
            for pred in predictions.values():
                prediction_counts[pred] = prediction_counts.get(pred, 0) + 1
            
            ensemble_prediction = max(prediction_counts, key=prediction_counts.get)
            
            # Average probabilities
            avg_probabilities = np.mean(list(probabilities.values()), axis=0)
            confidence = np.max(avg_probabilities)
            
            # Convert prediction to direction
            direction_map = {0: 'short', 1: 'neutral', 2: 'long'}
            direction = direction_map.get(ensemble_prediction, 'neutral')
            
            result = {
                'direction': direction,
                'confidence': float(confidence),
                'prediction': int(ensemble_prediction),
                'probabilities': {
                    'bearish': float(avg_probabilities[0]),
                    'neutral': float(avg_probabilities[1]),
                    'bullish': float(avg_probabilities[2])
                },
                'individual_predictions': {name: int(pred) for name, pred in predictions.items()},
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in predict: {e}")
            return None
    
    async def save_models(self):
        """Save trained models to disk"""
        try:
            if not self.models:
                return
            
            # Save models
            for name, model in self.models.items():
                model_path = os.path.join(self.model_dir, f"{name}.joblib")
                joblib.dump(model, model_path)
            
            # Save scalers
            if self.scalers:
                scaler_path = os.path.join(self.model_dir, "scalers.joblib")
                joblib.dump(self.scalers, scaler_path)
            
            # Save feature columns
            if self.feature_columns:
                features_path = os.path.join(self.model_dir, "feature_columns.joblib")
                joblib.dump(self.feature_columns, features_path)
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    async def load_models(self):
        """Load trained models from disk"""
        try:
            # Load models
            models = {}
            for model_name in ['random_forest', 'gradient_boosting', 'logistic_regression', 'svm']:
                model_path = os.path.join(self.model_dir, f"{model_name}.joblib")
                if os.path.exists(model_path):
                    models[model_name] = joblib.load(model_path)
            
            if models:
                self.models = models
                
                # Load scalers
                scaler_path = os.path.join(self.model_dir, "scalers.joblib")
                if os.path.exists(scaler_path):
                    self.scalers = joblib.load(scaler_path)
                
                # Load feature columns
                features_path = os.path.join(self.model_dir, "feature_columns.joblib")
                if os.path.exists(features_path):
                    self.feature_columns = joblib.load(features_path)
                
                self.is_trained = True
                logger.info("Models loaded successfully")
            else:
                logger.warning("No saved models found")
                
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def get_model_performance(self) -> Dict[str, Any]:
        """Get model performance metrics"""
        # This would be implemented with validation data
        # For now, return placeholder metrics
        return {
            'accuracy': 0.65,
            'precision': 0.63,
            'recall': 0.62,
            'f1_score': 0.61,
            'last_trained': datetime.now().isoformat()
        }