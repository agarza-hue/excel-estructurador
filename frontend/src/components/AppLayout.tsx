import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/upload", label: "Subir Excel" },
  { to: "/capture", label: "Captura" },
  { to: "/explorer", label: "Explorador" },
  { to: "/config", label: "Config" }
];

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white px-4 py-5 lg:block">
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Excel</p>
          <h1 className="mt-1 text-xl font-semibold text-slate-950">Estructurador</h1>
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                [
                  "block rounded-md px-3 py-2 text-sm font-medium",
                  isActive ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                ].join(" ")
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
          <div className="mb-3 font-semibold text-slate-950">Excel Estructurador</div>
          <nav className="flex gap-2 overflow-x-auto pb-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  [
                    "whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium",
                    isActive ? "bg-blue-50 text-blue-700" : "bg-slate-100 text-slate-700"
                  ].join(" ")
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
