import { FlaskConical, GitCompareArrows, Search } from "lucide-react";
import { useEffect, useState } from "react";
import FragmentComparePage from "./pages/FragmentComparePage";
import FragmentDetailPage from "./pages/FragmentDetailPage";
import FragmentSearchPage from "./pages/FragmentSearchPage";
import MoleculeDetailPage from "./pages/MoleculeDetailPage";

type Route =
  | { name: "search" }
  | { name: "fragment"; id: string }
  | { name: "compare"; fragmentA: string; fragmentB: string }
  | { name: "molecule"; id: string };

function parseRoute(): Route {
  const hash = window.location.hash.replace(/^#/, "");
  const parts = hash.split("/").filter(Boolean);
  if (parts[0] === "compare" && parts[1] && parts[2]) return { name: "compare", fragmentA: parts[1], fragmentB: parts[2] };
  if (parts[0] === "fragments" && parts[1]) return { name: "fragment", id: parts[1] };
  if (parts[0] === "molecules" && parts[1]) return { name: "molecule", id: parts[1] };
  return { name: "search" };
}

export default function App() {
  const [route, setRoute] = useState<Route>(parseRoute());

  useEffect(() => {
    const onHashChange = () => setRoute(parseRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-white/70 bg-white/85 shadow-sm backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between px-5 py-4">
          <a href="#" className="flex items-center gap-3 text-ink">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-signal text-white shadow-sm">
              <FlaskConical size={20} />
            </span>
            <div>
              <h1 className="text-lg font-semibold tracking-normal text-slate-950">MedChem Fragment Atlas</h1>
              <p className="text-xs text-slate-600">BRICS fragments with ChEMBL and clean TDC ADMET context</p>
            </div>
          </a>
          <nav className="flex items-center gap-2">
            <a className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:border-signal hover:text-signal" href="#">
              <Search size={16} />
              Search
            </a>
            <span className="hidden items-center gap-2 rounded-md border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800 md:inline-flex">
              <GitCompareArrows size={14} />
              ADMET comparison ready
            </span>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-[1500px] px-5 py-6">
        {route.name === "search" && <FragmentSearchPage />}
        {route.name === "compare" && <FragmentComparePage fragmentA={route.fragmentA} fragmentB={route.fragmentB} />}
        {route.name === "fragment" && <FragmentDetailPage fragmentId={route.id} />}
        {route.name === "molecule" && <MoleculeDetailPage chemblId={route.id} />}
      </main>
    </div>
  );
}
