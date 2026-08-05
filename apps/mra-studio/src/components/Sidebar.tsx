import { NavLink } from "react-router-dom";

const items = [
  ["Dashboard", "/dashboard"],
  ["Knowledge", "/knowledge"],
  ["Manuals", "/manuals"],
  ["Academy", "/academy"],
  ["Quiz", "/quiz"],
  ["Media", "/media"],
  ["Marketplace", "/marketplace"],
  ["Partners", "/partners"],
  ["Laboratory", "/laboratory"],
  ["Analytics", "/analytics"],
  ["Users", "/users"],
  ["Settings", "/settings"],
] as const;

export function Sidebar() {
  return (
    <aside className="sidebar">
      <nav aria-label="Navigazione principale">
        {items.map(([label, path]) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              isActive ? "nav-item active" : "nav-item"
            }
          >
            <span className="nav-dot" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <span>KNOWLEDGE ENGINE</span>
        <strong>KE-002</strong>
      </div>
    </aside>
  );
}
