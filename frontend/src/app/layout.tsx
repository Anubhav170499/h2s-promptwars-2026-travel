import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TravelPilot - Adaptive Travel & Cultural Discovery",
  description: "Capture travel styles, complete local etiquette diagnostics, and explore tailored GenAI-powered itineraries with active budget feasibility.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <main className="min-h-screen flex flex-col">
          {children}
        </main>
      </body>
    </html>
  );
}
