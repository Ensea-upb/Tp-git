import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Recherche de Stage",
  description: "Copilote intelligent de recherche de stage avec human-in-the-loop",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen bg-slate-50">
        {/* Navigation principale */}
        <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-14">
              <Link href="/" className="flex items-center gap-2">
                <span className="text-lg font-bold text-gray-900">Agent Stage</span>
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">Sprint 5</span>
              </Link>
              <div className="flex items-center gap-6 text-sm font-medium">
                <Link href="/offers" className="text-gray-600 hover:text-blue-700 transition-colors">
                  Offres
                </Link>
                <Link href="/preferences" className="text-gray-600 hover:text-blue-700 transition-colors">
                  Préférences
                </Link>
                <Link href="/profile" className="text-gray-600 hover:text-blue-700 transition-colors">
                  Profil
                </Link>
              </div>
            </div>
          </div>
        </nav>

        {/* Contenu */}
        <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        {/* Footer minimal */}
        <footer className="border-t border-gray-200 mt-16">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <p className="text-xs text-gray-400 text-center">
              Agent Personnel de Recherche de Stage — Sprint 5 — Copilote IA local
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
