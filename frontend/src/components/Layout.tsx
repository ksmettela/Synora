import React from "react";
import { NavLink, Outlet } from "react-router-dom";

const NAV = [
  { path: "/", label: "Overview", end: true },
  { path: "/segments", label: "Segments" },
  { path: "/campaigns", label: "Campaigns" },
  { path: "/reports", label: "Reports" },
  { path: "/settings", label: "Settings" },
];

export function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark">S</div>
          <div className="brand-text">
            <div className="brand-name">Synora</div>
            <div className="brand-sub">Advertiser Console</div>
          </div>
        </div>
        <nav className="sidebar-nav">
          {NAV.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="env-pill">demo · mock data</div>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
