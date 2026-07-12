import React from "react"
import ReactDOM from "react-dom/client"
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom"
import { AnimatePresence } from "framer-motion"
import App from "./App.jsx"
import LandingPage from "./pages/LandingPage.jsx"
import ChampionshipPage from "./pages/ChampionshipPage.jsx"
import TradingTerminal from "./pages/TradingTerminal.jsx"
import RacingArena from "./pages/RacingArena.jsx"
import SpaceBackground from "./components/SpaceBackground.jsx"
import UfoFleet from "./components/UfoFleet.jsx"
import NavBar from "./components/NavBar.jsx"
import CinematicIntro from "./components/CinematicIntro.jsx"
import { AppProvider, useApp } from "./state/AppContext.jsx"
import "./index.css"

// Intro plays once per landing visit — mounts only on "/"
function LandingIntro() {
  const { pathname } = useLocation()
  const { intro } = useApp()
  if (pathname !== "/") return null
  return <AnimatePresence>{intro && <CinematicIntro />}</AnimatePresence>
}

function Shell({ children }) {
  const { pathname } = useLocation()
  // /dashboard hosts the L99 Trading Terminal — full-page UI, no SpaceBackground/UFOs
  const isTerminal = pathname === "/dashboard"
  return (
    <>
      {!isTerminal && <SpaceBackground />}
      {!isTerminal && <UfoFleet max={5} />}
      <NavBar />
      <LandingIntro />
      {children}
    </>
  )
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/"             element={<Shell><LandingPage /></Shell>} />
          <Route path="/dashboard"    element={<Shell><TradingTerminal /></Shell>} />
          <Route path="/championship" element={<Shell><ChampionshipPage /></Shell>} />
          <Route path="/arena"        element={<Shell><RacingArena /></Shell>} />
          <Route path="/war-room"     element={<Shell><App /></Shell>} />
        </Routes>
      </BrowserRouter>
    </AppProvider>
  </React.StrictMode>
)
