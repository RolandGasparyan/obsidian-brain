import type { MarketData } from "@shared/schema";
import crypto from "crypto";

const BASE_URL = "https://api.gateio.ws/api/v4";

// Gate.io Futures minimum contract sizes (in contracts/coins)
// These are the minimum order sizes required by Gate.io
// Gate.io Futures uses INTEGER contract sizes
// Each contract = a fixed amount of the underlying asset
const CONTRACT_MULTIPLIERS: Record<string, number> = {
  "BTC_USDT": 0.0001,   // 1 contract = 0.0001 BTC (~$8)
  "ETH_USDT": 0.01,     // 1 contract = 0.01 ETH (~$25)
  "SOL_USDT": 0.1,      // 1 contract = 0.1 SOL (~$11)
  "XRP_USDT": 10,       // 1 contract = 10 XRP (~$16)
  "AVAX_USDT": 0.1,     // 1 contract = 0.1 AVAX (~$1)
};

const MINIMUM_CONTRACT_SIZES: Record<string, number> = {
  "BTC_USDT": 1,        // Min 1 contract
  "ETH_USDT": 1,        // Min 1 contract
  "SOL_USDT": 1,        // Min 1 contract
  "XRP_USDT": 1,        // Min 1 contract
  "AVAX_USDT": 1,       // Min 1 contract
};

// Get contract multiplier (how much asset per contract)
export function getContractMultiplier(contract: string): number {
  const formatted = contract.replace("/", "_");
  return CONTRACT_MULTIPLIERS[formatted] || 0.01;
}

// Get minimum contract size for a pair
export function getMinContractSize(contract: string): number {
  const formatted = contract.replace("/", "_");
  return MINIMUM_CONTRACT_SIZES[formatted] || 1;
}

interface GateTickerResponse {
  currency_pair: string;
  last: string;
  lowest_ask: string;
  highest_bid: string;
  change_percentage: string;
  base_volume: string;
  quote_volume: string;
  high_24h: string;
  low_24h: string;
}

interface GateCandlestick {
  t: string;
  v: string;
  c: string;
  h: string;
  l: string;
  o: string;
}

interface GateFuturesTicker {
  contract: string;
  funding_rate: string;
  funding_rate_indicative: string;
  index_price: string;
  mark_price: string;
  volume_24h: string;
  volume_24h_quote: string;
  open_interest: string;
  long_short_ratio?: string;
}

interface GateOrderBook {
  asks: [string, string][];
  bids: [string, string][];
}

interface GateLiquidation {
  time: number;
  contract: string;
  size: number;
  order_price: string;
  fill_price: string;
  left: number;
}

function convertSymbol(symbol: string): string {
  return symbol.replace("/", "_");
}

function convertToFuturesSymbol(symbol: string): string {
  return symbol.replace("/", "_").replace("USDT", "USDT");
}

async function fetchTicker(symbol: string): Promise<GateTickerResponse | null> {
  try {
    const currencyPair = convertSymbol(symbol);
    const response = await fetch(`${BASE_URL}/spot/tickers?currency_pair=${currencyPair}`);
    
    if (!response.ok) {
      console.error(`Gate.io ticker error: ${response.status}`);
      return null;
    }
    
    const data = await response.json() as GateTickerResponse[];
    return data.length > 0 ? data[0] : null;
  } catch (error) {
    console.error("Failed to fetch Gate.io ticker:", error);
    return null;
  }
}

async function fetchCandlesticks(symbol: string, interval: string = "1h", limit: number = 100): Promise<number[][] | null> {
  try {
    const currencyPair = convertSymbol(symbol);
    const response = await fetch(
      `${BASE_URL}/spot/candlesticks?currency_pair=${currencyPair}&interval=${interval}&limit=${limit}`
    );
    
    if (!response.ok) {
      console.error(`Gate.io candlesticks error: ${response.status}`);
      return null;
    }
    
    const data = await response.json() as string[][];
    return data.map(candle => candle.map(v => parseFloat(v)));
  } catch (error) {
    console.error("Failed to fetch Gate.io candlesticks:", error);
    return null;
  }
}

async function fetchFuturesTicker(symbol: string): Promise<GateFuturesTicker | null> {
  try {
    const contract = symbol.replace("/", "_");
    const response = await fetch(`${BASE_URL}/futures/usdt/tickers?contract=${contract}`);
    
    if (!response.ok) {
      return null;
    }
    
    const data = await response.json() as GateFuturesTicker[];
    return data.length > 0 ? data[0] : null;
  } catch (error) {
    console.error("Failed to fetch Gate.io futures ticker:", error);
    return null;
  }
}

async function fetchOrderBook(symbol: string, limit: number = 20): Promise<GateOrderBook | null> {
  try {
    const currencyPair = convertSymbol(symbol);
    const response = await fetch(`${BASE_URL}/spot/order_book?currency_pair=${currencyPair}&limit=${limit}`);
    
    if (!response.ok) {
      return null;
    }
    
    return await response.json() as GateOrderBook;
  } catch (error) {
    console.error("Failed to fetch Gate.io order book:", error);
    return null;
  }
}

async function fetchFuturesLiquidations(symbol: string): Promise<GateLiquidation[]> {
  try {
    const contract = symbol.replace("/", "_");
    const now = Math.floor(Date.now() / 1000);
    const dayAgo = now - 86400;
    const response = await fetch(
      `${BASE_URL}/futures/usdt/liq_orders?contract=${contract}&from=${dayAgo}&to=${now}&limit=100`
    );
    
    if (!response.ok) {
      return [];
    }
    
    return await response.json() as GateLiquidation[];
  } catch (error) {
    console.error("Failed to fetch Gate.io liquidations:", error);
    return [];
  }
}

function calculateOrderBookImbalance(orderBook: GateOrderBook): { imbalance: number; spread: number } {
  if (!orderBook.bids.length || !orderBook.asks.length) {
    return { imbalance: 0, spread: 0 };
  }
  
  const totalBidVolume = orderBook.bids.reduce((sum, [, vol]) => sum + parseFloat(vol), 0);
  const totalAskVolume = orderBook.asks.reduce((sum, [, vol]) => sum + parseFloat(vol), 0);
  
  const imbalance = totalBidVolume / (totalBidVolume + totalAskVolume) * 2 - 1;
  
  const bestBid = parseFloat(orderBook.bids[0][0]);
  const bestAsk = parseFloat(orderBook.asks[0][0]);
  const spread = ((bestAsk - bestBid) / bestBid) * 100;
  
  return { imbalance, spread };
}

function calculateLiquidationStats(liquidations: GateLiquidation[], currentPrice: number): {
  longLiquidations: number;
  shortLiquidations: number;
  totalLiquidations: number;
} {
  let longLiquidations = 0;
  let shortLiquidations = 0;
  
  for (const liq of liquidations) {
    const value = Math.abs(liq.size) * parseFloat(liq.fill_price);
    if (liq.size > 0) {
      shortLiquidations += value;
    } else {
      longLiquidations += value;
    }
  }
  
  return {
    longLiquidations,
    shortLiquidations,
    totalLiquidations: longLiquidations + shortLiquidations,
  };
}

function calculateRSI(closes: number[], period: number = 14): number {
  if (closes.length < period + 1) return 50;
  
  let gains = 0;
  let losses = 0;
  
  for (let i = 1; i <= period; i++) {
    const change = closes[i] - closes[i - 1];
    if (change >= 0) {
      gains += change;
    } else {
      losses -= change;
    }
  }
  
  let avgGain = gains / period;
  let avgLoss = losses / period;
  
  for (let i = period + 1; i < closes.length; i++) {
    const change = closes[i] - closes[i - 1];
    if (change >= 0) {
      avgGain = (avgGain * (period - 1) + change) / period;
      avgLoss = (avgLoss * (period - 1)) / period;
    } else {
      avgGain = (avgGain * (period - 1)) / period;
      avgLoss = (avgLoss * (period - 1) - change) / period;
    }
  }
  
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
}

function calculateEMA(data: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const emaArray: number[] = [];
  
  let ema = data.slice(0, period).reduce((a, b) => a + b, 0) / period;
  emaArray.push(ema);
  
  for (let i = period; i < data.length; i++) {
    ema = data[i] * k + ema * (1 - k);
    emaArray.push(ema);
  }
  
  return emaArray;
}

function calculateMACD(closes: number[]): { macd: number; signal: number; histogram: number } {
  if (closes.length < 26) {
    return { macd: 0, signal: 0, histogram: 0 };
  }
  
  const ema12 = calculateEMA(closes, 12);
  const ema26 = calculateEMA(closes, 26);
  
  const macdLine: number[] = [];
  const offset = 26 - 12;
  
  for (let i = 0; i < ema26.length; i++) {
    macdLine.push(ema12[i + offset] - ema26[i]);
  }
  
  const signalLine = calculateEMA(macdLine, 9);
  
  const macd = macdLine[macdLine.length - 1] || 0;
  const signal = signalLine[signalLine.length - 1] || 0;
  const histogram = macd - signal;
  
  return { macd, signal, histogram };
}

function calculateBollingerBands(closes: number[], period: number = 20, multiplier: number = 2): { upper: number; middle: number; lower: number } {
  if (closes.length < period) {
    const price = closes[closes.length - 1] || 0;
    return { upper: price * 1.02, middle: price, lower: price * 0.98 };
  }
  
  const recentCloses = closes.slice(-period);
  const sma = recentCloses.reduce((a, b) => a + b, 0) / period;
  
  const squaredDiffs = recentCloses.map(close => Math.pow(close - sma, 2));
  const variance = squaredDiffs.reduce((a, b) => a + b, 0) / period;
  const stdDev = Math.sqrt(variance);
  
  return {
    upper: sma + (multiplier * stdDev),
    middle: sma,
    lower: sma - (multiplier * stdDev),
  };
}

function calculateVWAP(candles: number[][]): number {
  if (candles.length === 0) return 0;
  
  let cumulativeTPV = 0;
  let cumulativeVolume = 0;
  
  for (const candle of candles) {
    const high = candle[3];
    const low = candle[4];
    const close = candle[2];
    const volume = candle[1];
    
    const typicalPrice = (high + low + close) / 3;
    cumulativeTPV += typicalPrice * volume;
    cumulativeVolume += volume;
  }
  
  return cumulativeVolume > 0 ? cumulativeTPV / cumulativeVolume : 0;
}

export async function fetchGateMarketData(symbol: string): Promise<MarketData | null> {
  console.log(`Fetching Gate.io market data for ${symbol}...`);
  
  const [ticker, candlesticks, futuresTicker, orderBook, liquidations] = await Promise.all([
    fetchTicker(symbol),
    fetchCandlesticks(symbol, "1h", 100),
    fetchFuturesTicker(symbol),
    fetchOrderBook(symbol, 50),
    fetchFuturesLiquidations(symbol),
  ]);
  
  if (!ticker) {
    console.error(`Failed to fetch ticker for ${symbol}`);
    return null;
  }
  
  const currentPrice = parseFloat(ticker.last);
  const priceChange24h = parseFloat(ticker.change_percentage);
  const volume24h = parseFloat(ticker.quote_volume);
  const high24h = parseFloat(ticker.high_24h);
  const low24h = parseFloat(ticker.low_24h);
  
  let rsi = 50;
  let macd = { macd: 0, signal: 0, histogram: 0 };
  let bollingerBands = { upper: currentPrice * 1.02, middle: currentPrice, lower: currentPrice * 0.98 };
  let vwap = currentPrice;
  
  if (candlesticks && candlesticks.length > 0) {
    const sortedCandles = [...candlesticks].reverse();
    const closes = sortedCandles.map(c => c[2]);
    
    rsi = calculateRSI(closes);
    macd = calculateMACD(closes);
    bollingerBands = calculateBollingerBands(closes);
    vwap = calculateVWAP(sortedCandles);
  }
  
  let fundingRate = 0;
  let predictedFundingRate: number | undefined;
  let openInterest = 0;
  let longShortRatio = 1.0;
  let markPrice: number | undefined;
  let indexPrice: number | undefined;
  
  if (futuresTicker) {
    fundingRate = parseFloat(futuresTicker.funding_rate) || 0;
    predictedFundingRate = parseFloat(futuresTicker.funding_rate_indicative) || undefined;
    openInterest = parseFloat(futuresTicker.open_interest) * currentPrice || 0;
    longShortRatio = futuresTicker.long_short_ratio ? parseFloat(futuresTicker.long_short_ratio) : 1.0;
    markPrice = parseFloat(futuresTicker.mark_price) || undefined;
    indexPrice = parseFloat(futuresTicker.index_price) || undefined;
  }
  
  let orderBookImbalance: number | undefined;
  let bidAskSpread: number | undefined;
  
  if (orderBook) {
    const { imbalance, spread } = calculateOrderBookImbalance(orderBook);
    orderBookImbalance = parseFloat(imbalance.toFixed(4));
    bidAskSpread = parseFloat(spread.toFixed(6));
  }
  
  let liquidations24h: { longLiquidations: number; shortLiquidations: number; totalLiquidations: number } | undefined;
  
  if (liquidations.length > 0) {
    liquidations24h = calculateLiquidationStats(liquidations, currentPrice);
  }
  
  const marketData: MarketData = {
    symbol,
    currentPrice: parseFloat(currentPrice.toFixed(2)),
    priceChange24h: parseFloat(priceChange24h.toFixed(2)),
    volume24h: parseFloat(volume24h.toFixed(0)),
    high24h: parseFloat(high24h.toFixed(2)),
    low24h: parseFloat(low24h.toFixed(2)),
    vwap: parseFloat(vwap.toFixed(2)),
    rsi: parseFloat(rsi.toFixed(1)),
    macd: {
      macd: parseFloat(macd.macd.toFixed(2)),
      signal: parseFloat(macd.signal.toFixed(2)),
      histogram: parseFloat(macd.histogram.toFixed(2)),
    },
    bollingerBands: {
      upper: parseFloat(bollingerBands.upper.toFixed(2)),
      middle: parseFloat(bollingerBands.middle.toFixed(2)),
      lower: parseFloat(bollingerBands.lower.toFixed(2)),
    },
    fundingRate: parseFloat(fundingRate.toFixed(6)),
    predictedFundingRate,
    openInterest: parseFloat(openInterest.toFixed(0)),
    longShortRatio: parseFloat(longShortRatio.toFixed(2)),
    orderBookImbalance,
    bidAskSpread,
    markPrice,
    indexPrice,
    liquidations24h,
    timestamp: new Date().toISOString(),
    dataSource: "live",
  };
  
  console.log(`Successfully fetched Gate.io data for ${symbol}: $${currentPrice} (Funding: ${(fundingRate * 100).toFixed(4)}%, OI: $${(openInterest / 1e6).toFixed(1)}M)`);
  return marketData;
}

export async function getAvailableSymbols(): Promise<string[]> {
  try {
    const response = await fetch(`${BASE_URL}/spot/currency_pairs`);
    if (!response.ok) return [];
    
    const pairs = await response.json() as { id: string; trade_status: string }[];
    const tradable = pairs.filter(p => p.trade_status === "tradable");
    
    const popular = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "DOGE_USDT", "ADA_USDT", "AVAX_USDT", "DOT_USDT"];
    
    return tradable
      .filter(p => popular.includes(p.id))
      .map(p => p.id.replace("_", "/"));
  } catch (error) {
    console.error("Failed to fetch available symbols:", error);
    return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"];
  }
}

// ============================================
// TRADING API - Authenticated Endpoints
// ============================================

// Gate.io API credentials
const API_KEY = (process.env.GATE_API_KEY || "").trim();
const API_SECRET = (process.env.GATE_API_SECRET || "").trim();

// Gate.io Funding Pass - For fund transfers and withdrawals
const FUNDING_KEY = (process.env.GATE_IO_FUNDING_KEY || "").trim();
// Parse funding key if it contains both key:secret format
const [FUNDING_API_KEY, FUNDING_API_SECRET] = FUNDING_KEY.includes(":") 
  ? FUNDING_KEY.split(":") 
  : [FUNDING_KEY, ""];

function generateSignature(
  method: string,
  url: string,
  queryString: string,
  body: string,
  timestamp: string
): string {
  // Gate.io v4 signature: METHOD + \n + URL + \n + QUERY + \n + HexEncode(SHA512(body)) + \n + TIMESTAMP
  const hashedBody = crypto.createHash("sha512").update(body || "").digest("hex");
  const signatureString = `${method}\n${url}\n${queryString}\n${hashedBody}\n${timestamp}`;
  return crypto.createHmac("sha512", API_SECRET).update(signatureString).digest("hex");
}

export async function authenticatedRequest(
  method: string,
  endpoint: string,
  body?: object
): Promise<any> {
  if (!API_KEY || !API_SECRET) {
    throw new Error("Gate.io API credentials not configured");
  }
  
  // Split endpoint into path and query string
  const [path, queryString] = endpoint.includes("?") 
    ? endpoint.split("?") 
    : [endpoint, ""];
  
  const timestamp = Math.floor(Date.now() / 1000).toString();
  // Gate.io signature requires full path including /api/v4 prefix
  const url = `/api/v4${path}`;
  const bodyStr = body ? JSON.stringify(body) : "";
  
  const signature = generateSignature(method, url, queryString, bodyStr, timestamp);
  
  const headers: Record<string, string> = {
    "KEY": API_KEY,
    "SIGN": signature,
    "Timestamp": timestamp,
    "Content-Type": "application/json",
  };
  
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? bodyStr : undefined,
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Gate.io API error: ${response.status} - ${errorText}`);
  }
  
  return response.json();
}

// ============================================
// FUNDING API - For Withdrawals & Transfers
// Uses GATE_IO_FUNDING_KEY for enhanced security
// ============================================

function generateFundingSignature(
  method: string,
  url: string,
  queryString: string,
  body: string,
  timestamp: string
): string {
  const secret = FUNDING_API_SECRET || API_SECRET;
  const hashedBody = crypto.createHash("sha512").update(body || "").digest("hex");
  const signatureString = `${method}\n${url}\n${queryString}\n${hashedBody}\n${timestamp}`;
  return crypto.createHmac("sha512", secret).update(signatureString).digest("hex");
}

export async function fundingRequest(
  method: string,
  endpoint: string,
  body?: object
): Promise<any> {
  const apiKey = FUNDING_API_KEY || API_KEY;
  const apiSecret = FUNDING_API_SECRET || API_SECRET;
  
  if (!apiKey || !apiSecret) {
    throw new Error("Gate.io Funding API credentials not configured");
  }
  
  const [path, queryString] = endpoint.includes("?") 
    ? endpoint.split("?") 
    : [endpoint, ""];
  
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const url = `/api/v4${path}`;
  const bodyStr = body ? JSON.stringify(body) : "";
  
  const signature = generateFundingSignature(method, url, queryString, bodyStr, timestamp);
  
  const headers: Record<string, string> = {
    "KEY": apiKey,
    "SIGN": signature,
    "Timestamp": timestamp,
    "Content-Type": "application/json",
  };
  
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? bodyStr : undefined,
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Gate.io Funding API error: ${response.status} - ${errorText}`);
  }
  
  return response.json();
}

// Withdraw to cold wallet
export async function withdrawToColdWallet(
  amount: number,
  address: string,
  network: string = "TRC20",
  currency: string = "USDT"
): Promise<{
  success: boolean;
  txId?: string;
  message: string;
  withdrawalId?: string;
}> {
  try {
    // Gate.io network names: BSC stays as BSC, TRC20 becomes TRX
    const chainName = network === "TRC20" ? "TRX" : network;
    
    console.log(`\n${"═".repeat(60)}`);
    console.log(`💰 WITHDRAWING $${amount.toFixed(2)} ${currency} TO COLD WALLET`);
    console.log(`   Address: ${address}`);
    console.log(`   Network: ${chainName} (${network})`);
    console.log(`${"═".repeat(60)}`);
    
    // Use authenticatedRequest (same as trading API) since main key has withdraw permission
    const result = await authenticatedRequest("POST", "/wallet/withdrawals", {
      currency,
      address,
      amount: amount.toString(),
      chain: chainName,
    });
    
    console.log(`✅ Withdrawal submitted successfully!`);
    console.log(`   Withdrawal ID: ${result.id || "N/A"}`);
    console.log(`   TX Hash: ${result.txid || "Pending"}`);
    
    return {
      success: true,
      txId: result.txid,
      withdrawalId: result.id,
      message: `Successfully initiated withdrawal of $${amount.toFixed(2)} ${currency} to ${address}`,
    };
  } catch (error: any) {
    console.error(`❌ Withdrawal failed:`, error.message);
    return {
      success: false,
      message: `Withdrawal failed: ${error.message}`,
    };
  }
}

// Get withdrawal history
export async function getWithdrawalHistory(currency: string = "USDT"): Promise<any[]> {
  try {
    const withdrawals = await fundingRequest("GET", `/wallet/withdrawals?currency=${currency}`);
    return withdrawals || [];
  } catch (error) {
    console.error("Failed to get withdrawal history:", error);
    return [];
  }
}

// Transfer between accounts via Funding API (spot, futures, margin)
export async function transferViaFundingPass(
  from: "spot" | "futures" | "margin" | "cross_margin",
  to: "spot" | "futures" | "margin" | "cross_margin",
  amount: number,
  currency: string = "USDT"
): Promise<{ success: boolean; message: string }> {
  try {
    await fundingRequest("POST", "/wallet/transfers", {
      currency,
      from,
      to,
      amount: amount.toString(),
    });
    
    console.log(`✅ Transferred $${amount.toFixed(2)} ${currency} from ${from} to ${to}`);
    return { success: true, message: `Transferred $${amount} from ${from} to ${to}` };
  } catch (error: any) {
    console.error(`❌ Transfer failed:`, error.message);
    return { success: false, message: error.message };
  }
}

// Check if funding API is configured
export function isFundingApiConfigured(): boolean {
  return !!(FUNDING_API_KEY || API_KEY) && !!(FUNDING_API_SECRET || API_SECRET);
}

// Get funding API status
export function getFundingApiStatus(): {
  configured: boolean;
  hasSeparateFundingKey: boolean;
  message: string;
} {
  const hasSeparateFundingKey = !!(FUNDING_API_KEY && FUNDING_API_SECRET);
  const hasMainKey = !!(API_KEY && API_SECRET);
  
  return {
    configured: hasSeparateFundingKey || hasMainKey,
    hasSeparateFundingKey,
    message: hasSeparateFundingKey 
      ? "✅ Funding Pass configured (separate funding key)"
      : hasMainKey 
        ? "✅ Funding Pass using main API key"
        : "❌ No funding credentials configured",
  };
}

// Get futures account balance
export async function getFuturesBalance(): Promise<{
  available: number;
  total: number;
  unrealizedPnl: number;
  currency: string;
} | null> {
  try {
    const accounts = await authenticatedRequest("GET", "/futures/usdt/accounts");
    return {
      available: parseFloat(accounts.available || "0"),
      total: parseFloat(accounts.total || "0"),
      unrealizedPnl: parseFloat(accounts.unrealised_pnl || "0"),
      currency: "USDT",
    };
  } catch (error) {
    console.error("Failed to get futures balance:", error);
    return null;
  }
}

// Get spot account balance for a specific currency
export async function getSpotBalance(currency: string = "USDT"): Promise<{
  available: number;
  locked: number;
  currency: string;
} | null> {
  try {
    const accounts = await authenticatedRequest("GET", "/spot/accounts");
    const account = accounts.find((a: any) => a.currency === currency);
    if (!account) {
      return { available: 0, locked: 0, currency };
    }
    return {
      available: parseFloat(account.available || "0"),
      locked: parseFloat(account.locked || "0"),
      currency,
    };
  } catch (error) {
    console.error("Failed to get spot balance:", error);
    return null;
  }
}

// Get ALL spot balances (all currencies with non-zero balance)
export async function getAllSpotBalances(): Promise<Array<{
  currency: string;
  available: number;
  locked: number;
  total: number;
}>> {
  try {
    const accounts = await authenticatedRequest("GET", "/spot/accounts");
    return accounts
      .filter((a: any) => parseFloat(a.available || "0") > 0 || parseFloat(a.locked || "0") > 0)
      .map((a: any) => ({
        currency: a.currency,
        available: parseFloat(a.available || "0"),
        locked: parseFloat(a.locked || "0"),
        total: parseFloat(a.available || "0") + parseFloat(a.locked || "0"),
      }));
  } catch (error) {
    console.error("Failed to get all spot balances:", error);
    return [];
  }
}

// Get margin account balance
export async function getMarginBalance(): Promise<Array<{
  currency: string;
  available: number;
  locked: number;
}>> {
  try {
    const accounts = await authenticatedRequest("GET", "/margin/accounts");
    return accounts
      .filter((a: any) => parseFloat(a.available || "0") > 0 || parseFloat(a.locked || "0") > 0)
      .map((a: any) => ({
        currency: a.currency,
        available: parseFloat(a.available || "0"),
        locked: parseFloat(a.locked || "0"),
      }));
  } catch (error) {
    console.error("Failed to get margin balance:", error);
    return [];
  }
}

// Get cross margin account balance
export async function getCrossMarginBalance(): Promise<Array<{
  currency: string;
  available: number;
  locked: number;
}>> {
  try {
    const accounts = await authenticatedRequest("GET", "/margin/cross/accounts");
    if (accounts && accounts.balances) {
      return Object.entries(accounts.balances)
        .filter(([_, v]: [string, any]) => parseFloat(v.available || "0") > 0)
        .map(([k, v]: [string, any]) => ({
          currency: k,
          available: parseFloat(v.available || "0"),
          locked: parseFloat(v.locked || "0"),
        }));
    }
    return [];
  } catch (error) {
    console.error("Failed to get cross margin balance:", error);
    return [];
  }
}

// Check for active Grid Trading Bots
export async function getActiveGridBots(): Promise<any[]> {
  try {
    const bots = await authenticatedRequest("GET", "/spot/price_orders");
    return bots || [];
  } catch (error) {
    console.error("Failed to get grid bots:", error);
    return [];
  }
}

// Check unified account (might hold locked funds)
export async function getUnifiedAccount(): Promise<any> {
  try {
    const account = await authenticatedRequest("GET", "/unified/accounts");
    return account;
  } catch (error) {
    console.error("Failed to get unified account:", error);
    return null;
  }
}

// Check for any pending withdrawals
export async function getPendingWithdrawals(): Promise<any[]> {
  try {
    const withdrawals = await authenticatedRequest("GET", "/wallet/withdrawals");
    return withdrawals.filter((w: any) => w.status === "PEND" || w.status === "REQUEST") || [];
  } catch (error) {
    console.error("Failed to get withdrawals:", error);
    return [];
  }
}

// Get sub-account balances
export async function getSubAccounts(): Promise<any[]> {
  try {
    const subs = await authenticatedRequest("GET", "/sub_accounts");
    return subs || [];
  } catch (error) {
    console.error("Failed to get sub accounts:", error);
    return [];
  }
}

// Check Copy Trading positions
export async function getCopyTradingPositions(): Promise<any> {
  try {
    const positions = await authenticatedRequest("GET", "/copy_trading/portfolios");
    return positions || [];
  } catch (error) {
    console.error("Failed to get copy trading:", error);
    return [];
  }
}

// Check Dual Investment orders
export async function getDualInvestments(): Promise<any> {
  try {
    const orders = await authenticatedRequest("GET", "/earn/dual/orders");
    return orders || [];
  } catch (error) {
    console.error("Failed to get dual investments:", error);
    return [];
  }
}

// Check Structured Products
export async function getStructuredProducts(): Promise<any> {
  try {
    const products = await authenticatedRequest("GET", "/earn/structured/orders");
    return products || [];
  } catch (error) {
    console.error("Failed to get structured products:", error);
    return [];
  }
}

// Check all loan orders
export async function getLoanOrders(): Promise<any> {
  try {
    const loans = await authenticatedRequest("GET", "/margin/uni/loans");
    return loans || [];
  } catch (error) {
    console.error("Failed to get loans:", error);
    return [];
  }
}

// Get account book history to find what's locking funds
export async function getAccountBook(currency: string = "USDT"): Promise<any[]> {
  try {
    const history = await authenticatedRequest("GET", `/spot/account_book?currency=${currency}&limit=50`);
    return history || [];
  } catch (error) {
    console.error("Failed to get account book:", error);
    return [];
  }
}

// Convert small balances to GT (dust conversion)
export async function convertSmallBalancesToGT(): Promise<any> {
  try {
    const result = await authenticatedRequest("POST", "/wallet/small_balance", { currency: "GT" });
    return result;
  } catch (error) {
    console.error("Failed to convert small balances:", error);
    throw error;
  }
}

// Check savings/lending products
export async function getSavingsAccounts(): Promise<any[]> {
  try {
    const savings = await authenticatedRequest("GET", "/earn/uni/lends");
    return savings || [];
  } catch (error) {
    console.error("Failed to get savings:", error);
    return [];
  }
}

// Check flash swap orders
export async function getFlashSwapOrders(): Promise<any[]> {
  try {
    const orders = await authenticatedRequest("GET", "/flash_swap/orders?limit=10");
    return orders || [];
  } catch (error) {
    console.error("Failed to get flash swap orders:", error);
    return [];
  }
}

// Check options account
export async function getOptionsAccount(): Promise<any> {
  try {
    const account = await authenticatedRequest("GET", "/options/accounts");
    return account;
  } catch (error) {
    console.error("Failed to get options account:", error);
    return null;
  }
}

// Check delivery account (futures delivery)
export async function getDeliveryAccount(): Promise<any> {
  try {
    const account = await authenticatedRequest("GET", "/delivery/usdt/accounts");
    return account;
  } catch (error) {
    console.error("Failed to get delivery account:", error);
    return null;
  }
}

// Transfer from unified to spot
export async function transferFromUnified(currency: string, amount: number): Promise<any> {
  try {
    const result = await authenticatedRequest("POST", "/wallet/transfers", {
      currency,
      from: "unified",
      to: "spot",
      amount: amount.toString(),
    });
    return result;
  } catch (error) {
    console.error("Failed to transfer from unified:", error);
    throw error;
  }
}

// Transfer from options to spot
export async function transferFromOptions(currency: string, amount: number): Promise<any> {
  try {
    const result = await authenticatedRequest("POST", "/wallet/transfers", {
      currency,
      from: "options",
      to: "spot",
      amount: amount.toString(),
    });
    return result;
  } catch (error) {
    console.error("Failed to transfer from options:", error);
    throw error;
  }
}

// Transfer from delivery to spot
export async function transferFromDelivery(currency: string, amount: number): Promise<any> {
  try {
    const result = await authenticatedRequest("POST", "/wallet/transfers", {
      currency,
      from: "delivery",
      to: "spot",
      amount: amount.toString(),
      settle: "usdt",
    });
    return result;
  } catch (error) {
    console.error("Failed to transfer from delivery:", error);
    throw error;
  }
}

// Redeem from lending
export async function redeemFromLending(currency: string): Promise<any> {
  try {
    const result = await authenticatedRequest("POST", "/earn/uni/lends", {
      currency,
      amount: "0", // 0 = redeem all
    });
    return result;
  } catch (error) {
    console.error("Failed to redeem from lending:", error);
    throw error;
  }
}

// Transfer funds between accounts (spot <-> futures)
export async function transferFunds(params: {
  currency: string;
  amount: number;
  from: "spot" | "futures";
  to: "spot" | "futures";
}): Promise<{ success: boolean; txId?: string; error?: string }> {
  try {
    // Gate.io wallet transfer API requires specific format
    // For futures, need to specify "futures" with settle currency
    const fromAccount = params.from === "spot" ? "spot" : "futures";
    const toAccount = params.to === "spot" ? "spot" : "futures";
    
    // Gate.io requires max 8 decimal places for amount
    const roundedAmount = Math.floor(params.amount * 100000000) / 100000000;
    
    const transferBody: Record<string, string> = {
      currency: params.currency,
      from: fromAccount,
      to: toAccount,
      amount: roundedAmount.toString(),
    };
    
    // Gate.io requires settle parameter for futures transfers
    if (params.from === "futures" || params.to === "futures") {
      transferBody.settle = "usdt";
    }
    
    const result = await authenticatedRequest("POST", "/wallet/transfers", transferBody);
    
    return { success: true, txId: result.tx_id };
  } catch (error) {
    console.error("Failed to transfer funds:", error);
    return { 
      success: false, 
      error: error instanceof Error ? error.message : "Transfer failed" 
    };
  }
}

// Place spot order (buy or sell)
export interface SpotOrderParams {
  currencyPair: string;  // e.g., "BTC_USDT"
  side: "buy" | "sell";
  amount: string;        // Amount in base currency for sell, or quote currency for buy
  price?: string;        // Limit price (omit for market order)
  type?: "limit" | "market";
}

export async function placeSpotOrder(params: SpotOrderParams): Promise<{
  id: string;
  currencyPair: string;
  side: string;
  amount: string;
  price: string;
  status: string;
} | null> {
  try {
    const orderBody: Record<string, string> = {
      currency_pair: params.currencyPair,
      side: params.side,
      amount: params.amount,
      type: params.type || "market",
    };
    
    if (params.price && params.type === "limit") {
      orderBody.price = params.price;
    }
    
    // For market orders, set time_in_force to ioc
    if (params.type === "market" || !params.type) {
      orderBody.time_in_force = "ioc";
    }
    
    const result = await authenticatedRequest("POST", "/spot/orders", orderBody);
    return {
      id: result.id,
      currencyPair: result.currency_pair,
      side: result.side,
      amount: result.amount,
      price: result.price || "0",
      status: result.status,
    };
  } catch (error) {
    console.error("Failed to place spot order:", error);
    throw error;
  }
}

// Get open spot orders across ALL pairs
export async function getOpenSpotOrders(): Promise<Array<{
  id: string;
  currencyPair: string;
  side: string;
  amount: string;
  price: string;
  status: string;
  left: string;
}>> {
  try {
    // Get all open orders without specifying a pair
    const response = await authenticatedRequest("GET", "/spot/open_orders");
    console.log("Raw open orders response:", JSON.stringify(response));
    
    // The response might be an array of objects with orders nested inside
    const allOrders: any[] = [];
    if (Array.isArray(response)) {
      for (const item of response) {
        if (item.orders && Array.isArray(item.orders)) {
          // Format: [{currency_pair: "XRP_USDT", orders: [...]}]
          for (const order of item.orders) {
            allOrders.push({
              id: order.id,
              currencyPair: item.currency_pair,
              side: order.side,
              amount: order.amount,
              price: order.price,
              status: order.status,
              left: order.left || order.amount,
            });
          }
        } else if (item.id) {
          // Direct order format
          allOrders.push({
            id: item.id,
            currencyPair: item.currency_pair,
            side: item.side,
            amount: item.amount,
            price: item.price,
            status: item.status,
            left: item.left || item.amount,
          });
        }
      }
    }
    return allOrders;
  } catch (error) {
    console.error("Failed to get open spot orders:", error);
    return [];
  }
}

// Cancel all open spot orders
export async function cancelAllSpotOrders(): Promise<{ success: boolean; cancelled: number; error?: string }> {
  try {
    const orders = await getOpenSpotOrders();
    if (orders.length === 0) {
      return { success: true, cancelled: 0 };
    }
    
    let cancelled = 0;
    for (const order of orders) {
      try {
        await authenticatedRequest("DELETE", `/spot/orders/${order.id}?currency_pair=${order.currencyPair}`);
        cancelled++;
      } catch (e) {
        console.error(`Failed to cancel order ${order.id}:`, e);
      }
    }
    
    return { success: true, cancelled };
  } catch (error) {
    console.error("Failed to cancel spot orders:", error);
    return { 
      success: false, 
      cancelled: 0,
      error: error instanceof Error ? error.message : "Failed to cancel orders" 
    };
  }
}

// Get open positions
export async function getOpenPositions(): Promise<Array<{
  contract: string;
  size: number;
  leverage: number;
  entryPrice: number;
  markPrice: number;
  unrealizedPnl: number;
  margin: number;
}>> {
  try {
    const positions = await authenticatedRequest("GET", "/futures/usdt/positions");
    return positions
      .filter((p: any) => parseFloat(p.size) !== 0)
      .map((p: any) => ({
        contract: p.contract,
        size: parseFloat(p.size),
        leverage: parseFloat(p.leverage),
        entryPrice: parseFloat(p.entry_price),
        markPrice: parseFloat(p.mark_price),
        unrealizedPnl: parseFloat(p.unrealised_pnl),
        margin: parseFloat(p.margin),
      }));
  } catch (error) {
    console.error("Failed to get open positions:", error);
    return [];
  }
}

// Place futures order
export interface PlaceOrderParams {
  contract: string;  // e.g., "BTC_USDT"
  size: number;      // Positive for long, negative for short
  price?: number;    // Limit price (omit for market order)
  leverage?: number; // Leverage (1-100)
  reduceOnly?: boolean;
  tif?: "gtc" | "ioc" | "poc"; // Time in force
}

export interface OrderResult {
  id: string;
  contract: string;
  size: number;
  price: number;
  status: string;
  createTime: number;
}

export async function placeFuturesOrder(params: PlaceOrderParams): Promise<OrderResult> {
  const contract = params.contract.replace("/", "_");
  
  // ═══════════════════════════════════════════════════════════════════════════
  // 🚫 SHORTS ONLY - HARD BLOCK ON LONG POSITIONS
  // ═══════════════════════════════════════════════════════════════════════════
  // Positive size = LONG position - BLOCKED
  // Negative size = SHORT position - ALLOWED
  if (params.size > 0 && !params.reduceOnly) {
    console.log(`🚫 BLOCKED LONG ORDER: ${contract} size=${params.size} - SHORTS ONLY MODE`);
    throw new Error(`BLOCKED: Long positions are DISABLED. Only SHORT positions allowed. Size must be negative.`);
  }
  // ═══════════════════════════════════════════════════════════════════════════
  
  // Get minimum contract size for this pair
  const minSize = getMinContractSize(contract);
  
  // Gate.io Futures requires INTEGER contract sizes
  // params.size is passed as number of base asset (e.g., 0.08 ETH)
  // Convert to integer contracts: contracts = size / multiplier
  const multiplier = getContractMultiplier(contract);
  
  // Calculate integer contract count
  // For ETH: 0.08 ETH / 0.01 = 8 contracts
  let contractCount = Math.round(Math.abs(params.size) / multiplier);
  
  // Ensure minimum
  if (contractCount < minSize && !params.reduceOnly) {
    contractCount = minSize;
  }
  
  // Apply direction (negative for shorts)
  let roundedSize = params.size > 0 ? contractCount : -contractCount;
  
  console.log(`[CONTRACT CALC] ${contract}: ${params.size} asset -> ${roundedSize} contracts (multiplier: ${multiplier})`);
  
  // Validate minimum size
  if (Math.abs(roundedSize) < minSize && !params.reduceOnly) {
    throw new Error(`Contract count ${Math.abs(roundedSize)} below minimum ${minSize} for ${contract}`);
  }
  
  // Set leverage first - always set to ensure it's configured
  const leverage = params.leverage || 10; // Default to 10x
  try {
    await authenticatedRequest("POST", "/futures/usdt/positions/" + contract + "/leverage", {
      leverage: leverage.toString(),
      cross_leverage_limit: leverage.toString(),
    });
  } catch (e: any) {
    // Ignore if leverage already set
    if (!e?.message?.includes("already")) {
      console.log("Leverage set note:", e?.message || e);
    }
  }
  
  const orderBody: any = {
    contract,
    size: roundedSize,
    tif: params.tif || "gtc",
    reduce_only: params.reduceOnly || false,
  };
  
  if (params.price) {
    orderBody.price = params.price.toString();
  } else {
    // Market order - use price 0 with ioc
    orderBody.price = "0";
    orderBody.tif = "ioc";
  }
  
  console.log(`[GATE.IO ORDER] ${contract}: size=${roundedSize}, leverage=${leverage}x, reduce=${params.reduceOnly}`);
  
  const result = await authenticatedRequest("POST", "/futures/usdt/orders", orderBody);
  
  return {
    id: result.id?.toString() || "",
    contract: result.contract,
    size: parseFloat(result.size),
    price: parseFloat(result.price),
    status: result.status,
    createTime: result.create_time,
  };
}

// Close position
export async function closePosition(contract: string): Promise<OrderResult | null> {
  try {
    const contractFormatted = contract.replace("/", "_");
    const positions = await getOpenPositions();
    const position = positions.find(p => p.contract === contractFormatted);
    
    if (!position || position.size === 0) {
      throw new Error("No open position to close");
    }
    
    // Close by placing opposite order
    return await placeFuturesOrder({
      contract: contractFormatted,
      size: -position.size, // Opposite of current position
      reduceOnly: true,
    });
  } catch (error) {
    console.error("Failed to close position:", error);
    return null;
  }
}

// Close ALL positions
export async function closeAllPositions(): Promise<{
  success: boolean;
  closed: number;
  positions: Array<{ contract: string; size: number; pnl: number }>;
  errors: string[];
}> {
  try {
    const positions = await getOpenPositions();
    const results: Array<{ contract: string; size: number; pnl: number }> = [];
    const errors: string[] = [];
    
    if (positions.length === 0) {
      console.log("[GATE.IO] No open positions to close");
      return { success: true, closed: 0, positions: [], errors: [] };
    }
    
    console.log(`[GATE.IO] Closing ${positions.length} open positions...`);
    
    for (const position of positions) {
      try {
        console.log(`[GATE.IO] Closing ${position.contract}: size=${position.size}, PnL=${position.unrealizedPnl}`);
        
        // Close by placing opposite order
        await placeFuturesOrder({
          contract: position.contract,
          size: -position.size, // Opposite of current position
          reduceOnly: true,
        });
        
        results.push({
          contract: position.contract,
          size: position.size,
          pnl: position.unrealizedPnl,
        });
        
        console.log(`[GATE.IO] Successfully closed ${position.contract}`);
      } catch (error) {
        const errMsg = `Failed to close ${position.contract}: ${error instanceof Error ? error.message : "Unknown error"}`;
        console.error(`[GATE.IO] ${errMsg}`);
        errors.push(errMsg);
      }
    }
    
    console.log(`[GATE.IO] Closed ${results.length}/${positions.length} positions`);
    return { 
      success: errors.length === 0, 
      closed: results.length, 
      positions: results,
      errors 
    };
  } catch (error) {
    console.error("[GATE.IO] Failed to close all positions:", error);
    return { 
      success: false, 
      closed: 0, 
      positions: [],
      errors: [error instanceof Error ? error.message : "Unknown error"] 
    };
  }
}

// Cancel order
export async function cancelOrder(orderId: string): Promise<boolean> {
  try {
    await authenticatedRequest("DELETE", `/futures/usdt/orders/${orderId}`);
    return true;
  } catch (error) {
    console.error("Failed to cancel order:", error);
    return false;
  }
}

// Get open orders
export async function getOpenOrders(contract?: string): Promise<OrderResult[]> {
  try {
    let endpoint = "/futures/usdt/orders?status=open";
    if (contract) {
      endpoint += `&contract=${contract.replace("/", "_")}`;
    }
    
    const orders = await authenticatedRequest("GET", endpoint);
    return orders.map((o: any) => ({
      id: o.id?.toString() || "",
      contract: o.contract,
      size: parseFloat(o.size),
      price: parseFloat(o.price),
      status: o.status,
      createTime: o.create_time,
    }));
  } catch (error) {
    console.error("Failed to get open orders:", error);
    return [];
  }
}
