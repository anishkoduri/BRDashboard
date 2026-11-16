"""Claims checked against the supplied PDFs. Figure bars that were not in the text layer are marked."""

LEDGER = [
    {
        "id": "rojas-2022",
        "source": "Rojas et al. 2022, Predicting BRD Risk in the First 45 Days Post Arrival",
        "doi": "10.3390/pathogens11040442",
        "file": "Predicting BRD Risk 45 Days Post Arrival.pdf",
        "used_for": "Cohort unit, 45-day recorded first-treatment outcome, 15% research classification, calibration targets, historical cost figures.",
        "claims": [
            "1,733 cohorts from 10 feedlots. Abstract animal total 188,188; results section 188,118. The cohort count matches; the animal totals do not.",
            "Mean 45-day cohort morbidity 6.30%. High-risk mean 27.07%. Low-risk mean 3.77%. Share at or above 15%: 10.85%.",
            "Test AUC 0.682–0.789. Random forest 0.789 was the highest AUC. The decision tree had the economic edge when high-risk cohorts were at or below 45% of the population.",
            "Historical scenario inputs: $151.18 lost value per morbid animal, $23.60 per metaphylaxis, effectiveness set at 0.5. Average cohort size in that formula: 109.",
            "Metaphylaxis history was not available for every cohort, so treatment recording can be confounded.",
        ],
        "not_used_as": "A fitted model to copy, a 2026 price list, or validation of these fictional yards.",
    },
    {
        "id": "adekunle-risk-2026",
        "source": "Adekunle et al. 2026, Mapping Variability in BRD Risk Factors",
        "doi": "10.3390/ani16111726",
        "file": "BRD Risk Factors Variation.pdf",
        "used_for": "Which arrival fields to collect, and the warning that study counts are not coefficients.",
        "claims": [
            "91 studies. Figure 5 counts how often a factor was studied, not its effect size. The text says transportation was examined most often, then commingling.",
            "Table A1 high-risk states include transport of six hours or more, commingling, fall season, temperature swings, light induction weight, and overcrowding.",
        ],
        "not_used_as": "Model weights. The prompt's bar heights (31, 28, 25, 23, 23, 15, 14, 13) were not in the PDF text layer, so they are not treated as verified counts.",
    },
    {
        "id": "adekunle-epi-2026",
        "source": "Adekunle and Kaniyamattam 2026, BRD Epidemiological Drivers",
        "doi": "10.3390/agriculture16030311",
        "file": "BRD Epidemiology.pdf",
        "used_for": "Framing BRD as multifactorial: host, pathogens, transport, commingling, nutrition, environment, surveillance limits, stewardship.",
        "claims": ["The review describes multifactorial pathogenesis and warns against single-cause stories."],
        "not_used_as": "A transmission rate inside the feedyard cash calculation.",
    },
    {
        "id": "weber-2024",
        "source": "Weber et al. 2024, BRD Morbidity and Net Return Distributions",
        "file": "Evaluation of BRD on Net Return.pdf",
        "used_for": "Why net returns are shown as distributions of assumptions, not a single causal savings number.",
        "claims": [
            "Proprietary pens, 2014–2015. The poster reports lower mean net return as the share treated rises, including a negative mean when treatment is heavy.",
            "Those gaps mix animals that needed treatment with the treatment itself. They are not used as the effect of withholding care.",
        ],
        "not_used_as": "Proof that treating less increases profit.",
    },
    {
        "id": "johnson-2017",
        "source": "Johnson and Pendell 2017, Market Impacts of Reducing BRD",
        "doi": "10.3389/fvets.2017.00189",
        "file": "Market impacts of BRD.pdf",
        "used_for": "Industry context only. Less disease is not a free gain for every part of the supply chain.",
        "claims": ["A partial-equilibrium model finds distributional effects across producers, processors, feed suppliers, and consumers."],
        "not_used_as": "A feedyard cash-flow input.",
    },
    {
        "id": "usda-2017",
        "source": "USDA APHIS, Antimicrobial Use and Stewardship on U.S. Feedlots, 2017",
        "file": "US Antimicrobial Use.pdf",
        "used_for": "Historical context for group treatment, individual treatment, and veterinary oversight in 2016.",
        "claims": [
            "378 feedlots reported on calendar year 2016, before the January 2017 FDA policy change. 87.5% gave antimicrobials in feed, water, or by injection.",
        ],
        "not_used_as": "A 2026 baseline or a target for this demo.",
    },
]
