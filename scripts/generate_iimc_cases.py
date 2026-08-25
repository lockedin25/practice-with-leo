"""Generator for all 10 IIM Calcutta Exemplar Case Packages under corpus/exemplars/iimc/."""

from __future__ import annotations
from scripts.generate_exemplars import emit_case, make_standard_tree


def generate_all_iimc_cases():
    print("Generating all 10 IIM Calcutta exemplar cases...")

    # Case 1: Steel Mill Cost Absorption
    emit_case(
        school_dir="iimc", slug="01-steel-mill-cost-absorption", title="Integrated Steel Mill Cost Absorption", school_tag="IIM-C",
        category="profitability", industry="heavy_manufacturing_and_steel", difficulty="advanced",
        opening_context="Your client is a 6M MT integrated blast furnace steel producer in Eastern India. Global steel dumping has compressed hot-rolled coil (HRC) spot prices by 28%, turning company EBITDA negative.",
        opening_objective="Determine whether to throttle blast furnace production or maintain high output to absorb fixed costs, and recommend an operational cost reduction plan.",
        decision_question="Should the steel mill throttle output or operate at 100% capacity during a price slump to optimize fixed cost absorption?",
        primary_metric="Cash breakeven per ton of HRC steel and Net Operating Cash Flow", time_horizon="twelve months",
        core_mechanism="Operating leverage and blast furnace thermal physics. Shutting down or damping down a blast furnace damages refractory lining and destroys fixed cost absorption (₹4,200/ton fixed overhead), causing higher cash burn than continuing to produce at marginal cost.",
        what_wanted_to_test="Heavy manufacturing operating leverage, blast furnace thermal continuity constraints, variable vs fixed cost decomposition, and value-added product mix optimization.",
        pivotal_insight="Throttling production by 25% raises fixed cost per ton by ₹1,400, worsening net cash loss; the mill must run at 100% capacity while shifting hot metal from commodity HRC to high-margin automotive CRCA and galvanised steel.",
        common_traps=["Recommending shutting down 2 of 4 blast furnaces without considering refractory restart costs ($40M).", "Assuming cutting blue-collar maintenance labor solves an operating leverage problem.", "Selling raw iron ore pellets instead of making steel."],
        takeaway_lesson="In capital-intensive continuous process industries (steel, petrochemicals, glass), high fixed cost structures mean volume curtailment during down-cycles accelerates insolvency; survival requires shifting product mix up the value curve.",
        suggested_readings=["knowledge_base/industries/14_heavy_manufacturing_and_steel.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "mill.capacity", "domain": "company", "release_level": "broad_context", "content": "Client operates 4 blast furnaces producing 6M MT of crude steel annually, integrated with captive iron ore mines."},
            {"id": "cost.structure", "domain": "financials", "release_level": "sharp_question", "content": "Total production cost is ₹42,000/ton (₹28,000 variable, ₹14,000 fixed). Spot HRC price dropped to ₹38,000/ton."},
            {"id": "thermal.constraints", "domain": "operations", "release_level": "hypothesis_backed", "content": "Damping down blast furnaces reduces volume by 30% but increases unit fixed cost to ₹18,600/ton and risks refractory skulling ($35M repair).", "dependencies": ["cost.structure"]},
            {"id": "value_add.spread", "domain": "commercial", "release_level": "hypothesis_backed", "content": "Specialty automotive-grade Cold Rolled Closed Annealed (CRCA) steel sells at ₹52,000/ton with positive contribution margin of ₹14,000/ton.", "dependencies": ["thermal.constraints"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Throttling output increases cash burn by losing fixed cost absorption and risking refractory damage; mill must maintain 100% blast furnace output while maximizing downstream conversion into automotive CRCA (+₹14k margin)."},
            {"id": "recommendation.max_utilization", "domain": "recommendation", "release_level": "synthesis_support", "content": "Maintain 100% blast furnace utilization to fully absorb ₹14,000/ton fixed overhead."},
            {"id": "recommendation.mix_shift", "domain": "recommendation", "release_level": "synthesis_support", "content": "Shift product mix from 70% commodity HRC to 60% value-added automotive CRCA and color-coated sheets."},
            {"id": "recommendation.pulverized_coal", "domain": "recommendation", "release_level": "synthesis_support", "content": "Increase Pulverized Coal Injection (PCI) from 120 kg to 180 kg/ton to substitute expensive imported metallurgical coking coal."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.steel-cost-absorption", root_label="Optimize production strategy and product mix during global steel slump.",
            branches=[
                {"id": "fixed-cost-leverage", "label": "Fixed Cost Absorption vs Volume Curtailment", "conclusion": "Throttling volume increases unit fixed cost from ₹14k to ₹18.6k/ton."},
                {"id": "blast-furnace-physics", "label": "Refractory Thermal Damage & Restart Capex", "conclusion": "Shutting furnaces risks $35M in refractory relining damage and takes 4 months."},
                {"id": "product-mix-realization", "label": "Commodity HRC vs Value-Add CRCA Spreads", "conclusion": "Automotive CRCA sells at ₹52,000/ton, generating ₹14,000/ton positive cash contribution."}
            ],
            diagnosis={"label": "Continuous Utilization & Value-Add Mix Shift", "evidence": ["fixed-cost-leverage", "blast-furnace-physics", "product-mix-realization"], "conclusion": "Curtailing production worsens cash losses due to lost fixed cost absorption; mill must maintain 100% output and shift hot metal to high-margin automotive CRCA."},
            recommendation={"label": "3-Pillar Industrial Turnaround Strategy", "evidence": ["diagnosis"], "conclusion": "Run blast furnaces at 100%, expand downstream CRCA line share, and maximize PCI coal substitution."},
            routes=[{"id": "cost-absorption-first", "sequence": ["fixed-cost-leverage", "blast-furnace-physics", "product-mix-realization", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from unit fixed cost math to product mix margin realization."}],
            recovery=["Ask candidate what happens to fixed cost per ton if production volume drops 30%.", "Clarify that selling price still covers variable cash costs.", "Redirect toward value-added steel mix (CRCA) and PCI injection."]
        )
    )

    # Case 2: Airline Fleet Turnaround Optimization
    emit_case(
        school_dir="iimc", slug="02-airline-fleet-optimization", title="Low-Cost Airline Turnaround Time", school_tag="IIM-C",
        category="operations", industry="aviation_and_airlines", difficulty="intermediate",
        opening_context="Your client is a major Indian low-cost carrier (LCC) operating 180 Airbus A320 aircraft. Ground Turnaround Time (TAT) between flights has slipped from 25 minutes to 36 minutes, reducing aircraft daily utilization by 1.8 block hours per tail.",
        opening_objective="Diagnose ground handling bottlenecks and engineer a 25-minute Turnaround Time process to unlock 1 additional daily flight per aircraft.",
        decision_question="How can the airline compress ground turnaround time to 25 minutes to maximize aircraft daily utilization?",
        primary_metric="Ground Turnaround Time (minutes) and Aircraft Daily Block Hours", time_horizon="six months",
        core_mechanism="Parallel process fragmentation and passenger deplaning bottlenecks. Baggage unloading, cabin catering/cleaning, and passenger boarding occur sequentially instead of concurrently due to single-door jet bridge boarding and delayed gate baggage belt arrivals.",
        what_wanted_to_test="Aviation turnaround critical path analysis, parallel vs sequential operations, dual-door deplaning, and gate ground-handling coordination.",
        pivotal_insight="Turnaround time critical path is governed by cabin cleaning and passenger boarding; introducing dual-door front/rear boarding stairs and concurrent cleaning cuts ground time by 11 minutes.",
        common_traps=["Assuming pilots are taxiing too slowly on the runway.", "Blaming air traffic control (ATC) holding patterns for ground-gate delays.", "Hiring twice as many ground crew without restructuring the critical path."],
        takeaway_lesson="In airline fleet operations, every minute saved on ground turnaround accumulates into aircraft utilization; compressing the critical path via parallel ground operations unlocks massive incremental revenue capacity.",
        suggested_readings=["knowledge_base/industries/06_aviation_and_airlines.md", "knowledge_base/case_types/unconventional_and_abstract.md", "knowledge_base/methodology/02_issue_tree_structuring.md"],
        facts=[
            {"id": "fleet.operations", "domain": "company", "release_level": "broad_context", "content": "Client operates 180 A320s flying 6.2 sectors/day per tail with 11.2 daily block hours."},
            {"id": "tat.inflation", "domain": "operations", "release_level": "sharp_question", "content": "Average TAT increased from 25 to 36 minutes across metro airports, causing flight cascading delays and eliminating the 7th daily sector."},
            {"id": "critical.path", "domain": "operations", "release_level": "hypothesis_backed", "content": "Critical path audit reveals passenger deplaning/boarding takes 22 minutes (single jet bridge door) and cabin cleaning starts only after full deplaning.", "dependencies": ["tat.inflation"]},
            {"id": "utilization.value", "domain": "financials", "release_level": "hypothesis_backed", "content": "Achieving 25-minute TAT enables 1 additional flight per tail daily, generating ₹650 Cr in incremental annual network revenue.", "dependencies": ["critical.path"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "TAT expanded to 36 mins because passenger deplaning and cabin cleaning operate sequentially through a single jet bridge door; switching to dual-door boarding and concurrent cabin cleaning recovers 25-min TAT and unlocks 1 flight/day per aircraft."},
            {"id": "recommendation.dual_boarding", "domain": "recommendation", "release_level": "synthesis_support", "content": "Enforce dual-door boarding/deplaning using aerobridge for front door and mobile ramp stairs for rear door."},
            {"id": "recommendation.concurrent_cleaning", "domain": "recommendation", "release_level": "synthesis_support", "content": "Deploy sectional cabin cleaning crews to start row cleaning concurrently as front-half passengers deplane."},
            {"id": "recommendation.gate_baggage", "domain": "recommendation", "release_level": "synthesis_support", "content": "Pre-stage baggage tugs at the gate 10 minutes prior to aircraft touchdown for instant offloading."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.airline-tat", root_label="Compress aircraft turnaround time from 36 to 25 minutes.",
            branches=[
                {"id": "tat-critical-path", "label": "Ground Turnaround Critical Path Breakdown", "conclusion": "Passenger deplaning (12m), cleaning (8m), and boarding (14m) occur sequentially."},
                {"id": "passenger-flow-bottleneck", "label": "Single-Door vs Dual-Door Passenger Flow", "conclusion": "Single-door boarding takes 22 mins; dual-door front/rear boarding takes 11 mins."},
                {"id": "ground-handling-concurrency", "label": "Concurrent Refueling, Baggage & Cleaning", "conclusion": "Staggering cleaning concurrently with deplaning saves 7 minutes."}
            ],
            diagnosis={"label": "Sequential Bottlenecks on Single-Door Critical Path", "evidence": ["tat-critical-path", "passenger-flow-bottleneck", "ground-handling-concurrency"], "conclusion": "TAT is 36 mins because deplaning, cleaning, and boarding run sequentially on a single door; parallel dual-door boarding restores 25-min TAT and unlocks 1 additional flight per tail."},
            recommendation={"label": "3-Pillar Turnaround Process Redesign", "evidence": ["diagnosis"], "conclusion": "Implement dual-door boarding, sectional concurrent cabin cleaning, and pre-staged baggage logistics."},
            routes=[{"id": "critical-path-first", "sequence": ["tat-critical-path", "passenger-flow-bottleneck", "ground-handling-concurrency", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate through the 36-minute critical path timeline."}],
            recovery=["Ask candidate what activities make up the 36-minute ground turnaround.", "Clarify that aircraft technical refueling takes only 12 minutes.", "Redirect toward passenger boarding flow and sequential cabin cleaning."]
        )
    )

    # Case 3: Telecom Tower Sharing
    emit_case(
        school_dir="iimc", slug="03-telecom-tower-sharing", title="Telecom Tower Tenancy Yield", school_tag="IIM-C",
        category="profitability", industry="telecom_and_media", difficulty="intermediate",
        opening_context="Your client is an Indian passive telecom infrastructure tower company managing 120,000 towers. Tenancy ratio has dropped from 2.2x to 1.6x following telco industry consolidation, eroding ROIC.",
        opening_objective="Diagnose tenancy loss and recommend a business model expansion into smart city small-cells, green energy management, and fiber sharing.",
        decision_question="How can the telecom tower company boost tenancy yield and expand into non-traditional infrastructure revenue?",
        primary_metric="Average Tenancy Ratio per Tower and Power & Fuel Margin", time_horizon="eighteen months",
        core_mechanism="Telco market consolidation (exit of sub-scale operators) leaving redundant duplicate tenancies, combined with high diesel generator energy costs where the towerco leaked power margins under fixed energy billing.",
        what_wanted_to_test="Passive telecom infrastructure economics, anchor tenancy vs sharing tenancy multipliers, energy pass-through contracts vs green energy-as-a-service, and 5G street furniture small-cells.",
        pivotal_insight="Adding a 2nd tenant to an existing tower requires negligible capex and generates 80% incremental EBITDA flow-through; transforming diesel-powered sites into solar-battery green energy hubs captures profitable energy margins.",
        common_traps=["Assuming the tower company can build thousands of new macro-towers when telcos are cutting macro-capex.", "Blaming steel structural maintenance costs.", "Failing to recognize that 5G requires dense micro-cells and fiberized street furniture."],
        takeaway_lesson="In passive infrastructure, operating leverage is driven by co-location tenancy ratios; as macro-tenancies consolidate, revenue growth shifts to energy-as-a-service and dense micro-small-cell deployment.",
        suggested_readings=["knowledge_base/industries/07_telecom_and_media.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "tower.scale", "domain": "company", "release_level": "broad_context", "content": "Client operates 120,000 macro-towers across all 22 Indian telecom circles."},
            {"id": "tenancy.drop", "domain": "financials", "release_level": "sharp_question", "content": "Average tenancy fell from 2.2x to 1.6x as merged telcos surrendered 70,000 redundant co-located tenancies."},
            {"id": "energy.leakage", "domain": "operations", "release_level": "hypothesis_backed", "content": "Client provides power/fuel at fixed rates but diesel generator costs rose, turning energy operations into a ₹220 Cr annual loss.", "dependencies": ["tenancy.drop"]},
            {"id": "small_cell.demand", "domain": "market", "release_level": "hypothesis_backed", "content": "5G rollout requires 400,000 street-level small cells (utility poles, bus shelters, billboards) connected by fiber.", "dependencies": ["energy.leakage"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Tenancy fell from 2.2x to 1.6x due to telco consolidation, while fixed diesel energy contracts lost ₹220 Cr; towerco must pivot to Energy-as-a-Service (solar/battery) and monetize 5G small-cell street furniture."},
            {"id": "recommendation.green_energy", "domain": "recommendation", "release_level": "synthesis_support", "content": "Convert 45,000 diesel tower sites into solar-plus-lithium battery hubs and shift to an Energy-as-a-Service model with fixed uptime SLAs."},
            {"id": "recommendation.small_cells", "domain": "recommendation", "release_level": "synthesis_support", "content": "Deploy 60,000 5G smart-city small-cells on municipal street poles and traffic lights."},
            {"id": "recommendation.fiber_sharing", "domain": "recommendation", "release_level": "synthesis_support", "content": "Monetize fiber-to-the-tower (FTTT) sharing across multiple telecom and broadband operators."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.tower-tenancy", root_label="Restore telecom tower company tenancy yield and operating profitability.",
            branches=[
                {"id": "tenancy-consolidation", "label": "Telco Consolidation & Macro-Tower Redundancy", "conclusion": "Telco mergers eliminated 70,000 co-located tenancies, dropping tenancy to 1.6x."},
                {"id": "energy-cost-pass-through", "label": "Diesel Fuel Operations & Green Power Conversion", "conclusion": "Fixed diesel billing created a ₹220 Cr energy loss; solar conversion secures profit."},
                {"id": "5g-small-cells-and-fiber", "label": "5G Small Cells, Street Furniture & Fiber Sharing", "conclusion": "Massive demand for 5G micro-sites and fiber sharing offers next growth wave."}
            ],
            diagnosis={"label": "Macro-Tenancy Loss & Diesel Power Bleed", "evidence": ["tenancy-consolidation", "energy-cost-pass-through", "5g-small-cells-and-fiber"], "conclusion": "EBITDA fell because telco consolidation reduced tenancy to 1.6x while diesel fuel contracts lost ₹220 Cr; recovery requires solarizing sites and deploying 5G small-cells."},
            recommendation={"label": "3-Pillar Passive Infrastructure Pivot", "evidence": ["diagnosis"], "conclusion": "Solarize tower energy operations, build municipal 5G street-pole small cells, and expand shared fiber infrastructure."},
            routes=[{"id": "tenancy-first", "sequence": ["tenancy-consolidation", "energy-cost-pass-through", "5g-small-cells-and-fiber", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from tenancy ratio drop to energy contract leakage and 5G micro-cells."}],
            recovery=["Ask candidate what happened to tower tenancies when telecom operators merged.", "Clarify that tower rent per tenant has a high 80% flow-through margin.", "Redirect toward power and fuel solarization and 5G small-cell infrastructure."]
        )
    )

    # Cases 4 to 10 for IIMC
    # Case 4: Port Dredging Concession
    emit_case(
        school_dir="iimc", slug="04-port-dredging-concession", title="Port Capital Dredging Concession", school_tag="IIM-C",
        category="mergers_and_acquisitions", industry="logistics_and_cold_chain", difficulty="advanced",
        opening_context="Your client is an infrastructure fund bidding for a 20-year concession to deepen the navigation channel of a major Indian port from 14m to 18m draft. Capital capex is ₹1,800 Cr with annual maintenance dredging commitments.",
        opening_objective="Value the dredging concession and determine whether incremental vessel tariff premiums cover maintenance dredging risk.",
        decision_question="What is the net present value (NPV) of the dredging concession and how should siltation risk be hedged?",
        primary_metric="Concession Project IRR and Annual Maintenance Dredging Cost", time_horizon="twenty years",
        core_mechanism="Tidal siltation rate volatility vs Cape-size vessel draft premiums. Deepening the channel to 18m attracts deep-draft 150,000 DWT Cape-size bulk vessels paying 35% higher vessel charges, but monsoon siltation requires 4M cubic meters of annual maintenance dredging.",
        what_wanted_to_test="Maritime infrastructure concession valuation, capital dredging capex vs maintenance dredging opex, hydrological siltation modeling, and vessel draft elasticity.",
        pivotal_insight="The concession delivers 16% IRR only if the concession agreement includes a 'Variable Siltation Band' tariff adjustment mechanism where port authorities co-fund dredging if monsoon siltation exceeds 3.5M m3/year.",
        common_traps=["Treating capital dredging as a one-time capex without budgeting for massive annual maintenance dredging.", "Assuming small Handymax vessels will pay higher tariffs for deep water they don't need.", "Ignoring environmental coastal dumping permit clearances."],
        takeaway_lesson="In maritime navigation concessions, annual maintenance dredging to maintain draft depth is an ongoing operational liability that must be contractually hedged against monsoon hydrological anomalies.",
        suggested_readings=["knowledge_base/industries/01_logistics_and_cold_chain.md", "knowledge_base/case_types/mergers_and_acquisitions.md", "knowledge_base/methodology/04_data_gathering_and_notes.md"],
        facts=[
            {"id": "project.scope", "domain": "company", "release_level": "broad_context", "content": "Project involves dredging 22 km access channel from 14m to 18m draft, requiring ₹1,800 Cr upfront capital dredging."},
            {"id": "vessel.traffic", "domain": "commercial", "release_level": "sharp_question", "content": "18m draft allows 150,000 DWT Cape-size bulk carriers to berth fully laden, eliminating ₹400/MT lighterage transshipment costs for steel/power plants."},
            {"id": "siltation.risk", "domain": "operations", "release_level": "hypothesis_backed", "content": "Monsoon oceanographic siltation deposits 3.5M to 5.2M cubic meters of silt annually, requiring ₹90 Cr-₹140 Cr annual maintenance dredging.", "dependencies": ["vessel.traffic"]},
            {"id": "tariff.structure", "domain": "financials", "release_level": "hypothesis_backed", "content": "Vessel-related charges (VRC) yield ₹320 Cr annually from deep-draft vessels, but high siltation years reduce equity IRR from 16% to 7.8% without tariff indexation.", "dependencies": ["siltation.risk"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Concession is highly accretive (16% IRR) due to Cape-size vessel demand, but annual monsoon siltation (up to 5.2M m3) threatens debt service; concession must include a risk-sharing siltation collar with the port authority."},
            {"id": "recommendation.siltation_collar", "domain": "recommendation", "release_level": "synthesis_support", "content": "Incorporate a contractual Siltation Collar: port authority compensates 100% of maintenance dredging costs when annual silt volume exceeds 3.8M m3."},
            {"id": "recommendation.hopper_dredger", "domain": "recommendation", "release_level": "synthesis_support", "content": "Purchase a dedicated 10,000 m3 Trailing Suction Hopper Dredger (TSHD) on long-term lease to reduce maintenance dredging cost by 30% vs spot chartering."},
            {"id": "recommendation.anchor_contracts", "domain": "recommendation", "release_level": "synthesis_support", "content": "Sign 10-year Minimum Volume Guarantee (MVG) contracts with regional coastal steel and thermal power plants."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.dredging-concession", root_label="Value port capital dredging concession and mitigate hydrological risk.",
            branches=[
                {"id": "traffic-and-lighterage-savings", "label": "Cape-Size Vessel Traffic & Lighterage Elimination", "conclusion": "Deep draft eliminates ₹400/MT lighterage costs, attracting 150k DWT bulk carriers."},
                {"id": "capital-vs-maintenance-dredging", "label": "Upfront Capex vs Ongoing Siltation Dredging", "conclusion": "Maintenance dredging costs ₹90-140 Cr/yr depending on monsoon siltation volume."},
                {"id": "contractual-risk-allocation", "label": "Concession Terms & Siltation Risk Sharing", "conclusion": "Uncapped siltation risk drops IRR to 7.8%; requires a contractual risk-sharing collar."}
            ],
            diagnosis={"label": "Cape-Size Traffic Upside with Siltation Volatility", "evidence": ["traffic-and-lighterage-savings", "capital-vs-maintenance-dredging", "contractual-risk-allocation"], "conclusion": "Concession is commercially attractive (16% IRR) but vulnerable to monsoon siltation volatility, requiring a contractual siltation collar and dedicated dredger procurement."},
            recommendation={"label": "3-Pillar Concession Structuring Strategy", "evidence": ["diagnosis"], "conclusion": "Negotiate contractual siltation risk collar, secure long-term TSHD dredger lease, and lock minimum volume guarantees with industrial anchors."},
            routes=[{"id": "concession-first", "sequence": ["traffic-and-lighterage-savings", "capital-vs-maintenance-dredging", "contractual-risk-allocation", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from vessel traffic demand to maintenance dredging siltation risk."}],
            recovery=["Ask candidate what happens to channel depth after monsoon ocean currents deposit silt.", "Clarify that capital dredging is only step one; maintenance is continuous.", "Redirect toward maintenance dredging cost volatility and contractual risk sharing."]
        )
    )

    # Case 5: Fertilizer Subsidy Mix
    emit_case(
        school_dir="iimc", slug="05-fertilizer-subsidy-mix", title="Fertilizer Subsidy & Product Mix", school_tag="IIM-C",
        category="growth_strategy", industry="heavy_manufacturing_and_steel", difficulty="intermediate",
        opening_context="Your client is a leading Indian chemical and complex fertilizer manufacturer producing 2M MT of NPK/Urea. Delayed government subsidy disbursements have created a ₹2,800 Cr working capital lockup, and EBITDA margins are capped at 4%.",
        opening_objective="Redesign product portfolio toward non-subsidized specialty water-soluble fertilizers and bio-stimulants to improve margin and cash flow.",
        decision_question="How should the fertilizer manufacturer transition its product portfolio to reduce reliance on government subsidies?",
        primary_metric="EBITDA margin and Working Capital Days", time_horizon="eighteen months",
        core_mechanism="Commodity subsidized fertilizers (Urea/DAP) have government-controlled retail prices and delayed 180-day subsidy payouts, while specialized water-soluble fertilizers (WSF), micronutrients, and bio-fertilizers have free market pricing, 28% gross margins, and zero subsidy dependency.",
        what_wanted_to_test="Regulated chemical economics, Nutrient Based Subsidy (NBS) scheme mechanics, working capital subsidy arrears, and agronomy-led specialty fertilizer marketing.",
        pivotal_insight="Specialty water-soluble fertilizers for drip-irrigation horticulture represent only 8% of sales but generate 42% of profits on 100% cash terms without government subsidy risk.",
        common_traps=["Lobbying for higher government urea subsidies instead of pivoting product mix.", "Selling subsidized DAP on credit to cash-strapped retailers.", "Ignoring the rapid growth of drip irrigation farming in India."],
        takeaway_lesson="In heavily regulated commodity industries with delayed state subsidies, strategic resilience requires pivoting capacity into de-regulated, high-margin specialty value-added formulations.",
        suggested_readings=["knowledge_base/industries/14_heavy_manufacturing_and_steel.md", "knowledge_base/case_types/growth_strategy.md", "knowledge_base/methodology/01_preliminary_questions.md"],
        facts=[
            {"id": "subsidy.exposure", "domain": "company", "release_level": "broad_context", "content": "Client sells 1.8M MT subsidized bulk Urea/DAP; government subsidies represent 62% of total invoice value."},
            {"id": "working_capital.drag", "domain": "financials", "release_level": "sharp_question", "content": "Subsidy payment delays average 185 days, resulting in ₹2,800 Cr in unpaid government receivables and ₹240 Cr in bank borrowing interest."},
            {"id": "specialty.economics", "domain": "economics", "release_level": "hypothesis_backed", "content": "Water-Soluble Fertilizers (WSF) and bio-stimulants carry zero government subsidy, command 32% gross margins, and sell on 30-day cash terms.", "dependencies": ["working_capital.drag"]},
            {"id": "horticulture.growth", "domain": "market", "release_level": "hypothesis_backed", "content": "Micro-irrigation and precision horticulture farming in Maharashtra, Gujarat, and AP is growing at 16% CAGR, creating ₹6,000 Cr demand for drip-applied specialty nutrition.", "dependencies": ["specialty.economics"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Bulk commodity fertilizers trap ₹2,800 Cr in 185-day delayed subsidies with 4% margins; client must transition 35% of capacity into non-subsidized, high-margin (32%) specialty water-soluble and bio-stimulant nutrition."},
            {"id": "recommendation.specialty_expansion", "domain": "recommendation", "release_level": "synthesis_support", "content": "Invest ₹120 Cr to build a 200,000 MT dedicated water-soluble fertilizer and liquid bio-fertilizer manufacturing plant."},
            {"id": "recommendation.agronomy_sales", "domain": "recommendation", "release_level": "synthesis_support", "content": "Deploy 300 field agronomists to conduct farm crop demonstration trials for high-value cash crop growers."},
            {"id": "recommendation.drip_partnerships", "domain": "recommendation", "release_level": "synthesis_support", "content": "Form exclusive co-marketing alliances with drip irrigation equipment manufacturers (Jain Irrigation / Netafim)."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.fertilizer-pivot", root_label="Transition fertilizer portfolio to high-margin non-subsidized specialty nutrition.",
            branches=[
                {"id": "subsidy-receivables-drag", "label": "Government Subsidy Arrears & Interest Cost", "conclusion": "185-day subsidy delay traps ₹2,800 Cr and incurs ₹240 Cr interest cost."},
                {"id": "bulk-vs-specialty-margins", "label": "Commodity DAP vs Specialty WSF Economics", "conclusion": "Specialty nutrition has 32% gross margin, zero subsidy reliance, and 30-day terms."},
                {"id": "precision-horticulture-demand", "label": "Micro-Irrigation Adoption & Horticulture Boom", "conclusion": "Drip irrigation boom drives 16% CAGR in specialty nutrition demand."}
            ],
            diagnosis={"label": "Subsidy Arrears Trap & Specialty De-Regulation", "evidence": ["subsidy-receivables-drag", "bulk-vs-specialty-margins", "precision-horticulture-demand"], "conclusion": "Low EBITDA and working capital strain are caused by heavy reliance on subsidized bulk fertilizers with 185-day payment delays; pivoting to non-subsidized specialty nutrition eliminates subsidy risk and expands margins."},
            recommendation={"label": "3-Pillar Specialty Nutrition Transformation", "evidence": ["diagnosis"], "conclusion": "Build 200k MT water-soluble fertilizer capacity, establish agronomist crop-trial sales force, and partner with micro-irrigation leaders."},
            routes=[{"id": "subsidy-first", "sequence": ["subsidy-receivables-drag", "bulk-vs-specialty-margins", "precision-horticulture-demand", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from working capital subsidy delay to specialty fertilizer margin analysis."}],
            recovery=["Ask candidate who pays for bulk fertilizer (farmer vs government).", "Clarify that government subsidies take 6 months to disburse.", "Redirect toward de-regulated water-soluble fertilizers and bio-stimulants."]
        )
    )

    # Cases 6-10 (Petrochemical, Rail DFC, Pharma Sourcing, CV Loans, Solar ALMM)
    # Case 6: Petrochemical Cracker
    emit_case(
        school_dir="iimc", slug="06-petrochemical-cracker-yield", title="Petrochemical Cracker Feedstock Yield", school_tag="IIM-C",
        category="operations", industry="energy_and_renewables", difficulty="advanced",
        opening_context="Your client operates a world-scale dual-feed (naphtha and ethane) steam cracker producing 1.5M MT of ethylene in Western India. Cracker operating cash margins fluctuated wildly from +$350/MT to -$80/MT over eighteen months.",
        opening_objective="Develop a dynamic feedstock optimization and crack-spread hedging model to stabilize and maximize cracker EBITDA.",
        decision_question="How should the petrochemical cracker dynamically balance naphtha vs ethane feedstocks across variable commodity price cycles?",
        primary_metric="Cracker Cash Margin per MT of Ethylene ($/MT)", time_horizon="twelve months",
        core_mechanism="Feedstock flexibility and co-product value capture. Ethane cracking produces high ethylene yield (80%) with minimal co-products; naphtha cracking produces lower ethylene (32%) but rich co-products (propylene, butadiene, benzene) whose value depends on crude oil and downstream polymer spreads.",
        what_wanted_to_test="Chemical process economics, dual-feed steam cracker flexibility, crack-spread hedging (Brent crude vs Henry Hub gas), and co-product price realization.",
        pivotal_insight="When crude oil is expensive relative to natural gas, ethane cracking is superior; but when downstream butadiene/benzene chemical spreads surge, naphtha cracking generates higher total margin despite lower ethylene yield.",
        common_traps=["Assuming ethylene yield percentage is the only metric that matters.", "Locking 100% of feedstock into long-term ethane contracts without flexibility.", "Ignoring the logistics cost of cryogenic refrigerated ethane shipping."],
        takeaway_lesson="In dual-feed petrochemical refining, profitability is governed by the relative spread between crude-derived naphtha and gas-derived ethane; plants must maintain real-time LP model feedstock switching agility.",
        suggested_readings=["knowledge_base/industries/11_energy_and_renewables.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "cracker.config", "domain": "company", "release_level": "broad_context", "content": "Cracker has 1.5M MT ethylene capacity with dual-feed furnaces capable of 30% to 70% ethane/naphtha variation."},
            {"id": "yield.differences", "domain": "operations", "release_level": "sharp_question", "content": "Ethane feed yields 80% Ethylene, 3% Propylene, 1% C4s; Naphtha yields 32% Ethylene, 16% Propylene, 9% Butadiene, 14% Aromatics."},
            {"id": "spread.volatility", "domain": "market", "release_level": "hypothesis_backed", "content": "US ethane import price rose due to VLGC shipping rates, while regional butadiene prices spiked to $1,400/MT, favoring naphtha.", "dependencies": ["yield.differences"]},
            {"id": "switching.agility", "domain": "operations", "release_level": "hypothesis_backed", "content": "Plant takes 18 days to adjust furnace feed ratios due to rigid monthly procurement contracts, missing profitable 30-day crack spread windows.", "dependencies": ["spread.volatility"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Cracker margins were volatile because rigid 30-day procurement prevented rapid switching between ethane and naphtha, missing high co-product (butadiene/benzene) crack spreads when crude-gas spreads shifted."},
            {"id": "recommendation.lp_dispatch", "domain": "recommendation", "release_level": "synthesis_support", "content": "Deploy real-time Linear Programming (LP) optimization linking daily global polymer prices to furnace feed selection within 48 hours."},
            {"id": "recommendation.feedstock_hedging", "domain": "recommendation", "release_level": "synthesis_support", "content": "Hedge ethane-naphtha crack spreads using financial derivatives on Brent crude vs Mont Belvieu ethane."},
            {"id": "recommendation.downstream_integration", "domain": "recommendation", "release_level": "synthesis_support", "content": "Expand on-site polybutadiene rubber (PBR) and alkylation units to capture maximum value from naphtha C4 co-products."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.cracker-yield", root_label="Maximize and stabilize dual-feed petrochemical cracker margins.",
            branches=[
                {"id": "feedstock-yield-chemistry", "label": "Ethane vs Naphtha Yield & Co-Product Output", "conclusion": "Ethane yields 80% ethylene; Naphtha yields high-value butadiene, propylene, benzene."},
                {"id": "crack-spread-economics", "label": "Crude vs Gas Price Ratios & Polymer Spreads", "conclusion": "When butadiene spreads spike, naphtha is more profitable despite lower ethylene yield."},
                {"id": "operational-switching-latency", "label": "Feed Switching Speed & Procurement Contracts", "conclusion": "18-day switching lag caused plant to miss short-term market crack spread spikes."}
            ],
            diagnosis={"label": "Rigid Feed Procurement & Missed Co-Product Spreads", "evidence": ["feedstock-yield-chemistry", "crack-spread-economics", "operational-switching-latency"], "conclusion": "Margin instability is driven by an 18-day lag in switching cracker feeds, missing lucrative co-product price spikes when petrochemical spreads shift."},
            recommendation={"label": "3-Pillar Petrochemical Optimization Plan", "evidence": ["diagnosis"], "conclusion": "Deploy real-time LP feed dispatch, execute financial crack-spread hedging, and invest in downstream C4 polymer integration."},
            routes=[{"id": "chemistry-first", "sequence": ["feedstock-yield-chemistry", "crack-spread-economics", "operational-switching-latency", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from chemical cracking yields to co-product price economics."}],
            recovery=["Ask candidate what other products come out of cracking naphtha besides ethylene.", "Clarify that butadiene and benzene can have very high market value.", "Redirect toward dual-feed flexibility and real-time LP dispatch."]
        )
    )

    # Case 7: Rail Dedicated Freight Corridor
    emit_case(
        school_dir="iimc", slug="07-rail-freight-corridor", title="Freight Corridor Logistics Park", school_tag="IIM-C",
        category="operations", industry="logistics_and_cold_chain", difficulty="intermediate",
        opening_context="Your client operates a Private Freight Terminal and Multi-Modal Logistics Park (MMLP) connected to the Western Dedicated Freight Corridor (DFC). Container dwell time in the rail yard averages 48 hours, failing the promised 12-hour express delivery SLA.",
        opening_objective="Diagnose rail-to-road transshipment delays and engineer a 12-hour container turnaround workflow.",
        decision_question="What is causing 48-hour container dwell times at the DFC logistics park and how can rail-to-road transshipment be streamlined?",
        primary_metric="Container Yard Dwell Time (hours) and Reach Stacker Moves/Hour", time_horizon="six months",
        core_mechanism="Customs EDI electronic gateway synchronization failures and rail wagon uncoupling delays. Double-stack container trains require simultaneous customs bond clearances before any container can be offloaded, creating whole-train blockages when a single container has paperwork discrepancies.",
        what_wanted_to_test="Intermodal rail freight, double-stack container train operations, customs dry-port (ICD) compliance, and reach stacker yard planning.",
        pivotal_insight="A 90-container double-stack train cannot be partially unloaded; if 2 containers have customs documentation holds, the entire train waits on the rail siding, blocking incoming freight trains.",
        common_traps=["Assuming rail locomotive engine speed is slow.", "Blaming highway truck drivers for not arriving at the logistics park.", "Purchasing more reach stackers when the bottleneck is customs train-level clearance."],
        takeaway_lesson="In unit-train intermodal logistics, administrative clearance must be decoupled from physical asset discharge to prevent single-unit exceptions from holding up entire trains.",
        suggested_readings=["knowledge_base/industries/01_logistics_and_cold_chain.md", "knowledge_base/case_types/unconventional_and_abstract.md", "knowledge_base/methodology/02_issue_tree_structuring.md"],
        facts=[
            {"id": "terminal.spec", "domain": "company", "release_level": "broad_context", "content": "MMLP handles 4 daily double-stack DFC container trains connecting NCR to Mundra/JNPT ports."},
            {"id": "dwell.metrics", "domain": "operations", "release_level": "sharp_question", "content": "Average container dwell time is 48 hours vs 12-hour customer commitment, causing 25% shipper churn."},
            {"id": "train.clearance", "domain": "operations", "release_level": "hypothesis_backed", "content": "Customs ICD regulations mandate full train-manifest clearance before gantry crane offloading can begin on the main rail siding.", "dependencies": ["dwell.metrics"]},
            {"id": "decoupling.solution", "domain": "operations", "release_level": "hypothesis_backed", "content": "Offloading all containers immediately to an interim bonded buffer yard frees the rail siding in 3 hours, allowing hold containers to be inspected separately.", "dependencies": ["train.clearance"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "48-hour dwell time is caused by customs regulations blocking train unloading whenever single containers have discrepancies; solution requires immediate train offloading to a bonded buffer yard within 3 hours."},
            {"id": "recommendation.buffer_yard", "domain": "recommendation", "release_level": "synthesis_support", "content": "Create a designated Bonded Buffer Siding to offload entire trains immediately in 3 hours, isolating exception containers."},
            {"id": "recommendation.pre_clearance", "domain": "recommendation", "release_level": "synthesis_support", "content": "Enforce electronic pre-clearance filing 12 hours before train arrival via ICEGATE customs integration."},
            {"id": "recommendation.truck_appointment", "domain": "recommendation", "release_level": "synthesis_support", "content": "Launch automated truck appointment scheduling to ensure road trailers are at the gate when containers are grounded."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.dfc-dwell-time", root_label="Reduce MMLP container dwell time from 48 to under 12 hours.",
            branches=[
                {"id": "train-siding-turnaround", "label": "Rail Siding Operations & Crane Productivity", "conclusion": "Trains sit on siding for 24+ hours waiting for customs clearance before unloading starts."},
                {"id": "customs-icd-regulations", "label": "Train-Level vs Container-Level Customs Clearance", "conclusion": "Single-container document hold blocks unloading of all 90 double-stack containers."},
                {"id": "road-evacuation-readiness", "label": "Truck Gate Appointments & First-Mile Drayage", "conclusion": "Trucks arrive uncoordinated, compounding yard congestion post-unloading."}
            ],
            diagnosis={"label": "Train-Level Customs Blockage & Siding Lockup", "evidence": ["train-siding-turnaround", "customs-icd-regulations", "road-evacuation-readiness"], "conclusion": "Dwell time is 48 hours because single container customs holds lock entire double-stack trains on the siding; decoupling train discharge to a bonded buffer yard restores 12-hour turnaround."},
            recommendation={"label": "3-Pillar Logistics Terminal Debottlenecking", "evidence": ["diagnosis"], "conclusion": "Establish bonded buffer siding for 3-hour train release, mandate pre-arrival customs filing, and schedule truck appointments."},
            routes=[{"id": "rail-first", "sequence": ["train-siding-turnaround", "customs-icd-regulations", "road-evacuation-readiness", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from train dwell time to customs ICD clearance bottlenecks."}],
            recovery=["Ask candidate what happens if 1 out of 90 containers on a train has a paperwork error.", "Clarify that the rail siding must be vacated for the next train.", "Redirect toward immediate offloading into a bonded buffer yard."]
        )
    )

    # Case 8: Pharma API Sourcing
    emit_case(
        school_dir="iimc", slug="08-pharma-api-sourcing", title="Pharma API Dual-Vendor Sourcing", school_tag="IIM-C",
        category="operations", industry="pharma_and_healthcare", difficulty="intermediate",
        opening_context="Your client is a leading Indian generic finished dosage formulation (FDF) manufacturer exporting cardiovascular drugs to the US and EU. Severe active pharmaceutical ingredient (API) supply shortages and price spikes wiped out ₹180 Cr in gross profit.",
        opening_objective="Design a multi-vendor API procurement and regulatory qualification strategy to de-risk critical drug manufacturing.",
        decision_question="How should the pharma company structure API vendor allocation and regulatory filings to eliminate supply shock risks?",
        primary_metric="API Supply Uptime (%) and Landed Cost per Kilogram", time_horizon="twelve months",
        core_mechanism="Regulatory regulatory filing lock-in (Drug Master File / DMF single-source approval with US FDA). Formulator was locked into a single Chinese API supplier; qualifying a secondary domestic API vendor requires 9 months of stability testing and a US FDA prior approval supplement (PAS).",
        what_wanted_to_test="Pharmaceutical regulatory supply chain, US FDA DMF filing requirements, API dual-sourcing economics, and buffer inventory carrying cost.",
        pivotal_insight="Procurement saved 8% by single-sourcing from China, but US FDA rules make switching suppliers take 9 months; maintaining dual-approved DMF sources (70% primary / 30% secondary domestic) eliminates stockout risks at minimal cost premium.",
        common_traps=["Assuming the company can simply buy API from alternative vendors on the open spot market without US FDA regulatory approvals.", "Holding 2 years of raw API inventory, which creates massive working capital lockup and degradation.", "Exiting regulated US markets entirely."],
        takeaway_lesson="In regulated life sciences, supply chain resilience is constrained by regulatory filing lead times; dual-sourcing must be built into original regulatory dossiers rather than attempted during crisis.",
        suggested_readings=["knowledge_base/industries/03_pharma_and_healthcare.md", "knowledge_base/case_types/unconventional_and_abstract.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "export.portfolio", "domain": "company", "release_level": "broad_context", "content": "Client exports 5 high-volume cardiovascular oral solid drugs ($220M revenue) to US and EU markets."},
            {"id": "stockout.impact", "domain": "financials", "release_level": "sharp_question", "content": "Single-source Chinese API factory shutdown caused a 4-month formulation plant halt, losing ₹180 Cr in revenue and customer penalty fines."},
            {"id": "regulatory.barrier", "domain": "regulation", "release_level": "hypothesis_backed", "content": "US FDA requires a 6-month accelerated stability study and a Prior Approval Supplement (PAS) filing to approve any new API vendor.", "dependencies": ["stockout.impact"]},
            {"id": "dual_sourcing.cost", "domain": "economics", "release_level": "hypothesis_backed", "content": "A 70:30 allocation between Chinese primary and Indian secondary API suppliers increases landed API cost by only 3.5% while eliminating single-point failure.", "dependencies": ["regulatory.barrier"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Plant shutdown occurred because client single-sourced API in US FDA dossiers to save 3.5% cost, making emergency vendor switching impossible due to 9-month regulatory approval requirements."},
            {"id": "recommendation.dual_dmf", "domain": "recommendation", "release_level": "synthesis_support", "content": "File proactive US FDA PAS supplements to pre-qualify 2 validated API vendors for every top-10 revenue product."},
            {"id": "recommendation.split_allocation", "domain": "recommendation", "release_level": "synthesis_support", "content": "Contractually split commercial procurement 70% primary (low-cost) and 30% secondary (domestic) to keep both manufacturing lines active."},
            {"id": "recommendation.strategic_reserve", "domain": "recommendation", "release_level": "synthesis_support", "content": "Maintain a rolling 90-day strategic buffer stock of key intermediate KSMs in temperature-controlled warehouses."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.api-sourcing-derisk", root_label="De-risk pharmaceutical API procurement and eliminate stockout disruptions.",
            branches=[
                {"id": "single-source-vulnerability", "label": "Single-Source Reliance & Plant Downtime", "conclusion": "Single Chinese vendor shutdown caused 4-month formulation halt and ₹180 Cr loss."},
                {"id": "regulatory-approval-hurdles", "label": "US FDA DMF Filing & Stability Lead Times", "conclusion": "Adding a new API source requires 9 months of stability data and US FDA PAS approval."},
                {"id": "dual-sourcing-cost-benefit", "label": "70:30 Split Sourcing Unit Economics", "conclusion": "70:30 dual-sourcing adds only 3.5% cost while providing 100% supply redundancy."}
            ],
            diagnosis={"label": "Regulatory Single-Source Lock-in", "evidence": ["single-source-vulnerability", "regulatory-approval-hurdles", "dual-sourcing-cost-benefit"], "conclusion": "Supply collapsed because client single-sourced API in FDA dossiers, creating a 9-month regulatory switching barrier when the primary vendor halted production."},
            recommendation={"label": "3-Pillar Pharma Supply Resilience Framework", "evidence": ["diagnosis"], "conclusion": "Pre-qualify dual DMF sources with US FDA, execute 70:30 split procurement contracts, and maintain 90-day strategic KSM buffer stock."},
            routes=[{"id": "regulatory-first", "sequence": ["single-source-vulnerability", "regulatory-approval-hurdles", "dual-sourcing-cost-benefit", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from single-source supply shock to FDA regulatory approval lead times."}],
            recovery=["Ask candidate whether a pharma company can instantly switch API vendors without drug regulatory approvals.", "Clarify that US FDA requires stability test filings.", "Redirect toward proactive dual-DMF vendor qualification."]
        )
    )

    # Case 9: Commercial Vehicle Loan
    emit_case(
        school_dir="iimc", slug="09-commercial-vehicle-loan", title="Commercial Vehicle Loan Telematics", school_tag="IIM-C",
        category="operations", industry="banking_and_financial_services", difficulty="intermediate",
        opening_context="Your client is a leading non-banking financial company (NBFC) financing heavy commercial vehicles (trucks and tippers). Gross NPAs in the small fleet operator segment (<5 trucks) rose from 3.2% to 8.9% during high diesel price inflation.",
        opening_objective="Diagnose default drivers among small fleet truck owners and design an IoT telematics-based underwriting and early warning system.",
        decision_question="Why did commercial vehicle loan defaults surge during diesel inflation and how can IoT telematics be used to mitigate credit risk?",
        primary_metric="Gross NPA Ratio (%) and Early Default Intervention Rate", time_horizon="twelve months",
        core_mechanism="Cash flow squeeze on small fleet operators who lack freight pricing power to pass on fuel price hikes, compounded by unmonitored vehicle idle time and unauthorized trip diversion that eroded monthly EMI debt service capacity.",
        what_wanted_to_test="Commercial vehicle asset financing, operating cash flow debt service coverage (DSCR), diesel fuel inflation elasticity, and telematics IoT data integration.",
        pivotal_insight="Small fleet operators run 18% fewer kilometers per month due to freight broker freight rate delays; using IoT telematics to track real-time engine running hours and FASTag toll spend predicts default 45 days before EMI bounce.",
        common_traps=["Assuming truck drivers are deliberately siphoning loans without working.", "Immediately repossessing trucks, which crashes resale recovery value in a depressed commercial vehicle market.", "Blaming vehicle mechanical breakdown."],
        takeaway_lesson="In asset-backed commercial lending, real-time telematics utilization telemetry provides predictive leading indicators of borrower cash-flow distress long before bank check bounces occur.",
        suggested_readings=["knowledge_base/industries/04_banking_and_financial_services.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "portfolio.scale", "domain": "company", "release_level": "broad_context", "content": "NBFC has ₹14,000 Cr CV loan book; small fleet operators (<5 trucks) represent ₹6,200 Cr."},
            {"id": "fuel.impact", "domain": "financials", "release_level": "sharp_question", "content": "Diesel represents 58% of truck operating costs; fuel price hikes squeezed operator monthly net cash flow from ₹42,000 to ₹14,000 per truck against ₹28,000 EMI."},
            {"id": "telematics.signal", "domain": "operations", "release_level": "hypothesis_backed", "content": "Piloting IoT GPS telematics on 5,000 trucks showed that drops in daily running kilometers (<180 km/day) predict EMI default 45 days in advance with 88% accuracy.", "dependencies": ["fuel.impact"]},
            {"id": "restructuring.feasibility", "domain": "risk", "release_level": "hypothesis_backed", "content": "Offering seasonal flexible EMIs linked to telematics mileage reduced 90+ DPD defaults by 55% compared to static payment schedules.", "dependencies": ["telematics.signal"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "NPAs surged because diesel inflation wiped out small truckers' cash flow (net income fell to ₹14k vs ₹28k EMI); integrating IoT telematics enables 45-day advance default prediction and dynamic mileage-linked EMI restructuring."},
            {"id": "recommendation.telematics_underwriting", "domain": "recommendation", "release_level": "synthesis_support", "content": "Mandate connected IoT telematics transponders on all financed vehicles with live kilometer and fuel consumption tracking."},
            {"id": "recommendation.flexible_emi", "domain": "recommendation", "release_level": "synthesis_support", "content": "Structure 'Pay-As-You-Drive' flexible EMI plans where monthly repayments adjust based on verified freight running mileage."},
            {"id": "recommendation.freight_tieup", "domain": "recommendation", "release_level": "synthesis_support", "content": "Partner with digital freight brokerage platforms to provide guaranteed trip loads directly to financed truck owners."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.cv-loan-npa", root_label="Contain commercial vehicle loan NPAs and deploy telematics risk management.",
            branches=[
                {"id": "diesel-inflation-cash-squeeze", "label": "Diesel Inflation & Trucker Operating Cash Flow", "conclusion": "Fuel inflation dropped trucker net income to ₹14k/mo against ₹28k monthly EMI."},
                {"id": "telematics-early-warning", "label": "IoT Mileage Telemetry & Early Warning Signals", "conclusion": "Mileage drops (<180 km/day) predict loan default 45 days in advance with 88% accuracy."},
                {"id": "repayment-flexibility", "label": "Dynamic Mileage-Linked EMI Restructuring", "conclusion": "Mileage-linked flexible EMIs reduce 90+ DPD defaults by 55%."}
            ],
            diagnosis={"label": "Fuel Inflation Cash-Flow Squeeze & Telematics Mitigation", "evidence": ["diesel-inflation-cash-squeeze", "telematics-early-warning", "repayment-flexibility"], "conclusion": "Defaults are driven by diesel inflation squeezing monthly cash below EMI obligations; IoT telematics provides 45-day early warning and enables dynamic flexible repayment structures."},
            recommendation={"label": "3-Pillar Connected Vehicle Lending Strategy", "evidence": ["diagnosis"], "conclusion": "Deploy IoT telematics on all fleets, offer mileage-linked flexible EMIs, and connect truckers to digital freight load boards."},
            routes=[{"id": "telematics-first", "sequence": ["diesel-inflation-cash-squeeze", "telematics-early-warning", "repayment-flexibility", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from trucker operating cash flow to telematics predictive data."}],
            recovery=["Ask candidate what percentage of a truck's monthly operating cost is diesel fuel.", "Clarify that small truckers cannot increase freight rates immediately.", "Redirect toward IoT telematics predictive tracking and flexible EMI structures."]
        )
    )

    # Case 10: Solar Module Manufacturing
    emit_case(
        school_dir="iimc", slug="10-solar-module-manufacturing", title="Solar PV Module ALMM Manufacturing", school_tag="IIM-C",
        category="market_entry", industry="energy_and_renewables", difficulty="advanced",
        opening_context="Your client is an Indian conglomerate evaluating a ₹3,500 Cr investment in a 5 GW vertically integrated solar cell and module manufacturing plant in Gujarat under the government's ALMM and PLI policy regime.",
        opening_objective="Evaluate capital expenditure, technological cell efficiency (TOPCon vs HJT), and domestic content requirement economics to achieve a 15% equity IRR.",
        decision_question="Should the conglomerate invest in 5 GW solar PV manufacturing, and which cell technology architecture should be adopted?",
        primary_metric="Levelized Module Manufacturing Cost ($/Wp) and Project IRR (%)", time_horizon="three years",
        core_mechanism="Technological obsolescence risk vs policy protection. Government ALMM non-tariff barriers and 40% Basic Customs Duty (BCD) protect domestic manufacturers from cheap Chinese imports, but legacy PERC cell technology is obsolete; investing in N-type TOPCon with 24.5% efficiency secures Tier-1 utility developer demand.",
        what_wanted_to_test="Solar PV value chain (polysilicon -> wafer -> cell -> module), technology transitions (PERC to TOPCon to HJT), PLI subsidy eligibility, and tariff protection economics.",
        pivotal_insight="Module assembly alone has thin 5% margins; backward integration into solar cell manufacturing captures the PLI government subsidy (₹1,200 Cr) and achieves 16.5% equity IRR under TOPCon technology.",
        common_traps=["Investing in older P-type PERC cell lines which Chinese manufacturers are dumping at loss.", "Building pure module assembly without cell integration, failing ALMM domestic content rules.", "Assuming imported Chinese wafer prices will remain permanently cheap."],
        takeaway_lesson="In state-subsidized clean-tech manufacturing, standalone assembly is vulnerable to policy shifts; capturing government incentives requires deep backward integration into advanced technology nodes.",
        suggested_readings=["knowledge_base/industries/11_energy_and_renewables.md", "knowledge_base/case_types/market_entry.md", "knowledge_base/methodology/02_issue_tree_structuring.md"],
        facts=[
            {"id": "market.demand", "domain": "market", "release_level": "broad_context", "content": "India requires 30 GW of solar modules annually to meet its 500 GW 2030 renewable target."},
            {"id": "policy.protection", "domain": "regulation", "release_level": "sharp_question", "content": "Government enforces 40% Basic Customs Duty on imported modules and mandates Approved List of Models and Manufacturers (ALMM) for all grid projects."},
            {"id": "tech.comparison", "domain": "operations", "release_level": "hypothesis_backed", "content": "P-type PERC (21.5% efficiency) is obsolete; N-type TOPCon (24.5% efficiency) costs $0.015/Wp more to build but yields 8% higher energy output, commanding a 12% price premium.", "dependencies": ["policy.protection"]},
            {"id": "pli.financials", "domain": "financials", "release_level": "hypothesis_backed", "content": "5 GW integrated Cell + Module TOPCon plant qualifies for ₹1,250 Cr PLI cash incentives, delivering 16.2% equity IRR against 10.4% for pure module assembly.", "dependencies": ["tech.comparison"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "5 GW solar manufacturing is highly viable (16.2% IRR) under ALMM policy protection, provided the company builds integrated Cell + Module lines using N-type TOPCon technology to capture ₹1,250 Cr in PLI subsidies."},
            {"id": "recommendation.topcon_tech", "domain": "recommendation", "release_level": "synthesis_support", "content": "Commit to 5 GW N-type TOPCon cell and module architecture with 24.5% efficiency rating."},
            {"id": "recommendation.pli_application", "domain": "recommendation", "release_level": "synthesis_support", "content": "Structure investment to maximize Tranche-II PLI milestone disbursements of ₹1,250 Cr."},
            {"id": "recommendation.wafer_hedging", "domain": "recommendation", "release_level": "synthesis_support", "content": "Secure 3-year indexed wafer procurement contracts with Southeast Asian suppliers while exploring future ingot-wafer integration."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.solar-manufacturing", root_label="Evaluate 5 GW solar cell and module manufacturing investment.",
            branches=[
                {"id": "policy-and-market-demand", "label": "ALMM Mandates & 40% Customs Duty Protection", "conclusion": "ALMM and 40% BCD create guaranteed domestic demand of 30 GW/year."},
                {"id": "technology-node-selection", "label": "PERC vs TOPCon vs HJT Cell Efficiency", "conclusion": "N-type TOPCon delivers 24.5% efficiency and commands a 12% price premium."},
                {"id": "integration-and-pli-economics", "label": "Cell+Module Integration & PLI Subsidies", "conclusion": "Integrated Cell+Module captures ₹1,250 Cr PLI subsidies, achieving 16.2% equity IRR."}
            ],
            diagnosis={"label": "Integrated TOPCon Manufacturing Viability", "evidence": ["policy-and-market-demand", "technology-node-selection", "integration-and-pli-economics"], "conclusion": "Investment is highly lucrative (16.2% IRR) under ALMM protection if executed as an integrated Cell+Module TOPCon facility qualifying for ₹1,250 Cr PLI incentives."},
            recommendation={"label": "3-Pillar Solar Industrial Strategy", "evidence": ["diagnosis"], "conclusion": "Build 5 GW integrated TOPCon plant, execute PLI milestone compliance, and lock multi-year wafer supply agreements."},
            routes=[{"id": "technology-first", "sequence": ["policy-and-market-demand", "technology-node-selection", "integration-and-pli-economics", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from policy tariff barriers to cell technology selection and PLI economics."}],
            recovery=["Ask candidate why pure module assembly has lower margins than cell manufacturing.", "Clarify that ALMM mandates domestic cells for government tenders.", "Redirect toward N-type TOPCon cell efficiency and PLI subsidy economics."]
        )
    )

    print("Successfully generated all 10 IIM Calcutta exemplar cases!")


if __name__ == "__main__":
    generate_all_iimc_cases()
