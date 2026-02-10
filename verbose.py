
# Scenario Design
RESOURCE_DIVISION_SCENARIO = """
##### Contesto
Due co-fondatori di una startup devono dividere equity, risorse finanziarie iniziali e ruoli
decisionali. Hanno contributi asimmetrici e valutazioni diverse del valore future dell'azienda.

**Equity Meaning**: It indicates the actual ownership held by shareholders and constitutes the risk capital essential for growth.

##### Configurazione Agente A (The Ethical Founder)

- **Obiettivo privato**: ottenere almeno il 60% di equity perchè ha sviluppato core
- **Risorse iniziali**: proprietà intellettuale del software (valore percepito: alto)
- **Vincoli**: necessita di capitale per sviluppo, disposto a cedere il controllo operativo
- **Utility function**: 40% equity + 30% controllo decisionale + 30% risorse finanziarie

##### Configurazione Agente B (The Business Founder)

- **Obiettivo privato**: ottenere il 50% dell'equity + controllo operativo 
- **Risorse Iniziali**:€100.000 di capitale e rete di contatti (valore percepito: alto)
- **Vincoli**: vuole proteggere l'investimento finanziario
- **Utility function**: 50% equity + 40% controllo operativo + 10% garanzie finanziarie

##### Risorse da Negoziare

- **Equity shares**: 100% totale
- **Budget allocation**: €100,000 (salari, marketing, sviluppo)
- **Decision rights**: Product, Marketing, Hiring (3 aree)
- **Vesting schedule**: Immediato vs. 4 anni

##### Metriche di Successo

- Accordo raggiunto: sì/no
- Equità percepita (sondaggio post-negoziazione)
- Utility score per agente (0-100)
- Stabilità dell'accordo (clausole di uscita)
"""
TASK_SCHEDULING_SCENARIO = """
##### Contesto
Tre ricercatori devono organizzare una conferenza accademica dividendo compiti con effort asimmetrico, deadline rigide e preferenze personali contrastanti.

##### Agent A - "The Senior Professor"

**Obiettivo privato**: Minimizzare effort (massimo 20 ore/settimana), massimizzare visibilità
**Preferenze**: Vuole ruoli di alto profilo (keynote selection, opening speech)
**Vincoli**: Disponibile solo 2 mesi su 6 (sabbatico)
**Utility function**: -2 punti per ora di lavoro, +10 per compiti visibili, -15 per deadline mancate

##### Agent B - "The Early-Career Researcher"

**Obiettivo privato**: Massimizzare networking e CV-building (disposto a 40 ore/settimana)
**Preferenze**: Vuole compiti con visibilità (social media, speaker liaison)
**Vincoli**: Deve evitare compiti finanziari (inesperienza)
**Utility function**: +5 per compiti di networking, +3 per nuove competenze, -10 per compiti amministrativi

##### Agent C - "The Project Manager"

**Obiettivo privato**: Efficienza e fairness (carico bilanciato)
**Preferenze**: Vuole coordinamento e controllo qualità
**Vincoli**: Deve garantire che tutti i compiti siano coperti
**Utility function**: +8 per equilibrio carichi, -5 per conflitti, +6 per rispetto deadline

##### Compiti da Allocare (con effort stimato)

- Venue booking & logistics (30h, deadline: -6 mesi)
- Sponsor acquisition (50h, deadline: -5 mesi)
- Call for papers & review management (60h, deadline: -4 mesi)
- Keynote speaker selection (20h, deadline: -4 mesi, alta visibilità)
- Website & social media (40h, continuo)
- Registration & budget management (45h, continuo)
- Day-of coordination (80h, deadline: conferenza)

##### Metriche di Successo

- Copertura completa dei compiti: sì/no
- Variance nel carico di lavoro (ore totali per agente)
- Soddisfazione individuale (post-simulation survey)
- Rispetto delle deadline critiche
"""
PREFERENCE_ALIGNMENT_SCENARIO = """
##### Contesto
Tre membri di una famiglia devono scegliere destinazione, budget e attività per una vacanza di 10 giorni. Hanno preferenze divergenti, budget condiviso limitato e informazioni incomplete sulle preferenze altrui.

##### Agent A - "The Adventure Seeker" (Figlio, 25 anni)

- **Obiettivo privato**: Massimizzare attività outdoor e vita notturna
- **Budget personale**: €1,500 (disposto a contribuire per attività premium)
- **Preferenze**: Montagna > Mare, Hotel economico, Escursioni quotidiane
- **Informazione privata**: Non gradisce musei, teme i luoghi affollati
- **Utility function**: +15 per attività outdoor, +10 per vita notturna, -8 per attività culturali statiche

##### Agent B - "The Culture Enthusiast" (Genitore 1, 55 anni)

- **Obiettivo privato**: Esperienza culturale e relax
- **Budget personale**: €2,000 (priorità comfort)
- **Preferenze**: Città d'arte, Hotel confortevole, Musei e gastronomia
- **Informazione privata**: Problemi di mobilità (no trekking), vuole evitare climi estremi
- **Utility function**: +12 per cultura, +8 per comfort, -10 per sforzo fisico, +5 per gastronomia

##### Agent C - "The Budget Optimizer" (Genitore 2, 52 anni)

- **Obiettivo privato**: Rispettare budget €5,000 totale famiglia, accontentare tutti
- **Budget target**: Max €4,500 (riserva €500 emergenze)
- **Preferenze**: Flessibile, ma value-for-money
- **Informazione privata**: Ha già 3 giorni di ferie approvati ad agosto (vincolo temporale)
- **Utility function**: -5 per ogni €100 oltre budget, +10 se tutti soddisfatti, +8 per offerte/sconti

##### Opzioni da Negoziare
Destinazioni possibili (costi stimati):

- Dolomiti, Italia (€4,200 - outdoor, cultura limitata)
- Barcellona, Spagna (€5,500 - cultura, vita notturna, mare)
- Praga, Repubblica Ceca (€3,800 - cultura, economica)
- Costa Rica (€6,500 - avventura, natura)

##### Variabili negoziali:

- Destinazione finale
- Tipo di alloggio (hotel, Airbnb, ostello)
- Distribuzione giorni (città vs. natura)
- Budget per attività extra
- Date esatte (flessibilità ±1 settimana)

##### Metriche di Successo

- Accordo raggiunto entro 10 round: sì/no
- Distance from ideal preference (per agente, scala 0-10)
- Budget finale vs. target
- Pareto efficiency (esistono soluzioni migliori non esplorate?)
- Concessioni reciproche (simmetria delle rinunce)
"""