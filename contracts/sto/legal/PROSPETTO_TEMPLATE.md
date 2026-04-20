# DOCUMENTO INFORMATIVO — TEMPLATE
# ⚠️ NON E' UN PROSPETTO VALIDO LEGALMENTE
# Solo scheletro da compilare con avvocato fintech italiano abilitato

> **Questo file è un template tecnico, NON una bozza legale. Non distribuire
> agli investitori senza revisione, compilazione e firma di un avvocato
> abilitato. Solo un avvocato/notaio può qualificare l'offerta ai sensi della
> normativa italiana ed EU.**

## 1. Emittente

- **Denominazione sociale**: [da compilare — NeoNoble Ramp S.r.l. o entità dedicata]
- **Sede legale**: [da compilare]
- **P.IVA / Codice Fiscale**: [da compilare]
- **Capitale sociale**: [da compilare]
- **Registro Imprese**: [da compilare]
- **Rappresentante legale**: [da compilare]

## 2. Oggetto dell'offerta

- **Denominazione del token**: NeoNoble Revenue Share Token (NNRS)
- **Standard**: ERC-3643-inspired custom, dettagli tecnici in `STO_DEPLOY.md`
- **Blockchain**: Polygon PoS (chainId 137)
- **Contratto**: [indirizzo Polygon dopo deploy]
- **Supply massima**: [da definire, es. 100.000 token]
- **Prezzo nominale di emissione**: €250 per token
- **Importo minimo investimento**: [da definire, es. €500]
- **Importo massimo investimento per investitore retail**: [da definire conforme MiCA]

## 3. Diritti conferiti agli holder

- Partecipazione pro-rata ai ricavi netti della piattaforma NeoNoble Ramp
- Redemption trimestrale a NAV con riserva dedicata (vedi punto 5)
- [altri diritti da definire con avvocato — es. voting su materie limitate]

## 4. Utilizzo dei proventi

- [da definire]: es. 40% espansione prodotto, 30% marketing, 20% licensing
  regolamentare, 10% riserva operativa
- Il 30% dei proventi in USDC viene destinato alla riserva Redemption

## 5. Redemption a NAV

- **Frequenza**: trimestrale (marzo/giugno/settembre/dicembre)
- **Calcolo NAV**: vedi `NAV_PROCEDURE.md`
- **Riserva dedicata**: conto bancario segregato Banca [X] + smart contract
  `RedemptionVault` su Polygon
- **Tetto trimestrale**: [da definire, es. 10% del supply per trimestre]
- **Tempi**: richiesta entro T-5 gg lavorativi, approvazione entro T-2,
  payout in USDC on-chain entro T
- **Caso insufficienza riserva**: prorata + waitlist al trimestre successivo

## 6. Struttura compliance on-chain

| Parametro | Valore configurato | Note |
|---|---|---|
| MAX_HOLDERS | 149 | Per esenzione art. 100-bis TUF (< 150 investitori) |
| LOCKUP_UNTIL | 12 mesi da go-live | Vesting iniziale mandatory |
| Country allowlist | IT, DE, FR, ES, NL, BE, AT, LU, IE, PT, FI, SE, DK, CH | EU + CH; esclude US/CN/RU/sanzionati |
| KYC provider | Sumsub (SumID) + internal review | Provider sostituibile via `kycProvider` |
| Pause function | YES | Richiesta MiCA art. 91 |
| Forced transfer | YES (loggato on-chain) | Per recovery chiavi o ordine giudiziario |

## 7. Rischi

- Rischio di perdita totale del capitale investito
- Rischio operativo smart contract (mitigato da audit [X])
- Rischio liquidità: la redemption dipende dalla riserva disponibile
- Rischio regolamentare: MiCA piena applicazione dal [data]
- Rischio tecnologico: Polygon PoS, MetaMask, chiavi wallet
- Rischio di valutazione NAV: soggetto a revisione trimestrale indipendente

## 8. Fiscalità (Italia)

- [da compilare con il commercialista]: trattamento fiscale plusvalenze,
  dividendi/revenue share, sostituto d'imposta

## 9. Esenzioni applicate

- Offerta inferiore a €8M ai sensi dell'art. 100-bis TUF ⇒ esenzione da prospetto
  pieno (da validare dall'avvocato)
- MiCA white paper semplificato da notificare a Banca d'Italia

## 10. Riferimenti

- Smart contract sorgenti: `/app/contracts/sto/contracts/`
- Audit report: [link post-audit]
- NAV report trimestrale: pubblicato su IPFS, hash registrato on-chain in
  `NAVOracle.reportHash`
- Sito: https://neonobleramp.com/sto

## 11. Dichiarazione di responsabilità

L'emittente dichiara che le informazioni contenute nel presente documento
sono complete, veritiere e non fuorvianti, ai sensi dell'art. 113-ter TUF
e della Direttiva Prospetto 2017/1129/UE.

Firma dell'emittente: ___________________________
Data: ___________________________
