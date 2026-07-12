import { Switch, Route, Link, useLocation } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/lib/theme";
import NotFound from "@/pages/not-found";
import Dashboard from "@/pages/Dashboard";
import TradingRace from "@/pages/TradingRace";
import GodsLevelStrategy from "@/pages/GodsLevelStrategy";
import TestingEngine from "@/pages/TestingEngine";
import { Trophy, LayoutDashboard, Crown, FlaskConical } from "lucide-react";

function NavBar() {
  const [location] = useLocation();
  
  return (
    <nav className="bg-card border-b border-border px-4 py-2" data-testid="main-nav">
      <div className="max-w-7xl mx-auto flex items-center gap-6">
        <span className="font-bold text-lg" data-testid="brand-name">Trading Guru</span>
        <div className="flex items-center gap-4 flex-wrap">
          <Link href="/" className={`flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors ${location === "/" ? "bg-primary text-primary-foreground" : "bg-muted"}`} data-testid="nav-dashboard">
            <LayoutDashboard className="w-4 h-4" />
            Dashboard
          </Link>
          <Link href="/race" className={`flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors ${location === "/race" ? "bg-primary text-primary-foreground" : "bg-muted"}`} data-testid="nav-race">
            <Trophy className="w-4 h-4" />
            AI Race
          </Link>
          <Link href="/gods-level" className={`flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors ${location === "/gods-level" ? "bg-primary text-primary-foreground" : "bg-muted"}`} data-testid="nav-gods-level">
            <Crown className="w-4 h-4" />
            Gods Level
          </Link>
          <Link href="/testing-engine" className={`flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors ${location === "/testing-engine" ? "bg-primary text-primary-foreground" : "bg-muted"}`} data-testid="nav-testing-engine">
            <FlaskConical className="w-4 h-4" />
            Testing Engine
          </Link>
        </div>
      </div>
    </nav>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={Dashboard} />
      <Route path="/race" component={TradingRace} />
      <Route path="/gods-level" component={GodsLevelStrategy} />
      <Route path="/testing-engine" component={TestingEngine} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider>
          <div className="min-h-screen bg-background">
            <NavBar />
            <Router />
          </div>
          <Toaster />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
