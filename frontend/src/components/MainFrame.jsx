import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import BrandMark from "./BrandMark";
import Icon from "./Icon";
import AccountModal from "./AccountModal";
import Avatar from "./Avatar";
import { api } from "../api";
import "../pages/account.css";

// The frame around the four main pages plus My Profile and Settings (listed after My Notebook): a left-hand menu (a slide-in drawer on phones), a header with a shortcut to the Notebook
// (so notes are one tap away while studying) and the student's account. Only signed-in students get in.
const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { to: "/planner", label: "Study Planner", icon: "planner" },
  { to: "/ai-zone", label: "AI Learning Zone", icon: "sparkle" },
  { to: "/notebook", label: "My Notebook", icon: "toolkit" },
  { to: "/profile", label: "My Profile", icon: "profile" },
  { to: "/settings", label: "Settings", icon: "settings" },
];

export default function MainFrame() {
  const { token, user, loading, logout } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [account, setAccount] = useState(false);
  const [pic, setPic] = useState(0);        // version of the profile picture (0 = none); changes when the student changes it in My Profile

  useEffect(() => {
    if (!token) return undefined;
    let dead = false;
    const load = () => api.myProfile(token).then((p) => { if (!dead) setPic(p.has_picture ? p.picture_version : 0); }).catch(() => {});
    load();
    window.addEventListener("mindsync:profile-changed", load);
    return () => { dead = true; window.removeEventListener("mindsync:profile-changed", load); };
  }, [token]);

  useEffect(() => { setMenuOpen(false); }, [location.pathname]);
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") setMenuOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!token && !loading) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (loading || !user) return <div className="page-loading" role="status">Loading MindSync…</div>;

  const onNotebook = location.pathname.startsWith("/notebook");
  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? "open" : ""}`} aria-label="Main">
        <div className="sidebar-brand">
          <Link to="/" title="Home" className="sidebar-brand-link">
            <BrandMark />
            <span><strong>MindSync</strong><small>Study smarter. Feel better.</small></span>
          </Link>
          <button className="icon-button sidebar-close" onClick={() => setMenuOpen(false)} aria-label="Close menu"><Icon name="close" /></button>
        </div>
        <nav className="sidebar-nav" aria-label="Pages">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
              <Icon name={item.icon} /><span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <button type="button" className="nav-item nav-item-small nav-button" onClick={() => setAccount(true)}><Icon name="profile" size={18} /><span>My account</span></button>
          <p className="sidebar-who p28-who" title={user.email}><Avatar token={token} name={user.display_name} version={pic} size={28} /><span>{user.display_name || "Student"}</span></p>
          <button className="link-button" onClick={() => logout()}><Icon name="logout" size={16} /> Log out</button>
        </div>
      </aside>
      {menuOpen && <button className="sidebar-scrim" aria-label="Close menu" onClick={() => setMenuOpen(false)} />}

      <div className="app-main">
        <header className="topbar">
          <button className="icon-button" onClick={() => setMenuOpen(true)} aria-label="Open menu" aria-expanded={menuOpen}><Icon name="menu" /></button>
          <Link to="/" className="topbar-brand"><BrandMark /><strong>MindSync</strong></Link>
          <span className="topbar-spacer" />
          {!onNotebook && <Link to="/notebook" className="topbar-notebook" title="Open My Notebook"><Icon name="toolkit" size={18} /><span>My Notebook</span></Link>}
          <button type="button" className="greeting greeting-button" onClick={() => setAccount(true)}><Avatar token={token} name={user.display_name} version={pic} size={28} /><span className="visually-hidden">My account: </span>{user.display_name}</button>
        </header>
        <main className="page" id="main"><Outlet /></main>
      </div>
      {account && <AccountModal onClose={() => setAccount(false)} />}
    </div>
  );
}
