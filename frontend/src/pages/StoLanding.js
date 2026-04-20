import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { stoApi } from '../api/sto';

/**
 * Landing pubblica SEO-optimized per STO.
 *
 * - Meta tags dinamici (OG, Twitter Card, schema.org)
 * - Hero + value prop + timeline + FAQ
 * - CTA verso /sto/invest per form pre-registrazione
 */
export default function StoLanding() {
  const [info, setInfo] = useState(null);

  useEffect(() => {
    (async () => {
      try { setInfo(await stoApi.publicInfo()); } catch (_) {}
    })();

    // Meta tags (dinamici via DOM — evita react-helmet per semplicita`)
    const set = (sel, content) => {
      const el = document.querySelector(sel);
      if (el) el.setAttribute('content', content);
    };
    const desc = 'NeoNoble Ramp STO — Security Token utility + revenue share su Polygon PoS, redemption trimestrale a NAV. Pre-registrati per il go-live.';
    document.title = 'NeoNoble STO — Security Token Offering | NNRS | Polygon';
    set('meta[name="description"]', desc);
    set('meta[property="og:title"]', 'NeoNoble Ramp STO — Revenue Share Security Token');
    set('meta[property="og:description"]', desc);
    set('meta[property="og:image"]', `${window.location.origin}/og-sto.png`);
    set('meta[property="og:url"]', `${window.location.origin}/sto`);
    set('meta[property="og:type"]', 'website');
    set('meta[name="twitter:card"]', 'summary_large_image');
    set('meta[name="twitter:title"]', 'NeoNoble Ramp STO');
    set('meta[name="twitter:description"]', desc);

    // schema.org JSON-LD
    const ld = document.createElement('script');
    ld.type = 'application/ld+json';
    ld.text = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'FinancialProduct',
      name: 'NeoNoble Revenue Share Security Token',
      description: desc,
      provider: {
        '@type': 'Organization',
        name: 'NeoNoble Ramp S.r.l.',
        url: 'https://neonobleramp.com',
      },
      offers: {
        '@type': 'Offer',
        priceCurrency: 'EUR',
        price: '250',
        availability: 'https://schema.org/PreOrder',
      },
    });
    document.head.appendChild(ld);
    return () => { try { document.head.removeChild(ld); } catch (_) {} };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 text-white">
      <div className="max-w-6xl mx-auto px-4 py-12">

        {/* Hero */}
        <div className="text-center mb-16">
          <span className="inline-block px-3 py-1 rounded-full bg-indigo-900/60 text-indigo-200 text-xs uppercase tracking-widest mb-6">
            Coming Soon · Polygon PoS · MiCA / TUF 100-bis Compliant
          </span>
          <h1 className="text-5xl md:text-7xl font-bold bg-gradient-to-r from-indigo-300 via-pink-300 to-amber-300 bg-clip-text text-transparent mb-6 leading-tight">
            Partecipa ai ricavi di<br />NeoNoble Ramp
          </h1>
          <p className="text-xl text-slate-300 max-w-2xl mx-auto mb-8">
            Un security token regolamentato che ti da` diritto a una <strong>quota pro-rata dei ricavi</strong> della
            piattaforma — con <strong>redemption trimestrale a NAV</strong> certificato da revisore indipendente.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              to="/sto/invest"
              data-testid="sto-landing-cta"
              className="px-8 py-4 rounded-xl text-lg font-semibold text-white bg-gradient-to-r from-indigo-600 to-pink-600 hover:from-indigo-500 hover:to-pink-500 transition shadow-xl shadow-indigo-900/40"
            >
              Pre-registrati al go-live →
            </Link>
            <a
              href="#how-it-works"
              className="px-8 py-4 rounded-xl text-lg font-medium text-slate-200 border border-slate-700 hover:border-slate-500 transition"
            >
              Come funziona
            </a>
          </div>
        </div>

        {/* Key metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-16">
          <Metric label="Raise target" value={info ? `€${info.target_raise_eur_min/1e6}–${info.target_raise_eur_max/1e6}M` : '€1–8M'} />
          <Metric label="Prezzo emissione" value={`€${info?.nominal_price_eur || 250}`} />
          <Metric label="Revenue share" value="Trimestrale" />
          <Metric label="Chain" value={info?.chain || 'Polygon PoS'} />
        </div>

        {/* How it works */}
        <div id="how-it-works" className="mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-8 text-center">Come funziona</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Step n="1" title="KYC + Whitelist" text="Completi la verifica identita` con Sumsub. Il tuo wallet viene registrato on-chain come investitore qualificato." />
            <Step n="2" title="Sottoscrivi token" text="Bonifico SEPA o USDC. Ricevi i token NNRS al prezzo di emissione. Il lockup iniziale e` di 12 mesi." />
            <Step n="3" title="Revenue & Redemption" text="Ogni trimestre ricevi la tua quota pro-rata dei ricavi NeoNoble. Puoi chiedere redemption a NAV con riserva USDC dedicata." />
          </div>
        </div>

        {/* Revenue breakdown */}
        <div className="mb-16 p-8 rounded-2xl bg-gradient-to-br from-slate-900/80 to-indigo-900/30 border border-slate-800">
          <h3 className="text-2xl font-bold mb-6">📊 Da dove arrivano i ricavi</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <RevenueSource icon="🔄" title="Fee swap DEX" text="Commissioni sulle transazioni via 1inch + PancakeSwap aggregator." />
            <RevenueSource icon="💳" title="Carte di pagamento" text="Interchange su ogni transazione carta + monthly fee." />
            <RevenueSource icon="🏦" title="Banking SEPA" text="Fee su bonifici in entrata/uscita e tenuta conto IBAN virtuale." />
            <RevenueSource icon="🚀" title="Launchpad" text="1% platform fee su ogni buy/sell nella bonding curve + deploy fee." />
          </div>
        </div>

        {/* Timeline */}
        <div className="mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-8 text-center">Roadmap Go-Live</h2>
          <div className="space-y-4">
            <Timeline phase="Q1 2026" title="Legal + Audit" status="in-progress" text="Nomina studio legale fintech, redazione prospetto art. 100-bis TUF, audit smart contract (OpenZeppelin / Certik)." />
            <Timeline phase="Q2 2026" title="Deploy Polygon" status="upcoming" text="Deploy contratti su Polygon mainnet, verifica Polygonscan, apertura subscription KYC-gated." />
            <Timeline phase="Q3 2026" title="First NAV" status="upcoming" text="Prima pubblicazione NAV certificato + apertura finestra redemption trimestrale." />
            <Timeline phase="Q4 2026" title="Revenue Distribution" status="upcoming" text="Prima distribuzione revenue share agli holder (in USDC)." />
          </div>
        </div>

        {/* FAQ */}
        <div className="mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-8 text-center">FAQ</h2>
          <div className="space-y-4">
            <FAQ q="Chi puo` investire?" a="Solo investitori KYC-verificati residenti in UE/SEE (inizialmente). L'emissione e` limitata a 150 holder per rimanere sotto le soglie dell'esenzione TUF art. 100-bis." />
            <FAQ q="Qual e` l'importo minimo?" a="Da definire con l'avvocato — indicativamente €500–1.000 per ticket. Conferma al go-live." />
            <FAQ q="Cosa succede se vendo sul mercato secondario?" a="I token hanno transfer restrictions: possono essere trasferiti solo tra wallet whitelisted. Non ci sara` un mercato secondario aperto in v1." />
            <FAQ q="Come viene calcolato il NAV?" a="Trimestralmente dal CFO + certificato da un revisore indipendente iscritto al Registro CONSOB. Report pubblicato su IPFS, hash registrato on-chain." />
            <FAQ q="Posso perdere tutto?" a="Si`. Investire in security token comporta rischio di perdita totale del capitale. Leggere il prospetto prima di investire." />
          </div>
        </div>

        {/* Footer CTA */}
        <div className="text-center p-8 rounded-2xl bg-gradient-to-br from-indigo-900/50 to-pink-900/30 border border-indigo-700/50">
          <h3 className="text-2xl md:text-3xl font-bold mb-3">Pronto al go-live?</h3>
          <p className="text-slate-300 mb-6">
            Lascia la tua email. Ti contattiamo appena apriamo le sottoscrizioni.
          </p>
          <Link
            to="/sto/invest"
            className="inline-block px-8 py-4 rounded-xl text-lg font-semibold text-white bg-gradient-to-r from-indigo-600 to-pink-600 hover:from-indigo-500 hover:to-pink-500 transition"
          >
            Pre-registrati →
          </Link>
        </div>

        <p className="mt-8 text-xs text-slate-500 text-center leading-relaxed max-w-2xl mx-auto">
          Questa pagina NON costituisce offerta al pubblico ai sensi dell'art. 94 TUF.
          L'emissione e` subordinata all'approvazione del prospetto (o esenzione art. 100-bis TUF)
          e all'audit smart contract. Gli investimenti in crypto-asset comportano rischi elevati.
        </p>
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="p-4 rounded-xl bg-slate-900/60 backdrop-blur border border-slate-800 text-center">
      <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
      <div className="text-xl md:text-2xl font-bold mt-1 bg-gradient-to-r from-indigo-300 to-pink-300 bg-clip-text text-transparent">
        {value}
      </div>
    </div>
  );
}
function Step({ n, title, text }) {
  return (
    <div className="p-6 rounded-2xl bg-slate-900/60 backdrop-blur border border-slate-800">
      <div className="w-10 h-10 mb-4 rounded-full bg-gradient-to-br from-indigo-500 to-pink-500 text-white font-bold flex items-center justify-center">
        {n}
      </div>
      <h3 className="font-bold text-lg mb-2">{title}</h3>
      <p className="text-sm text-slate-400">{text}</p>
    </div>
  );
}
function RevenueSource({ icon, title, text }) {
  return (
    <div className="flex gap-4">
      <div className="text-3xl">{icon}</div>
      <div>
        <h4 className="font-semibold mb-1">{title}</h4>
        <p className="text-sm text-slate-400">{text}</p>
      </div>
    </div>
  );
}
function Timeline({ phase, title, text, status }) {
  return (
    <div className="flex gap-4 p-4 rounded-xl bg-slate-900/50 border border-slate-800">
      <div className={`shrink-0 w-24 text-xs font-bold uppercase ${status === 'in-progress' ? 'text-amber-300' : 'text-slate-500'}`}>
        {phase}
      </div>
      <div>
        <div className="flex items-center gap-2 mb-1">
          <h4 className="font-semibold">{title}</h4>
          {status === 'in-progress' && (
            <span className="text-[10px] px-2 py-0.5 rounded bg-amber-900/50 text-amber-200 uppercase">in corso</span>
          )}
        </div>
        <p className="text-sm text-slate-400">{text}</p>
      </div>
    </div>
  );
}
function FAQ({ q, a }) {
  return (
    <details className="p-5 rounded-xl bg-slate-900/50 border border-slate-800 cursor-pointer group">
      <summary className="font-semibold list-none flex items-center justify-between">
        <span>{q}</span>
        <span className="text-slate-500 group-open:rotate-45 transition-transform">+</span>
      </summary>
      <p className="mt-3 text-sm text-slate-400">{a}</p>
    </details>
  );
}
