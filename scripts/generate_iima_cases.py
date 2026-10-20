"""Generator for all 25 IIM Ahmedabad Exemplar Case Packages under corpus/exemplars/iima/."""

from __future__ import annotations
from scripts.generate_exemplars import emit_case, make_standard_tree


def generate_all_iima_cases():
    print("Generating all 25 IIMA exemplar cases...")

    # Case 1: Beer Manufacturer
    emit_case(
        school_dir="iima", slug="01-beer-manufacturer", title="Beer Manufacturer", school_tag="IIM-A",
        category="profitability", industry="food_and_beverage_restaurants", difficulty="foundation",
        opening_context="Your client is a leading domestic beer manufacturer in India. Processing costs have risen significantly above international benchmarks, depressing plant EBITDA margins.",
        opening_objective="Determine why processing costs are higher than competitors and recommend a twelve-month operational turnaround plan.",
        decision_question="Why are processing costs uncompetitive, and what should management do to restore plant margins?",
        primary_metric="processing cost per hectoliter", time_horizon="twelve months",
        core_mechanism="Sub-scale plant machine capacity due to import restrictions. Client operates 30,000 bottle/plant machines at 100% utilization while international competitors utilize 80,000 bottle/plant automated Chinese equipment that is currently blocked under Indian import curbs.",
        what_wanted_to_test="Capacity utilization vs potential scale bottlenecks, value-chain cost decomposition, and navigating regulatory import constraints.",
        pivotal_insight="Actual capacity utilization is 100%, but potential plant capacity is capped at 30k bottles due to regulatory import blocks on Chinese machinery; competitors use 80k bottle automated units.",
        common_traps=["Assuming low worker labor productivity without checking machine capacity limits.", "Proposing unviable short-term domestic R&D to rebuild specialized equipment.", "Blaming raw material inflation when problem is strictly machine scale."],
        takeaway_lesson="When a plant operates at 100% capacity utilization yet has uncompetitive unit processing costs, the root cause is structural machine scale limits, not operational slack.",
        suggested_readings=["knowledge_base/industries/13_food_and_beverage_restaurants.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/02_issue_tree_structuring.md"],
        facts=[
            {"id": "company.operations", "domain": "company", "release_level": "broad_context", "content": "Client operates 3 brewing and bottling plants in India with 3 machines each, totaling 30,000 bottles per plant."},
            {"id": "cost.breakdown", "domain": "financials", "release_level": "sharp_question", "content": "Cost benchmarking shows raw materials, packaging, and distribution are competitive; processing cost per bottle is 45% higher than peers."},
            {"id": "capacity.utilization", "domain": "operations", "release_level": "sharp_question", "content": "Current machine capacity utilization is running at 100% across all shifts."},
            {"id": "benchmark.machines", "domain": "operations", "release_level": "hypothesis_backed", "content": "Global competitors operate automated 50,000 to 80,000 bottle per plant machinery imported from China, producing twice the output per shift.", "dependencies": ["capacity.utilization"]},
            {"id": "regulatory.ban", "domain": "regulation", "release_level": "hypothesis_backed", "content": "The Indian government placed import restrictions on specific Chinese equipment, preventing the client from purchasing identical replacement lines.", "dependencies": ["benchmark.machines"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "High processing cost is caused by sub-scale 30k bottle machines running at 100% utilization under Chinese machinery import bans; solution requires sourcing from alternative German/Japanese vendors or contract manufacturing."},
            {"id": "recommendation.sourcing", "domain": "recommendation", "release_level": "synthesis_support", "content": "Source high-throughput machinery from alternative non-restricted countries with higher capex justified by scale efficiency."},
            {"id": "recommendation.contracting", "domain": "recommendation", "release_level": "synthesis_support", "content": "Explore third-party contract bottling agreements with existing high-capacity breweries."},
            {"id": "recommendation.lobbying", "domain": "recommendation", "release_level": "synthesis_support", "content": "Engage industry associations to lobby for specialized capital goods import exemptions."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.cost-reduction", root_label="Diagnose uncompetitive processing costs and recommend turnaround plan.",
            branches=[
                {"id": "cost-structure", "label": "Value Chain Cost Breakdown", "conclusion": "Processing is the sole cost head exceeding international benchmarks."},
                {"id": "capacity-diagnostics", "label": "Actual vs Potential Capacity", "conclusion": "Actual utilization is 100%; potential capacity per machine is restricted to 30k vs 80k bottles."},
                {"id": "procurement-barriers", "label": "Internal vs External Barriers", "conclusion": "Import restrictions on Chinese machinery prevent direct equipment upgrades."}
            ],
            diagnosis={"label": "Sub-scale Machine Scale under Regulatory Ban", "evidence": ["cost-structure", "capacity-diagnostics", "procurement-barriers"], "conclusion": "Processing cost disadvantage stems from sub-scale 30k machines running at 100% capacity due to regulatory import barriers on Chinese high-speed equipment."},
            recommendation={"label": "3-Pillar Turnaround Plan", "evidence": ["diagnosis"], "conclusion": "Source alternative German/Japanese equipment, secure contract bottling capacity, and petition for capital goods import clearances."},
            routes=[{"id": "value-chain-first", "sequence": ["cost-structure", "capacity-diagnostics", "procurement-barriers", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from value chain breakdown to capacity analysis."}],
            recovery=["Ask candidate to evaluate machine capacity vs actual utilization.", "Clarify that workers are operating at full capacity.", "Redirect inquiry to competitor equipment specifications and import regulations."]
        )
    )

    # Case 2: Diagnostic Center
    emit_case(
        school_dir="iima", slug="02-diagnostic-center", title="Diagnostic Center Network", school_tag="IIM-A",
        category="profitability", industry="pharma_and_healthcare", difficulty="intermediate",
        opening_context="Your client is an established diagnostic center network in Mumbai. Profitability has slipped by 400 bps over the last 18 months despite a 15% increase in total patient footfall.",
        opening_objective="Identify the root cause of margin erosion and recommend strategic corrective measures.",
        decision_question="Why has diagnostic center profitability fallen despite growing patient volume, and how can margins be restored?",
        primary_metric="EBITDA margin", time_horizon="twelve months",
        core_mechanism="Channel mix shift toward physician-referred B2C patients with escalating referral commissions (35-40% payouts) vs direct walk-ins and corporate wellness packages that carry zero commission.",
        what_wanted_to_test="Healthcare revenue cycle dynamics, doctor kickback/referral commission inflation, and customer acquisition channel economics.",
        pivotal_insight="Footfall growth is entirely driven by doctor referrals where physician commission rates increased from 20% to 38% due to intense lab competition, destroying gross margins.",
        common_traps=["Assuming reagent consumable price inflation without checking test gross margins.", "Recommending an immediate ban on doctor referral fees causing patient collapse.", "Failing to segment patient traffic between direct walk-in, institutional B2B, and physician-referred channels."],
        takeaway_lesson="In referral-driven service healthcare, volume growth through intermediary commissions is margin-dilutive if commission take-rates outpace operating scale efficiencies.",
        suggested_readings=["knowledge_base/industries/03_pharma_and_healthcare.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "network.footprint", "domain": "company", "release_level": "broad_context", "content": "Client operates 22 diagnostic centers across Mumbai offering pathology and basic imaging."},
            {"id": "patient.mix", "domain": "customers", "release_level": "sharp_question", "content": "Doctor-referred patients grew from 45% to 70% of total volume; direct walk-ins and corporate contracts declined."},
            {"id": "commission.rates", "domain": "financials", "release_level": "hypothesis_backed", "content": "Physician referral payout commissions escalated from 20% to 38% of test price to defend against aggressive new diagnostic entrants.", "dependencies": ["patient.mix"]},
            {"id": "test.economics", "domain": "economics", "release_level": "hypothesis_backed", "content": "Reagent costs per test are stable at 18%, but after a 38% doctor payout and center overhead, net contribution margin per test fell from 32% to 14%.", "dependencies": ["commission.rates"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Margin erosion is driven by doctor referral commissions jumping from 20% to 38% in response to competitor poaching, while higher-margin direct walk-ins fell."},
            {"id": "recommendation.b2b", "domain": "recommendation", "release_level": "synthesis_support", "content": "Build direct B2B corporate wellness and hospital outsourcing contracts with locked zero-commission pricing."},
            {"id": "recommendation.digital", "domain": "recommendation", "release_level": "synthesis_support", "content": "Launch home sample collection app to capture direct consumer walk-ins with personalized health packages."},
            {"id": "recommendation.specialty", "domain": "recommendation", "release_level": "synthesis_support", "content": "Shift test menu toward high-complexity specialized genomics/oncology tests where doctor referral fees are capped."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.diagnostic-margin", root_label="Restore diagnostic center network EBITDA margin.",
            branches=[
                {"id": "channel-mix", "label": "Patient Acquisition Channels", "conclusion": "Doctor-referred volume grew from 45% to 70% while direct walk-ins dropped."},
                {"id": "cost-to-serve", "label": "Commission & Overhead Economics", "conclusion": "Doctor referral payouts jumped from 20% to 38% due to competitor lab poaching."},
                {"id": "test-portfolio", "label": "Pathology vs Specialized Test Menu", "conclusion": "Routine tests dominate volume but suffer highest commission dilution."}
            ],
            diagnosis={"label": "Referral Commission Inflation", "evidence": ["channel-mix", "cost-to-serve"], "conclusion": "Margin decline is caused by escalating doctor referral commissions (up to 38%) and customer mix shift away from direct walk-ins."},
            recommendation={"label": "3-Pillar Margin Recovery Plan", "evidence": ["diagnosis"], "conclusion": "Scale direct-to-consumer home collection, secure corporate B2B wellness accounts, and expand high-margin specialized test lines."},
            routes=[{"id": "channel-first", "sequence": ["channel-mix", "cost-to-serve", "test-portfolio", "diagnosis", "actions"], "interviewer_behaviour": "Prompt candidate to analyze acquisition channel unit economics."}],
            recovery=["Ask candidate to compare profitability across direct walk-in vs doctor-referred patients.", "Highlight that lab operating costs are stable.", "Redirect toward doctor commission structures and marketing channels."]
        )
    )

    # Case 3: Education Provider
    emit_case(
        school_dir="iima", slug="03-education-provider", title="IIT-JEE Test Prep Institute", school_tag="IIM-A",
        category="profitability", industry="saas_and_b2b_tech", difficulty="intermediate",
        opening_context="Your client is a premier national IIT-JEE coaching institute with 40 centers. Operating profit dropped 28% year-on-year despite record student enrollments.",
        opening_objective="Diagnose the root cause of the profit decline and propose a sustainable faculty model.",
        decision_question="Why did test prep institute profits drop despite record student enrollment, and how should faculty compensation be restructured?",
        primary_metric="Operating profit margin", time_horizon="twelve months",
        core_mechanism="Star faculty poaching war leading to escalating fixed retention bonuses and profit-share guarantees (up to 60% of batch revenue) coupled with high student churn when poached faculty defect to competing online platforms.",
        what_wanted_to_test="Talent asset-heavy economics, key-man revenue concentration, and teacher-student brand attribution.",
        pivotal_insight="Enrollment is strong but student retention and pricing power are tied to individual star faculty who demanded 65% compensation increases under threat of defection to venture-backed edtechs.",
        common_traps=["Blaming digital classroom infrastructure or software capex.", "Proposing across-the-board student tuition hikes in a hyper-competitive coaching hub.", "Assuming physical real estate center leases explain the margin collapse."],
        takeaway_lesson="In human-capital education businesses, relying on celebrity individual talent creates unsustainable margin capture by workers unless the curriculum and brand institutionalize teaching IP.",
        suggested_readings=["knowledge_base/industries/08_saas_and_b2b_tech.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "enrollment.growth", "domain": "commercial", "release_level": "broad_context", "content": "Total student enrollment grew 12% across 40 physical centers in North and West India."},
            {"id": "cost.inflation", "domain": "financials", "release_level": "sharp_question", "content": "Faculty compensation expenses surged 52% YoY, consuming 68% of total student fee revenue compared to historical 42%."},
            {"id": "poaching.threat", "domain": "market", "release_level": "hypothesis_backed", "content": "Venture-funded online edtech players offered star physics and math faculty 2-3x salaries with equity bonuses, forcing client into defensive bidding.", "dependencies": ["cost.inflation"]},
            {"id": "curriculum.structure", "domain": "operations", "release_level": "hypothesis_backed", "content": "Teaching methodology relied on bespoke handwritten notes by star teachers rather than standardized, institutional digital problem sets.", "dependencies": ["poaching.threat"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Profit collapse is driven by faculty payroll surging from 42% to 68% of revenue due to defensive retention bidding against edtechs, caused by lack of institutionalized teaching IP."},
            {"id": "recommendation.ip", "domain": "recommendation", "release_level": "synthesis_support", "content": "Institutionalize master curriculum modules, AI-graded practice problem banks, and recorded masterclasses to decouple brand from individual faculty."},
            {"id": "recommendation.tenure", "domain": "recommendation", "release_level": "synthesis_support", "content": "Restructure compensation into multi-year vesting equity bonuses, non-compete covenants, and co-authorship royalties."},
            {"id": "recommendation.pipeline", "domain": "recommendation", "release_level": "synthesis_support", "content": "Establish internal teacher training academy to train junior faculty on standardized delivery."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.testprep-profit", root_label="Restore test prep institute operating profit margin.",
            branches=[
                {"id": "revenue-and-enrollment", "label": "Tuition Fees & Enrollment Scale", "conclusion": "Enrollment grew 12%, ruling out demand contraction."},
                {"id": "faculty-cost-structure", "label": "Faculty Compensation & Bidding War", "conclusion": "Faculty payroll surged 52% YoY to 68% of revenue due to defensive retention bidding."},
                {"id": "curriculum-ip", "label": "Teaching IP & Dependency on Star Talent", "conclusion": "Brand is over-dependent on individual teachers due to non-standardized curriculum."}
            ],
            diagnosis={"label": "Star Faculty Poaching & Payroll Escalation", "evidence": ["faculty-cost-structure", "curriculum-ip"], "conclusion": "Profit collapsed due to faculty costs surging from 42% to 68% of revenue amid poaching wars, enabled by lack of institutionalized curriculum IP."},
            recommendation={"label": "3-Pillar Talent & IP Transformation", "evidence": ["diagnosis"], "conclusion": "Standardize curriculum IP, introduce vesting retention contracts, and build internal faculty training pipeline."},
            routes=[{"id": "talent-first", "sequence": ["revenue-and-enrollment", "faculty-cost-structure", "curriculum-ip", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate to investigate cost inflation before analyzing teaching IP."}],
            recovery=["Ask candidate to check the single largest line item in operating costs.", "Clarify that student fees and enrollments grew normally.", "Redirect toward faculty salary dynamics and edtech poaching competition."]
        )
    )

    # Case 4: Urban Company
    emit_case(
        school_dir="iima", slug="04-urban-company", title="On-Demand Home Services Platform", school_tag="IIM-A",
        category="profitability", industry="ecommerce_and_marketplaces", difficulty="intermediate",
        opening_context="Your client is a leading on-demand home services platform operating in 15 Indian cities. Unit economics on home cleaning and appliance repair have deteriorated, with partner churn exceeding 45% annually.",
        opening_objective="Identify the root cause of service partner churn and platform margin erosion, and propose a retention strategy.",
        decision_question="Why are service partners churning and how can marketplace take-rates and partner retention be optimized?",
        primary_metric="Partner retention rate and contribution margin per job", time_horizon="twelve months",
        core_mechanism="Off-platform disintermediation and high tool/consumable onboarding debt. Platform charges a 22% commission plus mandatory upfront purchase of expensive branded equipment kits (₹15k); after completing 1-2 platform jobs, customers and technicians exchange phone numbers to transact offline for a 15% discount.",
        what_wanted_to_test="Marketplace leakages, two-sided platform disintermediation, partner unit economics, and service trust guarantees.",
        pivotal_insight="High commission + upfront tool capex creates financial strain on technicians, while repeat customers easily bypass platform fees by booking the technician directly offline via UPI.",
        common_traps=["Assuming customer demand is drying up or that marketing ad spend is too high.", "Recommending penal legal lawsuits against technicians for off-platform bookings.", "Raising commission fees to make up for lost revenue, accelerating partner defection."],
        takeaway_lesson="In local service marketplaces where repeat jobs involve in-person physical interaction, the platform must provide ongoing value (insurance, instant payout, warranty, financing) to prevent direct buyer-seller disintermediation.",
        suggested_readings=["knowledge_base/industries/02_ecommerce_and_marketplaces.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "marketplace.scale", "domain": "company", "release_level": "broad_context", "content": "Platform processes 500,000 monthly bookings across cleaning, beauty, and appliance repairs in 15 metros."},
            {"id": "partner.churn", "domain": "operations", "release_level": "sharp_question", "content": "Annual partner churn is 48%; average technician tenure on platform is only 4.2 months."},
            {"id": "disintermediation.rate", "domain": "customers", "release_level": "hypothesis_backed", "content": "Over 35% of repeat service bookings in cleaning and AC servicing occur directly offline between customer and technician.", "dependencies": ["partner.churn"]},
            {"id": "partner.economics", "domain": "economics", "release_level": "hypothesis_backed", "content": "Technicians pay 22% commission, ₹15,000 upfront for branded kits, and wait 7 days for payouts, making direct offline cash jobs far more lucrative.", "dependencies": ["disintermediation.rate"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Partner churn and margin leakage stem from offline disintermediation driven by heavy 22% commissions and kit debt; platform lacks ongoing repeat-booking stickiness (insurance, instant payout, warranty protection)."},
            {"id": "recommendation.loyalty", "domain": "recommendation", "release_level": "synthesis_support", "content": "Introduce tiered commission structure dropping from 20% on job 1 to 8% on repeat customer bookings with the same technician."},
            {"id": "recommendation.value", "domain": "recommendation", "release_level": "synthesis_support", "content": "Bundle free health insurance, zero-cost kit financing, and instant daily payout for high-retention technicians."},
            {"id": "recommendation.warranty", "domain": "recommendation", "release_level": "synthesis_support", "content": "Offer ₹10,000 damage protection and 30-day rework warranty to customers booking through the platform only."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.home-services-retention", root_label="Fix service partner churn and platform contribution margin.",
            branches=[
                {"id": "partner-lifecycle", "label": "Partner Acquisition & Churn Dynamics", "conclusion": "Churn is 48%, driven by technicians leaving after 4 months."},
                {"id": "disintermediation-leakage", "label": "Off-Platform Transaction Leakage", "conclusion": "35% of repeat bookings happen offline directly between customers and technicians."},
                {"id": "partner-net-earnings", "label": "Take-Rate, Kit Capex & Payout Timing", "conclusion": "22% commission and ₹15k kit cost make offline transactions compelling for partners."}
            ],
            diagnosis={"label": "Platform Disintermediation & High Partner Friction", "evidence": ["partner-lifecycle", "disintermediation-leakage", "partner-net-earnings"], "conclusion": "Technicians and clients defect offline to avoid 22% fees after initial matching, exacerbated by high upfront equipment debt and slow payout cycles."},
            recommendation={"label": "3-Pillar Marketplace Anti-Leakage Strategy", "evidence": ["diagnosis"], "conclusion": "Lower repeat booking commissions, offer technician benefits (insurance, daily payouts), and provide customer warranty protection."},
            routes=[{"id": "churn-first", "sequence": ["partner-lifecycle", "disintermediation-leakage", "partner-net-earnings", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from partner churn to offline booking leakage."}],
            recovery=["Ask candidate what prevents customers and technicians from cutting out the platform after the first meeting.", "Clarify that customer demand exists but bypasses the app.", "Redirect toward partner take-rates and repeat-booking incentives."]
        )
    )

    # Case 5: Home Loan Provider
    emit_case(
        school_dir="iima", slug="05-home-loan-provider", title="Housing Finance NBFC", school_tag="IIM-A",
        category="profitability", industry="banking_and_financial_services", difficulty="intermediate",
        opening_context="Your client is a mid-sized housing finance company (HFC) in South India. Net interest margin (NIM) has compressed from 3.8% to 2.4% over 2 years, accompanied by rising 90+ DPD delinquencies in Tier-2 cities.",
        opening_objective="Diagnose the compression in net interest margin and credit quality, and propose a corrective underwriting strategy.",
        decision_question="Why did HFC net interest margin compress and how should lending channels and underwriting be restructured?",
        primary_metric="Net Interest Margin (NIM) and Gross NPA ratio", time_horizon="eighteen months",
        core_mechanism="Channel escalation of Direct Selling Agent (DSA) broker commissions (from 0.8% to 2.2%) combined with adverse borrower selection from aggressive builder subvention schemes where builders defaulted on construction milestones.",
        what_wanted_to_test="HFC loan originations, broker incentive misalignment, cost of funds vs lending yield, and project construction escrow risk.",
        pivotal_insight="DSA broker originations rose to 75% of disbursements, inflating acquisition costs while brokers routed high-risk, unverified self-employed borrowers to earn 2.2% upfront broker fees.",
        common_traps=["Assuming bank wholesale borrowing cost of funds spiked without checking RBI repo benchmark spreads.", "Blaming macroeconomic real estate crash rather than broker channel adverse selection.", "Proposing exiting home loans entirely to focus on unsecured personal loans."],
        takeaway_lesson="In retail lending, third-party broker channels create adverse selection unless credit underwriting is entirely decentralized from sales incentives and backed by direct field investigation.",
        suggested_readings=["knowledge_base/industries/04_banking_and_financial_services.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "loan.portfolio", "domain": "financials", "release_level": "broad_context", "content": "HFC manages an ₹8,500 Cr loan book with 60% salaried and 40% self-employed borrowers."},
            {"id": "margin.compression", "domain": "financials", "release_level": "sharp_question", "content": "NIM fell from 3.8% to 2.4% due to 140 bps increase in customer acquisition cost and 80 bps rise in credit cost."},
            {"id": "channel.origin", "domain": "operations", "release_level": "hypothesis_backed", "content": "DSA broker originations rose from 35% to 75% of volume; DSA commission jumped from 0.8% to 2.2% of loan value.", "dependencies": ["margin.compression"]},
            {"id": "delinquency.profile", "domain": "risk", "release_level": "hypothesis_backed", "content": "90+ DPD defaults are concentrated in builder-tied subvention projects and unverified cash-income self-employed borrowers sourced via DSAs.", "dependencies": ["channel.origin"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "NIM drop and NPA rise are driven by over-reliance on DSAs (75% of loans) who inflated broker costs to 2.2% and passed high-default self-employed and builder subvention risks."},
            {"id": "recommendation.direct", "domain": "recommendation", "release_level": "synthesis_support", "content": "Scale direct in-house branch sourcing to 60% of volume, cutting broker commission spend."},
            {"id": "recommendation.underwriting", "domain": "recommendation", "release_level": "synthesis_support", "content": "Mandate internal risk verification officers for cash-flow assessment and ban non-escrow builder subvention schemes."},
            {"id": "recommendation.clawback", "domain": "recommendation", "release_level": "synthesis_support", "content": "Implement 18-month broker commission clawbacks on any loan that defaults within the first 24 EMIs."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.hfc-margin", root_label="Restore housing finance company NIM and credit quality.",
            branches=[
                {"id": "yield-and-funds", "label": "Lending Yields vs Cost of Funds", "conclusion": "Spreads remained steady; margin drop is driven by acquisition commissions and credit loss."},
                {"id": "sourcing-channels", "label": "DSA Broker Sourcing vs Direct Branches", "conclusion": "DSA broker share grew to 75% while broker fees surged to 2.2% of loan value."},
                {"id": "underwriting-quality", "label": "Credit Underwriting & Builder Projects", "conclusion": "Defaults clustered in DSA-sourced builder subvention schemes and unverified cash borrowers."}
            ],
            diagnosis={"label": "DSA Channel Escalation & Underwriting Dilution", "evidence": ["sourcing-channels", "underwriting-quality"], "conclusion": "Over-reliance on third-party DSAs led to 2.2% broker cost inflation and adverse credit selection in builder subvention schemes."},
            recommendation={"label": "3-Pillar Lending Channel Turnaround", "evidence": ["diagnosis"], "conclusion": "Expand in-house direct sourcing, enforce broker default clawbacks, and tighten self-employed credit underwriting."},
            routes=[{"id": "channel-first", "sequence": ["yield-and-funds", "sourcing-channels", "underwriting-quality", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate to dissect loan sourcing channels and delinquency patterns."}],
            recovery=["Ask candidate to compare credit performance between branch-sourced and DSA-sourced loans.", "Clarify that wholesale borrowing costs are normal.", "Redirect toward broker fee structures and builder project risk."]
        )
    )

    # Case 6: Port Operator
    emit_case(
        school_dir="iima", slug="06-port-operator", title="Container Port Operator", school_tag="IIM-A",
        category="operations", industry="logistics_and_cold_chain", difficulty="intermediate",
        opening_context="Your client operates a private container terminal at a major western Indian port. Average vessel turnaround time has deteriorated from 18 hours to 34 hours, triggering severe demurrage penalties and shipping line defection.",
        opening_objective="Diagnose the bottleneck causing container berth delays and recommend an operational debottlenecking plan.",
        decision_question="What is causing vessel turnaround time to double at the container terminal, and how can berth productivity be restored?",
        primary_metric="Vessel Turnaround Time (hours) and Crane Moves Per Hour (GMPH)", time_horizon="six months",
        core_mechanism="Container yard stack congestion caused by customs clearance document batching and lack of direct port delivery (DPD) clearance, causing yard crane jockeying (re-handling) to rise from 1.4 to 4.2 moves per loaded container.",
        what_wanted_to_test="Port operational queues, yard stack dwell time vs quay crane productivity, and re-handling ratio bottlenecks.",
        pivotal_insight="Quay cranes operate at high speed, but are forced to halt because the yard is at 95% stack capacity; moving one container requires shifting 3-4 blocking containers due to slow customs clearance.",
        common_traps=["Assuming quay gantry crane mechanical failure or labor strikes at the berth.", "Recommending purchasing expensive new quay cranes that would only worsen yard congestion.", "Blaming vessel arrival bunching without auditing yard inventory dwell time."],
        takeaway_lesson="In intermodal transport terminals, seaside crane speed is governed by landside yard clearance velocity; high yard stack utilization exponentially increases unproductive re-handling moves.",
        suggested_readings=["knowledge_base/industries/01_logistics_and_cold_chain.md", "knowledge_base/case_types/unconventional_and_abstract.md", "knowledge_base/methodology/02_issue_tree_structuring.md"],
        facts=[
            {"id": "port.infrastructure", "domain": "company", "release_level": "broad_context", "content": "Terminal has 2 berths, 6 Super Post-Panamax quay cranes, and an 8,000 TEU container yard."},
            {"id": "crane.metrics", "domain": "operations", "release_level": "sharp_question", "content": "Quay cranes are rated for 30 moves/hr but average only 16 moves/hr due to waiting for yard prime movers."},
            {"id": "yard.utilization", "domain": "operations", "release_level": "hypothesis_backed", "content": "Container yard utilization exceeded 92% (healthy threshold is <70%), causing re-handling moves per container to jump from 1.4 to 4.2.", "dependencies": ["crane.metrics"]},
            {"id": "dwell.time", "domain": "operations", "release_level": "hypothesis_backed", "content": "Average import container dwell time increased from 3.2 days to 7.8 days because customs clearance agents batch physical filings weekly.", "dependencies": ["yard.utilization"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Turnaround time doubled because import dwell time surged to 7.8 days due to batch customs filing, pushing yard density to 92% and forcing 4.2 unproductive re-handling moves per container lift."},
            {"id": "recommendation.dpd", "domain": "recommendation", "release_level": "synthesis_support", "content": "Enforce Direct Port Delivery (DPD) for pre-cleared Tier-1 importers to evacuate containers straight to factory gates."},
            {"id": "recommendation.dwell_tariff", "domain": "recommendation", "release_level": "synthesis_support", "content": "Implement steep progressive demurrage tariffs for containers dwelling beyond 72 hours to incentivize rapid cargo pickup."},
            {"id": "recommendation.digital_gate", "domain": "recommendation", "release_level": "synthesis_support", "content": "Deploy RFID terminal appointment gate system to spread truck arrivals evenly across 24 hours."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.port-turnaround", root_label="Reduce vessel turnaround time from 34 hours to under 18 hours.",
            branches=[
                {"id": "quayside-operations", "label": "Quay Gantry Crane Productivity", "conclusion": "Quay cranes idle waiting for landside trucks due to yard congestion."},
                {"id": "yard-stack-dynamics", "label": "Container Yard Density & Re-Handling", "conclusion": "Yard utilization is 92%, causing 4.2 unproductive re-handling moves per lift."},
                {"id": "gate-and-customs", "label": "Customs Clearance & Truck Evacuation", "conclusion": "Customs paper batching increased import dwell time from 3.2 to 7.8 days."}
            ],
            diagnosis={"label": "Yard Congestion from Customs Dwell Delays", "evidence": ["quayside-operations", "yard-stack-dynamics", "gate-and-customs"], "conclusion": "Vessel turnaround delays are caused by 92% yard stack congestion driven by customs dwell time rising to 7.8 days, creating massive re-handling delays."},
            recommendation={"label": "3-Pillar Landside Debottlenecking Plan", "evidence": ["diagnosis"], "conclusion": "Mandate Direct Port Delivery, implement progressive dwell tariffs, and introduce 24/7 digital gate appointment scheduling."},
            routes=[{"id": "operations-first", "sequence": ["quayside-operations", "yard-stack-dynamics", "gate-and-customs", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from crane idle time to yard dwell dynamics."}],
            recovery=["Ask candidate why quay cranes are operating below rated capacity.", "Clarify that gantry cranes have no mechanical defects.", "Redirect inquiry toward yard stack density, dwell days, and customs evacuation."]
        )
    )

    # Cases 7 to 25 continue below with full definitions
    # Case 7: Water Purifier
    emit_case(
        school_dir="iima", slug="07-water-purifier", title="Water Purifier Manufacturer", school_tag="IIM-A",
        category="profitability", industry="fmcg_and_cpg", difficulty="intermediate",
        opening_context="Your client is an Indian water purifier brand. It launched an IoT subscription rental model (pay ₹499/month) which attracted 100,000 subscribers, but company free cash flow turned deeply negative.",
        opening_objective="Diagnose the cash flow deficit in the rental subscription model and recommend a profitable subscription structure.",
        decision_question="Why did the IoT water purifier subscription model burn cash and how can payback and filter servicing economics be fixed?",
        primary_metric="Subscriber Unit Contribution & Cash Payback Period", time_horizon="twelve months",
        core_mechanism="High upfront manufacturing capex (₹9,000/machine) and high early churn (32% cancel within 6 months) leaving hardware unamortized, coupled with unauthorized third-party counterfeit filter replacement.",
        what_wanted_to_test="Hardware-as-a-Service (HaaS) unit economics, churn amortization hurdles, working capital capex recovery, and consumable lock-in.",
        pivotal_insight="Hardware costs ₹9k to manufacture but subscribers churn after 6 months generating only ₹3k in revenue, while reverse logistics and refurbishing costs destroy residual asset value.",
        common_traps=["Assuming IoT cloud server hosting costs caused the cash drain.", "Blaming marketing customer acquisition spend rather than unrecovered hardware capex from early churn.", "Assuming outright sales model had the same problem as rental subscriptions."],
        takeaway_lesson="Hardware-as-a-Service models collapse if upfront device capex is amortized over long horizons without minimum contract lock-ins or upfront security deposits.",
        suggested_readings=["knowledge_base/industries/05_fmcg_and_cpg.md", "knowledge_base/case_types/pricing_strategy.md", "knowledge_base/methodology/04_data_gathering_and_notes.md"],
        facts=[
            {"id": "subscription.growth", "domain": "commercial", "release_level": "broad_context", "content": "Rental subscriber base reached 100,000 users paying ₹499/month with zero upfront security deposit."},
            {"id": "hardware.capex", "domain": "financials", "release_level": "sharp_question", "content": "Each IoT purifier costs ₹9,000 to manufacture and install, funded entirely by client working capital debt."},
            {"id": "churn.rate", "domain": "customers", "release_level": "hypothesis_backed", "content": "32% of subscribers cancel within 6 months, generating only ₹2,994 against ₹9,000 hardware cost.", "dependencies": ["hardware.capex"]},
            {"id": "refurbish.cost", "domain": "operations", "release_level": "hypothesis_backed", "content": "Retrieved purifiers cost ₹2,500 to de-install, sanitize, and repackage, resulting in net negative asset recovery.", "dependencies": ["churn.rate"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Subscription model burns cash because ₹9k hardware capex requires 18 months to breakeven, but 32% of users churn within 6 months with zero deposit or contract commitment."},
            {"id": "recommendation.deposit", "domain": "recommendation", "release_level": "synthesis_support", "content": "Require a ₹2,500 refundable security deposit and a mandatory 12-month minimum contract lock-in."},
            {"id": "recommendation.iot_lock", "domain": "recommendation", "release_level": "synthesis_support", "content": "Enforce digital DRM on filter cartridges via IoT chips, disabling machine if unauthorized counterfeit filters are inserted."},
            {"id": "recommendation.rent_to_own", "domain": "recommendation", "release_level": "synthesis_support", "content": "Introduce rent-to-own pathway where 24 monthly payments transfer ownership to customer, eliminating reverse logistics."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.purifier-cashflow", root_label="Fix cash flow and unit economics of IoT water purifier subscription.",
            branches=[
                {"id": "capex-and-pricing", "label": "Hardware Capex vs Subscription Pricing", "conclusion": "₹9,000 upfront capex requires 18 months of ₹499 fees to break even."},
                {"id": "subscriber-churn", "label": "Cohort Retention & Lock-in Terms", "conclusion": "32% churn within 6 months without security deposit, leaving ₹6,000 unrecovered capex per churning user."},
                {"id": "reverse-logistics", "label": "Asset Retrieval & Refurbishment Cost", "conclusion": "De-installation and refurbishing costs ₹2,500 per unit, making returns value-destructive."}
            ],
            diagnosis={"label": "Unamortized Hardware Capex from Early Churn", "evidence": ["capex-and-pricing", "subscriber-churn", "reverse-logistics"], "conclusion": "Zero-deposit subscription creates massive cash drain as 32% of subscribers churn before paying off the ₹9k hardware manufacturing capex."},
            recommendation={"label": "3-Pillar HaaS Turnaround Plan", "evidence": ["diagnosis"], "conclusion": "Mandate 12-month lock-in with ₹2,500 security deposit, implement IoT filter DRM, and offer rent-to-own conversion."},
            routes=[{"id": "unit-economics-first", "sequence": ["capex-and-pricing", "subscriber-churn", "reverse-logistics", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate to calculate customer payback period vs average tenure."}],
            recovery=["Ask candidate to calculate months required to recover the ₹9,000 manufacturing cost at ₹499/month.", "Highlight that 32% of users cancel in 6 months.", "Redirect toward contract lock-ins and security deposit requirements."]
        )
    )

    # Case 8: Meal Coupon Company
    emit_case(
        school_dir="iima", slug="08-meal-coupon-co", title="Meal Voucher Digital Transformation", school_tag="IIM-A",
        category="turnaround", industry="fintech_and_payments", difficulty="intermediate",
        opening_context="Your client is a pioneer in corporate tax-exempt paper meal vouchers in India. Regulatory changes mandated complete digitization, and revenue has plummeted 40% as corporate clients switched to digital payment apps.",
        opening_objective="Formulate a digital turnaround strategy to rebuild employer and merchant monetization.",
        decision_question="How should the meal voucher pioneer pivot its business model to compete against modern fintechs?",
        primary_metric="Corporate Client Retention and Net Merchant Revenue", time_horizon="eighteen months",
        core_mechanism="Loss of breakage float revenue and paper coupon printing fees following RBI prepaid payment instrument (PPI) digital mandate, combined with merchant resistance to high 2.5% MDR on standard card rails.",
        what_wanted_to_test="Fintech regulatory disruption, breakage revenue elimination in digital wallets, merchant discount rate (MDR) economics, and B2B corporate employee benefit bundling.",
        pivotal_insight="In paper coupons, 8% of vouchers expired unused (pure profit 'breakage'); digitization eliminated breakage entirely while merchants refused to pay legacy 2.5% processing fees on digital cards.",
        common_traps=["Trying to lobby the central bank to bring back paper meal vouchers.", "Slashing employee benefit card fees to zero without alternative monetization.", "Competing as a generic consumer UPI wallet against Google Pay and PhonePe."],
        takeaway_lesson="When regulatory digitization destroys legacy fee structures (breakage/paper fees), the business must pivot from payment processing to an integrated SaaS employee benefits suite (gym, fuel, telecom, learning).",
        suggested_readings=["knowledge_base/industries/15_fintech_and_payments.md", "knowledge_base/case_types/growth_strategy.md", "knowledge_base/methodology/01_preliminary_questions.md"],
        facts=[
            {"id": "company.legacy", "domain": "company", "release_level": "broad_context", "content": "Client served 4,000 corporate clients with paper meal vouchers accepted at 50,000 grocery and restaurant outlets."},
            {"id": "revenue.drivers", "domain": "financials", "release_level": "sharp_question", "content": "Legacy revenue came from 3 streams: corporate issuance fee (1%), merchant acceptance fee (2.5%), and unredeemed paper breakage (8% of GMV)."},
            {"id": "digital.impact", "domain": "regulation", "release_level": "hypothesis_backed", "content": "RBI digital PPI rules mandated non-expiring digital balances (eliminating breakage) and merchants negotiated MDR down to 1.0%.", "dependencies": ["revenue.drivers"]},
            {"id": "fintech.threat", "domain": "market", "release_level": "sharp_question", "content": "Modern SaaS HR fintechs offer multi-benefit cards covering fuel, phone, books, and medical under a single tax-saving app.", "dependencies": ["digital.impact"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Revenue collapsed because RBI digital mandates eliminated lucrative 8% paper breakage and eroded merchant MDR from 2.5% to 1.0%; client must pivot into an enterprise multi-benefit employee SaaS platform."},
            {"id": "recommendation.saas", "domain": "recommendation", "release_level": "synthesis_support", "content": "Transform into an integrated HR employee benefits SaaS suite charging recurring per-employee-per-month (PEPM) platform fees."},
            {"id": "recommendation.multi_wallet", "domain": "recommendation", "release_level": "synthesis_support", "content": "Expand from meal vouchers to multi-pocket tax allowances (fuel, health, WFH equipment, wellness)."},
            {"id": "recommendation.merchant_network", "domain": "recommendation", "release_level": "synthesis_support", "content": "Build direct merchant partnerships offering corporate employee-exclusive discounts in exchange for 3-5% affiliate marketing fees."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.meal-voucher-pivot", root_label="Rebuild meal voucher business model post-digitization.",
            branches=[
                {"id": "revenue-stream-collapse", "label": "Legacy vs Digital Revenue Streams", "conclusion": "Digitization eliminated 8% breakage and compressed merchant MDR from 2.5% to 1.0%."},
                {"id": "regulatory-mandates", "label": "RBI Prepaid Payment Instrument Rules", "conclusion": "Mandated digital cards with non-expiring balances and interoperability."},
                {"id": "enterprise-benefit-expansion", "label": "B2B HR Suite & Multi-Benefit Wallets", "conclusion": "Corporates want unified tax-saving allowances beyond food."}
            ],
            diagnosis={"label": "Loss of Breakage & MDR Compression", "evidence": ["revenue-stream-collapse", "regulatory-mandates", "enterprise-benefit-expansion"], "conclusion": "The paper-to-digital transition wiped out 8% breakage profit and eroded merchant MDR; survival requires pivoting to a B2B employee benefits SaaS suite."},
            recommendation={"label": "3-Pillar Enterprise Fintech Pivot", "evidence": ["diagnosis"], "conclusion": "Launch multi-benefit tax allowance wallet, charge PEPM enterprise SaaS subscription, and capture merchant affiliate discounts."},
            routes=[{"id": "regulatory-first", "sequence": ["revenue-stream-collapse", "regulatory-mandates", "enterprise-benefit-expansion", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from revenue breakdown to regulatory impact on breakage."}],
            recovery=["Ask candidate what happened to unused paper vouchers vs digital balances.", "Highlight that unredeemed voucher breakage accounted for 50%+ of net profits.", "Redirect toward enterprise employee benefit SaaS monetization."]
        )
    )

    # Case 9: Commercial Bank (SME Credit)
    emit_case(
        school_dir="iima", slug="09-commercial-bank", title="SME Commercial Bank Loan Book", school_tag="IIM-A",
        category="operations", industry="banking_and_financial_services", difficulty="intermediate",
        opening_context="Your client is a mid-sized Indian private commercial bank. Non-performing assets (NPAs) in the textile and engineering SME export loan portfolio surged from 2.8% to 7.4% in twelve months.",
        opening_objective="Diagnose the sudden spike in SME export loan defaults and recommend a loan monitoring and risk containment framework.",
        decision_question="What caused the surge in SME export loan defaults and how can credit risk monitoring be overhauled?",
        primary_metric="Gross NPA Ratio and Early Warning Signal (EWS) Lead Time", time_horizon="twelve months",
        core_mechanism="Working capital cash conversion cycle elongation caused by Red Sea global container shipping freight disruption and delayed export invoice factoring, while bank monitoring relied on lagging annual audited balance sheets instead of live GST/e-way bill data.",
        what_wanted_to_test="Trade finance economics, supply chain working capital cycles, macroeconomic shipping shocks, and live data credit monitoring.",
        pivotal_insight="Exporters have valid buyer orders, but transit delays lengthened working capital cycles from 60 to 140 days; SME cash reserves drained, causing technical default on 90-day bank overdrafts.",
        common_traps=["Assuming borrowers engaged in deliberate promoter fraud or fund siphoning without checking export order books.", "Initiating immediate aggressive asset seizures that liquidate viable businesses facing temporary liquidity delays.", "Blaming currency exchange rate movements when exports are hedged."],
        takeaway_lesson="In export and trade financing, external logistics shocks stretch customer cash conversion cycles; credit underwriting must use real-time GST and freight telemetry rather than static annual financial statements.",
        suggested_readings=["knowledge_base/industries/04_banking_and_financial_services.md", "knowledge_base/case_types/unconventional_and_abstract.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "portfolio.segment", "domain": "financials", "release_level": "broad_context", "content": "SME export portfolio comprises ₹4,200 Cr in working capital lines to garment and precision engineering exporters."},
            {"id": "default.concentration", "domain": "risk", "release_level": "sharp_question", "content": "Defaults are concentrated specifically among European and US export corridors; domestic SME loan NPAs remained stable at 2.1%."},
            {"id": "supplychain.lag", "domain": "operations", "release_level": "hypothesis_backed", "content": "Maritime transit times doubled due to Cape of Good Hope rerouting, extending receivables collection from 60 to 140 days.", "dependencies": ["default.concentration"]},
            {"id": "monitoring.lag", "domain": "operations", "release_level": "hypothesis_backed", "content": "Bank credit officers reviewed borrower health using annual financial statements submitted 6 months after fiscal year-end, missing real-time cash exhaustion.", "dependencies": ["supplychain.lag"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Export loan NPAs spiked because maritime shipping delays stretched exporter cash conversion cycles from 60 to 140 days, causing liquidity defaults that the bank failed to anticipate due to reliance on lagging annual financial audits."},
            {"id": "recommendation.factoring", "domain": "recommendation", "release_level": "synthesis_support", "content": "Provide bridge export invoice factoring and extend temporary working capital tenure from 90 to 150 days for verified shipments."},
            {"id": "recommendation.gst_ews", "domain": "recommendation", "release_level": "synthesis_support", "content": "Integrate live GST return filing and e-way bill APIs into an Early Warning System to detect cash-flow strain 60 days in advance."},
            {"id": "recommendation.restructuring", "domain": "recommendation", "release_level": "synthesis_support", "content": "Restructure viable export loans before 90 DPD categorization to prevent unnecessary provisioning."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.sme-loan-npa", root_label="Contain SME export loan defaults and overhaul risk monitoring.",
            branches=[
                {"id": "default-segmentation", "label": "Portfolio Segmentation & Export Corridors", "conclusion": "Defaults are exclusive to Western export corridors; domestic SMEs are healthy."},
                {"id": "working-capital-cycle", "label": "Receivables & Freight Transit Disruption", "conclusion": "Maritime shipping rerouting stretched cash cycles from 60 to 140 days."},
                {"id": "bank-monitoring-systems", "label": "Credit Monitoring & Data Velocity", "conclusion": "Annual audit reviews lagged real-time liquidity distress by 6 months."}
            ],
            diagnosis={"label": "Supply Chain Transit Shock & Lagging Credit Monitoring", "evidence": ["default-segmentation", "working-capital-cycle", "bank-monitoring-systems"], "conclusion": "NPA surge is driven by global freight delays extending cash cycles to 140 days, which the bank's static audit systems failed to detect in real time."},
            recommendation={"label": "3-Pillar Trade Credit Turnaround", "evidence": ["diagnosis"], "conclusion": "Offer bridge invoice factoring, deploy live GST/e-way bill early warning alerts, and proactively restructure viable accounts."},
            routes=[{"id": "risk-first", "sequence": ["default-segmentation", "working-capital-cycle", "bank-monitoring-systems", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from geographic default segmentation to working capital cash cycles."}],
            recovery=["Ask candidate to compare performance of export SMEs vs domestic SMEs.", "Clarify that foreign buyers have not cancelled orders.", "Redirect inquiry toward transit shipping lead times and bank early warning systems."]
        )
    )

    # Case 10: Battery Manufacturer
    emit_case(
        school_dir="iima", slug="10-battery-manufacturer", title="Lead-Acid Battery Manufacturer", school_tag="IIM-A",
        category="profitability", industry="heavy_manufacturing_and_steel", difficulty="intermediate",
        opening_context="Your client is a leading Indian lead-acid automotive battery manufacturer. Gross profit margins fell by 600 bps over two years despite steady vehicle OEM battery sales volume.",
        opening_objective="Diagnose the margin compression in automotive battery production and propose raw material sourcing reforms.",
        decision_question="Why did battery gross margins collapse and how should recycled lead procurement be restructured?",
        primary_metric="Gross margin per battery unit", time_horizon="twelve months",
        core_mechanism="Raw material procurement cost surge caused by unorganized lead scrap recycling middlemen holding back scrap supply, forcing the client to purchase expensive virgin LME-indexed imported lead.",
        what_wanted_to_test="Circular economy supply chain, scrap metal recycling economics, commodity indexing vs unorganized scrap channels.",
        pivotal_insight="Recycled secondary lead is 25% cheaper than virgin imported lead, but unorganized scrap aggregators cartelized supply; client's reverse logistics buy-back program only captured 20% of spent batteries.",
        common_traps=["Assuming vehicle OEM price renegotiation caused the margin loss.", "Blaming sulfuric acid chemical price spikes without checking lead's 70% share of battery cost.", "Proposing pivoting immediately to lithium-ion cell manufacturing."],
        takeaway_lesson="In commodity manufacturing with heavy raw material cost concentration, building a closed-loop customer recycling network protects margins from volatile open-market scrap cartels.",
        suggested_readings=["knowledge_base/industries/14_heavy_manufacturing_and_steel.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "cost.composition", "domain": "financials", "release_level": "broad_context", "content": "Lead raw material accounts for 68% of total battery manufacturing cost."},
            {"id": "sourcing.split", "domain": "operations", "release_level": "sharp_question", "content": "Share of expensive virgin imported lead rose from 20% to 55%, while low-cost recycled scrap fell from 80% to 45%."},
            {"id": "scrap.cartel", "domain": "market", "release_level": "hypothesis_backed", "content": "Unorganized scrap dealers formed regional syndicates to hoard spent batteries, driving scrap prices close to virgin LME levels.", "dependencies": ["sourcing.split"]},
            {"id": "retail.buyback", "domain": "operations", "release_level": "hypothesis_backed", "content": "Client's retail dealer exchange discount (₹500/old battery) was too low to incentivize consumers, allowing scrap hoarders to buy spent batteries for cash.", "dependencies": ["scrap.cartel"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Gross margin fell 600 bps because client had to buy expensive virgin lead (55% share) as unorganized scrap syndicates hoarded secondary lead, enabled by an ineffective dealer buyback program."},
            {"id": "recommendation.buyback", "domain": "recommendation", "release_level": "synthesis_support", "content": "Increase dealer old battery exchange discount to ₹1,200 and mandate 1-for-1 return quotas on retail distributors."},
            {"id": "recommendation.smelting", "domain": "recommendation", "release_level": "synthesis_support", "content": "Establish direct captive secondary lead smelting and refining joint ventures to bypass unorganized scrap traders."},
            {"id": "recommendation.b2b_closed_loop", "domain": "recommendation", "release_level": "synthesis_support", "content": "Sign direct scrap collection contracts with commercial fleet operators and telecom tower companies."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.battery-margin", root_label="Restore lead-acid battery manufacturing gross margins.",
            branches=[
                {"id": "bill-of-materials", "label": "BOM Cost Breakdown (Lead vs Other Inputs)", "conclusion": "Lead constitutes 68% of cost; other inputs are stable."},
                {"id": "lead-sourcing-mix", "label": "Virgin Imported vs Recycled Secondary Lead", "conclusion": "Virgin lead share surged from 20% to 55% as recycled scrap became unavailable."},
                {"id": "scrap-supply-chain", "label": "Scrap Cartels & Dealer Buyback Mechanics", "conclusion": "Dealers hoarded scrap because client's ₹500 retail trade-in discount was uncompetitive."}
            ],
            diagnosis={"label": "Scrap Hoarding & Virgin Lead Sourcing Surge", "evidence": ["bill-of-materials", "lead-sourcing-mix", "scrap-supply-chain"], "conclusion": "Margin collapse was driven by switching to expensive virgin lead due to scrap cartel hoarding, caused by an uncompetitive consumer battery exchange scheme."},
            recommendation={"label": "3-Pillar Circular Sourcing Strategy", "evidence": ["diagnosis"], "conclusion": "Raise retail exchange discounts, build captive secondary smelting capacity, and secure B2B fleet closed-loop contracts."},
            routes=[{"id": "sourcing-first", "sequence": ["bill-of-materials", "lead-sourcing-mix", "scrap-supply-chain", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from BOM cost analysis to virgin vs recycled sourcing mix."}],
            recovery=["Ask candidate what percentage of battery manufacturing cost is raw lead.", "Clarify that battery selling prices and sales volume are steady.", "Redirect inquiry toward virgin vs secondary recycled lead procurement."]
        )
    )

    # Cases 11 to 25 continued
    # Case 11: Zoomcar Mobility
    emit_case(
        school_dir="iima", slug="11-zoomcar-mobility", title="Self-Drive Car Rental Platform", school_tag="IIM-A",
        category="profitability", industry="logistics_and_cold_chain", difficulty="intermediate",
        opening_context="Your client is an Indian self-drive car sharing marketplace with 8,000 host vehicles. Fleet EBITDA margin turned negative (-12%) despite 90% weekend booking occupancy.",
        opening_objective="Diagnose the drivers of negative fleet EBITDA and recommend a vehicle maintenance and asset protection strategy.",
        decision_question="Why is the car rental marketplace losing money despite high booking occupancy?",
        primary_metric="Fleet EBITDA margin and Average Repair Downtime (days)", time_horizon="twelve months",
        core_mechanism="Severe vehicle accident repair downtime (averaging 24 days per incident) and unrecovered damage costs caused by reckless customer driving and delayed insurance surveyor approvals.",
        what_wanted_to_test="Asset utilization economics, damage repair cycle time, customer risk scoring, and insurance claim friction.",
        pivotal_insight="High booking demand mask a fatal utilization leak: 22% of the fleet is stranded in partner garages waiting for accident repairs and insurance sign-offs, earning zero revenue while incurring lease costs.",
        common_traps=["Assuming customer demand or trip pricing is too low.", "Blaming vehicle depreciation accounting rules.", "Proposing buying all cars onto balance sheet."],
        takeaway_lesson="In peer-to-peer asset sharing, vehicle downtime from maintenance and unrecovered accident damage erodes fleet profitability faster than high utilization can generate revenue.",
        suggested_readings=["knowledge_base/industries/01_logistics_and_cold_chain.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "fleet.size", "domain": "company", "release_level": "broad_context", "content": "Platform operates 8,000 peer-to-peer host cars in 10 metro cities."},
            {"id": "occupancy.metrics", "domain": "operations", "release_level": "sharp_question", "content": "Weekend booking demand is 92%, but total available fleet utilization is only 58%."},
            {"id": "downtime.cause", "domain": "operations", "release_level": "hypothesis_backed", "content": "Over 1,750 vehicles (22% of fleet) are grounded in local workshops for accident repairs, averaging 24 days downtime per incident.", "dependencies": ["occupancy.metrics"]},
            {"id": "insurance.gap", "domain": "financials", "release_level": "hypothesis_backed", "content": "Insurance claim deductibles and unapproved cosmetic body damages cost the platform ₹4,800 per active car monthly.", "dependencies": ["downtime.cause"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Negative EBITDA is driven by 22% fleet grounding in workshops with 24-day repair delays and unrecovered accident damage costs from reckless driving."},
            {"id": "recommendation.telematics", "domain": "recommendation", "release_level": "synthesis_support", "content": "Install IoT speed-limit and harsh-braking telematics that levy real-time security deposit fines for reckless driving."},
            {"id": "recommendation.fast_repair", "domain": "recommendation", "release_level": "synthesis_support", "content": "Create pre-approved cashless network of express body-shops with guaranteed 5-day repair SLAs."},
            {"id": "recommendation.host_insurance", "domain": "recommendation", "release_level": "synthesis_support", "content": "Package comprehensive zero-depreciation insurance policy co-funded by borrower trip damage fees."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.mobility-ebitda", root_label="Restore self-drive mobility platform fleet EBITDA.",
            branches=[
                {"id": "fleet-availability", "label": "Available Fleet vs Grounded Vehicles", "conclusion": "22% of fleet is grounded in workshops, reducing active fleet capacity."},
                {"id": "accident-and-repair", "label": "Accident Frequency & Repair Turnaround", "conclusion": "High accident rate and 24-day repair delays drain vehicle revenue days."},
                {"id": "damage-recovery", "label": "Insurance Settlement & Customer Recovery", "conclusion": "Unrecovered cosmetic damage and deductibles cost ₹4,800/car monthly."}
            ],
            diagnosis={"label": "Accident Downtime & Damage Cost Bleed", "evidence": ["fleet-availability", "accident-and-repair", "damage-recovery"], "conclusion": "Platform profitability is destroyed by 22% of cars being grounded in 24-day repair cycles, caused by driver moral hazard and slow insurance resolution."},
            recommendation={"label": "3-Pillar Fleet Protection Program", "evidence": ["diagnosis"], "conclusion": "Deploy telematics driver monitoring, establish 5-day express repair network, and introduce borrower damage protection fees."},
            routes=[{"id": "availability-first", "sequence": ["fleet-availability", "accident-and-repair", "damage-recovery", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from occupancy numbers to actual fleet grounding rates."}],
            recovery=["Ask candidate why total fleet utilization is only 58% despite 90% weekend demand.", "Clarify that 1,750 cars are in garages.", "Redirect inquiry toward accident frequency and repair turnaround times."]
        )
    )

    # Case 12: Fast Food Chain
    emit_case(
        school_dir="iima", slug="12-fast-food-chain", title="QSR Store Cannibalization", school_tag="IIM-A",
        category="growth_strategy", industry="food_and_beverage_restaurants", difficulty="intermediate",
        opening_context="Your client is a global burger QSR chain expanding in Delhi NCR. It opened 25 new stores in 12 months, but system-wide same-store sales growth (SSSG) turned negative (-8%).",
        opening_objective="Diagnose the negative same-store sales growth and recommend an optimal store expansion strategy.",
        decision_question="Why did QSR same-store sales turn negative during rapid expansion, and how should store territory density be governed?",
        primary_metric="Same-Store Sales Growth (SSSG) and Store Unit Payback", time_horizon="twelve months",
        core_mechanism="Store network cannibalization caused by opening new outlets within a 500-meter radius of existing flagship stores, splitting dine-in footfall without expanding total catchment demand.",
        what_wanted_to_test="Retail trade area dynamics, store cannibalization economics, customer catchment radius, and delivery-only cloud kitchen alternatives.",
        pivotal_insight="18 of the 25 new stores were located within a 10-minute walk of existing high-performing outlets, cannibalizing 30-35% of legacy store sales while duplicating high physical store capex.",
        common_traps=["Assuming customer food preference shifted to healthy salads.", "Blaming food quality or menu pricing changes.", "Cutting marketing ad spend across all outlets."],
        takeaway_lesson="In brick-and-mortar retail and dining, opening new stores inside existing customer catchment trade areas cannibalizes legacy store sales unless density expansion is shifted to low-capex delivery formats.",
        suggested_readings=["knowledge_base/industries/13_food_and_beverage_restaurants.md", "knowledge_base/case_types/growth_strategy.md", "knowledge_base/methodology/02_issue_tree_structuring.md"],
        facts=[
            {"id": "network.growth", "domain": "company", "release_level": "broad_context", "content": "Client expanded network from 50 to 75 outlets in Delhi NCR in 12 months."},
            {"id": "sssg.trend", "domain": "financials", "release_level": "sharp_question", "content": "Same-store sales at legacy 50 stores declined 8% YoY, while new stores generated 30% lower revenue than forecasted."},
            {"id": "geography.overlap", "domain": "operations", "release_level": "hypothesis_backed", "content": "Mobile geofencing data confirms 72% customer overlap between new stores and legacy stores located within 1 km.", "dependencies": ["sssg.trend"]},
            {"id": "channel.split", "domain": "customers", "release_level": "hypothesis_backed", "content": "Delivery sales grew but dine-in traffic split evenly between nearby stores, failing to cover duplicate store fixed rents.", "dependencies": ["geography.overlap"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Negative SSSG is driven by direct store cannibalization: new stores placed within 500m-1km of legacy outlets split dine-in footfall without expanding trade area catchment."},
            {"id": "recommendation.territory", "domain": "recommendation", "release_level": "synthesis_support", "content": "Establish strict 2.5 km minimum radial distance zoning rules for new full-service dine-in restaurants."},
            {"id": "recommendation.cloud_kitchen", "domain": "recommendation", "release_level": "synthesis_support", "content": "Serve high-density delivery demand through low-capex cloud kitchen pods rather than expensive dine-in street retail."},
            {"id": "recommendation.relocate", "domain": "recommendation", "release_level": "synthesis_support", "content": "Relocate or consolidate 8 severely cannibalizing underperforming stores to unserved sub-markets."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.qsr-cannibalization", root_label="Fix negative SSSG and optimize QSR store expansion density.",
            branches=[
                {"id": "sales-performance", "label": "Legacy vs New Store Sales Trajectory", "conclusion": "Legacy stores fell 8% and new stores missed targets by 30%."},
                {"id": "catchment-overlap", "label": "Geographic Proximity & Customer Cannibalization", "conclusion": "72% customer overlap across stores located within 1 km radius."},
                {"id": "channel-economics", "label": "Dine-In Footfall Split vs Delivery Demand", "conclusion": "Dine-in traffic split between stores while fixed occupancy rents doubled."}
            ],
            diagnosis={"label": "Trade Area Store Cannibalization", "evidence": ["sales-performance", "catchment-overlap", "channel-economics"], "conclusion": "Aggressive expansion placed 18 stores inside existing trade catchments, cannibalizing legacy dine-in revenue without adding incremental demand."},
            recommendation={"label": "3-Pillar Network Rationalization Plan", "evidence": ["diagnosis"], "conclusion": "Enforce 2.5 km radius zoning, pivot delivery expansion to cloud kitchens, and relocate cannibalized stores."},
            routes=[{"id": "geography-first", "sequence": ["sales-performance", "catchment-overlap", "channel-economics", "diagnosis", "actions"], "interviewer_behaviour": "Prompt candidate to analyze store catchment radius and footfall overlap."}],
            recovery=["Ask candidate to check the geographic distance between new stores and existing stores.", "Clarify that total market burger consumption is growing.", "Redirect inquiry toward trade area cannibalization and rent efficiency."]
        )
    )

    # Case 13: Lease Fee Turnaround
    emit_case(
        school_dir="iima", slug="13-lease-fee-turnaround", title="Commercial Office REIT", school_tag="IIM-A",
        category="turnaround", industry="hospitality_and_tourism", difficulty="intermediate",
        opening_context="Your client is a premier Grade-A commercial office REIT in Bengaluru with 12M sq ft across 4 tech parks. Portfolio occupancy dropped from 94% to 76% following IT client lease non-renewals.",
        opening_objective="Diagnose the structural occupancy decline and propose a commercial asset turnaround plan.",
        decision_question="Why did Grade-A IT office occupancy collapse and how should lease structures be adapted for hybrid work?",
        primary_metric="Portfolio Occupancy and Net Operating Income (NOI)", time_horizon="eighteen months",
        core_mechanism="Rigid 9-year long-term lease terms with 3-year lock-ins rejected by global IT clients who adopted hybrid 3-day workweeks and downsized dedicated desk footprints by 35%.",
        what_wanted_to_test="Commercial real estate yield, hybrid workplace dynamics, flexible enterprise managed spaces vs traditional bare-shell leases, and amenity monetization.",
        pivotal_insight="Tenants do not want to exit tech parks; they want to reduce dedicated leased floor plates while paying a premium for flexible, on-demand managed desks and meeting suites.",
        common_traps=["Slashing baseline base rent by 50% across all leases, destroying REIT debt service coverage.", "Assuming tech companies will fully return to 5-day in-office work mandating zero lease changes.", "Converting commercial office parks into residential apartments."],
        takeaway_lesson="In commercial real estate facing hybrid work disruption, landlord value shifts from leasing raw square footage on multi-year terms to operating flexible, fully managed workplace hospitality.",
        suggested_readings=["knowledge_base/industries/12_hospitality_and_tourism.md", "knowledge_base/case_types/growth_strategy.md", "knowledge_base/methodology/01_preliminary_questions.md"],
        facts=[
            {"id": "reit.portfolio", "domain": "company", "release_level": "broad_context", "content": "Client owns 12M sq ft Grade-A tech parks in Whitefield and Outer Ring Road, Bengaluru."},
            {"id": "occupancy.drop", "domain": "financials", "release_level": "sharp_question", "content": "Vacancy rose to 24% as 18 large tech clients downsized leased space upon 3-year term expiry."},
            {"id": "tenant.behavior", "domain": "customers", "release_level": "hypothesis_backed", "content": "Tech companies operate at 45% daily physical desk occupancy due to hybrid policies, seeking 30-40% smaller footprints.", "dependencies": ["occupancy.drop"]},
            {"id": "flex.demand", "domain": "market", "release_level": "hypothesis_backed", "content": "Third-party co-working and managed office operators in the same micromarket maintain 90% occupancy charging 25% rent premiums.", "dependencies": ["tenant.behavior"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Occupancy dropped from 94% to 76% because rigid 9-year traditional leases failed hybrid IT tenants who reduced dedicated space; managed co-working operators in the same market thrive by offering flexible terms."},
            {"id": "recommendation.flex", "domain": "recommendation", "release_level": "synthesis_support", "content": "Convert 3M sq ft of vacant space into internal branded enterprise managed flexible workspace charging 20% premium."},
            {"id": "recommendation.core_flex", "domain": "recommendation", "release_level": "synthesis_support", "content": "Offer 'Core & Flex' lease contracts (70% long-term dedicated floor, 30% flexible shared credits across the tech park)."},
            {"id": "recommendation.amenities", "domain": "recommendation", "release_level": "synthesis_support", "content": "Monetize centralized conference auditoriums, sports arenas, and F&B retail pavilions to generate non-rental ancillary yield."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.reit-occupancy", root_label="Restore commercial office REIT occupancy and Net Operating Income.",
            branches=[
                {"id": "lease-expiry-trend", "label": "Tenant Lease Expiries & Downsizing", "conclusion": "18 major IT tenants downsized space upon 3-year lease renewals."},
                {"id": "hybrid-work-patterns", "label": "Physical Office Utilization & Hybrid Policies", "conclusion": "Physical daily office attendance is 45%, driving demand for 35% smaller footprints."},
                {"id": "flex-vs-traditional", "label": "Managed Space Economics vs Bare-Shell Leases", "conclusion": "Managed flexible workspace maintains 90% occupancy at 25% higher rent."}
            ],
            diagnosis={"label": "Rigid Lease Structure Mismatch with Hybrid Work", "evidence": ["lease-expiry-trend", "hybrid-work-patterns", "flex-vs-traditional"], "conclusion": "Occupancy collapsed because traditional 9-year bare-shell leases cannot accommodate hybrid work, pushing clients toward flexible managed office operators."},
            recommendation={"label": "3-Pillar Managed Workplace Transformation", "evidence": ["diagnosis"], "conclusion": "Launch captive enterprise flex-space, structure 'Core & Flex' leases, and monetize centralized tech park amenities."},
            routes=[{"id": "tenant-first", "sequence": ["lease-expiry-trend", "hybrid-work-patterns", "flex-vs-traditional", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from tenant non-renewals to hybrid work utilization."}],
            recovery=["Ask candidate what percentage of leased desks are physically occupied on any given weekday.", "Clarify that IT clients still value tech park location.", "Redirect inquiry toward flexible managed office models."]
        )
    )

    # Case 14: Auto Insurance
    emit_case(
        school_dir="iima", slug="14-auto-insurance", title="Motor Insurance Loss Ratio", school_tag="IIM-A",
        category="profitability", industry="insurance", difficulty="advanced",
        opening_context="Your client is a top-5 Indian general insurance company. Motor third-party (TP) claim loss ratios surged from 82% to 118% in North India, erasing underwriting profits.",
        opening_objective="Diagnose the root cause of the motor third-party loss ratio spike and recommend fraud containment measures.",
        decision_question="Why did motor third-party claim loss ratios exceed 100% and how can fraudulent claims be detected and prevented?",
        primary_metric="Motor Third-Party Claims Loss Ratio", time_horizon="twelve months",
        core_mechanism="Organized syndicate fraud exploiting rural Motor Accident Claims Tribunals (MACT), staging delayed fake vehicular accident liability claims with fabricated police reports on uninsured commercial trucks.",
        what_wanted_to_test="P&C insurance claims underwriting, third-party bodily injury liability legal dynamics, fraud syndicate mechanics, and telemetry investigation.",
        pivotal_insight="Claims loss spike is not driven by higher road accidents, but by staged legal tribunal claims filed 18-24 months post-incident in 4 specific rural district courts with falsified police FIRs.",
        common_traps=["Assuming own-damage vehicle repair costs increased due to spare parts inflation.", "Proposing raising retail insurance premium rates which are strictly regulated and capped by IRDAI.", "Assuming young urban drivers caused the spike."],
        takeaway_lesson="In statutory liability insurance where pricing is regulated by state authorities, underwriting profitability depends entirely on aggressive legal defense and early fraud analytics at the tribunal level.",
        suggested_readings=["knowledge_base/industries/16_insurance.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "portfolio.lines", "domain": "company", "release_level": "broad_context", "content": "Motor portfolio generates ₹3,000 Cr GWP; Own Damage (OD) loss ratio is healthy at 62%, but Third Party (TP) is 118%."},
            {"id": "geographic.anomaly", "domain": "risk", "release_level": "sharp_question", "content": "70% of the loss ratio surge originates from claims filed across 4 specific rural districts in North India."},
            {"id": "claim.pattern", "domain": "operations", "release_level": "hypothesis_backed", "content": "Average delay between alleged accident date and court notice filing is 22 months; 85% of claims involve commercial trucks.", "dependencies": ["geographic.anomaly"]},
            {"id": "syndicate.nexus", "domain": "risk", "release_level": "hypothesis_backed", "content": "Investigation reveals organized legal syndicates colluding with local police stations to substitute insured commercial trucks into hit-and-run cases.", "dependencies": ["claim.pattern"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "TP loss ratio surged to 118% due to staged legal syndicate fraud in 4 rural district tribunals, filing delayed hit-and-run bodily injury claims with substituted insured vehicles."},
            {"id": "recommendation.special_investigation", "domain": "recommendation", "release_level": "synthesis_support", "content": "Form a dedicated Special Investigation Unit (SIU) in high-risk districts to conduct forensic on-site accident verifications within 7 days."},
            {"id": "recommendation.telematics", "domain": "recommendation", "release_level": "synthesis_support", "content": "Use commercial vehicle GPS and FASTag toll data to prove vehicle absence from accident locations during court defense."},
            {"id": "recommendation.compromise_settlement", "domain": "recommendation", "release_level": "synthesis_support", "content": "Fast-track genuine claims through Lok Adalat out-of-court settlements to avoid compounding legal interest penalties."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.insurance-loss-ratio", root_label="Reduce motor third-party loss ratio below 85%.",
            branches=[
                {"id": "product-line-split", "label": "Own Damage (OD) vs Third Party (TP) Losses", "conclusion": "OD is healthy (62%); TP loss ratio exploded to 118%."},
                {"id": "geographic-and-court-clustering", "label": "Geographic & Legal Tribunal Clustering", "conclusion": "Losses clustered in 4 rural district tribunals with 22-month delayed filings."},
                {"id": "fraud-syndicate-mechanics", "label": "Police FIR Fabrication & Vehicle Substitution", "conclusion": "Syndicates substitute insured commercial trucks into untraced hit-and-run accidents."}
            ],
            diagnosis={"label": "Staged Legal Tribunal Fraud Syndicates", "evidence": ["product-line-split", "geographic-and-court-clustering", "fraud-syndicate-mechanics"], "conclusion": "Loss ratio explosion is caused by organized tribunal fraud staging delayed fake bodily injury claims on commercial trucks in specific rural districts."},
            recommendation={"label": "3-Pillar Fraud Defense Strategy", "evidence": ["diagnosis"], "conclusion": "Deploy on-ground SIU forensic teams, defend court cases using GPS/FASTag telemetry, and settle genuine claims via Lok Adalats."},
            routes=[{"id": "claims-first", "sequence": ["product-line-split", "geographic-and-court-clustering", "fraud-syndicate-mechanics", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from OD vs TP split to court-level geographic anomalies."}],
            recovery=["Ask candidate whether own-damage or third-party liability is responsible for the loss.", "Clarify that actual road accident counts have not increased.", "Redirect inquiry toward legal tribunal filings, claim delays, and vehicle fraud."]
        )
    )

    # Cases 15 to 25 continued
    # Case 15: Apple Exporter
    emit_case(
        school_dir="iima", slug="15-apple-exporter", title="Fresh Fruit Export Quality Loss", school_tag="IIM-A",
        category="operations", industry="logistics_and_cold_chain", difficulty="intermediate",
        opening_context="Your client is an Indian premium apple grower and exporter from Himachal Pradesh. European port consignment rejection rates spiked from 3% to 19%, resulting in massive write-offs.",
        opening_objective="Identify the operational breakdown in the export cold chain and recommend cold chain integrity controls.",
        decision_question="Why are export apple consignments spoiling before reaching European ports and how can cold chain integrity be secured?",
        primary_metric="Consignment Rejection Rate (%)", time_horizon="six months",
        core_mechanism="Cold chain thermal abuse during multi-modal transshipment. Reefer containers experienced power disconnects during 48-hour port terminal yard staging in Mumbai before ship loading, breaking the critical 0-2°C controlled atmosphere.",
        what_wanted_to_test="Cold chain logistics, multi-modal transfer handoffs, perishable post-harvest respiration, and IoT datalogger telemetry.",
        pivotal_insight="Orchard pre-cooling and sea freight reefer systems worked perfectly; spoilage occurred entirely during the 48-hour land-to-sea port holding window where containers sat unplugged in direct sunlight.",
        common_traps=["Assuming post-harvest fungal infection or improper pesticide washing in orchards.", "Blaming shipping lines for slow vessel ocean transit.", "Blaming packaging cardboard box crushing."],
        takeaway_lesson="In multi-modal perishable logistics, quality breakdown almost always occurs at intermodal handoff transfer points where custody changes and auxiliary power is interrupted.",
        suggested_readings=["knowledge_base/industries/01_logistics_and_cold_chain.md", "knowledge_base/case_types/unconventional_and_abstract.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "export.volume", "domain": "company", "release_level": "broad_context", "content": "Client exports 1,200 reefer containers of premium Royal Delicious apples annually to Europe."},
            {"id": "spoilage.symptoms", "domain": "operations", "release_level": "sharp_question", "content": "Rejected apples arrive soft with internal browning, indicating exposure to temperatures above 6°C for >36 continuous hours."},
            {"id": "supplychain.legs", "domain": "operations", "release_level": "hypothesis_backed", "content": "Journey has 4 legs: Farm CA storage -> Road reefer truck -> Mumbai port container yard staging -> Ocean freight.", "dependencies": ["spoilage.symptoms"]},
            {"id": "port.power_break", "domain": "operations", "release_level": "hypothesis_backed", "content": "Port yard reefer plug points had a 40% shortage, causing containers to sit on diesel genset battery trucks that were switched off to save fuel.", "dependencies": ["supplychain.legs"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Rejection rate surged to 19% because reefer containers were unplugged during 48-hour port yard holding in Mumbai due to plug point shortages, causing temperature spike to 12°C."},
            {"id": "recommendation.iot", "domain": "recommendation", "release_level": "synthesis_support", "content": "Equip all containers with real-time cellular/satellite IoT temperature and humidity loggers with instant breach alerts."},
            {"id": "recommendation.port_sla", "domain": "recommendation", "release_level": "synthesis_support", "content": "Contract dedicated reserved reefer plug points with the port terminal backed by contractual penalty clauses."},
            {"id": "recommendation.smart_staging", "domain": "recommendation", "release_level": "synthesis_support", "content": "Schedule farm dispatches using just-in-time vessel arrival tracking to minimize port yard dwell time to <12 hours."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.apple-spoilage", root_label="Reduce export apple rejection rate from 19% to below 3%.",
            branches=[
                {"id": "orchard-postharvest", "label": "Farm Harvesting & Pre-Cooling", "conclusion": "Farm CA storage and initial grading meet global standards."},
                {"id": "transport-legs-audit", "label": "Multi-Modal Transit Temperature Handoffs", "conclusion": "Road transit and sea vessel temperatures are compliant; breach occurs at port yard."},
                {"id": "port-yard-handling", "label": "Mumbai Port Reefer Staging & Power", "conclusion": "40% plug point deficit caused containers to sit unplugged in port yard."}
            ],
            diagnosis={"label": "Port Reefer Power Disconnection", "evidence": ["orchard-postharvest", "transport-legs-audit", "port-yard-handling"], "conclusion": "Apple spoilage is caused by 48-hour power disconnects during port yard staging due to terminal plug shortages."},
            recommendation={"label": "3-Pillar Cold Chain Integrity Protocol", "evidence": ["diagnosis"], "conclusion": "Deploy IoT satellite temperature loggers, contract reserved port plug capacity, and synchronize JIT farm-to-vessel loading."},
            routes=[{"id": "transit-first", "sequence": ["orchard-postharvest", "transport-legs-audit", "port-yard-handling", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate through step-by-step temperature monitoring across transit legs."}],
            recovery=["Ask candidate to identify where custody changes during the export journey.", "Clarify that farm storage and ocean vessel temperatures are normal.", "Redirect inquiry toward port container yard staging and power supply."]
        )
    )

    # Continue with cases 16 to 25
    # Case 16: Oil Distributor
    emit_case(
        school_dir="iima", slug="16-oil-distributor", title="Automotive Lubricants Distributor", school_tag="IIM-A",
        category="profitability", industry="energy_and_renewables", difficulty="intermediate",
        opening_context="Your client is a regional distributor of automotive lubricants and engine oils in North India. Working capital is exhausted and net margins have fallen from 4.5% to 1.2% over two years.",
        opening_objective="Diagnose the margin compression and working capital lockup, and propose channel distribution reforms.",
        decision_question="Why did lubricant distribution margins collapse and how should retail credit and inventory be restructured?",
        primary_metric="Net margin and Days Sales Outstanding (DSO)", time_horizon="twelve months",
        core_mechanism="Over-extension of unsecured 90-day trade credit to unorganized independent auto mechanics and garages to chase sales targets, coupled with slow-moving specialty SKU proliferation that tied up working capital.",
        what_wanted_to_test="Wholesale distribution economics, working capital financing, channel credit risk, and SKU velocity Pareto analysis.",
        pivotal_insight="Top 20% high-velocity motorcycle oil SKUs generate 80% of profits on cash terms; bottom 50% niche industrial SKUs are sold on 90-day credit to unvetted garages who default.",
        common_traps=["Assuming oil marketing company (OMC) supplier wholesale prices increased.", "Cutting sales team incentives without fixing garage credit terms.", "Blaming synthetic vs mineral oil technology transitions."],
        takeaway_lesson="In route-to-market wholesale distribution, revenue growth driven by loose retailer credit terms destroys distributor equity through working capital lockup and bad debt write-offs.",
        suggested_readings=["knowledge_base/industries/11_energy_and_renewables.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "distributor.scale", "domain": "company", "release_level": "broad_context", "content": "Distributor supplies 3,500 retail outlets, spare part shops, and independent garages across Punjab and Haryana."},
            {"id": "dso.trend", "domain": "financials", "release_level": "sharp_question", "content": "DSO expanded from 32 days to 88 days, resulting in ₹18 Cr in unpaid dealer receivables and high bank overdraft interest."},
            {"id": "sku.analysis", "domain": "operations", "release_level": "hypothesis_backed", "content": "Distributor carries 420 SKUs; bottom 250 SKUs turn over less than twice a year but occupy 40% of warehouse space.", "dependencies": ["dso.trend"]},
            {"id": "channel.credit", "domain": "financials", "release_level": "hypothesis_backed", "content": "92% of bad debts and credit delays originate from unorganized small repair garages, while authorized service stations pay in 15 days.", "dependencies": ["sku.analysis"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Margin fell to 1.2% because working capital is trapped in 250 slow-moving SKUs and unorganized garage credit (DSO 88 days) where bad debts surged."},
            {"id": "recommendation.credit_policy", "domain": "recommendation", "release_level": "synthesis_support", "content": "Transition unorganized garages to cash-and-carry with 2% instant cash discounts, capping credit terms at 15 days for vetted dealers only."},
            {"id": "recommendation.sku_rationalization", "domain": "recommendation", "release_level": "synthesis_support", "content": "Delist bottom 150 slow-moving niche SKUs and focus inventory on fast-moving 4T motorcycle and commercial diesel oils."},
            {"id": "recommendation.fintech_financing", "domain": "recommendation", "release_level": "synthesis_support", "content": "Partner with supply-chain fintechs to offer retailer invoice financing, transferring balance-sheet credit risk to third parties."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.oil-distributor-margin", root_label="Restore lubricant distributor net margin and cash flow.",
            branches=[
                {"id": "gross-margin-vs-overhead", "label": "Wholesale Gross Margins vs Operating Costs", "conclusion": "Supplier margins are steady; bank overdraft interest and bad debts eroded profit."},
                {"id": "working-capital-and-dso", "label": "Receivables DSO & Garage Credit Risk", "conclusion": "DSO blew out to 88 days due to unsecured credit to unorganized repair garages."},
                {"id": "inventory-and-sku-velocity", "label": "SKU Velocity & Warehouse Holding Costs", "conclusion": "Bottom 250 SKUs turn <2x/year, trapping ₹8 Cr in dead inventory."}
            ],
            diagnosis={"label": "Garage Credit Default & SKU Proliferation", "evidence": ["gross-margin-vs-overhead", "working-capital-and-dso", "inventory-and-sku-velocity"], "conclusion": "Profitability collapsed due to loose 90-day credit to high-risk garages and carrying 250 slow-moving specialty SKUs."},
            recommendation={"label": "3-Pillar Distribution Restructuring Plan", "evidence": ["diagnosis"], "conclusion": "Enforce cash-and-carry for garages, rationalize slow-moving SKUs, and shift dealer credit to fintech invoice financing."},
            routes=[{"id": "working-capital-first", "sequence": ["gross-margin-vs-overhead", "working-capital-and-dso", "inventory-and-sku-velocity", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from profitability statement to working capital and receivables."}],
            recovery=["Ask candidate to check the growth in Days Sales Outstanding (DSO).", "Clarify that OMC oil prices did not increase.", "Redirect toward dealer credit terms and inventory SKU velocity."]
        )
    )

    # Cases 17-25 rapid generation with authentic details
    # Case 17: Deep-Sea Fishing Fleet
    emit_case(
        school_dir="iima", slug="17-fishing-fleet", title="Deep-Sea Fishing Fleet", school_tag="IIM-A",
        category="profitability", industry="food_and_beverage_restaurants", difficulty="intermediate",
        opening_context="Your client operates a fleet of 30 deep-sea trawlers based in Kochi. Operating profit per voyage has turned negative over the last two fishing seasons.",
        opening_objective="Diagnose voyage profitability decline and recommend a catch optimization strategy.",
        decision_question="Why are trawler voyages unprofitable and how should fleet dispatch and catch processing be optimized?",
        primary_metric="Profit per 20-day trawler voyage", time_horizon="twelve months",
        core_mechanism="Marine diesel fuel cost inflation (55% of voyage cost) combined with excessive low-value bycatch discard (45% of netted volume) due to lack of onboard cold-hold sorting.",
        what_wanted_to_test="Marine operations, voyage variable cost decomposition, catch composition value optimization, and satellite fishery scouting.",
        pivotal_insight="Trawlers spend 8 days searching blindly for high-value tuna, burning diesel while discarding thousands of tons of edible secondary fish that could be sold to surimi processors.",
        common_traps=["Blaming international fish export tariff quotas.", "Assuming overfishing has wiped out all marine stock without checking secondary catch.", "Recommending purchasing larger mega-trawlers."],
        takeaway_lesson="In asset-heavy natural resource extraction facing fuel inflation, profitability requires monetizing secondary co-products (bycatch) and using predictive scouting to reduce transit search fuel burn.",
        suggested_readings=["knowledge_base/industries/13_food_and_beverage_restaurants.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "fleet.overview", "domain": "company", "release_level": "broad_context", "content": "Client operates 30 motorized 24-meter deep-sea trawlers on 20-day Arabian Sea voyages."},
            {"id": "voyage.cost", "domain": "financials", "release_level": "sharp_question", "content": "Marine diesel fuel represents 56% of total voyage cost, up 35% over two years."},
            {"id": "catch.composition", "domain": "operations", "release_level": "hypothesis_backed", "content": "High-value yellowfin tuna represents only 20% of net volume; 45% is low-value bycatch discarded at sea to save cold-hold ice.", "dependencies": ["voyage.cost"]},
            {"id": "scouting.efficiency", "domain": "operations", "release_level": "hypothesis_backed", "content": "Trawlers average 9 days of active search cruise per 20-day trip without satellite oceanographic sea-surface temperature data.", "dependencies": ["catch.composition"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Voyages are unprofitable because trawlers spend 9 days burning fuel searching blindly while discarding 45% of catch (bycatch) due to lack of onboard chilling and commercial surimi tie-ups."},
            {"id": "recommendation.satellite", "domain": "recommendation", "release_level": "synthesis_support", "content": "Subscribe to ISRO/INCOIS Potential Fishing Zone (PFZ) satellite thermal maps to cut search cruise time by 40%."},
            {"id": "recommendation.bycatch", "domain": "recommendation", "release_level": "synthesis_support", "content": "Install onboard blast freezers and contract with coastal surimi/fishmeal processors to monetize secondary catch."},
            {"id": "recommendation.fuel_efficiency", "domain": "recommendation", "release_level": "synthesis_support", "content": "Implement engine speed governance (trolling at 8 knots vs 12 knots) to reduce diesel burn by 22%."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.fishing-voyage-profit", root_label="Restore deep-sea trawler voyage profitability.",
            branches=[
                {"id": "fuel-burn-analysis", "label": "Diesel Fuel Burn & Search Days", "conclusion": "Fuel is 56% of cost; blind search consumes 9 days per voyage."},
                {"id": "catch-value-yield", "label": "Target Catch vs Discarded Bycatch", "conclusion": "45% of netted catch is discarded at sea due to lack of cold-hold storage."},
                {"id": "onboard-processing", "label": "Onboard Chilling & Commercial Offtake", "conclusion": "Zero commercial contracts exist for secondary pelagic fish species."}
            ],
            diagnosis={"label": "Blind Search Fuel Burn & Bycatch Discard", "evidence": ["fuel-burn-analysis", "catch-value-yield", "onboard-processing"], "conclusion": "Voyages lose money due to 9 days of blind search fuel consumption and discarding 45% of catch that could be monetized."},
            recommendation={"label": "3-Pillar Marine Efficiency Plan", "evidence": ["diagnosis"], "conclusion": "Deploy satellite PFZ scouting, monetize bycatch through surimi processors, and optimize cruising speed."},
            routes=[{"id": "operations-first", "sequence": ["fuel-burn-analysis", "catch-value-yield", "onboard-processing", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from fuel cost breakdown to catch composition and search efficiency."}],
            recovery=["Ask candidate what percentage of a voyage is spent searching vs netting fish.", "Clarify that fish market prices for premium tuna remain high.", "Redirect toward search time reduction and bycatch monetization."]
        )
    )

    # Case 18: Chartered Flight Operator
    emit_case(
        school_dir="iima", slug="18-chartered-flight", title="Private Jet Charter Fleet", school_tag="IIM-A",
        category="operations", industry="aviation_and_airlines", difficulty="intermediate",
        opening_context="Your client operates an executive private jet charter fleet of 12 mid-sized business aircraft in India. Aircraft EBITDA is negative despite high corporate charter hourly rates.",
        opening_objective="Diagnose the low fleet profitability and recommend a schedule and fleet utilization plan.",
        decision_question="Why is the private jet charter operator losing money despite charging ₹4.5 lakh per flight hour?",
        primary_metric="Revenue hours per aircraft per month and Empty-Leg Ratio (%)", time_horizon="twelve months",
        core_mechanism="Severe deadhead empty-leg ferry flights (38% of total flight hours) where aircraft reposition without paying passengers, combined with high fixed parking and hangar fees at congested metro airports.",
        what_wanted_to_test="Aviation fleet economics, empty-leg ferry flight monetization, dynamic base repositioning, and maintenance downtime scheduling.",
        pivotal_insight="38% of all flight hours are unpaid deadhead repositioning flights (e.g. flying empty from Delhi to Hyderabad to pick up a client), consuming fuel and engine maintenance hours without revenue.",
        common_traps=["Assuming corporate charter demand dried up.", "Blaming pilot and flight attendant salary inflation.", "Proposing buying larger long-range intercontinental jets."],
        takeaway_lesson="In on-demand aviation and vehicle chartering, unmonetized repositioning deadhead legs destroy margins; operators must dynamically market discounted empty-legs or enforce floating fleet dispatch.",
        suggested_readings=["knowledge_base/industries/06_aviation_and_airlines.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/02_issue_tree_structuring.md"],
        facts=[
            {"id": "fleet.spec", "domain": "company", "release_level": "broad_context", "content": "Client operates 12 mid-size jets (Hawker/Learjet) based out of Delhi and Mumbai."},
            {"id": "hourly.pricing", "domain": "financials", "release_level": "sharp_question", "content": "Charter rate is ₹4.5 lakh/hour, but average billable hours per aircraft are only 24 hours/month (breakeven is 40 hours)."},
            {"id": "deadhead.rate", "domain": "operations", "release_level": "hypothesis_backed", "content": "38% of all airborne flight hours are unpaid empty-leg ferry flights required to reposition aircraft for one-way charters.", "dependencies": ["hourly.pricing"]},
            {"id": "airport.fees", "domain": "financials", "release_level": "hypothesis_backed", "content": "Night parking and landing charges at Delhi/Mumbai airports are 3x higher than regional secondary airports.", "dependencies": ["deadhead.rate"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Negative EBITDA is caused by low billable utilization (24 hrs/month vs 40 hrs breakeven) driven by 38% unpaid empty-leg repositioning flights and high metro parking fees."},
            {"id": "recommendation.empty_leg_app", "domain": "recommendation", "release_level": "synthesis_support", "content": "Launch digital empty-leg marketplace offering 50% discounted one-way seats to luxury leisure travelers."},
            {"id": "recommendation.floating_base", "domain": "recommendation", "release_level": "synthesis_support", "content": "Shift from fixed Delhi/Mumbai bases to a floating fleet model with regional overnight parking at lower-cost airports."},
            {"id": "recommendation.membership", "domain": "recommendation", "release_level": "synthesis_support", "content": "Introduce 25-hour and 50-hour corporate jet card memberships with round-trip commitment incentives."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.charter-profit", root_label="Restore private jet fleet EBITDA and billable utilization.",
            branches=[
                {"id": "utilization-vs-breakeven", "label": "Billable Flight Hours vs Breakeven", "conclusion": "Aircraft fly 24 billable hours/month against 40 hours required for breakeven."},
                {"id": "deadhead-ferry-legs", "label": "Empty Repositioning Flight Analysis", "conclusion": "38% of total flight time is unbilled deadhead ferry flying."},
                {"id": "base-operating-costs", "label": "Hangar & Metro Airport Parking Fees", "conclusion": "Metro airport parking and landing fees add ₹12 Cr annual fixed overhead."}
            ],
            diagnosis={"label": "High Deadhead Ratio & Fixed Base Overhead", "evidence": ["utilization-vs-breakeven", "deadhead-ferry-legs", "base-operating-costs"], "conclusion": "EBITDA is negative because 38% of flight hours are unpaid empty repositioning legs and fixed base parking costs at metro airports are excessive."},
            recommendation={"label": "3-Pillar Charter Fleet Optimization", "evidence": ["diagnosis"], "conclusion": "Monetize empty legs on digital consumer channels, adopt floating fleet dispatch, and sell prepaid corporate jet card programs."},
            routes=[{"id": "utilization-first", "sequence": ["utilization-vs-breakeven", "deadhead-ferry-legs", "base-operating-costs", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from hourly charter rates to billable utilization and empty legs."}],
            recovery=["Ask candidate to calculate total airborne hours vs revenue-generating hours.", "Clarify that charter hourly pricing is among the highest in the market.", "Redirect inquiry toward empty-leg ferry flights and base parking costs."]
        )
    )

    # Case 19: Textile Retail (Ethnic Wear)
    emit_case(
        school_dir="iima", slug="19-textile-retail", title="Bridal Ethnic Wear Retailer", school_tag="IIM-A",
        category="turnaround", industry="retail_and_fashion", difficulty="intermediate",
        opening_context="Your client is a heritage bridal and ethnic wear retailer with 18 luxury stores in North India. Gross margins fell by 800 bps due to heavy end-of-season clearance markdowns.",
        opening_objective="Diagnose inventory markdown losses and propose an open-to-buy merchandising and bridal customization model.",
        decision_question="Why did ethnic wear gross margins collapse and how should bridal inventory buying be redesigned?",
        primary_metric="Gross Margin and Full-Price Sell-Through (%)", time_horizon="twelve months",
        core_mechanism="Decentralized subjective bridal buying resulting in heavy pre-ordering of high-ticket bespoke bridal lehengas (₹1.5L-3L) that are size- and color-specific, leaving 40% unsold and requiring 60% markdowns.",
        what_wanted_to_test="Fashion retail merchandising, made-to-order vs ready-to-wear inventory risk, open-to-buy governance, and bridal customization lead times.",
        pivotal_insight="High-ticket bridal lehengas require made-to-measure customization; stocking pre-stitched finished inventory created massive obsolescence, while semi-stitched sample swatches eliminate inventory risk.",
        common_traps=["Assuming fabric embroidery craftsmanship costs increased.", "Proposing closing half the physical luxury stores without analyzing category sell-through.", "Blaming e-commerce competition for bespoke bridal wear."],
        takeaway_lesson="In high-ticket bespoke luxury apparel, stocking finished inventory creates extreme markdown risk; retail stores should operate as sample showrooms with made-to-order manufacturing.",
        suggested_readings=["knowledge_base/industries/09_retail_and_fashion.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "store.profile", "domain": "company", "release_level": "broad_context", "content": "Client operates 18 flagship stores with average ticket size of ₹85,000."},
            {"id": "markdown.surge", "domain": "financials", "release_level": "sharp_question", "content": "Gross margin dropped from 54% to 46% due to ₹24 Cr in end-of-season clearance discounts."},
            {"id": "category.split", "domain": "merchandising", "release_level": "hypothesis_backed", "content": "Ready-to-wear sarees and kurtas had 82% full-price sell-through; heavy bridal lehengas (>₹1.5L) had only 38% sell-through.", "dependencies": ["markdown.surge"]},
            {"id": "buying.process", "domain": "operations", "release_level": "hypothesis_backed", "content": "Store managers ordered finished, fully stitched bridal sets 9 months in advance with zero customer pre-orders.", "dependencies": ["category.split"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Margin loss is driven by finished pre-stitched bridal inventory (>₹1.5L) with low 38% sell-through, forcing heavy 60% clearance markdowns; bridal buying must shift to sample-based made-to-order."},
            {"id": "recommendation.mto", "domain": "recommendation", "release_level": "synthesis_support", "content": "Shift bridal wear from finished inventory to made-to-order sample master pieces with 21-day customized tailoring."},
            {"id": "recommendation.otb", "domain": "recommendation", "release_level": "synthesis_support", "content": "Implement centralized Open-To-Buy (OTB) planning with 50% budget reserved for in-season replenishment."},
            {"id": "recommendation.clearance", "domain": "recommendation", "release_level": "synthesis_support", "content": "Liquidate aged bridal inventory through private VIP trunk shows and rental platform partnerships."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.ethnic-retail-margin", root_label="Restore ethnic wear gross margins and eliminate bridal markdown losses.",
            branches=[
                {"id": "markdown-by-category", "label": "Markdown Concentration Across Product Lines", "conclusion": "Clearance discounts are 85% concentrated in heavy bridal lehengas (>₹1.5L)."},
                {"id": "bridal-sell-through", "label": "Bridal Inventory Sell-Through & Buying Cycle", "conclusion": "Bridal sell-through is only 38% on 9-month advance pre-stitched buys."},
                {"id": "made-to-order-feasibility", "label": "Sample Showrooming & Tailoring Lead Times", "conclusion": "Sample master pieces with 21-day tailoring eliminate finished inventory obsolescence."}
            ],
            diagnosis={"label": "Pre-Stitched Bridal Inventory Obsolescence", "evidence": ["markdown-by-category", "bridal-sell-through", "made-to-order-feasibility"], "conclusion": "Gross margin dropped 800 bps because high-ticket bridal sets were ordered as finished inventory 9 months ahead, suffering 62% unsold stock and heavy markdowns."},
            recommendation={"label": "3-Pillar Merchandising Overhaul", "evidence": ["diagnosis"], "conclusion": "Adopt sample showroom made-to-order model, centralize open-to-buy governance, and liquidate aged stock via VIP trunk shows."},
            routes=[{"id": "category-first", "sequence": ["markdown-by-category", "bridal-sell-through", "made-to-order-feasibility", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from overall markdowns to category-specific sell-through."}],
            recovery=["Ask candidate to compare sell-through between everyday ethnic wear and luxury bridal lehengas.", "Clarify that customer footfall in stores is steady.", "Redirect inquiry toward made-to-order sample models vs pre-stitched inventory."]
        )
    )

    # Case 20: Steel Producer
    emit_case(
        school_dir="iima", slug="20-steel-producer", title="Secondary Steel Induction Mill", school_tag="IIM-A",
        category="profitability", industry="heavy_manufacturing_and_steel", difficulty="intermediate",
        opening_context="Your client is a secondary steel billet and TMT bar manufacturer in Central India using induction furnaces. EBITDA margin dropped from 11% to 3% over twelve months.",
        opening_objective="Diagnose power and raw material cost inflation and recommend an energy and raw material optimization plan.",
        decision_question="Why did steel mill EBITDA margin collapse and how can furnace yield and power costs be optimized?",
        primary_metric="EBITDA per metric ton of TMT steel", time_horizon="twelve months",
        core_mechanism="Power tariff hikes (from ₹5.8 to ₹7.6/kWh) combined with variable sponge iron (DRI) metallization quality (dropping from 84% to 76%), which increased furnace melting electricity consumption by 32% per ton.",
        what_wanted_to_test="Secondary steel metallurgy, specific power consumption (kWh/ton), sponge iron metallization grade variance, and captive power plant economics.",
        pivotal_insight="Lower-grade sponge iron with high gangue/unreduced iron requires significantly more electricity and flux to melt, multiplying the impact of rising grid power tariffs.",
        common_traps=["Assuming TMT bar selling price crashed without checking domestic infrastructure demand.", "Blaming rolling mill labor costs which represent <5% of steel cost.", "Proposing closing induction furnaces to build an expensive blast furnace."],
        takeaway_lesson="In electro-intensive heavy manufacturing, using cheaper low-grade raw materials often backfires by dramatically inflating specific energy consumption per unit of finished product.",
        suggested_readings=["knowledge_base/industries/14_heavy_manufacturing_and_steel.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "plant.capacity", "domain": "company", "release_level": "broad_context", "content": "Plant produces 300,000 MT/year of TMT bars using sponge iron (DRI) and scrap in electric induction furnaces."},
            {"id": "cost.breakdown", "domain": "financials", "release_level": "sharp_question", "content": "Power and raw materials account for 88% of total production cost per ton."},
            {"id": "power.consumption", "domain": "operations", "release_level": "hypothesis_backed", "content": "Specific power consumption rose from 580 kWh/ton to 765 kWh/ton; grid power tariffs rose from ₹5.80 to ₹7.60/kWh.", "dependencies": ["cost.breakdown"]},
            {"id": "sponge_iron.quality", "domain": "operations", "release_level": "hypothesis_backed", "content": "Purchasing team switched to low-grade sponge iron with 76% metallization (down from 84%) to save ₹1,500/ton on purchase price.", "dependencies": ["power.consumption"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "EBITDA fell to 3% because buying cheap low-grade sponge iron (76% metallization) increased power consumption by 32% (765 kWh/ton), completely overwhelming the ₹1,500 raw material discount under rising power tariffs."},
            {"id": "recommendation.quality_sourcing", "domain": "recommendation", "release_level": "synthesis_support", "content": "Mandate minimum 84% sponge iron metallization standards, as energy savings of ₹1,400/ton exceed the raw material price delta."},
            {"id": "recommendation.waste_heat", "domain": "recommendation", "release_level": "synthesis_support", "content": "Install a 15 MW waste-heat recovery captive power plant to reduce grid power exposure by 40%."},
            {"id": "recommendation.furnace_automation", "domain": "recommendation", "release_level": "synthesis_support", "content": "Deploy automated oxygen-assisted lancing and scrap pre-heating to reduce batch tap-to-tap time."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.steel-mill-ebitda", root_label="Restore secondary steel induction mill EBITDA margin.",
            branches=[
                {"id": "power-and-tariffs", "label": "Specific Power Consumption (kWh/ton) & Tariffs", "conclusion": "Power use rose 32% (to 765 kWh/ton) while grid tariffs rose to ₹7.60/kWh."},
                {"id": "sponge-iron-metallurgy", "label": "Sponge Iron Metallization & Yield", "conclusion": "76% metallization sponge iron increased slag volume and melting energy."},
                {"id": "captive-power-options", "label": "Captive Generation & Waste Heat Recovery", "conclusion": "Plant has zero captive power, exposing 100% of load to state grid tariffs."}
            ],
            diagnosis={"label": "Low-Grade DRI Sponge Iron Power Penalty", "evidence": ["power-and-tariffs", "sponge-iron-metallurgy", "captive-power-options"], "conclusion": "Buying low-metallization sponge iron increased power consumption by 32%, turning rising power tariffs into a crippling margin blow."},
            recommendation={"label": "3-Pillar Energy & Raw Material Optimization", "evidence": ["diagnosis"], "conclusion": "Restore 84% metallization sourcing, install 15 MW waste-heat captive power, and automate oxygen lancing."},
            routes=[{"id": "energy-first", "sequence": ["power-and-tariffs", "sponge-iron-metallurgy", "captive-power-options", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from power cost breakdown to sponge iron metallization chemistry."}],
            recovery=["Ask candidate to evaluate specific power consumption per ton of steel.", "Clarify that TMT bar selling prices are healthy.", "Redirect inquiry toward sponge iron quality and its impact on electric melting energy."]
        )
    )

    # Cases 21 to 25 (EV, 5G, Quick Commerce, Oncology, GenAI)
    # Case 21: EV Manufacturer
    emit_case(
        school_dir="iima", slug="21-ev-manufacturer", title="Electric Two-Wheeler Market Entry", school_tag="IIM-A",
        category="market_entry", industry="automotive_and_ev", difficulty="advanced",
        opening_context="Your client is a leading Indian conventional two-wheeler OEM evaluating a ₹1,500 Cr entry into the electric scooter (E2W) market. Management is debating between battery swapping vs fast charging.",
        opening_objective="Evaluate battery swapping vs onboard fast-charging and recommend the winning architecture and commercial entry strategy.",
        decision_question="Should the OEM adopt battery swapping or onboard fast-charging, and what is the optimal market entry roadmap?",
        primary_metric="5-year Total Cost of Ownership (TCO) and Network Payback", time_horizon="three years",
        core_mechanism="Commercial B2B delivery fleets vs retail B2C consumer dichotomy. B2B delivery riders prioritize zero downtime and adopt battery swapping, while retail B2C consumers prefer home overnight charging and reject recurring battery subscription fees.",
        what_wanted_to_test="EV architecture trade-offs, battery swapping network density capex, B2B gig-economy fleet economics vs B2C consumer charging habits.",
        pivotal_insight="Battery swapping requires 1.8 batteries per vehicle plus dense automated swap stations (₹400 Cr capex); commercial B2B fleets provide the 85% daily utilization needed to make swapping profitable, whereas B2C retail adoption fails subscription economics.",
        common_traps=["Assuming a single charging architecture works for both commercial delivery fleets and daily office commuters.", "Underestimating battery swapping network density capital requirements.", "Treating EV entry as a pure hardware launch without considering battery lifecycle residual value."],
        takeaway_lesson="In EV infrastructure strategy, charging architecture is determined by fleet duty cycle: high-mileage commercial fleets require battery swapping, whereas low-mileage retail consumers are best served by home charging.",
        suggested_readings=["knowledge_base/industries/10_automotive_and_ev.md", "knowledge_base/case_types/market_entry.md", "knowledge_base/methodology/02_issue_tree_structuring.md"],
        facts=[
            {"id": "market.size", "domain": "market", "release_level": "broad_context", "content": "Indian E2W market is projected to reach 4M annual units by 2028, split 30% B2B commercial fleets and 70% B2C retail."},
            {"id": "swapping.economics", "domain": "economics", "release_level": "sharp_question", "content": "Battery swapping station costs ₹18 lakh, requires 1.8 battery packs per scooter, and breaks even at 25 swaps/day."},
            {"id": "rider.duty_cycle", "domain": "customers", "release_level": "hypothesis_backed", "content": "B2B delivery riders travel 120 km/day and cannot wait 45 mins for fast charging; B2C commuters travel 25 km/day and charge at home.", "dependencies": ["swapping.economics"]},
            {"id": "battery.standards", "domain": "regulation", "release_level": "hypothesis_backed", "content": "Government interoperability standards for swappable batteries remain fragmented across manufacturers.", "dependencies": ["rider.duty_cycle"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Optimal strategy is a bifurcated dual-platform: deploy battery swapping exclusively for commercial B2B fleets (Zomato/Swiggy/Amazon) where high daily utilization pays off station capex, while selling fixed-battery scooters with portable home chargers for B2C retail."},
            {"id": "recommendation.b2b_swapping", "domain": "recommendation", "release_level": "synthesis_support", "content": "Launch dedicated B2B commercial scooter with battery-as-a-service (BaaS) swapping in top 6 metros."},
            {"id": "recommendation.b2c_home", "domain": "recommendation", "release_level": "synthesis_support", "content": "Launch premium B2C retail scooter with 3.5 kWh fixed battery and bundled home smart charger."},
            {"id": "recommendation.second_life", "domain": "recommendation", "release_level": "synthesis_support", "content": "Monetize degraded 70% SOH batteries by redeploying them into stationary solar grid storage."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.ev-entry", root_label="Recommend E2W vehicle architecture and market entry strategy.",
            branches=[
                {"id": "market-segment-duty-cycles", "label": "Customer Segmentation & Daily Mileage", "conclusion": "B2B delivery rides 120 km/day (swapping fit); B2C rides 25 km/day (home charge fit)."},
                {"id": "infrastructure-unit-economics", "label": "Swapping Station Capex vs Fast Charging", "conclusion": "Swapping requires ₹18L/station and 25 swaps/day; viable only with dense B2B fleet demand."},
                {"id": "regulatory-interoperability", "label": "Battery Standards & Subsidies", "conclusion": "Fragmented battery standards make universal public swapping risky without OEM partnerships."}
            ],
            diagnosis={"label": "Bifurcated Architecture Strategy", "evidence": ["market-segment-duty-cycles", "infrastructure-unit-economics", "regulatory-interoperability"], "conclusion": "Neither architecture fits both markets: deploy battery swapping for high-mileage B2B commercial fleets and fixed home-charging batteries for B2C retail."},
            recommendation={"label": "3-Pillar EV Market Entry Roadmap", "evidence": ["diagnosis"], "conclusion": "Launch BaaS commercial fleet model with swapping, launch fixed-pack retail scooter, and repurpose second-life batteries for grid storage."},
            routes=[{"id": "customer-first", "sequence": ["market-segment-duty-cycles", "infrastructure-unit-economics", "regulatory-interoperability", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from rider daily mileage profiles to infrastructure station economics."}],
            recovery=["Ask candidate to compare daily charging needs of a food delivery rider vs an office commuter.", "Clarify that B2C consumers have home power sockets.", "Redirect toward segmenting product architecture between B2B and B2C."]
        )
    )

    # Case 22: 5G Plan Pricing
    emit_case(
        school_dir="iima", slug="22-5g-plan-pricing", title="Telecom 5G Plan Pricing", school_tag="IIM-A",
        category="pricing", industry="telecom_and_media", difficulty="advanced",
        opening_context="Your client is a top Indian telecom operator that invested ₹40,000 Cr in 5G spectrum and network rollout. 5G users consume 3x more data, but ARPU has risen only 4%.",
        opening_objective="Design a 5G tariff monetization and pricing structure to accelerate ARPU growth without triggering subscriber churn.",
        decision_question="How should the telecom operator restructure 5G mobile tariffs to monetize network capex?",
        primary_metric="Average Revenue Per User (ARPU) and 5G Subscriber Churn", time_horizon="twelve months",
        core_mechanism="Unlimited free 5G data promotional bundles cannibalized premium 4G recharge plans, while speed and latency differences are imperceptible to casual smartphone video viewers.",
        what_wanted_to_test="Telecom tariff design, price elasticity, network slicing monetization, speed tiering vs data capping, and OTT content bundling.",
        pivotal_insight="Offering unmetered free 5G data trained consumers to treat 5G as a free utility; monetization requires shifting from generic data allowances to speed-tiered plans and high-speed 5G Fixed Wireless Access (FWA) home broadband.",
        common_traps=["Raising baseline entry-level prepaid recharge prices causing mass churn to competitors.", "Charging extra purely for 5G data volume when consumers already get 2GB/day on 4G.", "Ignoring home broadband 5G FWA monetization."],
        takeaway_lesson="When a next-gen technology upgrade provides excess raw capacity, pricing must shift from commodity data metering to differentiated experience tiering (speed, latency, home broadband).",
        suggested_readings=["knowledge_base/industries/07_telecom_and_media.md", "knowledge_base/case_types/pricing_strategy.md", "knowledge_base/methodology/04_data_gathering_and_notes.md"],
        facts=[
            {"id": "capex.scale", "domain": "company", "release_level": "broad_context", "content": "Operator deployed 150,000 5G base stations covering 80% of urban India."},
            {"id": "arpu.trend", "domain": "financials", "release_level": "sharp_question", "content": "ARPU is ₹182; 5G data consumption is 32 GB/month (vs 11 GB on 4G), but 5G users pay the same ₹299 monthly recharge."},
            {"id": "consumer.perception", "domain": "customers", "release_level": "hypothesis_backed", "content": "Consumers see no willingness to pay extra for mobile 5G speed on social media/video, but 45% of households lack high-speed fiber home broadband.", "dependencies": ["arpu.trend"]},
            {"id": "fwa.opportunity", "domain": "market", "release_level": "hypothesis_backed", "content": "5G Fixed Wireless Access (FWA) routers can deliver 100 Mbps home Wi-Fi at ₹599/month, generating 3.2x mobile ARPU with zero last-mile fiber digging.", "dependencies": ["consumer.perception"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Mobile 5G ARPU is stagnant because unlimited free data was bundled into standard plans; monetization must be captured through high-ARPU 5G FWA home broadband (₹599/mo) and premium speed-tiered OTT bundles."},
            {"id": "recommendation.fwa", "domain": "recommendation", "release_level": "synthesis_support", "content": "Aggressively scale 5G FWA home broadband routers targeting 20M non-fiber homes at ₹599-₹999/month."},
            {"id": "recommendation.speed_tier", "domain": "recommendation", "release_level": "synthesis_support", "content": "End unlimited free mobile 5G; introduce tiered speed plans (100 Mbps standard vs 1 Gbps ultra-HD gaming bundle)."},
            {"id": "recommendation.enterprise_slicing", "domain": "recommendation", "release_level": "synthesis_support", "content": "Monetize private 5G network slicing for enterprise manufacturing, ports, and hospital robotics."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.5g-pricing", root_label="Restructure 5G tariff architecture to accelerate ARPU growth.",
            branches=[
                {"id": "mobile-arpu-leakage", "label": "Mobile 5G Pricing & Data Consumption", "conclusion": "Data usage tripled to 32 GB/mo but free promotional bundling kept ARPU flat at ₹182."},
                {"id": "willingness-to-pay", "label": "Consumer WTP: Mobile vs Home Broadband", "conclusion": "Mobile consumers resist paying extra for speed; massive unmet demand exists for home Wi-Fi."},
                {"id": "fwa-and-enterprise", "label": "5G FWA & Enterprise Network Slicing", "conclusion": "5G FWA generates ₹599 ARPU (3.2x mobile) and enterprise slicing provides high-margin B2B contracts."}
            ],
            diagnosis={"label": "Promotional Cannibalization & Unlocked FWA Potential", "evidence": ["mobile-arpu-leakage", "willingness-to-pay", "fwa-and-enterprise"], "conclusion": "Free 5G promotional bundles stalled mobile ARPU; 5G capex must be monetized through 5G FWA home broadband and speed-tiered premium bundles."},
            recommendation={"label": "3-Pillar 5G Monetization Architecture", "evidence": ["diagnosis"], "conclusion": "Scale 5G FWA home broadband, sunset unlimited free mobile data in favor of speed tiers, and launch enterprise network slicing."},
            routes=[{"id": "pricing-first", "sequence": ["mobile-arpu-leakage", "willingness-to-pay", "fwa-and-enterprise", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from flat mobile ARPU to home FWA broadband economics."}],
            recovery=["Ask candidate how much revenue the operator makes per GB on 5G vs 4G.", "Clarify that 5G network coverage is comprehensive.", "Redirect toward home broadband 5G FWA and enterprise network slicing."]
        )
    )

    # Case 23: Quick Commerce Pricing
    emit_case(
        school_dir="iima", slug="23-quick-commerce-pricing", title="Quick-Commerce Membership Pricing", school_tag="IIM-A",
        category="pricing", industry="ecommerce_and_marketplaces", difficulty="intermediate",
        opening_context="Your client is a leading 10-minute quick-commerce grocery app in India. Operating loss per order is ₹22, driven by free delivery promotions on low-value orders (<₹199).",
        opening_objective="Redesign delivery fees, minimum order value (MOV) thresholds, and VIP membership pricing to achieve order contribution profitability.",
        decision_question="How should delivery fee thresholds and membership tiers be structured to make quick-commerce unit economics profitable?",
        primary_metric="Contribution Margin Per Order and Average Order Value (AOV)", time_horizon="twelve months",
        core_mechanism="High delivery partner payout (₹45/drop) and pick-pack cost (₹18) exceeding merchant margin (18% on ₹180 average basket = ₹32), resulting in net negative contribution on sub-₹250 orders.",
        what_wanted_to_test="Quick commerce unit economics, delivery cost structure, threshold pricing mechanics, and paid subscription program design.",
        pivotal_insight="Sub-₹199 impulse orders (milk, chips) represent 42% of volume but generate a ₹35 net loss per drop; introducing a ₹299 free-delivery threshold and a ₹99/month VIP subscription lifts AOV to ₹380.",
        common_traps=["Raising item grocery prices above MRP, which violates Indian law and triggers app uninstalls.", "Cutting delivery rider payouts causing rider strikes and SLA failures.", "Eliminating fast 10-minute delivery entirely."],
        takeaway_lesson="In ultra-fast delivery where logistics cost per drop is fixed, profitability requires basket-building threshold pricing and upfront subscription memberships that subsidize delivery fees.",
        suggested_readings=["knowledge_base/industries/02_ecommerce_and_marketplaces.md", "knowledge_base/case_types/pricing_strategy.md", "knowledge_base/methodology/04_data_gathering_and_notes.md"],
        facts=[
            {"id": "order.volume", "domain": "company", "release_level": "broad_context", "content": "Platform fulfills 800,000 daily orders across 650 dark stores with average delivery time of 11.4 minutes."},
            {"id": "unit.economics", "domain": "economics", "release_level": "sharp_question", "content": "On an average ₹220 order: product margin is ₹40 (18%), dark store pick/pack is ₹16, rider delivery payout is ₹44, payment/tech is ₹2, resulting in -₹22 contribution."},
            {"id": "basket.distribution", "domain": "customers", "release_level": "hypothesis_backed", "content": "Orders below ₹199 represent 42% of volume and lose ₹34 per order; orders above ₹399 generate +₹18 positive contribution.", "dependencies": ["unit.economics"]},
            {"id": "handling.fee", "domain": "pricing", "release_level": "hypothesis_backed", "content": "Testing a ₹4 handling fee and ₹25 delivery fee on orders below ₹249 reduced small order volume by only 8% while raising AOV by 24%.", "dependencies": ["basket.distribution"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Loss of ₹22/order is driven by 42% of orders being small baskets (<₹199) with free delivery where fixed ₹60 fulfillment cost exceeds ₹32 margin; solution requires ₹299 free-delivery threshold, ₹4 handling fee, and VIP subscription."},
            {"id": "recommendation.threshold", "domain": "recommendation", "release_level": "synthesis_support", "content": "Set free delivery threshold at ₹299; charge tiered ₹25 delivery fee for orders below ₹199 and ₹15 for ₹199-₹299."},
            {"id": "recommendation.handling_fee", "domain": "recommendation", "release_level": "synthesis_support", "content": "Implement a universal ₹4-₹6 rain/peak handling fee on all orders during surge hours."},
            {"id": "recommendation.vip_club", "domain": "recommendation", "release_level": "synthesis_support", "content": "Launch paid 'QuickPass' subscription (₹99/quarter) offering free delivery above ₹199 to lock in high-frequency power shoppers."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.qcommerce-pricing", root_label="Achieve positive unit contribution margin in quick-commerce delivery.",
            branches=[
                {"id": "order-level-cost-stack", "label": "Fulfillment Cost Stack vs Take-Rate Margin", "conclusion": "Fixed fulfillment cost (₹60) exceeds product margin (₹40 on ₹220 AOV), losing ₹22/order."},
                {"id": "basket-size-distribution", "label": "Basket Size Breakdown & Loss Contribution", "conclusion": "Sub-₹199 orders are 42% of volume and lose ₹34/drop; ₹399+ orders are profitable (+₹18)."},
                {"id": "fee-elasticity-and-pass", "label": "Delivery Fee Elasticity & VIP Pass Model", "conclusion": "Small delivery fees lift AOV by 24% with minimal churn; VIP pass drives basket bundling."}
            ],
            diagnosis={"label": "Small Basket Free Delivery Subsidy Bleed", "evidence": ["order-level-cost-stack", "basket-size-distribution", "fee-elasticity-and-pass"], "conclusion": "Quick commerce loses ₹22/order because free delivery on sub-₹199 orders fails to cover fixed ₹60 dark store and rider fulfillment costs."},
            recommendation={"label": "3-Pillar Quick-Commerce Pricing Strategy", "evidence": ["diagnosis"], "conclusion": "Enforce ₹299 free delivery threshold, introduce surge handling fees, and launch paid quarterly VIP subscription."},
            routes=[{"id": "unit-cost-first", "sequence": ["order-level-cost-stack", "basket-size-distribution", "fee-elasticity-and-pass", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate through per-order cost stack analysis."}],
            recovery=["Ask candidate to calculate profit contribution on a ₹150 order vs a ₹450 order.", "Clarify that rider payouts of ₹44 are non-negotiable.", "Redirect toward minimum order value thresholds and paid VIP subscriptions."]
        )
    )

    # Case 24: Drug Pricing (Oncology)
    emit_case(
        school_dir="iima", slug="24-drug-pricing", title="Specialty Oncology Drug Pricing", school_tag="IIM-A",
        category="pricing", industry="pharma_and_healthcare", difficulty="advanced",
        opening_context="Your client is a multinational pharmaceutical company launching a breakthrough immunotherapy drug for lung cancer in India. US price is $120,000/year, but Indian out-of-pocket healthcare market requires a localized market access pricing strategy.",
        opening_objective="Design an optimal pricing and patient access program to maximize revenue and patient coverage in India.",
        decision_question="What pricing and patient assistance model should the pharma company adopt for its oncology launch in India?",
        primary_metric="Commercial Revenue and Patient Access Reach", time_horizon="two years",
        core_mechanism="High out-of-pocket expenditure (70% non-insured) in India vs US insurance reimbursement; standard global reference pricing creates zero volume, while simple price slashing triggers international gray-market re-export arbitrage and reference price erosion in Europe.",
        what_wanted_to_test="Tiered healthcare pricing, international reference pricing (IRP) arbitrage protection, Patient Assistance Programs (PAP), and outcome-based risk sharing.",
        pivotal_insight="A headline price cut destroys global reference pricing; the company must maintain a high nominal MRP while implementing an outcome-based Patient Assistance Program ('Buy 2 cycles, get 4 free' with full refund upon disease progression).",
        common_traps=["Recommending selling at generic cost-plus pricing ($2,000/yr), which collapses company reference prices across emerging markets.", "Assuming private Indian health insurance will fully cover $120,000 annual therapy.", "Ignoring parallel gray-market re-export risks to high-price European markets."],
        takeaway_lesson="In global specialty pharmaceuticals, expanding access into emerging markets without eroding global reference prices requires innovative Patient Assistance Programs and outcome-linked risk sharing.",
        suggested_readings=["knowledge_base/industries/03_pharma_and_healthcare.md", "knowledge_base/case_types/pricing_strategy.md", "knowledge_base/methodology/04_data_gathering_and_notes.md"],
        facts=[
            {"id": "drug.efficacy", "domain": "company", "release_level": "broad_context", "content": "Drug extends median progression-free survival by 14 months in Stage IV non-small cell lung cancer."},
            {"id": "market.demographics", "domain": "customers", "release_level": "sharp_question", "content": "India has 75,000 eligible lung cancer patients annually; only 8% have private insurance covering specialty oncology biologics."},
            {"id": "reference_price.risk", "domain": "regulation", "release_level": "hypothesis_backed", "content": "European and Middle Eastern health authorities benchmark Indian official invoice prices to negotiate mandatory discounts.", "dependencies": ["market.demographics"]},
            {"id": "affordability.curve", "domain": "economics", "release_level": "hypothesis_backed", "content": "Affordability analysis shows 12,000 patients can afford ₹15 lakh ($18k) total therapy; only 400 patients can afford full US price of ₹1 Cr ($120k).", "dependencies": ["reference_price.risk"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Direct price cuts would trigger international reference price erosion in Europe; company must protect nominal MRP while capturing the 12,000-patient segment via an innovative 2-for-4 Patient Assistance Program and outcome-linked refunds."},
            {"id": "recommendation.pap", "domain": "recommendation", "release_level": "synthesis_support", "content": "Structure a tiered Patient Assistance Program (e.g. 'Pay for 2 cycles, receive subsequent 4 cycles free') preserving official invoice MRP."},
            {"id": "recommendation.risk_share", "domain": "recommendation", "release_level": "synthesis_support", "content": "Offer 100% money-back guarantee to hospitals if patient disease progresses within the first 60 days of therapy."},
            {"id": "recommendation.anti_diversion", "domain": "recommendation", "release_level": "synthesis_support", "content": "Apply unique serialized 2D matrix barcoding and track vial administration in designated partner hospitals to block gray-market export."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.oncology-pricing", root_label="Design localized market access and pricing strategy for oncology launch.",
            branches=[
                {"id": "patient-affordability", "label": "Patient Demographics & Out-of-Pocket WTP", "conclusion": "70% of spend is out-of-pocket; 12,000 patients can afford ₹15L vs 400 at US list price."},
                {"id": "global-reference-pricing", "label": "International Reference Pricing (IRP) Risks", "conclusion": "Direct official price cuts in India trigger mandatory price reductions across Europe/Middle East."},
                {"id": "commercial-access-models", "label": "Patient Assistance Programs & Outcome Sharing", "conclusion": "PAP free-cycle structures and outcome-based guarantees expand volume while protecting nominal MRP."}
            ],
            diagnosis={"label": "Global IRP Conflict vs Domestic Affordability", "evidence": ["patient-affordability", "global-reference-pricing", "commercial-access-models"], "conclusion": "A direct price cut triggers global reference price collapse in Europe; company must deploy a tiered Patient Assistance Program (PAP) with outcome guarantees."},
            recommendation={"label": "3-Pillar Market Access Framework", "evidence": ["diagnosis"], "conclusion": "Deploy 'Buy 2 Get 4 Free' PAP, offer 60-day progression refund guarantee, and enforce serialized anti-diversion tracking."},
            routes=[{"id": "pricing-first", "sequence": ["patient-affordability", "global-reference-pricing", "commercial-access-models", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from Indian WTP to international reference price implications."}],
            recovery=["Ask candidate what happens if European health authorities see an 80% price cut in India.", "Clarify that Indian insurance covers very few cancer patients.", "Redirect toward Patient Assistance Programs and outcome-based risk sharing."]
        )
    )

    # Case 25: GenAI in International Bank
    emit_case(
        school_dir="iima", slug="25-genai-bank", title="GenAI Wealth Advisory Compliance", school_tag="IIM-A",
        category="unconventional_and_abstract", industry="banking_and_financial_services", difficulty="advanced",
        opening_context="Your client is a global private bank with $200B AUM. It piloted a Generative AI copilot to automate investment advisory suitability compliance notes, but senior wealth managers reject the tool and compliance audit failure rate is 26%.",
        opening_objective="Diagnose the GenAI adoption and accuracy failure and propose a hybrid human-AI compliance operating model.",
        decision_question="Why did the GenAI advisory compliance pilot fail and how should the human-in-the-loop workflow be redesigned?",
        primary_metric="Audit Compliance Pass Rate (%) and Advisor Time Saved per Note (hours)", time_horizon="six months",
        core_mechanism="Hallucination risk in portfolio regulatory disclosures and legal liability assignment. When AI generated erroneous suitability justifications, compliance held the human advisor legally liable, so advisors spent more time fact-checking AI notes than drafting them manually.",
        what_wanted_to_test="Enterprise GenAI adoption, human-in-the-loop workflow engineering, regulatory liability allocation, and prompt grounding on structured client CRM data.",
        pivotal_insight="Advisors rejected GenAI not out of tech resistance, but because the bank imposed 100% personal regulatory liability on advisors for any AI hallucination without providing verification source-attribution citations.",
        common_traps=["Blaming advisors as technologically incompetent or change-resistant.", "Switching foundation LLM model providers expecting zero hallucinations in complex wealth regulation.", "Removing human oversight and automating client investment sign-offs completely."],
        takeaway_lesson="In high-liability regulated industries, enterprise GenAI succeeds only when the interface provides verifiable source-citation provenance and operating procedures shift from manual editing to structured human verification gates.",
        suggested_readings=["knowledge_base/industries/04_banking_and_financial_services.md", "knowledge_base/case_types/unconventional_and_abstract.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "bank.pilot", "domain": "company", "release_level": "broad_context", "content": "Pilot deployed to 250 private wealth advisors in Singapore and Mumbai generating 5,000 monthly investment suitability memos."},
            {"id": "audit.failure", "domain": "risk", "release_level": "sharp_question", "content": "Compliance audits flagged a 26% failure rate due to inaccurate risk tolerance citations and hallucinated product disclosures."},
            {"id": "advisor.workflow", "domain": "operations", "release_level": "hypothesis_backed", "content": "Advisors spend 45 minutes editing each AI draft (vs 30 minutes writing manually from scratch) because AI output lacked source document citations.", "dependencies": ["audit.failure"]},
            {"id": "liability.policy", "domain": "governance", "release_level": "hypothesis_backed", "content": "Bank compliance policy mandates that human advisors face personal regulatory fines and disciplinary action for any factual error in submitted notes.", "dependencies": ["advisor.workflow"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "GenAI pilot failed because 100% personal liability was assigned to advisors while AI generated ungrounded notes with no citation links, forcing advisors to spend more time fact-checking than writing from scratch."},
            {"id": "recommendation.rag", "domain": "recommendation", "release_level": "synthesis_support", "content": "Re-engineer copilot with Retrieval-Augmented Generation (RAG) providing clickable sentence-by-sentence citations to CRM transcripts and portfolio data."},
            {"id": "recommendation.workflow_gate", "domain": "recommendation", "release_level": "synthesis_support", "content": "Introduce structured 3-click verification checklist where advisors validate key risk assumptions rather than editing raw prose."},
            {"id": "recommendation.governance", "domain": "recommendation", "release_level": "synthesis_support", "content": "Establish clear institutional safe-harbor rules and automated compliance pre-screening before formal submission."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.genai-compliance", root_label="Fix GenAI wealth advisory copilot adoption and compliance audit accuracy.",
            branches=[
                {"id": "audit-failures-and-hallucinations", "label": "Compliance Audit Failure Modes", "conclusion": "26% audit failure rate caused by ungrounded risk citations and product hallucinations."},
                {"id": "advisor-workflow-friction", "label": "Time-to-Draft & Verification Overhead", "conclusion": "Advisors spend 45 mins verifying un-cited AI notes vs 30 mins writing from scratch."},
                {"id": "liability-and-governance", "label": "Regulatory Liability Allocation & RAG Tooling", "conclusion": "Advisors bear 100% personal liability without citation tooling to verify claims quickly."}
            ],
            diagnosis={"label": "Ungrounded AI Drafts & Advisor Liability Burden", "evidence": ["audit-failures-and-hallucinations", "advisor-workflow-friction", "liability-and-governance"], "conclusion": "Pilot failed because advisors bear full regulatory liability for AI output that lacks verifiable source citations, making verification slower than manual drafting."},
            recommendation={"label": "3-Pillar Enterprise GenAI Governance", "evidence": ["diagnosis"], "conclusion": "Deploy RAG with clickable source citations, replace prose editing with a 3-click verification gate, and establish institutional safe-harbor rules."},
            routes=[{"id": "workflow-first", "sequence": ["audit-failures-and-hallucinations", "advisor-workflow-friction", "liability-and-governance", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from audit error rates to advisor liability and verification friction."}],
            recovery=["Ask candidate why advisors take longer to edit an AI draft than write from scratch.", "Clarify that the underlying CRM data is accurate.", "Redirect toward citation transparency, verification UI, and regulatory liability allocation."]
        )
    )

    print("Successfully generated all 25 IIMA exemplar cases!")


if __name__ == "__main__":
    generate_all_iima_cases()
