import { Server as HttpServer } from "http";
import { Server, Socket } from "socket.io";
import { tradingEngine } from "./tradingEngine";

let io: Server | null = null;

export function initializeWebSocket(httpServer: HttpServer): Server {
  io = new Server(httpServer, {
    cors: {
      origin: "*",
      methods: ["GET", "POST"]
    },
    path: "/socket.io"
  });

  io.on("connection", (socket: Socket) => {
    console.log(`Client connected: ${socket.id}`);

    socket.emit("connected", { message: "Connected to AI Trading Platform", timestamp: new Date().toISOString() });

    socket.on("subscribe:leaderboard", () => {
      socket.join("leaderboard");
      console.log(`${socket.id} subscribed to leaderboard`);
    });

    socket.on("subscribe:trades", () => {
      socket.join("trades");
      console.log(`${socket.id} subscribed to trades`);
    });

    socket.on("subscribe:market", () => {
      socket.join("market");
      console.log(`${socket.id} subscribed to market`);
    });

    socket.on("disconnect", () => {
      console.log(`Client disconnected: ${socket.id}`);
    });
  });

  startBroadcastLoops();

  return io;
}

function startBroadcastLoops() {
  setInterval(async () => {
    if (!io) return;
    try {
      const leaderboard = await tradingEngine.getLeaderboard();
      io.to("leaderboard").emit("leaderboard:update", {
        data: leaderboard,
        timestamp: new Date().toISOString()
      });
    } catch (e) {
      console.error("Leaderboard broadcast error:", e);
    }
  }, 10000);

  setInterval(async () => {
    if (!io) return;
    try {
      const trades = await tradingEngine.getRecentTrades(10);
      io.to("trades").emit("trades:update", {
        data: trades,
        timestamp: new Date().toISOString()
      });
    } catch (e) {
      console.error("Trades broadcast error:", e);
    }
  }, 5000);

  setInterval(async () => {
    if (!io) return;
    try {
      const opportunities = await tradingEngine.getMarketOpportunities();
      io.to("market").emit("market:update", {
        data: opportunities,
        timestamp: new Date().toISOString()
      });
    } catch (e) {
      console.error("Market broadcast error:", e);
    }
  }, 30000);
}

export function emitTradeEvent(trade: any) {
  if (io) {
    io.to("trades").emit("trade:new", {
      data: trade,
      timestamp: new Date().toISOString()
    });
  }
}

export function emitPredictionResult(prediction: any) {
  if (io) {
    io.emit("prediction:result", {
      data: prediction,
      timestamp: new Date().toISOString()
    });
  }
}

export function getIO(): Server | null {
  return io;
}
