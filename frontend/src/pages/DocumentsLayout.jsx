import { NavLink, Outlet } from "react-router-dom";

export default function DocumentsLayout() {
  return (
    <div className="docs-shell">
      <div className="docs-subnav">
        <NavLink
          to="/documents"
          end
          className={({ isActive }) => (isActive ? "subnav-link active" : "subnav-link")}
        >
          Listing
        </NavLink>
        <NavLink
          to="/documents/upload"
          className={({ isActive }) => (isActive ? "subnav-link active" : "subnav-link")}
        >
          Upload
        </NavLink>
      </div>
      <div className="docs-content">
        <Outlet />
      </div>
    </div>
  );
}
