# Backlog

<!-- sprint-flow:regole (le aggiorna il timer notturno di sprint-flow: non modificarle qui) -->
Le voci stanno in quattro classi. L'**importanza** decide l'ordine: alta =
correttezza, perdita di dati, sicurezza, installazione bloccata, errori visibili
a chi usa il progetto; poi la comodità di chi ci lavora, poi l'estetica. La
**complessità** decide il modo: **(S)** fino a mezza giornata, **(M)** 1-2
giorni, **(L)** serve un piano o un ramo dedicato.

- **Prioritario**: importanza alta, complessità S. Si fa subito, anche dentro il lavoro in corso.
- **Importante**: importanza alta, complessità M o L. Va messo in calendario.
- **Minore**: importanza bassa, complessità S o M. A pacchetti, o quando si tocca quel codice.
- **Da valutare**: importanza bassa o incerta e complessità L, oppure decisione di altri o dato che manca. Parcheggiato: si rivede o si chiude.

Dentro una classe le aree con più voci vengono prima; dentro un'area prima le
più importanti e, a parità, le più semplici. «(verifica dell'utente)» indica una
prova da fare a mano.

### Come aggiungere o chiudere una voce (anche per gli agenti)

1. Ogni voce nuova va nella classe giusta e sotto l'area `###` esistente più vicina: mai in una sezione datata in fondo al file. Se la classe è incerta, va in «Da valutare».
2. Formato: testo autosufficiente con i nomi esatti di file, classi e comandi, poi la complessità `(S)`, `(M)` o `(L)` e l'origine con la data fra parentesi, es. «(review del piano X, 13/11)».
3. Un'area `###` nuova solo se nessuna di quelle esistenti va bene.
4. **Una voce fatta si toglie da qui nello stesso commit del lavoro.** Il changelog la riporta da solo, con data e agente.
5. Mentre si aggiunge una voce non si riordinano né si riscrivono le voci degli altri.
<!-- sprint-flow:regole-fine -->

## Prioritario

## Importante

## Minore

## Da valutare
