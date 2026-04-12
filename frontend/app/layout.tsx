import type { Metadata } from "next";
import Script from "next/script";
import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import ClientWrapper from "./ClientWrapper";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-jakarta",
  weight: ["300", "400", "500", "600", "700", "800"],
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Controllo BPO Analytics",
  description: "Plataforma de Inteligência Financeira e Análise Contábil — Controllo BPO",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        {/* Bloqueia renderização até definir o tema — evita flash */}
        <Script id="theme-flash-prevention" strategy="beforeInteractive">
          {`(function(){var t=localStorage.getItem('controllo_tema')||'dark';document.documentElement.classList.add(t);}())`}
        </Script>
      </head>
      <body
        className={`${jakarta.variable} ${jetbrains.variable} font-jakarta antialiased`}
        style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}
      >
        <ClientWrapper>{children}</ClientWrapper>
      </body>
    </html>
  );
}
