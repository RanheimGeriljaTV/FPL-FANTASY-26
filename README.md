# FPL Fantasy Optimizer 2025/26 ⚽🧠

En avansert, matematisk Fantasy Premier League (FPL) tropps- og overgangs-optimalisator bygget med **Streamlit**, **PuLP (Coin-OR CBC MILP Solver)** og det offisielle **FPL API-et**.

---

## 🌟 Hovedfunksjoner

1. **Matematisk MILP Optimalisering:**
   - Beregner optimale bytter og troppssammensetning over en definert horisont (1–5 runder).
   - Tar hensyn til rullerende frie bytter (FTs), minuspoeng-kostnader, chip-strategier (Wildcard, Free Hit, Bench Boost, Triple Captain) og lagrestriksjoner.
2. **FUT & Panini Spillerkort:**
   - Fotorealistiske spillerkort med lagfarger, dynamisk badge, live kamptilstand (pågående, ferdigspilt, starter) og neste motstanders FDR.
3. **⚽ Spillerprofil & Dybdeanalyse (@st.dialog):**
   - Interaktiv modal med Altair xP/poeng-grafer, hjemme/borte-splitt og effektivitetsnøkkeltall.
4. **🎯 Skreddersydd Byttekalkulator & Track Record:**
   - Automatisk logging og evaluering av simulerte overganger mot faktisk utfall.
5. **🌐 RanheimKraft Integrasjon & Flere Brukere:**
   - Dynamisk `st.query_params["id"]` støtte.
   - Sømløs integrasjon mot [ranheimkraft.no/fpl.html](https://ranheimkraft.no/fpl.html) med lokalt minne (`localStorage`) per manager.

---

## 🚀 Komme i gang

### 1. Klon depotet og installer avhengigheter
```bash
git clone https://github.com/RanheimGeriljaTV/FPL-FANTASY-26.git
cd FPL-FANTASY-26
pip install -r requirements.txt
```

### 2. Start applikasjonen lokalt
Kjør enten oppstartsskriptet:
```bash
start.bat
```
eller direkte via Streamlit:
```bash
streamlit run app.py
```

---

## ⚙️ Teknisk stakk

- **Frontend & Dashboard:** Streamlit, Altair, HTML5/CSS3 FUT Badges
- **Optimaliseringsmotor:** Python PuLP, HiGHS / Coin-OR CBC MILP Solver
- **Datakilder:** Det offisielle Premier League FPL API-et + FPL Review xP-projeksjoner
- **Deploy:** Streamlit Community Cloud / RanheimKraft.no iframe
