# Procedura NAV Trimestrale — NeoNoble STO

> Procedura operativa interna per il calcolo, la revisione e la pubblicazione
> on-chain del NAV (Net Asset Value) del token NNRS.

## Cadenza

Trimestrale: 31 marzo, 30 giugno, 30 settembre, 31 dicembre.

## Figure coinvolte

| Ruolo | Responsabilità |
|---|---|
| **CFO NeoNoble** | Predisposizione bilancio trimestrale + calcolo NAV interno |
| **Revisore indipendente** | [da nominare, es. BDO / Mazars / PKF] — certificazione NAV |
| **Oracle operator** (wallet on-chain) | Pubblicazione NAV on-chain via `NAVOracle.updateNAV` |
| **Tesoreria** | Alimentazione riserva `RedemptionVault.fund()` |

## Formula NAV

```
NAV_per_token = (Asset_netti_EUR) / (Supply_totale_NNRS)

Asset_netti = Attività (cassa + investimenti liquidi + crediti operativi)
           - Passività (debiti fornitori + debiti finanziari)
           - Riserve obbligatorie (es. redemption già approvata non ancora pagata)
```

Il NAV viene espresso in USDC (6 decimali) on-chain. Conversione EUR→USDC
al tasso BCE del giorno del calcolo.

## Workflow

### T-20 (20 giorni prima della data di riferimento)
- CFO avvia chiusura contabile trimestrale
- Richiesta lettera di conferma ai depositari bancari

### T-10
- CFO produce draft NAV + working paper
- Invio al revisore indipendente per verifica

### T-5
- Revisore conclude verifica, firma digitalmente il report NAV
- Report caricato su IPFS, CID calcolato
- Hash keccak256 del report (o CID bytes) preparato per pubblicazione

### T-2
- Oracle operator chiama `NAVOracle.updateNAV(newNavWei, effectiveFromUnix, reportHash)`
  con `effectiveFrom = T` per annunciare 48h in anticipo agli investitori
- Pubblicazione sul sito NeoNoble: email broadcast agli holder + post blog

### T
- Il nuovo NAV diventa attivo
- Le richieste di redemption della finestra successiva useranno il NAV snapshot
- Tesoreria alimenta la riserva per coprire i requests Pending

### T+5 (payout)
- Operator approva/rifiuta le `requestRedemption` sul `RedemptionVault`
- Gli investitori possono chiamare `claim(requestId)` e ricevere USDC

## Disclosure

Ogni aggiornamento NAV viene pubblicato su:
- Sito NeoNoble sezione `/sto/nav-history` (to-do backend)
- IPFS report firmato
- Blocco on-chain (PolygonScan evento `NAVUpdated`)
- Email broadcast agli holder (database `sto_whitelist`)
- [opzionale] Twitter/Telegram ufficiale

## Controllo qualità

- Il revisore indipendente deve essere **diverso** dal revisore contabile
  dell'emittente (segregazione dei controlli).
- Il report NAV include: stato patrimoniale, conto economico, rendiconto
  finanziario, elenco investimenti, stress test liquidità, conferma
  riserva redemption.
- L'opinione del revisore è pubblica (su IPFS).
- Deviazioni NAV > 5% trimestre-su-trimestre richiedono memo esplicativo.

## Sospensione NAV

Il NAV può essere sospeso (tramite `NenoSecurityToken.pause()`) nei seguenti
casi:
- Incidente tecnico sulla rete Polygon
- Richiesta autorità di vigilanza
- Evento straordinario che impedisce valutazione attendibile
- Audit in corso per sospette frodi contabili

In caso di sospensione:
- Le redemption vengono congelate fino a riattivazione
- Comunicazione tempestiva agli holder (entro 24h)
- Report dettagliato sulla natura dell'evento
