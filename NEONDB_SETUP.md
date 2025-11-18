# HyperBot NeonDB PostgreSQL Setup Guide

## 🎯 Why PostgreSQL?

**Current: JSONL Files**
- ❌ No analytics without parsing files
- ❌ No complex queries
- ❌ Hard to track ML performance
- ❌ Files grow indefinitely

**New: PostgreSQL (NeonDB)**
- ✅ Fast analytics queries
- ✅ Track ML model accuracy
- ✅ Find best trading hours/symbols
- ✅ Auto-indexing and optimization
- ✅ **FREE 0.5GB storage = ~39 YEARS of data!**

---

## 📊 Storage Analysis

**Your Current Usage:**
- ~35KB per day JSONL logs
- 12.7MB per year
- **0.5GB NeonDB = 39 years capacity** ✅

Even with 10x trading volume, you have 3+ years of storage!

---

## 🚀 NeonDB Setup (5 minutes)

### 1. Create Free NeonDB Account

```bash
# Visit: https://neon.tech
# Click "Sign Up" (free tier, no credit card)
# Create new project: "hyperbot"
# Region: Choose closest to your VPS
```

### 2. Get Connection String

After creating project, you'll see:
```
postgres://username:password@ep-xxx-xxx.region.aws.neon.tech/dbname?sslmode=require
```

Copy this entire string!

### 3. Add to .env File

```bash
# On your VPS:
cd /path/to/hyperbot
nano .env

# Add this line (replace with YOUR connection string):
DATABASE_URL=postgres://username:password@ep-xxx-xxx.region.aws.neon.tech/dbname?sslmode=require
```

Save and exit (Ctrl+X, Y, Enter)

### 4. Install Dependencies

```bash
# Pull latest code
git pull origin main

# Install PostgreSQL driver
pip install asyncpg psycopg2-binary

# Or use deploy script:
./deploy.sh install
```

### 5. Restart Bot

```bash
# If using PM2:
pm2 restart hyperbot

# If using screen:
# Stop bot (Ctrl+C)
# Start again: python3 app/bot.py
```

Bot will automatically:
- ✅ Connect to NeonDB
- ✅ Create all tables
- ✅ Start logging to database
- ✅ Keep JSONL as backup (optional)

---

## 📊 Database Schema

### Tables Created:

1. **trades** - All trade history with PnL
2. **signals** - Every signal (executed or not) with indicators
3. **ml_predictions** - Model predictions and accuracy
4. **account_snapshots** - Regular account state saves
5. **performance_metrics** - Daily/hourly aggregated stats
6. **market_data** - OHLCV for backtesting
7. **system_events** - Errors, restarts, events

### Analytics Views:

- `daily_performance` - PnL, win rate by day
- `symbol_performance` - Best/worst trading pairs
- `hourly_activity` - Optimal trading hours
- `ml_model_performance` - Model accuracy tracking

---

## 🎮 New Telegram Commands

```
/analytics          - Full performance dashboard
/analytics daily    - Last 30 days performance
/analytics symbols  - Best performing symbols
/analytics hours    - Best trading hours
/analytics ml       - ML model accuracy
/dbstats            - Database health and size
```

---

## 🔍 What You Can Now Analyze:

**Performance Queries:**
- Which hours are most profitable?
- Which symbols have best win rate?
- Average trade duration by signal type
- PnL trends over time
- Best/worst trading days

**ML Analytics:**
- Which model is most accurate?
- Feature importance tracking
- Prediction confidence vs actual results
- Model drift detection

**Risk Management:**
- Real-time drawdown tracking
- Sharpe ratio calculation
- Win/loss streaks
- Position sizing effectiveness

---

## 🛠️ Troubleshooting

**Connection Failed?**
```bash
# Check DATABASE_URL is correct
grep DATABASE_URL .env

# Test connection
python3 -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('YOUR_DATABASE_URL'))"
```

**Missing asyncpg?**
```bash
pip install asyncpg psycopg2-binary
```

**Bot can't find database?**
```bash
# Check error_handler logs
pm2 logs hyperbot --err
# Or
tail -100 logs/bot_*.log | grep -i database
```

**Want to migrate old JSONL data?**
```bash
# Run migration script (creates one for you):
python3 app/database/migrate_jsonl.py
```

---

## 📈 Storage Monitoring

**Check database size:**
```sql
-- Connect to NeonDB console or use psql:
SELECT pg_size_pretty(pg_database_size('dbname'));
```

**Check table sizes:**
```sql
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::text)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::text) DESC;
```

**NeonDB Dashboard:**
- Login to neon.tech
- View storage usage, query performance
- Set up alerts for storage limits

---

## 🔄 Migration Strategy

**Phase 1: Dual Logging (Current)**
- Bot logs to BOTH database AND JSONL
- Zero risk, can rollback anytime
- Keep JSONL as backup

**Phase 2: Database Only (Optional)**
- Remove JSONL logging after 30 days
- Free up disk space on VPS
- 100% database-driven

**Phase 3: Historical Migration (Optional)**
- Script to import old JSONL into database
- One-time operation
- Full historical analytics

---

## 🎯 Benefits You'll See Immediately:

1. **/analytics command** - Instant performance dashboard
2. **ML tracking** - See which models work best
3. **Time analysis** - Find profitable trading hours
4. **Symbol insights** - Focus on winning pairs
5. **Real-time queries** - No more parsing log files
6. **Backup safety** - Cloud-hosted, auto-replicated

---

## 💰 Cost Analysis:

**NeonDB Free Tier:**
- ✅ 0.5GB storage (39 years for you!)
- ✅ Unlimited queries
- ✅ Auto-suspend after inactivity
- ✅ Resume in milliseconds
- ✅ No credit card needed

**When to Upgrade:**
- If you hit 0.5GB (unlikely!)
- If you need >1 database
- Pro tier: $19/month, 10GB storage

For your bot: **FREE tier is perfect!** 🎉

---

## 🚀 Next Steps:

1. ✅ Create NeonDB account (2 min)
2. ✅ Add DATABASE_URL to .env (1 min)
3. ✅ Pull latest code: `git pull` (30 sec)
4. ✅ Install deps: `./deploy.sh install` (1 min)
5. ✅ Restart bot: `pm2 restart hyperbot` (30 sec)
6. ✅ Test: `/analytics` in Telegram (instant!)

**Total setup time: ~5 minutes** ⏱️

---

## 📞 Support:

After setup, test with:
```
/dbstats
```

Should show:
- ✅ Database: Connected
- ✅ Tables: 7 created
- ✅ Trades logged: X
- ✅ Storage used: ~1MB

If any issues, check:
```bash
pm2 logs hyperbot | grep -i database
```

---

**Your bot will now have enterprise-level analytics! 📊**
