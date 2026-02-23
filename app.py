import { useState, useEffect, useRef } from "react";

const MOCK_DATA = {
  AAPL: {
    name: "Apple Inc.",
    price: 189.45,
    change: 2.34,
    changePct: 1.25,
    open: 187.11,
    high: 190.22,
    low: 186.88,
    volume: "52.3M",
    mktCap: "2.94T",
    pe: 29.4,
    eps: 6.44,
    week52High: 199.62,
    week52Low: 143.9,
    rating: "BUY",
    ratingScore: 82,
    history: [143, 152, 158, 162, 155, 170, 175, 168, 180, 178, 185, 189],
  },
  TSLA: {
    name: "Tesla, Inc.",
    price: 242.8,
    change: -8.45,
    changePct: -3.36,
    open: 251.25,
    high: 253.1,
    low: 240.5,
    volume: "118.7M",
    mktCap: "771.2B",
    pe: 62.1,
    eps: 3.91,
    week52High: 278.98,
    week52Low: 138.8,
    rating: "HOLD",
    ratingScore: 54,
    history: [139, 155, 180, 210, 195, 220, 260, 245, 278, 255, 251, 243],
  },
  MSFT: {
    name: "Microsoft Corp.",
    price: 415.2,
    change: 5.1,
    changePct: 1.24,
    open: 410.1,
    high: 416.5,
    low: 409.8,
    volume: "21.4M",
    mktCap: "3.08T",
    pe: 35.6,
    eps: 11.66,
    week52High: 430.82,
    week52Low: 309.45,
    rating: "BUY",
    ratingScore: 88,
    history: [310, 328, 340, 355, 362, 375, 388, 400, 410, 405, 410, 415],
  },
  NVDA: {
    name: "NVIDIA Corp.",
    price: 875.4,
    change: 22.3,
    changePct: 2.62,
    open: 853.1,
    high: 881.2,
    low: 850.0,
    volume: "44.1M",
    mktCap: "2.15T",
    pe: 68.3,
    eps: 12.81,
    week52High: 974.0,
    week52Low: 410.0,
    rating: "STRONG BUY",
    ratingScore: 94,
    history: [410, 480, 520, 600, 680, 750, 820, 790, 860, 840, 853, 875],
  },
  AMZN: {
    name: "Amazon.com Inc.",
    price: 185.6,
    change: -1.2,
    changePct: -0.64,
    open: 186.8,
    high: 187.5,
    low: 184.2,
    volume: "33.8M",
    mktCap: "1.93T",
    pe: 44.8,
    eps: 4.14,
    week52High: 201.2,
    week52Low: 118.35,
    rating: "BUY",
    ratingScore: 76,
    history: [118, 130, 142, 155, 160, 168, 175, 190, 200, 195, 187, 186],
  },
};

const MONTHS = ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan"];

function MiniChart({ history, positive }) {
  const min = Math.min(...history);
  const max = Math.max(...history);
  const range = max - min || 1;
  const W = 200, H = 60;
  const pts = history.map((v, i) => {
    const x = (i / (history.length - 1)) * W;
    const y = H - ((v - min) / range) * H;
    return `${x},${y}`;
  });
  const color = positive ? "#00e5a0" : "#ff4d6d";
  const fillPts = `0,${H} ${pts.join(" ")} ${W},${H}`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 60 }}>
      <defs>
        <linearGradient id={`grad-${positive}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <polygon points={fillPts} fill={`url(#grad-${positive})`} />
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

function RatingGauge({ score }) {
  const color = score >= 80 ? "#00e5a0" : score >= 55 ? "#f5c518" : "#ff4d6d";
  const label = score >= 80 ? (score >= 90 ? "STRONG BUY" : "BUY") : score >= 55 ? "HOLD" : "SELL";
  const circumference = 2 * Math.PI * 40;
  const dash = (score / 100) * circumference;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
      <svg width="100" height="100" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="40" fill="none" stroke="#1e2433" strokeWidth="8" />
        <circle
          cx="50" cy="50" r="40" fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          style={{ transition: "stroke-dasharray 1s ease" }}
        />
        <text x="50" y="46" textAnchor="middle" fill={color} fontSize="22" fontWeight="700" fontFamily="'DM Mono', monospace">{score}</text>
        <text x="50" y="62" textAnchor="middle" fill="#8892a4" fontSize="9" fontFamily="'DM Mono', monospace">/ 100</text>
      </svg>
      <span style={{ color, fontSize: 12, fontWeight: 700, letterSpacing: 2, fontFamily: "'DM Mono', monospace" }}>{label}</span>
    </div>
  );
}

export default function StockEvaluator() {
  const [query, setQuery] = useState("");
  const [ticker, setTicker] = useState("AAPL");
  const [data, setData] = useState(MOCK_DATA["AAPL"]);
  const [error, setError] = useState("");
  const [animKey, setAnimKey] = useState(0);
  const inputRef = useRef();

  const handleSearch = (e) => {
    e.preventDefault();
    const sym = query.trim().toUpperCase();
    if (MOCK_DATA[sym]) {
      setTicker(sym);
      setData(MOCK_DATA[sym]);
      setError("");
      setAnimKey(k => k + 1);
    } else {
      setError(`"${sym}" not found. Try: ${Object.keys(MOCK_DATA).join(", ")}`);
    }
    setQuery("");
  };

  const isPositive = data.change >= 0;
  const accentColor = isPositive ? "#00e5a0" : "#ff4d6d";

  const statRow = (label, value, highlight) => (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #1e2433" }}>
      <span style={{ color: "#8892a4", fontSize: 12, fontFamily: "'DM Mono', monospace", letterSpacing: 1 }}>{label}</span>
      <span style={{ color: highlight ? accentColor : "#e8ecf4", fontSize: 13, fontWeight: 600, fontFamily: "'DM Mono', monospace" }}>{value}</span>
    </div>
  );

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #080d17; }
        .evaluator-root {
          min-height: 100vh;
          background: #080d17;
          background-image: radial-gradient(ellipse at 20% 0%, rgba(0,229,160,0.06) 0%, transparent 60%),
                            radial-gradient(ellipse at 80% 100%, rgba(99,102,241,0.06) 0%, transparent 60%);
          font-family: 'DM Mono', monospace;
          padding: 32px 24px;
          color: #e8ecf4;
        }
        .card {
          background: #0e1523;
          border: 1px solid #1e2433;
          border-radius: 12px;
          padding: 20px;
        }
        .ticker-chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
        .chip {
          padding: 5px 12px;
          border-radius: 20px;
          border: 1px solid #1e2433;
          background: transparent;
          color: #8892a4;
          font-size: 11px;
          font-family: 'DM Mono', monospace;
          cursor: pointer;
          letter-spacing: 1px;
          transition: all 0.2s;
        }
        .chip:hover, .chip.active {
          border-color: #00e5a0;
          color: #00e5a0;
          background: rgba(0,229,160,0.08);
        }
        .search-bar {
          display: flex;
          gap: 10px;
          align-items: center;
        }
        .search-input {
          flex: 1;
          background: #0e1523;
          border: 1px solid #1e2433;
          border-radius: 8px;
          padding: 10px 16px;
          color: #e8ecf4;
          font-family: 'DM Mono', monospace;
          font-size: 13px;
          outline: none;
          text-transform: uppercase;
          letter-spacing: 2px;
          transition: border-color 0.2s;
        }
        .search-input:focus { border-color: #00e5a0; }
        .search-input::placeholder { color: #3a4455; text-transform: none; letter-spacing: 0; }
        .search-btn {
          background: #00e5a0;
          color: #080d17;
          border: none;
          border-radius: 8px;
          padding: 10px 20px;
          font-family: 'DM Mono', monospace;
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 1px;
          cursor: pointer;
          transition: opacity 0.2s;
        }
        .search-btn:hover { opacity: 0.85; }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .anim { animation: fadeUp 0.4s ease forwards; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        @media (max-width: 640px) { .grid-2 { grid-template-columns: 1fr; } }
        .price-big {
          font-family: 'Syne', sans-serif;
          font-size: 48px;
          font-weight: 800;
          line-height: 1;
          letter-spacing: -1px;
        }
        .range-bar-track {
          height: 4px;
          background: #1e2433;
          border-radius: 2px;
          position: relative;
          margin-top: 4px;
        }
        .range-bar-fill {
          position: absolute;
          left: 0;
          top: 0;
          height: 4px;
          border-radius: 2px;
          transition: width 1s ease;
        }
        .range-dot {
          position: absolute;
          top: -4px;
          width: 12px;
          height: 12px;
          border-radius: 50%;
          transform: translateX(-50%);
          border: 2px solid #080d17;
          transition: left 1s ease;
        }
        .live-dot {
          width: 8px; height: 8px; border-radius: 50%; background: #00e5a0;
          animation: pulse 1.5s infinite;
          display: inline-block; margin-right: 6px;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.8); }
        }
      `}</style>

      <div className="evaluator-root">
        <div style={{ maxWidth: 800, margin: "0 auto" }}>

          {/* Header */}
          <div style={{ marginBottom: 28 }}>
            <h1 style={{ fontFamily: "'Syne', sans-serif", fontSize: 28, fontWeight: 800, letterSpacing: -0.5 }}>
              Stock <span style={{ color: "#00e5a0" }}>Evaluator</span>
            </h1>
            <p style={{ color: "#8892a4", fontSize: 12, marginTop: 4, letterSpacing: 1 }}>REAL-TIME ANALYSIS · TECHNICAL SCORING · MARKET SIGNALS</p>
          </div>

          {/* Search */}
          <div className="card" style={{ marginBottom: 20 }}>
            <form onSubmit={handleSearch} className="search-bar">
              <input
                ref={inputRef}
                className="search-input"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Enter ticker symbol (e.g. MSFT)"
              />
              <button type="submit" className="search-btn">EVALUATE</button>
            </form>
            {error && <p style={{ color: "#ff4d6d", fontSize: 11, marginTop: 8, fontFamily: "'DM Mono', monospace" }}>{error}</p>}
            <div className="ticker-chips">
              {Object.keys(MOCK_DATA).map(sym => (
                <button key={sym} className={`chip ${ticker === sym ? "active" : ""}`} onClick={() => { setTicker(sym); setData(MOCK_DATA[sym]); setAnimKey(k => k + 1); setError(""); }}>
                  {sym}
                </button>
              ))}
            </div>
          </div>

          {/* Main Content */}
          <div key={animKey} className="anim">

            {/* Price Hero */}
            <div className="card" style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                    <span className="live-dot" />
                    <span style={{ color: "#8892a4", fontSize: 11, letterSpacing: 2 }}>LIVE</span>
                    <span style={{ color: "#3a4455", fontSize: 11 }}>·</span>
                    <span style={{ color: "#8892a4", fontSize: 11, letterSpacing: 1 }}>{ticker}</span>
                  </div>
                  <div style={{ color: "#8892a4", fontSize: 13, marginBottom: 4 }}>{data.name}</div>
                  <div className="price-big">${data.price.toFixed(2)}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
                    <span style={{ color: accentColor, fontSize: 16, fontWeight: 600 }}>
                      {isPositive ? "▲" : "▼"} ${Math.abs(data.change).toFixed(2)}
                    </span>
                    <span style={{
                      background: isPositive ? "rgba(0,229,160,0.1)" : "rgba(255,77,109,0.1)",
                      color: accentColor,
                      padding: "2px 8px",
                      borderRadius: 4,
                      fontSize: 12,
                      fontWeight: 600,
                    }}>
                      {isPositive ? "+" : ""}{data.changePct.toFixed(2)}%
                    </span>
                  </div>
                </div>
                <RatingGauge score={data.ratingScore} />
              </div>

              {/* Mini chart */}
              <div style={{ marginTop: 16 }}>
                <MiniChart history={data.history} positive={isPositive} />
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                  {MONTHS.map((m, i) => (
                    <span key={i} style={{ color: "#3a4455", fontSize: 9, fontFamily: "'DM Mono', monospace" }}>{m}</span>
                  ))}
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid-2" style={{ marginBottom: 16 }}>
              <div className="card">
                <div style={{ color: "#8892a4", fontSize: 10, letterSpacing: 2, marginBottom: 12 }}>TRADING DATA</div>
                {statRow("OPEN", `$${data.open.toFixed(2)}`)}
                {statRow("HIGH", `$${data.high.toFixed(2)}`, true)}
                {statRow("LOW", `$${data.low.toFixed(2)}`)}
                {statRow("VOLUME", data.volume)}
                {statRow("MKT CAP", data.mktCap)}
              </div>

              <div className="card">
                <div style={{ color: "#8892a4", fontSize: 10, letterSpacing: 2, marginBottom: 12 }}>FUNDAMENTALS</div>
                {statRow("P/E RATIO", data.pe)}
                {statRow("EPS", `$${data.eps}`)}
                {statRow("52W HIGH", `$${data.week52High}`)}
                {statRow("52W LOW", `$${data.week52Low}`)}
                {statRow("ANALYST", data.rating, true)}
              </div>
            </div>

            {/* 52W Range */}
            <div className="card">
              <div style={{ color: "#8892a4", fontSize: 10, letterSpacing: 2, marginBottom: 16 }}>52-WEEK RANGE</div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ color: "#ff4d6d", fontSize: 12 }}>${data.week52Low}</span>
                <span style={{ color: "#e8ecf4", fontSize: 12, fontWeight: 600 }}>${data.price.toFixed(2)}</span>
                <span style={{ color: "#00e5a0", fontSize: 12 }}>${data.week52High}</span>
              </div>
              <div className="range-bar-track">
                {(() => {
                  const pct = ((data.price - data.week52Low) / (data.week52High - data.week52Low)) * 100;
                  return (
                    <>
                      <div className="range-bar-fill" style={{ width: `${pct}%`, background: `linear-gradient(90deg, #ff4d6d, ${accentColor})` }} />
                      <div className="range-dot" style={{ left: `${pct}%`, background: accentColor }} />
                    </>
                  );
                })()}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10 }}>
                <span style={{ color: "#3a4455", fontSize: 10 }}>52W LOW</span>
                <span style={{ color: "#3a4455", fontSize: 10 }}>52W HIGH</span>
              </div>
            </div>

          </div>

          <p style={{ textAlign: "center", color: "#3a4455", fontSize: 10, marginTop: 20, letterSpacing: 1 }}>
            SIMULATED DATA FOR DEMONSTRATION PURPOSES ONLY · NOT FINANCIAL ADVICE
          </p>
        </div>
      </div>
    </>
  );
}
