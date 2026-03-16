import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-6xl font-bold text-gray-200">404</p>
      <h1 className="text-xl font-semibold text-gray-700 mt-4">Page introuvable</h1>
      <p className="text-sm text-gray-500 mt-2">La ressource demandée n&apos;existe pas.</p>
      <Link
        href="/"
        className="mt-6 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
      >
        Retour au tableau de bord
      </Link>
    </div>
  );
}
