import React from 'react';
import { Link } from 'react-router-dom';

export default function Help() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 text-white">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold flex items-center gap-3">
              <span>❓</span> Guida agli Swap On-Chain
            </h1>
            <p className="text-slate-400 mt-2">
              Tutto quello che devi sapere per usare la funzione Swap di NeoNoble Ramp
            </p>
          </div>
          <div className="flex gap-3">
            <Link to="/swap" className="text-sm text-purple-400 hover:text-purple-300 underline">
              → Vai a Swap
            </Link>
            <Link to="/dashboard" className="text-sm text-slate-300 hover:text-white underline">
              ← Dashboard
            </Link>
          </div>
        </div>

        {/* FAQ Content */}
        <div className="space-y-6">
          {/* Section 1 */}
          <FAQSection
            icon="🔗"
            title="1. Come Connettere MetaMask"
            content={
              <>
                <p className="mb-3">
                  Per usare la funzione Swap, devi prima connettere il tuo wallet MetaMask:
                </p>
                <ol className="list-decimal list-inside space-y-2 ml-4">
                  <li>Vai alla pagina <Link to="/swap" className="text-purple-400 underline">Swap</Link></li>
                  <li>Clicca sul pulsante <strong>"Connect wallet"</strong> in alto a destra nella card Swap</li>
                  <li>Seleziona <strong>MetaMask</strong> dal menu che appare</li>
                  <li>Autorizza la connessione nella finestra popup di MetaMask</li>
                  <li>Il tuo indirizzo wallet apparirà nella card (es. <code className="text-xs bg-slate-800 px-2 py-1 rounded">0x1234...abcd</code>)</li>
                </ol>
                <div className="mt-4 p-3 bg-blue-900/30 border border-blue-700/50 rounded-lg text-sm">
                  💡 <strong>Suggerimento:</strong> Assicurati di essere sulla rete <strong>BSC Mainnet (Binance Smart Chain)</strong>. 
                  Se sei su una rete diversa, l'app ti chiederà automaticamente di cambiare rete.
                </div>
              </>
            }
          />

          {/* Section 2 */}
          <FAQSection
            icon="⛽"
            title="2. Perché Serve BNB per il Gas?"
            content={
              <>
                <p className="mb-3">
                  Gli swap on-chain su BSC richiedono che tu paghi le <strong>commissioni gas</strong> in BNB:
                </p>
                <ul className="list-disc list-inside space-y-2 ml-4">
                  <li><strong>Cosa sono le commissioni gas?</strong> Sono le fee pagate ai validatori della blockchain per processare la tua transazione.</li>
                  <li><strong>Quanto costa?</strong> Generalmente tra 0.0005 e 0.003 BNB per transazione (circa $0.30-$2 USD).</li>
                  <li><strong>Chi paga?</strong> Tu paghi direttamente dal tuo wallet connesso. NeoNoble Ramp <em>non</em> paga il gas per te.</li>
                  <li><strong>Quanti BNB servono?</strong> Ti consigliamo di avere almeno <strong>0.005-0.01 BNB</strong> nel tuo wallet per coprire più transazioni.</li>
                </ul>
                <div className="mt-4 p-3 bg-amber-900/30 border border-amber-700/50 rounded-lg text-sm">
                  ⚠️ <strong>Importante:</strong> Se il tuo saldo BNB è inferiore a 0.002, vedrai un banner di avviso nella pagina Swap. 
                  Senza BNB, non potrai firmare e inviare le transazioni.
                </div>
                <p className="mt-3 text-sm text-slate-400">
                  📌 Come ottenere BNB? Puoi acquistare BNB su exchange centralizzati (Binance, Coinbase, ecc.) e trasferirli al tuo wallet MetaMask.
                </p>
              </>
            }
          />

          {/* Section 3 */}
          <FAQSection
            icon="🔄"
            title="3. Come Fare Approve + Swap di Token"
            content={
              <>
                <p className="mb-3">
                  Il processo di swap si compone di due passaggi principali:
                </p>
                
                <div className="space-y-4">
                  <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                    <h4 className="font-semibold text-purple-300 mb-2">Passo 1: Approve (Approvazione Token)</h4>
                    <p className="text-sm mb-2">
                      Se stai scambiando un token ERC-20 (come NENO, USDT, BTCB), devi prima <strong>approvare</strong> il contratto router a spendere i tuoi token:
                    </p>
                    <ul className="list-disc list-inside space-y-1 ml-4 text-sm text-slate-300">
                      <li>Inserisci l'importo da swappare e seleziona i token</li>
                      <li>Clicca sul pulsante <strong>"Swap NENO → USDT"</strong></li>
                      <li>MetaMask aprirà una finestra popup per firmare l'<strong>approvazione</strong></li>
                      <li>Conferma la transazione di approvazione (costa gas, ma solo la prima volta per ogni token)</li>
                      <li>Attendi qualche secondo per la conferma on-chain</li>
                    </ul>
                    <p className="text-xs text-slate-400 mt-2">
                      💡 Nota: Se hai già approvato quel token in passato con allowance sufficiente, questo step viene saltato automaticamente.
                    </p>
                  </div>

                  <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                    <h4 className="font-semibold text-emerald-300 mb-2">Passo 2: Swap (Transazione Vera e Propria)</h4>
                    <p className="text-sm mb-2">
                      Dopo l'approvazione, l'app chiederà di firmare la transazione di swap:
                    </p>
                    <ul className="list-disc list-inside space-y-1 ml-4 text-sm text-slate-300">
                      <li>MetaMask aprirà una seconda finestra popup per il <strong>swap</strong></li>
                      <li>Verifica i dettagli della transazione (importo, destinazione, gas)</li>
                      <li>Conferma la transazione</li>
                      <li>Attendi la conferma on-chain (generalmente 5-15 secondi)</li>
                      <li>I token di output arriveranno <strong>direttamente nel tuo wallet connesso</strong></li>
                    </ul>
                    <p className="text-xs text-emerald-400 mt-2">
                      ✅ Quando la transazione è confermata, vedrai un messaggio di successo con il link a BscScan.
                    </p>
                  </div>
                </div>

                <div className="mt-4 p-3 bg-purple-900/30 border border-purple-700/50 rounded-lg text-sm">
                  🎯 <strong>Riepilogo:</strong> Firma l'approvazione (se necessario) → Firma lo swap → I token arrivano nel tuo wallet. Tutto avviene on-chain, in modo trasparente e sicuro.
                </div>
              </>
            }
          />

          {/* Section 4 */}
          <FAQSection
            icon="🔍"
            title="4. Come Verificare la Transazione su BscScan"
            content={
              <>
                <p className="mb-3">
                  Dopo aver completato uno swap, puoi verificare lo stato della transazione direttamente su <strong>BscScan</strong> (l'explorer ufficiale di BSC):
                </p>
                <ol className="list-decimal list-inside space-y-2 ml-4">
                  <li>Nella card Swap, apparirà un messaggio di successo con un link <strong>"View on BscScan ↗"</strong></li>
                  <li>Clicca sul link per aprire BscScan in una nuova tab</li>
                  <li>Verifica i dettagli della transazione:
                    <ul className="list-disc list-inside ml-6 mt-1 text-sm text-slate-300">
                      <li><strong>Status:</strong> Success (verde) = transazione confermata</li>
                      <li><strong>From:</strong> Il tuo indirizzo wallet</li>
                      <li><strong>To:</strong> L'indirizzo del router/contratto</li>
                      <li><strong>Tokens Transferred:</strong> I token che hai scambiato</li>
                    </ul>
                  </li>
                  <li>Puoi anche vedere il <strong>gas fee</strong> pagato e il <strong>block number</strong> della conferma</li>
                </ol>
                <div className="mt-4 p-3 bg-slate-800 border border-slate-700 rounded-lg text-sm">
                  <p className="font-semibold mb-2">📋 Link Utili:</p>
                  <ul className="space-y-1">
                    <li>
                      <a href="https://bscscan.com" target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300 underline">
                        🔗 BscScan Homepage
                      </a>
                    </li>
                    <li>
                      <span className="text-slate-400">💡 Puoi anche cercare il tuo wallet address su BscScan per vedere tutte le tue transazioni BSC</span>
                    </li>
                  </ul>
                </div>
              </>
            }
          />

          {/* Section 5 - Additional Info */}
          <FAQSection
            icon="🛡️"
            title="5. Sicurezza e Best Practices"
            content={
              <>
                <ul className="list-disc list-inside space-y-2 ml-4">
                  <li><strong>Non condividere mai</strong> la tua seed phrase o private key con nessuno</li>
                  <li><strong>Controlla sempre</strong> i dettagli della transazione prima di confermare in MetaMask</li>
                  <li><strong>Usa slippage appropriato:</strong> 0.5-1% per stablecoin, 1-2% per token volatili</li>
                  <li><strong>Verifica l'indirizzo del contratto:</strong> assicurati di scambiare i token corretti (controlla su BscScan)</li>
                  <li><strong>Inizia con importi piccoli</strong> se è la tua prima volta, per familiarizzare con il processo</li>
                </ul>
                <div className="mt-4 p-3 bg-emerald-900/30 border border-emerald-700/50 rounded-lg text-sm">
                  ✅ <strong>Ricorda:</strong> Con NeoNoble Ramp Swap, sei sempre tu a controllare i tuoi fondi. 
                  I token non passano mai attraverso i nostri server — tutto avviene direttamente sulla blockchain BSC.
                </div>
              </>
            }
          />
        </div>

        {/* CTA */}
        <div className="mt-10 p-6 bg-gradient-to-r from-purple-900/40 to-pink-900/40 border border-purple-700 rounded-2xl text-center">
          <h3 className="text-xl font-bold mb-2">Pronto per Iniziare?</h3>
          <p className="text-slate-300 mb-4">
            Vai alla pagina Swap e inizia a scambiare token on-chain su BSC in modo sicuro e trasparente.
          </p>
          <Link
            to="/swap"
            className="inline-block px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 rounded-xl font-semibold transition"
          >
            🚀 Vai a Swap On-Chain
          </Link>
          <Link
            to="/launchpad"
            className="ml-3 inline-block px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 rounded-xl font-semibold transition"
          >
            🎯 Launchpad Token
          </Link>
        </div>

        {/* Launchpad FAQ */}
        <div className="mt-10 space-y-6">
          <h2 className="text-2xl md:text-3xl font-bold flex items-center gap-3">
            <span>🎯</span> Launchpad — Bonding Curve Token
          </h2>

          <FAQSection
            icon="🚀"
            title="Cos'è il Launchpad?"
            content={
              <div className="space-y-3">
                <p>
                  Il Launchpad ti permette di <strong>creare un token ERC-20 sulla BSC</strong> con
                  bonding curve automatica (stile Pump.fun). Paghi solo la <strong>deploy fee (~0.05 BNB)</strong>,
                  nessun collateral, nessun capitale bloccato.
                </p>
                <p className="text-sm text-slate-400">
                  Il prezzo del token parte basso e sale man mano che gli utenti comprano. La liquidità
                  viene interamente dai buyer — tu come creator ricevi l'1% di fee automaticamente su ogni
                  compra/vendita.
                </p>
              </div>
            }
          />

          <FAQSection
            icon="📈"
            title="Come funziona la bonding curve?"
            content={
              <div className="space-y-2 text-sm">
                <p>
                  <strong>Formula:</strong> x * y = k (constant-product, stile Uniswap V2). Le reserve
                  "virtuali" iniziali bootstrapano il prezzo senza bisogno di LP.
                </p>
                <ul className="list-disc ml-6 space-y-1 text-slate-400">
                  <li>Ogni buy: l'utente paga BNB → il contratto minta token</li>
                  <li>Ogni sell: l'utente brucia token → il contratto restituisce BNB dalle reserve</li>
                  <li>Quando il contratto raccoglie <strong>85 BNB</strong> la curva si chiude (graduation)</li>
                  <li>200M token vengono riservati per creare un LP su PancakeSwap post-graduation</li>
                </ul>
              </div>
            }
          />

          <FAQSection
            icon="💡"
            title="Importante: NON è un sistema a prezzo fisso"
            content={
              <div className="space-y-2 text-sm">
                <p className="text-amber-200">
                  Il prezzo del tuo token <strong>fluttua col volume</strong>. Non c'è redeem garantito a
                  un valore nominale prestabilito. Se nessuno compra, chi ha comprato presto può vendere solo
                  al prezzo corrente della curva (che può essere più basso).
                </p>
                <p className="text-slate-400">
                  Per un sistema con valore ancorato + redeem a NAV trimestrale, è in sviluppo il
                  <strong> programma STO (Security Token)</strong> — conforme MiCA/CONSOB. Contattaci per
                  accesso beta.
                </p>
              </div>
            }
          />
        </div>

        {/* Low BNB Gas tip */}
        <div className="mt-10 space-y-6">
          <h2 className="text-2xl md:text-3xl font-bold flex items-center gap-3">
            <span>⛽</span> BNB per il gas
          </h2>
          <FAQSection
            icon="💰"
            title="Perché mi serve BNB?"
            content={
              <div className="space-y-2 text-sm">
                <p>
                  Ogni transazione su BSC (swap, buy, sell, approve) richiede un piccolo pagamento in BNB
                  come <strong>gas fee</strong> (~0.0005–0.002 BNB per operazione). Questo va ai miner della
                  rete, <strong>non a NeoNoble</strong>.
                </p>
                <p className="text-slate-400">
                  Raccomandiamo di tenere sempre <strong>0.005–0.01 BNB</strong> nel wallet per non rimanere
                  bloccato a metà operazione. Vedi il banner giallo nella pagina Swap se il tuo saldo è basso.
                </p>
                <p className="text-slate-400 text-xs">
                  Puoi comprare BNB direttamente da MetaMask (pulsante "Buy"), da un exchange (Binance,
                  Coinbase, Kraken) e inviarlo al tuo wallet, oppure usare on-ramp come Transak integrato
                  in NeoNoble.
                </p>
              </div>
            }
          />
        </div>

        {/* Spare div for spacing */}
        <div className="mt-10">
        </div>

        {/* Contact/Support */}
        <div className="mt-8 text-center text-sm text-slate-400">
          <p>Hai ancora domande? Contatta il supporto o consulta la <Link to="/dashboard" className="text-purple-400 underline">Dashboard</Link></p>
        </div>
      </div>
    </div>
  );
}

function FAQSection({ icon, title, content }) {
  return (
    <div className="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-2xl p-6 shadow-xl">
      <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
        <span className="text-2xl">{icon}</span>
        {title}
      </h2>
      <div className="text-slate-300 leading-relaxed">
        {content}
      </div>
    </div>
  );
}
