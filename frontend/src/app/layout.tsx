import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Radar de Precios",
  description: "Plataforma SaaS para comparar precios reales de supermercados chilenos."
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es" className="dark">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
