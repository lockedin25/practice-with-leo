"""Generator for all 10 IIM Bangalore Exemplar Case Packages under corpus/exemplars/iimb/."""

from __future__ import annotations
from scripts.generate_exemplars import emit_case, make_standard_tree


def generate_all_iimb_cases():
    print("Generating all 10 IIM Bangalore exemplar cases...")

    # Case 1: Microfinance Credit
    emit_case(
        school_dir="iimb", slug="01-microfinance-credit", title="Microfinance Portfolio Risk", school_tag="IIM-B",
        category="operations", industry="banking_and_financial_services", difficulty="intermediate",
        opening_context="Your client is a leading Indian Microfinance Institution (MFI) with 2.5M women borrowers across Joint Liability Groups (JLGs). Collection efficiency in a flood-affected agricultural state plunged from 98.5% to 74%.",
        opening_objective="Diagnose default contagion across JLGs and recommend a field collection and loan restructuring strategy.",
        decision_question="How can the MFI halt group default contagion and restore loan collection efficiency?",
        primary_metric="Portfolio at Risk (PAR 30) and Collection Efficiency (%)", time_horizon="six months",
        core_mechanism="Social collateral collapse in Joint Liability Groups where mutual guarantee peer pressure broke down due to widespread flood crop damage, leading to collective strategic default when center meetings were suspended.",
        what_wanted_to_test="Microfinance JLG group dynamics, peer monitoring collapse under systemic covariate shocks, and field collection restructuring.",
        pivotal_insight="Individual borrowers who had cash refused to pay because peer group members were insolvent; once group center meetings stopped, moral hazard spread to non-affected neighboring villages.",
        common_traps=["Deploying aggressive coercive collection agents, which violates RBI microfinance fair practices code and causes political backlash.", "Writing off the entire portfolio without distinguishing flooded vs non-affected borrowers.", "Assuming flood insurance covered all micro-borrowers."],
        takeaway_lesson="In group microfinance, covariate natural disasters destroy peer guarantees; recovery requires unbundling joint liability into individual emergency moratoriums and resuming weekly center meetings.",
        suggested_readings=["knowledge_base/industries/04_banking_and_financial_services.md", "knowledge_base/case_types/unconventional_and_abstract.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "mfi.portfolio", "domain": "company", "release_level": "broad_context", "content": "MFI has ₹6,000 Cr AUM; affected state represents ₹1,400 Cr across 500,000 JLG borrowers."},
            {"id": "collection.drop", "domain": "financials", "release_level": "sharp_question", "content": "Weekly collection efficiency fell from 98.5% to 74% within 6 weeks post-monsoon flooding."},
            {"id": "group.dynamics", "domain": "operations", "release_level": "hypothesis_backed", "content": "45% of borrowers suffered crop loss, but 85% of center meetings ceased because healthy borrowers refused to cover insolvent peers' weekly payments.", "dependencies": ["collection.drop"]},
            {"id": "contagion.spread", "domain": "risk", "release_level": "hypothesis_backed", "content": "Rumors of state government farm loan waivers led non-flooded districts to withhold repayments.", "dependencies": ["group.dynamics"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Default contagion occurred because systemic flood damage broke the JLG mutual guarantee mechanism; healthy borrowers strategically defaulted when weekly center meetings were abandoned amid loan waiver rumors."},
            {"id": "recommendation.moratorium", "domain": "recommendation", "release_level": "synthesis_support", "content": "Provide immediate 90-day interest-free loan restructuring and emergency livelihood top-ups to verified flood-damaged households."},
            {"id": "recommendation.decouple", "domain": "recommendation", "release_level": "synthesis_support", "content": "Temporarily decouple joint liability so non-affected members can repay their individual share without penalization for group defaults."},
            {"id": "recommendation.meetings", "domain": "recommendation", "release_level": "synthesis_support", "content": "Re-establish weekly center meetings led by local branch officers to dispel loan waiver misinformation."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.mfi-recovery", root_label="Halt MFI default contagion and restore collection efficiency.",
            branches=[
                {"id": "flood-impact-segmentation", "label": "Direct Flood Damage vs Contagion", "conclusion": "45% suffered physical crop loss, but default spread to 74% due to behavioral contagion."},
                {"id": "jlg-peer-pressure-failure", "label": "JLG Mutual Guarantee Breakdown", "conclusion": "Healthy borrowers refuse to pay when forced to cover insolvent group members."},
                {"id": "field-operations-and-moratorium", "label": "Center Meetings & Waiver Rumors", "conclusion": "Suspension of weekly meetings fueled political loan waiver speculation."}
            ],
            diagnosis={"label": "Joint Liability Breakdown & Moral Hazard Contagion", "evidence": ["flood-impact-segmentation", "jlg-peer-pressure-failure", "field-operations-and-moratorium"], "conclusion": "Collection collapsed because systemic crop damage broke the JLG mutual guarantee, triggering strategic defaults that spread due to suspended center meetings."},
            recommendation={"label": "3-Pillar Microfinance Recovery Strategy", "evidence": ["diagnosis"], "conclusion": "Restructure flood-hit loans, decouple group liability for healthy borrowers, and resume disciplined weekly center meetings."},
            routes=[{"id": "field-first", "sequence": ["flood-impact-segmentation", "jlg-peer-pressure-failure", "field-operations-and-moratorium", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from portfolio loss to group behavioral dynamics."}],
            recovery=["Ask candidate why non-flooded borrowers stopped paying their loans.", "Clarify that the MFI operates on group liability (JLGs).", "Redirect toward the breakdown of peer guarantees and center meetings."]
        )
    )

    # Case 2: Hospital Bed Occupancy
    emit_case(
        school_dir="iimb", slug="02-hospital-bed-occupancy", title="Hospital Surgical Throughput", school_tag="IIM-B",
        category="operations", industry="pharma_and_healthcare", difficulty="intermediate",
        opening_context="Your client is a 450-bed multispecialty tertiary hospital in Bengaluru. Overall bed occupancy is low (64%), yet elective surgeries are routinely cancelled due to ICU bed shortages.",
        opening_objective="Diagnose the operational bottleneck in surgical and ICU patient flow and recommend a capacity optimization plan.",
        decision_question="Why are elective surgeries delayed despite low overall hospital bed occupancy?",
        primary_metric="Surgical Theatre Utilization (%) and ICU Length of Stay (days)", time_horizon="six months",
        core_mechanism="ICU bed blockage caused by step-down ward discharge delays (averaging 14 hours post-physician discharge order) and non-standardized post-operative recovery protocols, which backed up into operating theatre cancellations.",
        what_wanted_to_test="Hospital patient flow dynamics, critical care capacity bottlenecks, discharge coordination lag, and schedule smoothing across surgical specialties.",
        pivotal_insight="General ward beds are 36% empty, but post-op cardiac/orthopedic patients cannot leave the 40-bed ICU because step-down wards take 14 hours to process billing, pharmacy clearance, and bed turnover.",
        common_traps=["Assuming surgeon availability or operating room count is the constraint.", "Recommending building an expensive 50-bed ICU expansion without auditing discharge cycle time.", "Blaming emergency trauma patient spikes for scheduled surgery cancellations."],
        takeaway_lesson="In complex healthcare systems, flow blockage in downstream recovery units (ICU/step-down) starves upstream revenue-generating assets (Operating Theatres), regardless of total hospital bed capacity.",
        suggested_readings=["knowledge_base/industries/03_pharma_and_healthcare.md", "knowledge_base/case_types/unconventional_and_abstract.md", "knowledge_base/methodology/02_issue_tree_structuring.md"],
        facts=[
            {"id": "hospital.capacity", "domain": "company", "release_level": "broad_context", "content": "Hospital has 450 beds: 350 general/semi-private, 60 step-down, 40 ICU beds, and 12 Operating Rooms (ORs)."},
            {"id": "occupancy.split", "domain": "operations", "release_level": "sharp_question", "content": "General beds average 64% occupancy; ICU runs at 96% occupancy with an average wait time of 6 hours for post-op admissions."},
            {"id": "discharge.lag", "domain": "operations", "release_level": "hypothesis_backed", "content": "Patients medically cleared for ICU step-down wait an average of 14.2 hours in ICU beds due to slow ward cleaning, billing clearance, and insurance TPA approvals.", "dependencies": ["occupancy.split"]},
            {"id": "or.cancellations", "domain": "financials", "release_level": "hypothesis_backed", "content": "18% of scheduled high-margin elective surgeries are postponed because no guaranteed post-op ICU bed is available on surgery morning.", "dependencies": ["discharge.lag"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Surgeries are cancelled because ICU beds are blocked by medically cleared patients waiting 14+ hours for ward transfers due to administrative and TPA insurance bottlenecks."},
            {"id": "recommendation.discharge_lounge", "domain": "recommendation", "release_level": "synthesis_support", "content": "Establish a dedicated Transit Discharge Lounge with pharmacy and billing desks to free up inpatient beds by 11 AM."},
            {"id": "recommendation.icu_stepdown", "domain": "recommendation", "release_level": "synthesis_support", "content": "Convert 20 under-utilized general beds into a High Dependency Unit (HDU) with continuous monitoring to bypass full ICU for routine recoveries."},
            {"id": "recommendation.tpa_automation", "domain": "recommendation", "release_level": "synthesis_support", "content": "Implement automated pre-authorization with health insurance TPAs 24 hours prior to scheduled discharge."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.hospital-throughput", root_label="Eliminate elective surgery cancellations and optimize ICU flow.",
            branches=[
                {"id": "bed-utilization-by-unit", "label": "Occupancy Breakdown: Ward vs ICU vs OR", "conclusion": "Wards are 64% full while ICU runs at 96%, blocking Operating Rooms."},
                {"id": "patient-discharge-cycle", "label": "ICU-to-Ward Transfer & Discharge Delays", "conclusion": "Cleared patients occupy ICU beds for 14.2 hours waiting for ward clearance and billing."},
                {"id": "tpa-and-ward-turnaround", "label": "Insurance TPA Approvals & Housekeeping", "conclusion": "Administrative discharge delays create artificial bed shortages during morning peak admissions."}
            ],
            diagnosis={"label": "Downstream ICU Transfer Blockage", "evidence": ["bed-utilization-by-unit", "patient-discharge-cycle", "tpa-and-ward-turnaround"], "conclusion": "High-margin surgeries are cancelled because ICU beds are choked by cleared patients experiencing a 14-hour discharge lag to general wards."},
            recommendation={"label": "3-Pillar Patient Flow Debottlenecking", "evidence": ["diagnosis"], "conclusion": "Create a Transit Discharge Lounge, expand HDU step-down capacity, and automate digital TPA insurance clearances."},
            routes=[{"id": "flow-first", "sequence": ["bed-utilization-by-unit", "patient-discharge-cycle", "tpa-and-ward-turnaround", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from overall occupancy to ICU vs ward discharge bottlenecks."}],
            recovery=["Ask candidate why surgeries are cancelled if general wards are 36% empty.", "Clarify that operating rooms have surgeon availability.", "Redirect inquiry toward ICU bed availability and discharge transfer times."]
        )
    )

    # Case 3: Renewable IPP Bidding
    emit_case(
        school_dir="iimb", slug="03-renewable-ipp-bidding", title="Renewable IPP Tariff Bidding", school_tag="IIM-B",
        category="pricing", industry="energy_and_renewables", difficulty="advanced",
        opening_context="Your client is a leading Independent Power Producer (IPP) in India bidding for a 1,200 MW SECI Solar-Wind Hybrid tender with 4-hour Battery Energy Storage (BESS). Competitors are bidding aggressive tariffs below ₹3.40/kWh.",
        opening_objective="Determine the bidding tariff floor and optimize the generation asset mix to achieve a 14% equity IRR.",
        decision_question="What is the lowest sustainable bid tariff for the hybrid storage tender and how should the generation/storage capacity be sized?",
        primary_metric="Levelized Cost of Electricity (LCOE) and Equity IRR (%)", time_horizon="three years",
        core_mechanism="Transmission curtailment risk and battery degradation cycling vs peak-hour tariff arbitrage. Over-sizing solar capacity leads to daytime clipping losses unless matched with wind generation whose peak production matches evening peak power demand.",
        what_wanted_to_test="Renewable tariff modeling, hybrid generation correlation (solar diurnal curve vs wind evening peak), BESS sizing optimization, and inter-state transmission system (ISTS) waiver economics.",
        pivotal_insight="A 60:40 Solar-Wind hybrid balance reduces required battery storage capacity by 45% compared to pure solar-plus-storage, because coastal wind generation peaks between 6 PM and 10 PM during the mandatory delivery window.",
        common_traps=["Modeling the bid as pure solar + massive battery storage, which drives capex too high to compete with ₹3.40 tariffs.", "Ignoring battery degradation replacement capex in year 8.", "Assuming 100% transmission availability during peak solar noon."],
        takeaway_lesson="In round-the-clock renewable bidding, optimizing generation resource complementarity (solar + wind) drastically reduces expensive battery storage capex requirements.",
        suggested_readings=["knowledge_base/industries/11_energy_and_renewables.md", "knowledge_base/case_types/pricing_strategy.md", "knowledge_base/methodology/04_data_gathering_and_notes.md"],
        facts=[
            {"id": "tender.terms", "domain": "company", "release_level": "broad_context", "content": "Tender mandates 1,200 MW supply with guaranteed 85% peak-hour availability (6 AM-9 AM and 6 PM-11 PM)."},
            {"id": "capex.costs", "domain": "financials", "release_level": "sharp_question", "content": "Solar capex is ₹3.4 Cr/MW; Wind capex is ₹6.2 Cr/MW; BESS lithium storage is ₹1.4 Cr/MWh with 10-year life."},
            {"id": "generation.profile", "domain": "operations", "release_level": "hypothesis_backed", "content": "Solar CUF is 24% (daytime only); Wind CUF is 34% with peak generation from 6 PM to 2 AM in Gujarat/Tamil Nadu.", "dependencies": ["capex.costs"]},
            {"id": "tariff.sensitivity", "domain": "economics", "release_level": "hypothesis_backed", "content": "A 100% solar + storage model requires ₹4.10/kWh tariff for 14% IRR; an optimal 60:40 Solar:Wind + 250 MWh BESS model achieves 14% IRR at ₹3.32/kWh.", "dependencies": ["generation.profile"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Competitive bidding at ₹3.32/kWh requires a complementary 60:40 Solar-Wind generation mix, which cuts expensive BESS storage capex by 45% by utilizing evening wind generation."},
            {"id": "recommendation.mix", "domain": "recommendation", "release_level": "synthesis_support", "content": "Bid at ₹3.34/kWh using a 700 MW Solar + 500 MW Wind + 250 MWh BESS configuration to secure 14.5% equity IRR."},
            {"id": "recommendation.procurement", "domain": "recommendation", "release_level": "synthesis_support", "content": "Lock long-term Tier-1 solar module procurement contracts with ALMM domestic exemption clauses."},
            {"id": "recommendation.storage_option", "domain": "recommendation", "release_level": "synthesis_support", "content": "Structure BESS contract with performance degradation warranties and cell replacement guarantees at year 7."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.renewable-bidding", root_label="Determine optimal tariff bid and asset configuration for hybrid tender.",
            branches=[
                {"id": "tender-mandates", "label": "Tender Performance Mandates & Peak Hours", "conclusion": "Requires 85% availability during 6-9 AM and 6-11 PM peak windows."},
                {"id": "generation-resource-mix", "label": "Solar vs Wind Generation Profiles", "conclusion": "Wind generation peaks in evening, perfectly covering the 6-11 PM peak window."},
                {"id": "storage-capex-optimization", "label": "BESS Sizing & Lifecycle Degradation", "conclusion": "Solar-wind complementarity cuts BESS storage requirement from 600 MWh to 250 MWh."}
            ],
            diagnosis={"label": "Solar-Wind Complementarity Storage Reduction", "evidence": ["tender-mandates", "generation-resource-mix", "storage-capex-optimization"], "conclusion": "Target 14% IRR at ₹3.34/kWh is achievable only by leveraging evening wind generation to downsize expensive battery storage by 45%."},
            recommendation={"label": "3-Pillar Bidding & Asset Sizing Plan", "evidence": ["diagnosis"], "conclusion": "Bid ₹3.34/kWh on 60:40 Solar:Wind + 250 MWh BESS, hedge module procurement, and lock battery degradation warranties."},
            routes=[{"id": "generation-first", "sequence": ["tender-mandates", "generation-resource-mix", "storage-capex-optimization", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from tender peak-hour mandates to solar-wind generation curves."}],
            recovery=["Ask candidate what time of day solar vs wind generation peaks.", "Clarify that batteries are the single most expensive capex component per MWh.", "Redirect toward reducing battery size through wind generation."]
        )
    )

    # Case 4: D2C Personal Care
    emit_case(
        school_dir="iimb", slug="04-d2c-personal-care", title="D2C Skincare Omnichannel Expansion", school_tag="IIM-B",
        category="growth_strategy", industry="fmcg_and_cpg", difficulty="intermediate",
        opening_context="Your client is a venture-backed D2C organic skincare brand with ₹120 Cr online revenue. Online Customer Acquisition Cost (CAC) doubled in 18 months, stalling growth.",
        opening_objective="Evaluate offline retail channel expansion (Modern Trade vs General Trade vs Exclusive Brand Outlets) to restore profitable growth.",
        decision_question="Which offline retail channels should the D2C skincare brand prioritize and how should unit economics be managed?",
        primary_metric="Contribution margin after distribution cost and retail store payback", time_horizon="eighteen months",
        core_mechanism="Rising digital CAC (₹850 on a ₹1,100 basket) making pure online scaling unviable, while expanding into Modern Trade supermarkets (supermarket chains) requires high listing fees, 35% retailer margins, and 90-day payment credit.",
        what_wanted_to_test="Omnichannel distribution economics, digital-to-offline brand migration, trade margin structures, and beauty advisor in-store conversion.",
        pivotal_insight="Modern Trade supermarkets generate high volume but destroy margin with 38% distributor/retailer take-rates and slotting fees; opening small footprint Exclusive Brand Outlets (EBOs) in premium malls achieves 28% EBITDA margin by leveraging existing online brand awareness.",
        common_traps=["Assuming traditional general trade mom-and-pop stores are the right starting channel for premium ₹1,100 organic serums.", "Continuing to pump digital performance marketing spend on Facebook/Google.", "Treating offline retail as purely transactional without trained beauty advisors."],
        takeaway_lesson="When a digital-native D2C brand exhausts online CAC efficiency, expanding via high-margin Exclusive Brand Outlets (EBOs) captures brand equity better than margin-squeezing supermarket modern trade.",
        suggested_readings=["knowledge_base/industries/05_fmcg_and_cpg.md", "knowledge_base/case_types/growth_strategy.md", "knowledge_base/methodology/01_preliminary_questions.md"],
        facts=[
            {"id": "d2c.baseline", "domain": "company", "release_level": "broad_context", "content": "Client sells organic serums, moisturizers, and sunscreens (AOV ₹1,100) with 68% gross margin."},
            {"id": "digital.cac", "domain": "financials", "release_level": "sharp_question", "content": "Blended digital CAC rose from ₹420 to ₹850 due to iOS privacy changes and ad bidding competition, erasing first-order profitability."},
            {"id": "modern_trade.terms", "domain": "economics", "release_level": "hypothesis_backed", "content": "Modern Trade supermarket chains demand 38% total margin, ₹5 lakh per SKU slotting fees per chain, and return-to-vendor privileges on unsold stock.", "dependencies": ["digital.cac"]},
            {"id": "ebo.economics", "domain": "economics", "release_level": "hypothesis_backed", "content": "300 sq ft kiosk/EBO in top-tier malls costs ₹2.5L/mo rent, generates ₹12L/mo revenue, and delivers 26% store EBITDA margin with 8-month capex payback.", "dependencies": ["modern_trade.terms"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Online CAC doubled to ₹850, breaking unit economics; Modern Trade demands punitive 38% margins and slotting fees, making mall-based Exclusive Brand Outlets (EBO kiosks) the superior 26% EBITDA growth channel."},
            {"id": "recommendation.ebo_rollout", "domain": "recommendation", "release_level": "synthesis_support", "content": "Open 40 branded mall kiosks and EBOs in top 6 metros with trained beauty consultants."},
            {"id": "recommendation.selective_modern_trade", "domain": "recommendation", "release_level": "synthesis_support", "content": "Enter only specialty beauty retailers (Nykaa/Sephora) with negotiated 25% margins, avoiding generic grocery supermarkets."},
            {"id": "recommendation.omnichannel_crm", "domain": "recommendation", "release_level": "synthesis_support", "content": "Unify offline POS loyalty with the online app to drive omnichannel repeat purchases with zero incremental CAC."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.d2c-omnichannel", root_label="Design profitable offline expansion strategy for D2C skincare brand.",
            branches=[
                {"id": "digital-acquisition-ceiling", "label": "Online CAC Inflation & Unit Margins", "conclusion": "CAC rose to ₹850 on ₹1,100 AOV, destroying online first-order profit."},
                {"id": "offline-channel-economics", "label": "Modern Trade vs EBO vs General Trade", "conclusion": "Modern Trade take-rates are 38% + slotting; EBO kiosks deliver 26% EBITDA and 8-month payback."},
                {"id": "omnichannel-synergy", "label": "Brand Equity & Omnichannel Loyalty", "conclusion": "Online brand recognition drives instant mall footfall without traditional offline advertising."}
            ],
            diagnosis={"label": "EBO Expansion Superiority over Modern Trade", "evidence": ["digital-acquisition-ceiling", "offline-channel-economics", "omnichannel-synergy"], "conclusion": "Online CAC exhaustion makes offline expansion mandatory; mall EBO kiosks capture premium brand equity at 26% EBITDA, avoiding supermarket slotting fee dilution."},
            recommendation={"label": "3-Pillar Omnichannel Strategy", "evidence": ["diagnosis"], "conclusion": "Roll out 40 mall EBO kiosks, partner selectively with specialty beauty chains, and unify omnichannel loyalty data."},
            routes=[{"id": "channel-first", "sequence": ["digital-acquisition-ceiling", "offline-channel-economics", "omnichannel-synergy", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from digital CAC inflation to comparing offline channel margins."}],
            recovery=["Ask candidate to compare economics between a supermarket shelf and a mall kiosk.", "Clarify that general trade grocers do not stock ₹1,100 serums.", "Redirect toward mall EBO kiosk economics and specialty beauty retail."]
        )
    )

    # Case 5: Toll Road Yield
    emit_case(
        school_dir="iimb", slug="05-toll-road-yield", title="Highway Concession Toll Yield", school_tag="IIM-B",
        category="operations", industry="logistics_and_cold_chain", difficulty="intermediate",
        opening_context="Your client is an infrastructure investment trust (InvIT) owning a 140 km 4-lane toll highway concession in Western India. Annual toll collection is 18% below projected revenue despite a 10% increase in regional freight traffic.",
        opening_objective="Diagnose toll revenue underperformance and recommend operational and enforcement measures to recover lost yield.",
        decision_question="Why is toll revenue lagging traffic growth and how can toll leakage be eliminated?",
        primary_metric="Toll Collection Efficiency (%) and Average Plaza Dwell Time", time_horizon="twelve months",
        core_mechanism="Toll avoidance leakage: overloaded multi-axle commercial trucks using an unmonitored 12 km rural state highway bypass road to avoid electronic FASTag toll plazas and weigh-in-motion overload penalties.",
        what_wanted_to_test="Infrastructure asset yield, toll plaza leakage, FASTag electronic toll collection (ETC) compliance, and heavy commercial vehicle route elasticity.",
        pivotal_insight="Traffic is growing, but 30% of high-paying multi-axle commercial trucks divert onto a narrow state bypass road 5 km before the toll plaza to evade the ₹850 toll and statutory axle-overload fines.",
        common_traps=["Assuming toll plaza cashier cash theft (FASTag is 98% digital).", "Blaming macroeconomic economic slowdown in industrial manufacturing.", "Proposing raising toll tariffs which would push even more trucks to the bypass."],
        takeaway_lesson="In infrastructure concessions, traffic demand elasticity is highly sensitive to the availability of un-tolled parallel alternative routes; yield protection requires route enforcement or joint concession integration.",
        suggested_readings=["knowledge_base/industries/01_logistics_and_cold_chain.md", "knowledge_base/case_types/unconventional_and_abstract.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "concession.terms", "domain": "company", "release_level": "broad_context", "content": "Client operates 140 km 4-lane highway with 2 toll plazas charging ₹120 for cars and ₹850 for multi-axle trucks (MAVs)."},
            {"id": "revenue.shortfall", "domain": "financials", "release_level": "sharp_question", "content": "Toll collection is ₹112 Cr vs ₹136 Cr projected; car traffic is on target, but MAV truck volume at toll plazas fell 22%."},
            {"id": "bypass.route", "domain": "operations", "release_level": "hypothesis_backed", "content": "Drone surveys identify 2,400 daily trucks diverting through a 12 km rural state road (SH-42) that bypasses Plaza 1.", "dependencies": ["revenue.shortfall"]},
            {"id": "overload.avoidance", "domain": "regulation", "release_level": "hypothesis_backed", "content": "Truckers bypass the plaza primarily to avoid the automated Weigh-in-Motion (WIM) system that imposes 10x penalty fees for overloading.", "dependencies": ["bypass.route"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Toll revenue shortfall is caused by 2,400 daily multi-axle trucks diverting to a rural state bypass road to avoid the ₹850 toll fee and automated weigh-in-motion overloading penalties."},
            {"id": "recommendation.bypass_toll", "domain": "recommendation", "release_level": "synthesis_support", "content": "Partner with state government to install an automated check-post/toll barrier on the SH-42 rural road under commercial load restrictions."},
            {"id": "recommendation.weigh_regulation", "domain": "recommendation", "release_level": "synthesis_support", "content": "Implement graduated overload fee structures rather than punitive 10x fines to encourage compliance on the main expressway."},
            {"id": "recommendation.fleet_pass", "domain": "recommendation", "release_level": "synthesis_support", "content": "Offer 15% volume discount monthly FASTag passes to major regional fleet logistics operators."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.toll-recovery", root_label="Recover toll revenue yield and halt commercial vehicle bypass diversion.",
            branches=[
                {"id": "traffic-mix-breakdown", "label": "Traffic Volume by Vehicle Category", "conclusion": "Car traffic is on target; high-revenue commercial multi-axle trucks dropped 22%."},
                {"id": "leakage-and-bypass-routes", "label": "Bypass Diversion & Alternate Route Economics", "conclusion": "2,400 daily trucks use un-tolled SH-42 rural bypass to avoid the ₹850 toll."},
                {"id": "enforcement-and-wim", "label": "Weigh-in-Motion Overload Penalty Dynamics", "conclusion": "10x WIM overload penalties strongly incentivize trucks to take the longer rural bypass."}
            ],
            diagnosis={"label": "Overload Penalty Avoidance & Bypass Leakage", "evidence": ["traffic-mix-breakdown", "leakage-and-bypass-routes", "enforcement-and-wim"], "conclusion": "Toll revenue shortfall is driven by commercial trucks diverting to an un-tolled rural bypass road to evade ₹850 toll fees and strict Weigh-in-Motion overloading fines."},
            recommendation={"label": "3-Pillar Toll Yield Recovery Plan", "evidence": ["diagnosis"], "conclusion": "Install check-posts on bypass road, rationalize WIM penalty tiers, and offer monthly commercial fleet FASTag discounts."},
            routes=[{"id": "traffic-first", "sequence": ["traffic-mix-breakdown", "leakage-and-bypass-routes", "enforcement-and-wim", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from vehicle category revenue breakdown to bypass route analysis."}],
            recovery=["Ask candidate which vehicle category accounts for the revenue drop.", "Clarify that overall regional industrial freight is growing.", "Redirect toward alternate routes and truck weigh-in-motion avoidance."]
        )
    )

    # Cases 6-10 for IIMB
    # Case 6: Dairy Supply Chain
    emit_case(
        school_dir="iimb", slug="06-dairy-supply-chain", title="Dairy Cold Chain Milk Sourage", school_tag="IIM-B",
        category="operations", industry="fmcg_and_cpg", difficulty="intermediate",
        opening_context="Your client is a state dairy cooperative in Gujarat processing 4M liters of milk daily. Milk sourage losses during transit from village collection centers to district processing dairies rose from 0.8% to 3.4%, costing ₹45 Cr annually.",
        opening_objective="Diagnose the operational drivers of milk sourage and recommend a cold-chain optimization plan.",
        decision_question="What is causing milk sourage during transit and how can bulk milk chilling and logistics be optimized?",
        primary_metric="Milk Sour Quality Loss (%) and Transit Turnaround Time", time_horizon="six months",
        core_mechanism="Delayed Bulk Milk Chilling (BMC) turnaround and route transit delays exceeding the 4-hour microbial threshold, caused by uncoordinated village collection schedules and power outages at rural chilling centers.",
        what_wanted_to_test="Perishable dairy cold chain, microbial sourage kinetics (temperature vs time to chill to <4°C), route routing optimization, and rural solar backup.",
        pivotal_insight="Raw milk must be chilled to 4°C within 3.5 hours of milking; rural grid power cuts delayed chilling at village centers, while un-routed milk tankers waited 3 hours in queues at processing dairies.",
        common_traps=["Blaming adulteration by dairy farmers without testing microbial acidity (MBRT).", "Recommending purchasing refrigerated insulated tankers for every village (capex prohibitive).", "Assuming processing dairy pasteurizers were malfunctioning."],
        takeaway_lesson="In agricultural perishables, product degradation is a function of time-to-first-chill; decentralized solar-backed chilling at the point of origin is far more effective than expensive refrigerated transport.",
        suggested_readings=["knowledge_base/industries/05_fmcg_and_cpg.md", "knowledge_base/case_types/unconventional_and_abstract.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "dairy.scale", "domain": "company", "release_level": "broad_context", "content": "Cooperative collects milk from 18,000 village societies twice daily, feeding into 120 Bulk Milk Coolers (BMCs)."},
            {"id": "sour.losses", "domain": "financials", "release_level": "sharp_question", "content": "Sour milk write-offs rose to 3.4% of procurement volume, concentrated during summer morning collections."},
            {"id": "bmc.power", "domain": "operations", "release_level": "hypothesis_backed", "content": "40% of rural BMCs face morning power cuts of 2-3 hours; diesel backup generators suffered a 35% breakdown rate.", "dependencies": ["sour.losses"]},
            {"id": "tanker.queue", "domain": "operations", "release_level": "hypothesis_backed", "content": "Insulated road tankers arrive uncoordinated between 10 AM and 12 PM, creating a 3-hour queue in 42°C ambient heat before unloading.", "dependencies": ["bmc.power"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Milk sourage reached 3.4% because rural BMC power cuts delayed initial chilling past the 3.5-hour threshold, compounded by 3-hour tanker unloading queues at central dairies."},
            {"id": "recommendation.solar_bmc", "domain": "recommendation", "release_level": "synthesis_support", "content": "Install rooftop solar with thermal ice-bank storage at all 120 rural BMC centers for instant off-grid chilling."},
            {"id": "recommendation.tanker_slotting", "domain": "recommendation", "release_level": "synthesis_support", "content": "Implement GPS-based tanker dispatch appointment slots to eliminate unloading bottlenecks at central processing plants."},
            {"id": "recommendation.farmer_incentive", "domain": "recommendation", "release_level": "synthesis_support", "content": "Introduce MBRT quality testing premiums paying farmers ₹1.5/liter extra for milk chilled within 90 minutes."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.dairy-sour-loss", root_label="Reduce milk sourage losses from 3.4% to below 0.8%.",
            branches=[
                {"id": "village-chilling-operations", "label": "Village Chilling Time & Rural Power Outages", "conclusion": "BMCs delayed chilling past 3.5 hrs due to 2-3 hr morning rural power outages."},
                {"id": "tanker-logistics-and-queuing", "label": "Tanker Routing & Plant Unloading Queues", "conclusion": "Unscheduled tanker arrivals created 3-hour holding queues in extreme ambient heat."},
                {"id": "farmer-milking-practices", "label": "Farmgate Hygiene & Collection Timings", "conclusion": "Farmer hygiene is standard; failure occurs entirely in post-milking chilling logistics."}
            ],
            diagnosis={"label": "Delayed Initial Chilling & Central Plant Queuing", "evidence": ["village-chilling-operations", "tanker-logistics-and-queuing", "farmer-milking-practices"], "conclusion": "Sourage is driven by delayed initial chilling at village BMCs due to power cuts, exacerbated by 3-hour tanker unloading queues at central dairies."},
            recommendation={"label": "3-Pillar Cold Chain Modernization", "evidence": ["diagnosis"], "conclusion": "Deploy solar thermal BMCs, enforce digital tanker arrival slotting, and pay farmer quality premiums."},
            routes=[{"id": "logistics-first", "sequence": ["village-chilling-operations", "tanker-logistics-and-queuing", "farmer-milking-practices", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate through time-to-chill kinetics across the supply chain."}],
            recovery=["Ask candidate how long raw milk can stay un-chilled before souring.", "Clarify that insulated tankers do not actively chill milk (they only maintain temperature).", "Redirect toward village chilling center power availability and plant queuing."]
        )
    )

    # Case 7: Cement Distribution
    emit_case(
        school_dir="iimb", slug="07-cement-distribution", title="Cement Multimodal Logistics", school_tag="IIM-B",
        category="operations", industry="heavy_manufacturing_and_steel", difficulty="intermediate",
        opening_context="Your client is a leading cement producer in Southern India producing 15M MT annually. Logistics costs represent 32% of total delivered cost, severely eroding margins against northern competitors.",
        opening_objective="Design a multimodal logistics network (rail, road, and coastal shipping) to reduce freight cost per bag by 15%.",
        decision_question="How should cement distribution be optimized across road, rail, and coastal shipping to reduce logistics spend?",
        primary_metric="Freight Cost Per Metric Ton (₹/MT)", time_horizon="twelve months",
        core_mechanism="Over-reliance on direct road trucking (>60% share) for distances exceeding 400 km due to rail wagon shortages, while coastal shipping remains un-utilized despite coastal plant and warehouse locations.",
        what_wanted_to_test="Heavy commodity freight economics, modal cost curves (road vs rail vs coastal shipping), private freight terminal (PFT) capex, and bulk vs bagged handling.",
        pivotal_insight="Coastal shipping from Andhra to Tamil Nadu costs ₹450/MT vs ₹1,850/MT by road; investing in coastal bagging terminals unlocks 65% freight savings for coastal consumption markets.",
        common_traps=["Assuming fuel diesel surcharges are the only driver of freight cost.", "Building road trucking fleets on company balance sheet.", "Ignoring railway rake turnaround detention penalties."],
        takeaway_lesson="In low-value high-weight commodities (cement, steel, coal), modal shift to rail and coastal shipping creates insurmountable cost advantages over direct road transport for distances >300 km.",
        suggested_readings=["knowledge_base/industries/14_heavy_manufacturing_and_steel.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/02_issue_tree_structuring.md"],
        facts=[
            {"id": "production.footprint", "domain": "company", "release_level": "broad_context", "content": "Client operates 3 integrated plants in Andhra Pradesh producing 15M MT cement annually."},
            {"id": "logistics.spend", "domain": "financials", "release_level": "sharp_question", "content": "Total logistics spend is ₹2,100 Cr (₹1,400/MT); road transport accounts for 62% of dispatches."},
            {"id": "modal.costs", "domain": "economics", "release_level": "hypothesis_backed", "content": "Road freight is ₹3.2/MT-km; Rail is ₹1.4/MT-km; Coastal shipping is ₹0.6/MT-km for long-haul routes.", "dependencies": ["logistics.spend"]},
            {"id": "terminal.bottleneck", "domain": "operations", "release_level": "hypothesis_backed", "content": "Coastal plants are 25 km from deep-water ports, but destination markets in Kerala and Tamil Nadu lack bulk cement terminals.", "dependencies": ["modal.costs"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Logistics cost is uncompetitive because 62% of cement moves by expensive road trucks (₹3.2/MT-km); shifting coastal demand (4M MT) to sea shipping (₹0.6/MT-km) reduces freight cost by ₹180 Cr annually."},
            {"id": "recommendation.coastal", "domain": "recommendation", "release_level": "synthesis_support", "content": "Charter 2 coastal bulk cement vessels and build automated silo bagging terminals at Cochin and Tuticorin ports."},
            {"id": "recommendation.rail_siding", "domain": "recommendation", "release_level": "synthesis_support", "content": "Procure 6 private freight railway rakes under Indian Railways GPWIS scheme to secure dedicated wagon availability."},
            {"id": "recommendation.dynamic_dispatch", "domain": "recommendation", "release_level": "synthesis_support", "content": "Deploy AI freight optimization engine to route orders dynamically based on plant lead distance and real-time modal costs."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.cement-freight", root_label="Reduce cement distribution logistics cost per MT by 15%.",
            branches=[
                {"id": "modal-share-split", "label": "Current Modal Share (Road vs Rail vs Sea)", "conclusion": "62% is moved by road (₹3.2/MT-km), driving high freight costs on >400 km hauls."},
                {"id": "modal-cost-benchmarks", "label": "Freight Cost per Ton-Km Comparison", "conclusion": "Coastal shipping is ₹0.6/MT-km (80% cheaper than road) for coastal markets."},
                {"id": "terminal-infrastructure", "label": "Port Handling & Destination Bagging Silos", "conclusion": "Lack of bulk bagging silos at destination ports currently blocks sea transit."}
            ],
            diagnosis={"label": "Road Over-Reliance & Unutilized Coastal Waterways", "evidence": ["modal-share-split", "modal-cost-benchmarks", "terminal-infrastructure"], "conclusion": "Distribution spend is excessive because 62% of volume travels by expensive road; building destination port bagging silos enables an 80% cheaper coastal shipping modal shift."},
            recommendation={"label": "3-Pillar Multimodal Logistics Strategy", "evidence": ["diagnosis"], "conclusion": "Deploy coastal shipping to Kerala/Tamil Nadu, invest in GPWIS private rail rakes, and implement dynamic AI dispatch routing."},
            routes=[{"id": "modal-first", "sequence": ["modal-share-split", "modal-cost-benchmarks", "terminal-infrastructure", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate to compare cost per ton-km across transport modes."}],
            recovery=["Ask candidate to compare freight cost per ton-km across road, rail, and sea.", "Clarify that the manufacturing plants are located near the eastern coastline.", "Redirect toward coastal shipping and destination port bagging terminals."]
        )
    )

    # Case 8: Agritech Platform
    emit_case(
        school_dir="iimb", slug="08-agritech-platform", title="Farm-to-Fork Agritech Wastage", school_tag="IIM-B",
        category="growth_strategy", industry="ecommerce_and_marketplaces", difficulty="intermediate",
        opening_context="Your client is a B2B farm-to-retail agritech platform sourcing fresh vegetables from 10,000 farmers and supplying 4,000 urban kirana stores. Gross margin is negative (-6%) due to high post-harvest wastage.",
        opening_objective="Diagnose post-harvest vegetable wastage and redesign the collection and sorting supply chain to achieve positive gross margins.",
        decision_question="Why is post-harvest vegetable wastage eroding agritech margins and how can farmgate sorting and cold supply chain be restructured?",
        primary_metric="Post-Harvest Wastage (%) and Fulfillment Contribution Margin", time_horizon="twelve months",
        core_mechanism="Un-graded bulk farmgate purchasing resulting in 22% spoilage at urban fulfillment centers, compounded by ambient temperature truck transport during 14-hour transit.",
        what_wanted_to_test="Agritech supply chain economics, farmgate grading vs central sorting, cold chain handling, and secondary market clearance channels.",
        pivotal_insight="Grading vegetables at village collection centers (rejecting Grade-C at farmgate for local cattle feed) eliminates 80% of urban fulfillment center dumping and reduces freight weight by 25%.",
        common_traps=["Assuming farmers are intentionally supplying rotten produce.", "Blaming kirana store retailers for rejecting deliveries.", "Purchasing fully refrigerated reefer trucks for all rural routes."],
        takeaway_lesson="In fresh farm produce distribution, grading and sorting must occur at the point of harvest; transporting un-graded bulk crops transports waste and multiplies freight costs.",
        suggested_readings=["knowledge_base/industries/02_ecommerce_and_marketplaces.md", "knowledge_base/case_types/growth_strategy.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "platform.volume", "domain": "company", "release_level": "broad_context", "content": "Platform handles 400 MT of fresh tomatoes, potatoes, onions, and leafy greens daily across 4 metros."},
            {"id": "wastage.rate", "domain": "financials", "release_level": "sharp_question", "content": "Total produce wastage is 22.5% of purchased weight, destroying ₹14 Cr in gross margin monthly."},
            {"id": "sorting.location", "domain": "operations", "release_level": "hypothesis_backed", "content": "Vegetables are bought in un-graded bulk lots at farmgate and sorted only upon arrival at city distribution centers 14 hours later.", "dependencies": ["wastage.rate"]},
            {"id": "grading.impact", "domain": "operations", "release_level": "hypothesis_backed", "content": "Testing computer-vision grading tables at village collection centers reduced transit freight weight by 24% and cut urban DC wastage to 4.2%.", "dependencies": ["sorting.location"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Wastage is 22.5% because un-graded bulk produce is transported 14 hours in ambient heat before sorting in cities; grading at village centers cuts freight cost by 24% and slashes urban wastage to 4%."},
            {"id": "recommendation.farmgate_grading", "domain": "recommendation", "release_level": "synthesis_support", "content": "Deploy standardized digital grading and optical sorting booths at all village collection centers."},
            {"id": "recommendation.secondary_channel", "domain": "recommendation", "release_level": "synthesis_support", "content": "Sell Grade-B produce to institutional food processors (ketchup/chips) and Grade-C to cattle feed directly at farmgate."},
            {"id": "recommendation.crate_logistics", "domain": "recommendation", "release_level": "synthesis_support", "content": "Replace loose gunny bags with ventilated plastic foldable crates to eliminate transit pressure bruising."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.agritech-wastage", root_label="Reduce fresh produce wastage and achieve positive gross margin.",
            branches=[
                {"id": "wastage-point-of-origin", "label": "Wastage Points: Farmgate vs Transit vs DC", "conclusion": "Bulk of wastage occurs at central urban DCs during delayed sorting."},
                {"id": "farmgate-grading-economics", "label": "Village Level Grading & Weight Elimination", "conclusion": "Sorting at village centers eliminates 24% dead weight from transit freight."},
                {"id": "packaging-and-transit-bruising", "label": "Gunny Bags vs Ventilated Crates", "conclusion": "Gunny bags cause 12% transit crushing in heavy vegetables."}
            ],
            diagnosis={"label": "Un-Graded Bulk Transport & Transit Bruising", "evidence": ["wastage-point-of-origin", "farmgate-grading-economics", "packaging-and-transit-bruising"], "conclusion": "Gross margin is negative because un-graded bulk produce is transported in gunny bags, generating 22.5% wastage and paying freight on unusable Grade-C produce."},
            recommendation={"label": "3-Pillar Fresh Supply Chain Optimization", "evidence": ["diagnosis"], "conclusion": "Implement farmgate digital grading, monetize Grade-B/C locally, and transition to ventilated plastic crates."},
            routes=[{"id": "wastage-first", "sequence": ["wastage-point-of-origin", "farmgate-grading-economics", "packaging-and-transit-bruising", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from wastage breakdown to farmgate grading feasibility."}],
            recovery=["Ask candidate where vegetables are currently sorted in the supply chain.", "Clarify that kirana stores demand high-grade fresh produce.", "Redirect inquiry toward village collection center sorting and crate packaging."]
        )
    )

    # Case 9: Specialty Chemicals
    emit_case(
        school_dir="iimb", slug="09-specialty-chemicals", title="Agrochem Backward Integration M&A", school_tag="IIM-B",
        category="mergers_and_acquisitions", industry="heavy_manufacturing_and_steel", difficulty="advanced",
        opening_context="Your client is a leading Indian specialty agrochemical formulation exporter ($400M revenue). Severe Chinese supply chain shutdowns of key starting materials (KSMs) caused plant shutdowns and customer delivery defaults.",
        opening_objective="Evaluate acquiring a domestic continuous-flow chemical synthesis target vs long-term contract manufacturing to secure raw material sovereignty.",
        decision_question="Should the agrochem exporter acquire the domestic KSM target or pursue multi-vendor contracts?",
        primary_metric="Value creation versus standalone, supply reliability, and payback", time_horizon="three years",
        core_mechanism="Supply security vs environmental regulatory compliance risk. Acquiring the target secures 80% of critical intermediate KSM requirements, but the target's manufacturing plant requires ₹65 Cr in effluent treatment (ETP) capex to meet zero-liquid-discharge (ZLD) norms.",
        what_wanted_to_test="Specialty chemical value chain, backward integration economics, environmental pollution control capex, and China+1 supply security.",
        pivotal_insight="The acquisition is highly strategic for supply sovereignty, but the buyer must haircut the purchase price to account for ₹65 Cr in mandatory Zero Liquid Discharge (ZLD) pollution capex required by environmental regulators.",
        common_traps=["Ignoring environmental pollution control compliance in chemical manufacturing.", "Assuming global spot chemical prices will remain at peak historical crisis levels.", "Failing to retain the target's key chemical synthesis process patents and R&D chemists."],
        takeaway_lesson="In chemical M&A, backward integration provides essential supply sovereignty, but valuation must strictly deduct regulatory environmental remediation capex (ETP/ZLD) before signing.",
        suggested_readings=["knowledge_base/industries/14_heavy_manufacturing_and_steel.md", "knowledge_base/case_types/mergers_and_acquisitions.md", "knowledge_base/methodology/04_data_gathering_and_notes.md"],
        facts=[
            {"id": "client.exposure", "domain": "company", "release_level": "broad_context", "content": "Client imports 72% of active ingredient KSM intermediates from single-source Chinese suppliers."},
            {"id": "target.profile", "domain": "company", "release_level": "sharp_question", "content": "Target is a Gujarat-based chemical synthesis company producing 3 critical KSM intermediates with 45% spare capacity."},
            {"id": "etp.compliance", "domain": "regulation", "release_level": "hypothesis_backed", "content": "State Pollution Control Board issued a conditional notice requiring ₹65 Cr investment in Zero Liquid Discharge (ZLD) effluent treatment within 12 months.", "dependencies": ["target.profile"]},
            {"id": "synergy.valuation", "domain": "financials", "release_level": "hypothesis_backed", "content": "Backward integration saves $22M/year in import duties and freight, but target asking price of $80M does not account for the ₹65 Cr ($8M) ZLD capex.", "dependencies": ["etp.compliance"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Acquisition creates $22M annual synergy by securing captive KSM supply, but buyer must negotiate an $8M purchase price deduction to fund mandatory Zero Liquid Discharge environmental compliance capex."},
            {"id": "recommendation.price_adjustment", "domain": "recommendation", "release_level": "synthesis_support", "content": "Proceed with acquisition, adjusting bid price from $80M to $72M to fund the mandatory ₹65 Cr ZLD effluent treatment plant."},
            {"id": "recommendation.continuous_flow", "domain": "recommendation", "release_level": "synthesis_support", "content": "Upgrade batch synthesis lines to automated continuous-flow chemistry to increase yield by 18%."},
            {"id": "recommendation.rnd_retention", "domain": "recommendation", "release_level": "synthesis_support", "content": "Structure 3-year retention bonuses and patent royalties for target chemical process scientists."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.agrochem-mna", root_label="Evaluate acquisition of domestic KSM chemical intermediate manufacturer.",
            branches=[
                {"id": "supply-chain-vulnerability", "label": "Chinese Import Exposure & Plant Disruptions", "conclusion": "72% import reliance creates acute production disruption risk."},
                {"id": "target-technical-capability", "label": "Technical Fit & Synthesis Capabilities", "conclusion": "Target covers 3 critical KSMs with 45% spare capacity."},
                {"id": "environmental-compliance-capex", "label": "Pollution Control (ZLD) Compliance & Valuation", "conclusion": "Target requires ₹65 Cr ($8M) in mandatory ZLD capex, which must be deducted from purchase price."}
            ],
            diagnosis={"label": "Strategic Backward Integration with Environmental Capex Haircut", "evidence": ["supply-chain-vulnerability", "target-technical-capability", "environmental-compliance-capex"], "conclusion": "Acquisition is essential for supply security ($22M savings/yr) but requires an $8M price haircut to fund mandatory Zero Liquid Discharge environmental upgrades."},
            recommendation={"label": "3-Pillar M&A Execution Terms", "evidence": ["diagnosis"], "conclusion": "Deduct $8M for ZLD capex from purchase price, upgrade to continuous flow synthesis, and retain key R&D patent chemists."},
            routes=[{"id": "strategic-first", "sequence": ["supply-chain-vulnerability", "target-technical-capability", "environmental-compliance-capex", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from supply disruption risk to environmental regulatory due diligence."}],
            recovery=["Ask candidate what regulatory risks exist in chemical manufacturing plants.", "Clarify that the target has strong chemical synthesis know-how.", "Redirect toward environmental pollution notices and ZLD capital expenditure."]
        )
    )

    # Case 10: Tier-2 Cinema Multiplex
    emit_case(
        school_dir="iimb", slug="10-tier2-cinema-multiplex", title="Tier-2 Cinema Multiplex Revenue", school_tag="IIM-B",
        category="profitability", industry="telecom_and_media", difficulty="intermediate",
        opening_context="Your client is a major Indian multiplex cinema operator with 600 screens. Revenue Per Patron (RPP) in Tier-2 city multiplexes is 35% below metros, and weekday occupancy averages only 18%.",
        opening_objective="Diagnose low Tier-2 multiplex profitability and recommend dynamic F&B pricing and alternate content monetization.",
        decision_question="How can the cinema operator boost weekday occupancy and food & beverage spend in Tier-2 markets?",
        primary_metric="Revenue Per Patron (RPP) and Weekday Occupancy (%)", time_horizon="twelve months",
        core_mechanism="Metro-style pricing copy-paste. Operator priced popcorn/colas at metro rates (₹450/combo), leading Tier-2 patrons to buy movie tickets but completely boycott concession stands, while relying 100% on Bollywood theatrical releases for weekday footfall.",
        what_wanted_to_test="Entertainment unit economics, cinema F&B concession gross margins (80%+), price elasticity in non-metro markets, and non-theatrical screen monetization (esports, live cricket, regional festivals).",
        pivotal_insight="F&B has an 82% gross margin; lowering popcorn pricing from ₹450 to a localized ₹199 combo lifts concession spend per patron by 140%, while screening live cricket matches on weekdays raises occupancy from 18% to 52%.",
        common_traps=["Slashing ticket prices below distributor minimum revenue share thresholds.", "Assuming Tier-2 audiences only watch pirated movies on smartphones.", "Closing down multiplex screens on weekdays."],
        takeaway_lesson="In experiential entertainment, high concession margins allow aggressive local price tiering to drive volume; under-utilized real estate can be monetized via non-theatrical community events.",
        suggested_readings=["knowledge_base/industries/07_telecom_and_media.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/04_data_gathering_and_notes.md"],
        facts=[
            {"id": "screen.footprint", "domain": "company", "release_level": "broad_context", "content": "Client operates 180 screens across 35 Tier-2 cities (Lucknow, Indore, Coimbatore, Jaipur)."},
            {"id": "rpp.breakdown", "domain": "financials", "release_level": "sharp_question", "content": "Ticket price averages ₹180, but F&B Spend Per Head (SPH) is only ₹42 in Tier-2 (vs ₹135 in metros)."},
            {"id": "fb.pricing", "domain": "pricing", "release_level": "hypothesis_backed", "content": "Popcorn and beverage combos are priced at standard metro rates (₹420-₹550), leading 82% of Tier-2 patrons to skip concessions completely.", "dependencies": ["rpp.breakdown"]},
            {"id": "non_theatrical.demand", "domain": "customers", "release_level": "hypothesis_backed", "content": "Piloting live IPL cricket screenings and regional gaming tournaments on Tuesday/Wednesday evenings achieved 58% seat occupancy.", "dependencies": ["fb.pricing"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Tier-2 multiplexes underperform because metro-level ₹450 F&B pricing causes an 82% concession boycott, while weekday screens sit empty (18% occupancy) due to total reliance on theatrical movie slates."},
            {"id": "recommendation.localized_fb", "domain": "recommendation", "release_level": "synthesis_support", "content": "Introduce localized F&B menu with regional snacks (samosas, chai, regional combos) priced affordably at ₹149-₹199."},
            {"id": "recommendation.event_cinema", "domain": "recommendation", "release_level": "synthesis_support", "content": "Monetize weekday daytime and evening lulls through live sports, corporate training bookings, and gaming events."},
            {"id": "recommendation.subscription", "domain": "recommendation", "release_level": "synthesis_support", "content": "Launch a weekday 'MoviePass' subscription (₹399/month for 4 weekday tickets) to build consistent habituated footfall."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.multiplex-rpp", root_label="Boost Tier-2 multiplex Revenue Per Patron and weekday occupancy.",
            branches=[
                {"id": "concession-spend-elasticity", "label": "F&B Concession Pricing & Conversion Rate", "conclusion": "Metro pricing (₹450) causes 82% of Tier-2 patrons to avoid concession stands."},
                {"id": "weekday-screen-utilization", "label": "Theatrical Content Slates & Weekday Lulls", "conclusion": "Weekday occupancy is only 18% due to exclusive reliance on theatrical movie schedules."},
                {"id": "alternate-content-monetization", "label": "Live Sports, Gaming & Corporate Bookings", "conclusion": "Live sports screenings achieve 58% occupancy on weekday evenings."}
            ],
            diagnosis={"label": "F&B Price Resistance & Weekday Theatrical Lull", "evidence": ["concession-spend-elasticity", "weekday-screen-utilization", "alternate-content-monetization"], "conclusion": "Profitability lags because metro F&B pricing killed concession conversion in Tier-2 and screens sit empty on weekdays without alternate content."},
            recommendation={"label": "3-Pillar Entertainment Yield Strategy", "evidence": ["diagnosis"], "conclusion": "Launch localized ₹149-₹199 F&B combos, screen live sports/gaming on weekdays, and introduce a weekday MoviePass subscription."},
            routes=[{"id": "concession-first", "sequence": ["concession-spend-elasticity", "weekday-screen-utilization", "alternate-content-monetization", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from F&B conversion metrics to weekday screen utilization."}],
            recovery=["Ask candidate what percentage of patrons purchase food at ₹450 per combo.", "Clarify that F&B has an 82% gross margin.", "Redirect toward localized affordable combos and weekday alternate content."]
        )
    )

    print("Successfully generated all 10 IIM Bangalore exemplar cases!")


if __name__ == "__main__":
    generate_all_iimb_cases()
