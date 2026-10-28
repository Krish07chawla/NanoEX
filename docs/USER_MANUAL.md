# User manual: NanoEX Web

> Everything here is paper trading with virtual money. No real orders are placed and nothing is financial advice.

## Getting started
1. Open the app (http://localhost:8080 with Docker, or http://localhost:5173 in development).
2. Click **Create account**, enter your name, email and a password (8+ characters, at least one letter and one number).
3. You start with **₹5,00,000** of virtual money.

The amber **PAPER TRADING · SIMULATION** badge at the top is always visible, and the top bar shows your available cash.

## Pages

### Dashboard
Your equity, total P&L, available cash and open positions at a glance, plus HFT-style stats: orders per second, average order latency and tick-to-trade time. The chart shows the selected stock's live price on NSE or BSE. Use the **Order ticket** to buy or sell, and click a row in the **Watchlist** to change the chart.

### Profit & Portfolio
A page only about results. Total profit is measured against the money you put in (₹5,00,000 plus top-ups), so a top-up never looks like profit. You'll see realised and unrealised P&L, charges paid, win rate, best and worst trade, an equity curve, daily P&L, and P&L split by strategy, by stock and by source (manual, strategy bots, arbitrage).

### Live Market
Pick a stock to see its NSE and BSE prices side by side (last price, bid × ask), a live chart for either exchange, the quote table for all 10 stocks, and an order ticket.

### Arbitrage (NSE-BSE)
- **Live spreads:** each stock's price on NSE and BSE, the difference, and what 100 shares would net after all charges. Usually this is negative, which is the lesson: tiny gaps don't cover costs.
- **Opportunities:** gaps that do beat costs at your chosen quantity. Click **Execute** to buy on the cheaper exchange and sell on the dearer one at the same time.
- **Auto mode:** turn it on, set a minimum net profit and a quantity per leg, then **Save threshold**. The bot executes the best opportunity above your threshold, at most once every 3 seconds per stock.
- **Results:** each trade shows its status:
  - COMPLETED: both legs filled.
  - HEDGED: one leg failed and the other was closed at market. This usually costs a little.
  - PARTIAL: the legs filled different quantities.
  - FAILED: neither leg filled.

  Each result also shows latency and net P&L after charges.

### Strategies
Create a bot by choosing one of nine strategies, a stock, an exchange, a quantity and optional stop-loss, take-profit and trailing-stop percentages. Each strategy's parameters are explained under its input box. Press **Start** to let it trade, and **Stop** to pause it. Every order a bot sends records the reason, for example "EMA9 crossed above EMA21".

| Strategy | Idea |
|---|---|
| Momentum | Buy when price has risen enough over N bars; sell when it falls |
| Mean Reversion | Buy when price is well below its average; sell when back above |
| Breakout | Buy a new N-bar high; sell a new N-bar low |
| EMA Crossover | Buy when the fast EMA crosses above the slow EMA |
| MACD Crossover | Buy when MACD crosses above its signal line |
| RSI Reversal | Buy when RSI is oversold; sell when overbought |
| Bollinger Bands | Buy at the lower band; sell at the upper band |
| Z-Score | Buy when price is many standard deviations below its mean |
| Ensemble Vote | Trade only when several strategies agree |

### Backtester
Pick a strategy, stock, data source (synthetic or Yahoo Finance), number of days, seed, capital and slippage, then **Run backtest**. You get total return against buy-and-hold, max drawdown, Sharpe, Sortino, win rate, profit factor, charges paid, an equity curve and every trade with its reason. The same seed always gives the same result, so you can compare parameter changes fairly.

### Order Book
Ten levels of bids and asks for any stock and exchange, with quantities and order counts, updating live. Your own resting limit orders sit in this book; the **My open orders** table lets you cancel them, which releases the blocked cash.

### Portfolio & Wallet
Open positions, your wallet balance and the full wallet ledger (every credit, debit, charge and top-up).
- **Top up:** add up to ₹10,00,000 at a time, up to 5 times a day.
- **Reset:** go back to ₹5,00,000. This is only allowed when you hold no positions and have no open orders.

### Trade History
Every fill with exchange, price, quantity, charges, realised P&L, source and reason. Filter by stock, side, exchange, source and date. Use **Export CSV** to download.

### Risk Settings
Your safety limits: max order quantity, max order value, max position value, daily loss limit, daily volume cap and max open orders. The **Kill switch** stops everything at once. It blocks new orders, cancels open ones and stops bots and auto arbitrage.

### Profile
Change your name or password. Changing the password signs out your other sessions.

### Admin (admins only)
- **Users:** every account with role, status, wallet balance and last login. Disable or enable an account, or credit/debit its wallet with a reason. (Role changes are available through the API: `PATCH /api/v1/admin/users/{id}`.)
- **System Metrics:** uptime, orders per second, latency, tick-to-trade, totals, market feed status, and the **audit log** with a filter by action (logins, failed logins, orders, arbitrage, top-ups, kill switch, admin actions).

## Charges applied to every trade

| Charge | Rate |
|---|---|
| Brokerage | ₹20 or 0.03% of trade value, whichever is lower |
| STT | 0.025% on the sell side |
| Exchange transaction charge | NSE 0.00297%, BSE 0.00375% |
| SEBI fee | 0.0001% |
| GST | 18% on brokerage + exchange charge + SEBI fee |
| Stamp duty | 0.003% on the buy side |

## FAQ
**Why did my order get rejected?** Open Trade History or the order list. The reason is shown, for example "Order value exceeds your max order value". You can change limits in Risk Settings.

**Why do most arbitrage spreads show a negative net?** Real NSE-BSE gaps are a few paise, and charges on both legs are several rupees. This mirrors reality: retail arbitrage rarely pays. The simulator adds occasional bigger dislocations so you can see the mechanics work.

**My positions show one line per stock, not per exchange. Why?** Like a demat account, shares are netted. Buying 50 on NSE and selling 50 on BSE leaves you flat.
