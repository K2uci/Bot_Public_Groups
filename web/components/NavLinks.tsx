"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, UserCog, Users } from "lucide-react";

const items = [
  { href: "/", label: "Panel", icon: LayoutDashboard },
  { href: "/clientes", label: "Clientes", icon: Users },
  { href: "/cuenta", label: "Cuenta", icon: UserCog },
];

export default function NavLinks() {
  const pathname = usePathname();
  return (
    <nav className="nav" aria-label="Principal">
      {items.map(({ href, label, icon: Icon }) => {
        const activo = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link key={href} href={href} aria-current={activo ? "page" : undefined}>
            <Icon size={18} aria-hidden />
            <span>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
