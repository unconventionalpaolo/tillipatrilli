# Libro dell'anniversario

Apri `book/index.html` in un browser (doppio clic, funziona anche da file). Scorri o usa le frecce.

## Struttura
- `pages/p01..p19.png` tavole statiche approvate (4:5)
- `book/` il libro HTML (index.html + assets)
- `tools/build_book.py` + `tools/book_template.html` rigenerano `book/index.html` (testi, ordine, animazioni)
- `tools/split_p01.py` esempio di taglio a livelli per una scena (pagina 1)
- `work/pNN/` materiale di lavorazione (cutout dei personaggi, sfondo vuoto)

## Pipeline per animare una pagina (pagina 1 e' il pilota)
1. Sfondo vuoto: edit della tavola su Higgsfield (`gpt_image_2_6`) "togli i personaggi, riempi quello che era nascosto".
2. Personaggi isolati: `remove_background` sulla tavola.
3. Residui (fiori, ombre, scintille): differenza tavola - sfondo, fuori dal cutout.
4. Taglio in parti con poligoni (testa, corpo, braccio) in `split_pNN.py`, perni di rotazione in `layers.json`.
5. Animazione in CSS (`@keyframes`), max 3 secondi di azione, poi respiro/ammiccamenti in loop.

Le pagine senza livelli mostrano la tavola statica con un lento zoom (segnaposto).
