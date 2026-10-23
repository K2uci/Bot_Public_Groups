import Link from "next/link";
import { logout } from "@/app/actions";

export default function Shell({ children }: { children: React.ReactNode }) {
  return (
    <>
      <header className="top">
        <nav>
          <strong>Bot Facebook</strong>
          <Link href="/">Panel</Link>
          <Link href="/clientes">Clientes</Link>
          <Link href="/cuenta">Cuenta</Link>
        </nav>
        <form action={logout}>
          <button className="sec" type="submit">Salir</button>
        </form>
      </header>
      <main>{children}</main>
    </>
  );
}
