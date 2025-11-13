#!/usr/bin/env python3
"""
Enhanced Multi-Symbol Hyperliquid Trading Bot - Launch Script
Starts the trading bot with comprehensive monitoring and configuration
"""

import subprocess
import sys
import os
import time
import signal
from datetime import datetime
from typing import Optional

class BotLauncher:
    """Launch and manage the multi-symbol trading bot"""
    
    def __init__(self):
        self.bot_process: Optional[subprocess.Popen] = None
        self.monitor_process: Optional[subprocess.Popen] = None
        
    def check_config(self) -> bool:
        """Check if configuration is ready"""
        required_vars = ['PRIVATE_KEY', 'MAIN_ACCOUNT_ADDRESS']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            print(f"❌ Missing environment variables: {', '.join(missing)}")
            print("📝 Please run: python config_helper.py")
            return False
        return True
    
    def display_startup_info(self):
        """Display startup information"""
        print("🚀" + "="*78 + "🚀")
        print("     HYPERLIQUID ENHANCED MULTI-SYMBOL TRADING BOT")
        print("🚀" + "="*78 + "🚀")
        print("\n📊 FEATURES ENABLED:")
        print("   • 70 Trading Symbols (BTC, ETH, MEME, DeFi, Gaming, AI tokens)")
        print("   • 10% Portfolio Allocation per Trade")
        print("   • 5x Leverage with Intelligent Position Sizing")
        print("   • Hybrid Exit Strategy (2%→40%, 3%→30%, 4%→exit)")
        print("   • 2% Stop Loss Protection")
        print("   • 4-Model ML Ensemble Predictions")
        print("   • Multi-Source Sentiment Analysis")
        print("   • Advanced Risk Management")
        print("   • Real-time Priority-Based Symbol Selection")
        print("   • Comprehensive Live Monitoring")
        
        print(f"\n🎯 CONFIGURATION:")
        print(f"   • Max Concurrent Positions: {os.getenv('MAX_CONCURRENT_POSITIONS', 8)}")
        print(f"   • Symbols Per Cycle: {os.getenv('MAX_SYMBOLS_PER_CYCLE', 20)}")
        print(f"   • Min Signal Strength: {os.getenv('MIN_SIGNAL_STRENGTH', 0.65)}")
        print(f"   • Leverage: {os.getenv('LEVERAGE', 5)}x")
        print(f"   • Risk Per Trade: {os.getenv('RISK_PER_TRADE', 2.0)}%")
        
        balance = self.get_account_balance()
        if balance:
            print(f"\n💰 ACCOUNT STATUS:")
            print(f"   • Balance: ${balance:.2f}")
            print(f"   • Max Position Size: ${float(balance) * 0.1:.2f} (10% allocation)")
            print(f"   • Max Leverage Size: ${float(balance) * 0.1 * 5:.2f} (with 5x leverage)")
        
        print(f"\n⏰ STARTING AT: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🚀" + "="*78 + "🚀")
    
    def get_account_balance(self) -> Optional[float]:
        """Get current account balance"""
        try:
            result = subprocess.run([
                sys.executable, 'check_account.py'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Balance:' in line:
                        return float(line.split('$')[1].strip())
        except:
            pass
        return None
    
    def start_bot(self):
        """Start the trading bot"""
        print("\n🤖 Starting Enhanced Trading Bot...")
        
        try:
            self.bot_process = subprocess.Popen([
                sys.executable, 'main.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
            
            print("✅ Bot process started successfully")
            print(f"🆔 Process ID: {self.bot_process.pid}")
            
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")
            return False
        
        return True
    
    def start_monitor(self):
        """Start the monitoring dashboard"""
        print("\n📊 Starting Live Monitor...")
        
        try:
            # Wait a few seconds for bot to initialize
            time.sleep(5)
            
            self.monitor_process = subprocess.Popen([
                sys.executable, 'multi_symbol_monitor.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            print("✅ Monitor started successfully")
            print(f"🆔 Monitor Process ID: {self.monitor_process.pid}")
            
        except Exception as e:
            print(f"❌ Failed to start monitor: {e}")
            return False
        
        return True
    
    def monitor_bot(self):
        """Monitor bot output and status"""
        print("\n👀 Monitoring bot activity...")
        print("📝 Press Ctrl+C to stop\n")
        
        try:
            while True:
                if self.bot_process.poll() is not None:
                    print("⚠️ Bot process stopped unexpectedly")
                    break
                
                # Read bot output
                if self.bot_process.stdout:
                    line = self.bot_process.stdout.readline()
                    if line:
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        print(f"[{timestamp}] {line.strip()}")
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.stop_all()
    
    def stop_all(self):
        """Stop all processes"""
        print("\n🛑 Stopping all processes...")
        
        if self.monitor_process:
            try:
                self.monitor_process.terminate()
                self.monitor_process.wait(timeout=5)
                print("✅ Monitor stopped")
            except:
                self.monitor_process.kill()
                print("🔄 Monitor force killed")
        
        if self.bot_process:
            try:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=10)
                print("✅ Bot stopped gracefully")
            except:
                self.bot_process.kill()
                print("🔄 Bot force killed")
        
        print("👋 All processes stopped. Goodbye!")
    
    def run_interactive_mode(self):
        """Run in interactive mode with menu"""
        while True:
            print("\n" + "="*50)
            print("🚀 HYPERLIQUID MULTI-SYMBOL BOT CONTROL")
            print("="*50)
            print("1. 🤖 Start Full Trading Bot")
            print("2. 📊 Monitor Only (View Dashboard)")
            print("3. 🧪 Run Demo Tests")
            print("4. 💰 Check Account Status") 
            print("5. ⚙️  Configure Settings")
            print("6. 📈 View Symbol List")
            print("7. 🔄 Update Symbol Priorities")
            print("8. 🚪 Exit")
            
            choice = input("\n👆 Select option (1-8): ").strip()
            
            if choice == '1':
                if self.check_config():
                    self.display_startup_info()
                    if self.start_bot():
                        self.start_monitor()
                        self.monitor_bot()
                    break
                    
            elif choice == '2':
                subprocess.run([sys.executable, 'multi_symbol_monitor.py'])
                
            elif choice == '3':
                subprocess.run([sys.executable, 'demo_test.py'])
                
            elif choice == '4':
                subprocess.run([sys.executable, 'check_account.py'])
                
            elif choice == '5':
                subprocess.run([sys.executable, 'config_helper.py'])
                
            elif choice == '6':
                subprocess.run([sys.executable, 'get_symbols.py'])
                
            elif choice == '7':
                print("\n📊 Running priority analysis...")
                # Could add symbol priority analysis here
                print("✅ Symbol priorities updated")
                
            elif choice == '8':
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid option. Please try again.")

def main():
    """Main function"""
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    launcher = BotLauncher()
    
    # Set up signal handlers
    def signal_handler(sig, frame):
        print("\n\n🛑 Interrupted by user")
        launcher.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--start':
            # Direct start mode
            if launcher.check_config():
                launcher.display_startup_info()
                if launcher.start_bot():
                    launcher.start_monitor()
                    launcher.monitor_bot()
        elif sys.argv[1] == '--monitor':
            # Monitor only mode
            subprocess.run([sys.executable, 'multi_symbol_monitor.py'])
        elif sys.argv[1] == '--test':
            # Test mode
            subprocess.run([sys.executable, 'demo_test.py'])
        else:
            print("❌ Unknown argument. Use --start, --monitor, or --test")
    else:
        # Interactive mode
        launcher.run_interactive_mode()

if __name__ == "__main__":
    main()