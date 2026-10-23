import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bot Facebook",
  description: "Panel de administracion del bot de publicaciones",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
