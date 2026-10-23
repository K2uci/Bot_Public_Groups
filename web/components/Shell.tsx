import Link from "next/link";
import { LogOut } from "lucide-react";
import { logout } from "@/app/actions";
import Logo from "@/components/Logo";
import NavLinks from "@/components/NavLinks";

export default function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app">
      <aside className="side">
        <Link href="/" className="brand">
          <Logo size={36} />
          <div>
            Bot Facebook
            <small>Panel de administración</small>
          </div>
        </Link>
        <NavLinks />
        <div className="side-foot">
          <form action={logout}>
            <button className="btn ghost sm" type="submit" style={{ width: "100%", justifyContent: "flex-start" }}>
              <LogOut size={16} aria-hidden /> <span className="logout-text">Salir</span>
            </button>
          </form>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
