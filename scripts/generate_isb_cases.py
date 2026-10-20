"""Generator for all 12 Indian School of Business (ISB) Exemplar Case Packages under corpus/exemplars/isb/."""

from __future__ import annotations
from scripts.generate_exemplars import emit_case, make_standard_tree


def generate_all_isb_cases():
    print("Generating all 12 ISB exemplar cases...")

    # Case 1: BNPL Default Containment
    emit_case(
        school_dir="isb", slug="01-fintech-bnpl-default", title="Fintech BNPL Credit Risk", school_tag="ISB",
        category="operations", industry="fintech_and_payments", difficulty="intermediate",
        opening_context="Your client is a venture-backed Buy-Now-Pay-Later (BNPL) checkout fintech integrated across 20,000 Indian e-commerce merchants. First-payment default (FPD) rates on new user checkouts jumped from 4.2% to 11.8%, eroding unit margins.",
        opening_objective="Diagnose the drivers of BNPL first-payment default and design a real-time risk-gating underwriting model.",
        decision_question="Why did BNPL first-payment defaults surge and how should checkout friction vs credit risk be optimized?",
        primary_metric="First-Payment Default (FPD %) and Checkout Conversion Rate (%)", time_horizon="six months",
        core_mechanism="Frictionless instant onboarding with zero credit bureau verification for sub-₹2,000 purchases exploited by bot syndicates and synthetic identity fraud during festive sales.",
        what_wanted_to_test="Fintech checkout friction vs fraud trade-off, device fingerprinting, transaction velocity gating, and post-purchase credit limit escalation.",
        pivotal_insight="Removing all OTP/identity steps to boost merchant conversion attracted fraud rings targeting high-liquidity electronics and gift cards; introducing silent device-binding and merchant SKU category risk-gating cuts fraud by 70% with zero checkout drop-off.",
        common_traps=["Requiring a full 5-minute PAN/Aadhaar video KYC for every ₹500 purchase, which destroys merchant checkout conversion by 60%.", "Stopping all lending on e-commerce platforms.", "Assuming honest consumers suddenly stopped paying EMIs."],
        takeaway_lesson="In instant embedded fintech lending, sub-second underwriting must rely on silent device and transaction behavioral telemetry rather than heavy user-facing verification friction.",
        suggested_readings=["knowledge_base/industries/15_fintech_and_payments.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "bnpl.scale", "domain": "company", "release_level": "broad_context", "content": "Fintech processes 2.5M monthly BNPL transactions with an average ticket size of ₹1,850."},
            {"id": "fpd.surge", "domain": "financials", "release_level": "sharp_question", "content": "FPD jumped to 11.8%, resulting in ₹38 Cr in monthly credit write-offs."},
            {"id": "fraud.pattern", "domain": "risk", "release_level": "hypothesis_backed", "content": "82% of defaults cluster in digital gift vouchers, gaming credits, and mobile phones ordered to temporary addresses from emulator devices.", "dependencies": ["fpd.surge"]},
            {"id": "device.telemetry", "domain": "operations", "release_level": "hypothesis_backed", "content": "Implementing automated device-ID hashing, SIM-binding, and IP velocity limits flags 88% of fraudulent checkouts without user friction.", "dependencies": ["fraud.pattern"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "FPD surged to 11.8% because frictionless 1-click checkout was exploited by emulator fraud syndicates buying liquid vouchers; solution requires silent device-fingerprinting and category-level risk gating."},
            {"id": "recommendation.device_risk", "domain": "recommendation", "release_level": "synthesis_support", "content": "Deploy silent SDK device fingerprinting, emulator detection, and SIM-binding on all merchant checkout pages."},
            {"id": "recommendation.category_gating", "domain": "recommendation", "release_level": "synthesis_support", "content": "Require step-up UPI autopay mandate authentication for high-risk digital gift cards and electronics."},
            {"id": "recommendation.graduated_limits", "domain": "recommendation", "release_level": "synthesis_support", "content": "Start new users with a conservative ₹1,000 credit line, escalating dynamically only after 2 on-time repayment cycles."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.bnpl-fpd", root_label="Reduce BNPL first-payment default rate from 11.8% to under 4%.",
            branches=[
                {"id": "default-concentration-by-sku", "label": "SKU Category & Merchant Risk Clustering", "conclusion": "82% of defaults occur in digital vouchers and electronics ordered via emulators."},
                {"id": "underwriting-friction-vs-conversion", "label": "Instant Checkout vs Bureau KYC Friction", "conclusion": "Zero friction enabled syndicate abuse; heavy manual KYC causes 60% checkout drop-off."},
                {"id": "silent-telemetry-defense", "label": "Device Fingerprinting & Velocity Gating", "conclusion": "Silent SIM/device binding blocks 88% of fraud with zero user friction."}
            ],
            diagnosis={"label": "Frictionless Checkout Vulnerability to Emulator Syndicates", "evidence": ["default-concentration-by-sku", "underwriting-friction-vs-conversion", "silent-telemetry-defense"], "conclusion": "Defaults exploded because frictionless checkout lacked basic device risk verification, allowing fraud rings to liquidate digital vouchers; silent telemetry restores risk control."},
            recommendation={"label": "3-Pillar Embedded Risk Architecture", "evidence": ["diagnosis"], "conclusion": "Implement silent device SDK risk scoring, enforce step-up auth on liquid SKUs, and use graduated credit limits."},
            routes=[{"id": "risk-first", "sequence": ["default-concentration-by-sku", "underwriting-friction-vs-conversion", "silent-telemetry-defense", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from fraud category concentration to silent technical verification solutions."}],
            recovery=["Ask candidate which product categories have the highest default rates.", "Clarify that genuine fashion/grocery buyers have low default rates.", "Redirect toward silent device fingerprinting and graduated credit limits."]
        )
    )

    # Case 2: SaaS Cross-Sell (Enterprise NRR)
    emit_case(
        school_dir="isb", slug="02-saas-cross-sell", title="Enterprise SaaS Net Revenue Retention", school_tag="ISB",
        category="growth_strategy", industry="saas_and_b2b_tech", difficulty="intermediate",
        opening_context="Your client is a high-growth B2B enterprise SaaS platform with $60M ARR. Net Revenue Retention (NRR) has slipped from 124% to 102%, depressing software valuation multiples.",
        opening_objective="Diagnose expansion revenue stalls and design a multi-product cross-selling and consumption-based packaging model.",
        decision_question="Why did SaaS NRR decelerate and how should cross-selling and usage-based pricing be restructured?",
        primary_metric="Net Revenue Retention (NRR %) and Multi-Product Customer Share (%)", time_horizon="twelve months",
        core_mechanism="Siloed sales compensation and product fragmentation. Account executives were rewarded exclusively on new customer logos rather than account expansion, while the 3 standalone software modules had separate logins, un-integrated data, and conflicting pricing tiers.",
        what_wanted_to_test="B2B SaaS metrics (CAC, LTV, NRR, GRR), seat-based vs consumption pricing, customer success alignment, and product suite bundling.",
        pivotal_insight="80% of enterprise customers use only 1 core module; customer success managers have no quota for upsell, while fragmented pricing makes purchasing secondary modules require a full procurement contract cycle.",
        common_traps=["Assuming customer logo churn is the problem (Gross Revenue Retention is healthy at 94%).", "Blaming engineering software downtime for lack of expansion.", "Cutting software license prices across the board."],
        takeaway_lesson="In enterprise SaaS, high NRR requires unifying fragmented products into a single modular platform and aligning Customer Success compensation with net expansion quotas.",
        suggested_readings=["knowledge_base/industries/08_saas_and_b2b_tech.md", "knowledge_base/case_types/growth_strategy.md", "knowledge_base/methodology/01_preliminary_questions.md"],
        facts=[
            {"id": "saas.metrics", "domain": "company", "release_level": "broad_context", "content": "Client has 850 enterprise clients with $60M ARR; Gross Revenue Retention is 94%, but NRR dropped to 102%."},
            {"id": "module.adoption", "domain": "product", "release_level": "sharp_question", "content": "Only 14% of clients adopt more than 1 module; Module 2 (Analytics) and Module 3 (Automation) are sold as separate standalone contracts."},
            {"id": "sales.comp", "domain": "operations", "release_level": "hypothesis_backed", "content": "Account Executives receive 12% commission on new logos and 0% on renewals/upsells; Customer Success managers manage support tickets with zero commercial quotas.", "dependencies": ["module.adoption"]},
            {"id": "platform.integration", "domain": "product", "release_level": "hypothesis_backed", "content": "Modules require separate user logins and do not share unified data schemas, creating IT integration friction for enterprise buyers.", "dependencies": ["sales.comp"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "NRR dropped to 102% because secondary modules are sold as fragmented standalone tools with separate logins, and sales compensation ignores account expansion in favor of new logos."},
            {"id": "recommendation.unified_platform", "domain": "recommendation", "release_level": "synthesis_support", "content": "Unify all 3 modules into a single modular platform with unified Single Sign-On (SSO) and shared data analytics."},
            {"id": "recommendation.account_expansion", "domain": "recommendation", "release_level": "synthesis_support", "content": "Create a dedicated Account Management expansion team compensated on Net Expansion ARR with 130% target tiers."},
            {"id": "recommendation.product_led_growth", "domain": "recommendation", "release_level": "synthesis_support", "content": "Introduce in-app free trials of secondary modules with 1-click credit-card or invoice add-ons."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.saas-nrr", root_label="Accelerate enterprise SaaS Net Revenue Retention from 102% to 125%+.",
            branches=[
                {"id": "nrr-decomposition", "label": "Gross Churn vs Net Expansion Breakdown", "conclusion": "Gross churn is low (6%); failure is lack of account expansion and upsell."},
                {"id": "multi-product-friction", "label": "Product Architecture & Integration Hurdles", "conclusion": "Separate logins and fragmented contracts restrict secondary module adoption to 14%."},
                {"id": "incentive-alignment", "label": "Sales Compensation & Customer Success Quotas", "conclusion": "Sales team is incentivized 100% on new logos with zero rewards for expansion."}
            ],
            diagnosis={"label": "Fragmented Product Silos & Misaligned Compensation", "evidence": ["nrr-decomposition", "multi-product-friction", "incentive-alignment"], "conclusion": "NRR stalled because secondary products operate as disconnected tools requiring separate contracts, and commercial teams are not compensated for account expansion."},
            recommendation={"label": "3-Pillar Enterprise NRR Acceleration Plan", "evidence": ["diagnosis"], "conclusion": "Unify product suite on single SSO platform, build dedicated expansion account management team, and enable in-app product-led upgrades."},
            routes=[{"id": "metrics-first", "sequence": ["nrr-decomposition", "multi-product-friction", "incentive-alignment", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate to unbundle NRR into gross retention vs expansion revenue."}],
            recovery=["Ask candidate to compare Gross Retention (94%) with Net Retention (102%).", "Clarify that customers are not churning, but not spending more over time.", "Redirect toward multi-product adoption and sales incentive structures."]
        )
    )

    # Case 3: Cloud Migration Cost Runaway
    emit_case(
        school_dir="isb", slug="03-cloud-migration-cost", title="Cloud Migration Infrastructure Cost", school_tag="ISB",
        category="digital_transformation", industry="saas_and_b2b_tech", difficulty="intermediate",
        opening_context="Your client is a top Indian private bank that migrated its core retail digital banking apps to public cloud (AWS/Azure). Monthly cloud operating expenditure ballooned from ₹4 Cr to ₹16 Cr, exceeding business case forecasts by 300%.",
        opening_objective="Diagnose the cloud cost runaway and design a FinOps governance and reserved instance optimization framework.",
        decision_question="Why did public cloud costs explode post-migration and how can cloud infrastructure spend be optimized by 40%?",
        primary_metric="Monthly Cloud OpEx (₹ Cr) and Compute Utilization Efficiency (%)", time_horizon="six months",
        core_mechanism="Lift-and-shift architecture with unreserved on-demand compute instances and unmonitored dev/test environments. Engineering teams provisioned peak-capacity uncompressed virtual machines 24/7 on expensive on-demand pricing with zero auto-scaling or reserved instance commitments.",
        what_wanted_to_test="Cloud economics, lift-and-shift vs cloud-native refactoring, on-demand vs reserved instances/savings plans, and FinOps unit governance.",
        pivotal_insight="Bank developers treated the cloud like infinite corporate on-premise hardware, leaving 450 oversized test servers running 24/7 on on-demand rates; switching to 3-year Savings Plans, automated overnight shutdown, and auto-scaling saves 48% immediately.",
        common_traps=["Recommending migrating everything back to legacy physical on-premise data centers.", "Blaming cloud provider data egress network fees without checking compute instance utilization.", "Assuming cybersecurity compliance tools caused the bill explosion."],
        takeaway_lesson="Cloud migration without architectural modernization (auto-scaling) and FinOps commercial governance (reserved commitments) turns variable agility into runaway fixed operating costs.",
        suggested_readings=["knowledge_base/industries/08_saas_and_b2b_tech.md", "knowledge_base/case_types/growth_strategy.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "cloud.footprint", "domain": "company", "release_level": "broad_context", "content": "Bank migrated 140 retail banking microservices to public cloud across 1,800 virtual compute instances."},
            {"id": "bill.breakdown", "domain": "financials", "release_level": "sharp_question", "content": "Monthly bill is ₹16.2 Cr; compute instances represent 68%, storage 18%, network/data egress 14%."},
            {"id": "utilization.waste", "domain": "operations", "release_level": "hypothesis_backed", "content": "Average CPU utilization across all provisioned cloud instances is only 14%; 600 development/QA environments run 24/7 on weekends.", "dependencies": ["bill.breakdown"]},
            {"id": "pricing.commitment", "domain": "pricing", "release_level": "hypothesis_backed", "content": "92% of workloads run on expensive on-demand hourly pricing; bank committed zero 1-year or 3-year Reserved Instances or Compute Savings Plans.", "dependencies": ["utilization.waste"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Cloud cost exploded to ₹16 Cr/month because workloads run on 100% on-demand rates with 14% average CPU utilization and unmanaged 24/7 dev environments; FinOps governance and 3-year Savings Plans reduce spend by 48%."},
            {"id": "recommendation.commitments", "domain": "recommendation", "release_level": "synthesis_support", "content": "Purchase 3-year Compute Savings Plans for steady-state production workloads, securing a 60% hourly discount."},
            {"id": "recommendation.rightsizer", "domain": "recommendation", "release_level": "synthesis_support", "content": "Right-size oversized virtual machines and deploy automated horizontal pod autoscaling (HPA) to match diurnal banking traffic."},
            {"id": "recommendation.dev_governance", "domain": "recommendation", "release_level": "synthesis_support", "content": "Implement automated cron schedules to shut down all non-production dev/QA environments during nights and weekends."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.cloud-cost-finops", root_label="Reduce monthly cloud OpEx from ₹16 Cr to under ₹9 Cr.",
            branches=[
                {"id": "cost-category-decomposition", "label": "Compute vs Storage vs Network Breakdown", "conclusion": "Compute is 68% of spend; compute instances are provisioned on-demand."},
                {"id": "workload-utilization-efficiency", "label": "CPU/RAM Utilization & Idle Dev Environments", "conclusion": "Average CPU is 14%; 600 dev servers run un-utilized on weekends."},
                {"id": "commercial-pricing-models", "label": "On-Demand vs Reserved Instances / Savings Plans", "conclusion": "Zero reserved commitments exist, paying 2.5x standard discounted rates."}
            ],
            diagnosis={"label": "Oversized On-Demand Instances & Idle Environments", "evidence": ["cost-category-decomposition", "workload-utilization-efficiency", "commercial-pricing-models"], "conclusion": "Cloud spend exploded due to lift-and-shift provisioning of oversized on-demand instances at 14% utilization without commercial savings plans or idle dev shutdowns."},
            recommendation={"label": "3-Pillar FinOps Optimization Roadmap", "evidence": ["diagnosis"], "conclusion": "Lock 3-year Savings Plans, right-size compute with auto-scaling, and enforce automated non-prod environment shutdowns."},
            routes=[{"id": "bill-first", "sequence": ["cost-category-decomposition", "workload-utilization-efficiency", "commercial-pricing-models", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from monthly bill line items to compute utilization and pricing commitments."}],
            recovery=["Ask candidate to check the average CPU utilization of the cloud servers.", "Clarify that the bank has zero reserved instance contracts.", "Redirect toward right-sizing compute instances and 3-year Savings Plans."]
        )
    )

    # Cases 4-12 for ISB
    # Case 4: Q-Commerce Dark Store
    emit_case(
        school_dir="isb", slug="04-qcommerce-dark-store", title="Quick-Commerce Dark Store Density", school_tag="ISB",
        category="operations", industry="ecommerce_and_marketplaces", difficulty="intermediate",
        opening_context="Your client operates 300 quick-commerce dark stores across 5 Indian metros. Dark store EBITDA is negative (-8%) due to high picker-packer labor overhead and rider idle waiting time.",
        opening_objective="Optimize dark store layout, batch-picking algorithms, and rider dispatch to achieve dark store EBITDA breakeven.",
        decision_question="How should dark store operations and order batching be re-engineered to achieve store-level profitability?",
        primary_metric="Dark Store EBITDA Margin (%) and Orders Picked Per Man-Hour", time_horizon="six months",
        core_mechanism="Pick-path congestion and un-batched order picking. Pickers walk 140 meters per single order across poorly mapped aisles, while delivery riders wait 6.5 minutes outside for packing completion, destroying labor productivity.",
        what_wanted_to_test="Warehouse layout optimization, pick-path routing algorithms, wave vs batch picking, and dispatch synchronization.",
        pivotal_insight="Re-organizing dark stores with top-100 high-velocity SKUs near the packing station and implementing multi-order batch picking cuts picker walking distance by 65% and doubles picks per hour.",
        common_traps=["Assuming store rent in city centers is the sole cause of store losses.", "Cutting dark store staff, which causes order fulfillment times to miss the 10-minute SLA.", "Expanding store square footage."],
        takeaway_lesson="In micro-fulfillment, picker walking distance is the primary labor bottleneck; high-density golden-zone slotting and multi-order batching double labor productivity.",
        suggested_readings=["knowledge_base/industries/02_ecommerce_and_marketplaces.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/02_issue_tree_structuring.md"],
        facts=[
            {"id": "store.profile", "domain": "company", "release_level": "broad_context", "content": "Dark stores average 2,500 sq ft, carrying 3,200 SKUs and fulfilling 1,200 orders/day."},
            {"id": "picker.productivity", "domain": "operations", "release_level": "sharp_question", "content": "Picker productivity is only 18 orders/man-hour; pickers spend 72% of their time walking aisles looking for items."},
            {"id": "layout.slotting", "domain": "operations", "release_level": "hypothesis_backed", "content": "High-velocity dairy and snacks are placed at the back of the store, forcing pickers to traverse the entire 2,500 sq ft space for 80% of orders.", "dependencies": ["picker.productivity"]},
            {"id": "batching.impact", "domain": "operations", "release_level": "hypothesis_backed", "content": "Piloting dynamic 3-order batch picking with LED pick-to-light sorting carts cut order pick time from 210 seconds to 65 seconds.", "dependencies": ["layout.slotting"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Dark store losses are driven by low labor productivity (18 picks/hr) caused by suboptimal layout slotting and single-order picking; high-velocity golden-zone layout and 3-order batching double throughput to 40 picks/hr."},
            {"id": "recommendation.golden_zone", "domain": "recommendation", "release_level": "synthesis_support", "content": "Re-slot top-150 fastest-moving SKUs into a 'Golden Zone' 3 meters from the dispatch counter."},
            {"id": "recommendation.batch_picking", "domain": "recommendation", "release_level": "synthesis_support", "content": "Deploy smart multi-order batch-picking carts equipped with barcode scanners and pick-to-light compartments."},
            {"id": "recommendation.dispatch_sync", "domain": "recommendation", "release_level": "synthesis_support", "content": "Synchronize rider dispatch algorithms to assign riders only when order picking hits 80% completion, cutting rider wait time to <90 seconds."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.darkstore-ebitda", root_label="Optimize dark store labor productivity and achieve store EBITDA breakeven.",
            branches=[
                {"id": "labor-cost-and-productivity", "label": "Picker Productivity & Labor Cost per Order", "conclusion": "Pickers fulfill only 18 orders/hr, spending 72% of time walking aisles."},
                {"id": "store-layout-and-slotting", "label": "SKU Placement & High-Velocity Golden Zones", "conclusion": "Fast-moving dairy/snacks are located at the back, maximizing walking distance."},
                {"id": "order-batching-algorithms", "label": "Single-Order vs Multi-Order Batch Picking", "conclusion": "3-order batch picking with pick-to-light cuts pick time from 210s to 65s."}
            ],
            diagnosis={"label": "Suboptimal Layout Slotting & Single-Order Walking Waste", "evidence": ["labor-cost-and-productivity", "store-layout-and-slotting", "order-batching-algorithms"], "conclusion": "Dark stores lose money because poor layout slotting and single-order picking waste 72% of labor time walking; golden-zone re-slotting and batch carts double throughput."},
            recommendation={"label": "3-Pillar Micro-Fulfillment Overhaul", "evidence": ["diagnosis"], "conclusion": "Re-slot top SKUs in front Golden Zone, deploy 3-order batch-picking carts, and synchronize rider arrival dispatch."},
            routes=[{"id": "productivity-first", "sequence": ["labor-cost-and-productivity", "store-layout-and-slotting", "order-batching-algorithms", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from labor cost breakdown to warehouse slotting and batching."}],
            recovery=["Ask candidate what percentage of a picker's time is spent walking vs picking.", "Clarify that dark store inventory is in stock.", "Redirect toward SKU slotting near dispatch and multi-order batching."]
        )
    )

    # Case 5: EdTech CAC Optimization
    emit_case(
        school_dir="isb", slug="05-edtech-cac-optimization", title="EdTech Sales CAC Optimization", school_tag="ISB",
        category="growth_strategy", industry="saas_and_b2b_tech", difficulty="intermediate",
        opening_context="Your client is a K-12 live online tutoring platform in India. Customer Acquisition Cost (CAC) reached ₹22,000 on an annual course price of ₹35,000, eroding business viability.",
        opening_objective="Diagnose outbound tele-calling sales inefficiency and design a teacher-led referral and product-led growth acquisition model.",
        decision_question="How should the EdTech platform reduce customer acquisition cost from ₹22,000 to under ₹8,000?",
        primary_metric="Blended Customer Acquisition Cost (CAC) and Lead Conversion Rate (%)", time_horizon="twelve months",
        core_mechanism="High burn outbound tele-calling sales engine. Buying cold parent phone numbers and employing 2,000 aggressive inside-sales reps led to a 0.8% lead conversion rate, high lead fatigue, and brand reputation damage.",
        what_wanted_to_test="EdTech unit economics, outbound tele-sales vs organic word-of-mouth, teacher-led student referrals, and freemium diagnostic test funnels.",
        pivotal_insight="Outbound tele-sales conversion is 0.8% at ₹24k CAC; students referred by school teachers or participating in free diagnostic olympiad tests convert at 14% with a CAC of ₹3,500.",
        common_traps=["Increasing cold calling volume with autodialers.", "Offering heavy 50% course discounts that degrade perceived academic quality.", "Spending more on celebrity Bollywood brand ambassador TV commercials."],
        takeaway_lesson="In consumer education where parental trust is paramount, aggressive outbound cold calling burns capital; sustainable acquisition requires teacher-endorsed organic referral loops and diagnostic academic funnels.",
        suggested_readings=["knowledge_base/industries/08_saas_and_b2b_tech.md", "knowledge_base/case_types/growth_strategy.md", "knowledge_base/methodology/01_preliminary_questions.md"],
        facts=[
            {"id": "edtech.model", "domain": "company", "release_level": "broad_context", "content": "Client enrols 60,000 K-12 students annually paying ₹35,000 for live math and science classes."},
            {"id": "sales.spend", "domain": "financials", "release_level": "sharp_question", "content": "Sales & marketing expenses represent 63% of total revenue; outbound sales force CAC is ₹22,500 per customer."},
            {"id": "lead.funnel", "domain": "operations", "release_level": "hypothesis_backed", "content": "Outbound sales conversion is 0.8% on purchased cold lead lists; parent rejection and spam blocking reached 76%.", "dependencies": ["sales.spend"]},
            {"id": "organic.referral", "domain": "customers", "release_level": "hypothesis_backed", "content": "Piloting free national diagnostic math benchmarking tests in 250 schools generated 45,000 qualified student leads with a 14.5% conversion rate at ₹3,200 CAC.", "dependencies": ["lead.funnel"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "CAC reached ₹22,000 because client relied on cold outbound tele-calling with a 0.8% conversion rate; shifting acquisition to school diagnostic benchmarking tests and teacher referrals slashes CAC to ₹4,000."},
            {"id": "recommendation.diagnostic_funnel", "domain": "recommendation", "release_level": "synthesis_support", "content": "Replace cold calling with free nationwide school diagnostic benchmarking assessments that deliver customized learning gap reports to parents."},
            {"id": "recommendation.teacher_advocates", "domain": "recommendation", "release_level": "synthesis_support", "content": "Establish a Teacher Ambassador Program offering free classroom teaching tools and academic referral grants."},
            {"id": "recommendation.sales_rebalance", "domain": "recommendation", "release_level": "synthesis_support", "content": "Downsize aggressive outbound cold-calling reps by 60% and transition remaining team into consultative academic counselors."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.edtech-cac", root_label="Reduce EdTech customer acquisition cost from ₹22,000 to under ₹8,000.",
            branches=[
                {"id": "outbound-sales-efficiency", "label": "Cold Outbound Tele-Sales Conversion", "conclusion": "Outbound tele-sales conversion is 0.8% at ₹22,500 CAC, generating high spam fatigue."},
                {"id": "inbound-diagnostic-funnels", "label": "School Diagnostic Olympiads & Inbound Leads", "conclusion": "School diagnostic assessments convert at 14.5% with ₹3,200 CAC."},
                {"id": "word-of-mouth-referrals", "label": "Parent & Teacher Referral Advocacy Loops", "conclusion": "Teacher-referred students have 2.5x higher 12-month retention rates."}
            ],
            diagnosis={"label": "Outbound Tele-Sales Burn & Inbound Academic Authority", "evidence": ["outbound-sales-efficiency", "inbound-diagnostic-funnels", "word-of-mouth-referrals"], "conclusion": "CAC is unsustainable due to 0.8% outbound cold-calling conversion; pivoting to school diagnostic gap assessments and teacher referrals cuts CAC by 70%."},
            recommendation={"label": "3-Pillar Academic Growth Strategy", "evidence": ["diagnosis"], "conclusion": "Deploy school diagnostic test funnels, launch teacher ambassador program, and restructure sales force into academic advisors."},
            routes=[{"id": "funnel-first", "sequence": ["outbound-sales-efficiency", "inbound-diagnostic-funnels", "word-of-mouth-referrals", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from sales team cost breakdown to conversion rates across acquisition channels."}],
            recovery=["Ask candidate what the conversion rate is on cold outbound phone calls.", "Clarify that parents trust school teachers over telemarketers.", "Redirect toward diagnostic academic testing funnels."]
        )
    )

    # Cases 6-12 continued
    # Case 6: Healthtech Teleconsultation
    emit_case(
        school_dir="isb", slug="06-healthtech-teleconsultation", title="Digital Healthcare Teleconsultation", school_tag="ISB",
        category="growth_strategy", industry="pharma_and_healthcare", difficulty="intermediate",
        opening_context="Your client is a digital healthcare platform in India with 15M registered app users. It offers free and ₹99 teleconsultations with general physicians, but 90% of users churn after a single session.",
        opening_objective="Design a recurring chronic disease management subscription model (diabetes, hypertension) to monetize user traffic.",
        decision_question="How should the teleconsultation app pivot from transactional one-off doctor chats to recurring chronic care subscriptions?",
        primary_metric="Customer Lifetime Value (LTV) to CAC Ratio and 90-Day Retention (%)", time_horizon="twelve months",
        core_mechanism="Transactional acute care trap. One-off teleconsults for cough/cold have zero recurring retention and high doctor payout costs (₹250/call), while managing chronic conditions (diabetes/hypertension) requires monthly medicine deliveries, diagnostic testing, and continuous dietary coaching.",
        what_wanted_to_test="Digital health unit economics, acute vs chronic care retention, care plan subscription bundling (teleconsult + diagnostics + pharmacy), and insurance integration.",
        pivotal_insight="Acute cough/cold users have 5% annual retention; chronic diabetic patients generate ₹18,000 annual spend across continuous glucose monitoring, lab tests, and monthly prescription refills with 72% retention.",
        common_traps=["Raising one-off GP consultation fees from ₹99 to ₹500, destroying user acquisition.", "Hiring thousands of full-time doctors onto the payroll without guaranteed demand.", "Ignoring medicine delivery and lab test cross-selling."],
        takeaway_lesson="In digital health, standalone teleconsultation is a low-margin customer acquisition funnel; profitability is captured by bundling recurring pharmacy refills and chronic condition monitoring.",
        suggested_readings=["knowledge_base/industries/03_pharma_and_healthcare.md", "knowledge_base/case_types/growth_strategy.md", "knowledge_base/methodology/01_preliminary_questions.md"],
        facts=[
            {"id": "user.base", "domain": "company", "release_level": "broad_context", "content": "App processes 400,000 monthly teleconsults, mostly for episodic acute fever/colds."},
            {"id": "unit.economics", "domain": "financials", "release_level": "sharp_question", "content": "Doctor payout is ₹220/call while user fee is ₹99, losing ₹121 per teleconsult with 91% user churn after 30 days."},
            {"id": "chronic.opportunity", "domain": "market", "release_level": "hypothesis_backed", "content": "32% of users are diagnosed with pre-diabetes, diabetes, or hypertension during consultations, but receive no structured follow-up care plan.", "dependencies": ["unit.economics"]},
            {"id": "care_plan.financials", "domain": "economics", "release_level": "hypothesis_backed", "content": "Diabetic Care Subscription (₹1,499/month) bundling connected glucometer, monthly lab tests, doctor reviews, and home medicine delivery delivers 42% gross margin and ₹9,200 LTV.", "dependencies": ["chronic.opportunity"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Teleconsult app loses ₹121/call because it operates as a one-off acute triage tool with 91% churn; pivoting to recurring chronic care management (diabetes/hypertension) lifts annual LTV from ₹180 to ₹9,200."},
            {"id": "recommendation.chronic_bundles", "domain": "recommendation", "release_level": "synthesis_support", "content": "Launch structured 3-month and 12-month Chronic Care Management plans for diabetes, cardiac health, and PCOS."},
            {"id": "recommendation.pharma_diagnostics", "domain": "recommendation", "release_level": "synthesis_support", "content": "Automate recurring home medicine refills and quarterly home diagnostic blood panels within the subscription."},
            {"id": "recommendation.corporate_wellness", "domain": "recommendation", "release_level": "synthesis_support", "content": "Package the chronic management subscription as an employer corporate wellness benefit co-funded by group health insurers."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.telehealth-monetization", root_label="Transform teleconsultation platform into a profitable chronic care ecosystem.",
            branches=[
                {"id": "acute-teleconsult-losses", "label": "Episodic Teleconsult Unit Economics & Churn", "conclusion": "Loses ₹121/call on subsidized ₹99 acute consults with 91% 30-day user churn."},
                {"id": "chronic-disease-market", "label": "Chronic Prevalence & Prescription Stickiness", "conclusion": "32% of users have chronic conditions requiring ongoing medicine and lab testing."},
                {"id": "care-plan-packaging", "label": "Subscription Bundling (Doctor + Lab + Pharmacy)", "conclusion": "Chronic care subscription delivers ₹9,200 LTV at 42% margin with 72% retention."}
            ],
            diagnosis={"label": "Acute Care Loss-Leader & Chronic Care Subscription Pivot", "evidence": ["acute-teleconsult-losses", "chronic-disease-market", "care-plan-packaging"], "conclusion": "Platform burns money on one-off acute consultations; monetization requires converting the 32% chronic patient cohort into recurring care management subscriptions."},
            recommendation={"label": "3-Pillar Digital Health Transformation", "evidence": ["diagnosis"], "conclusion": "Launch chronic care subscriptions, integrate automated pharmacy/lab fulfillment, and sell to corporate health plans."},
            routes=[{"id": "economics-first", "sequence": ["acute-teleconsult-losses", "chronic-disease-market", "care-plan-packaging", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from per-call economics to chronic subscription LTV."}],
            recovery=["Ask candidate how much recurring revenue an acute cough/cold patient generates vs a diabetic patient.", "Clarify that 32% of users have chronic illnesses.", "Redirect toward chronic disease care subscriptions and medicine delivery."]
        )
    )

    # Case 7: Gaming In-App Monetization
    emit_case(
        school_dir="isb", slug="07-gaming-in-app-monetization", title="Real-Money Gaming Tax & Liquidity", school_tag="ISB",
        category="pricing", industry="telecom_and_media", difficulty="advanced",
        opening_context="Your client is a top Indian real-money skill gaming platform (Poker and Rummy). The government introduced a 28% Goods and Services Tax (GST) on full contest entry amounts, threatening platform viability.",
        opening_objective="Redesign platform rake fees, tournament prize pools, and VIP loyalty rewards to absorb the 28% GST impact without user churn.",
        decision_question="How should platform rake and table prize pools be restructured under the 28% GST regime?",
        primary_metric="Monthly Active Depositors (MAD) and Net Gaming Revenue (NGR)", time_horizon="six months",
        core_mechanism="Tax incidence and table liquidity dynamics. Passing 100% of 28% GST directly to players reduces return-to-player (RTP) payouts, causing casual players to deplete their wallet balances 3x faster and churn.",
        what_wanted_to_test="Gaming platform economics, Gross Gaming Revenue (GGR) vs Net Gaming Revenue (NGR), rake fee elasticity, liquidity matchmaking, and player lifetime value.",
        pivotal_insight="If players lose money rapidly due to tax deductions, table liquidity collapses; subsidizing GST on initial deposit via bonus non-withdrawable gameplay credits increases playing velocity, generating enough incremental rake to offset tax costs.",
        common_traps=["Passing the entire 28% tax as a direct upfront deduction on player deposits, causing a 45% drop in player lifetime.", "Exiting skill gaming entirely to offer free casual games with low ad monetization.", "Attempting illegal offshore corporate tax avoidance."],
        takeaway_lesson="In transaction-taxed two-sided marketplace platforms, subsidizing player entry via gameplay bonus credits preserves marketplace liquidity and increases transaction velocity.",
        suggested_readings=["knowledge_base/industries/07_telecom_and_media.md", "knowledge_base/case_types/pricing_strategy.md", "knowledge_base/methodology/04_data_gathering_and_notes.md"],
        facts=[
            {"id": "gaming.scale", "domain": "company", "release_level": "broad_context", "content": "Platform has 4M monthly active players generating ₹400 Cr in monthly contest entry amounts."},
            {"id": "tax.shock", "domain": "regulation", "release_level": "sharp_question", "content": "New 28% GST applies on total face-value deposits rather than platform rake, increasing tax liability from ₹8 Cr to ₹112 Cr monthly."},
            {"id": "liquidity.drain", "domain": "operations", "release_level": "hypothesis_backed", "content": "Passing tax directly to players reduced casual player gameplay sessions from 14 to 4 per month, destroying table matchmaking liquidity.", "dependencies": ["tax.shock"]},
            {"id": "bonus.economics", "domain": "economics", "release_level": "hypothesis_backed", "content": "Offering 100% GST cashback as non-withdrawable discount gameplay credits retains 88% of depositors and lifts table rake turnover by 34%.", "dependencies": ["liquidity.drain"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Direct tax pass-through destroyed player liquidity and game velocity; platform must absorb GST via non-withdrawable gameplay discount credits, offset by dynamic rake optimization on high-stakes tables."},
            {"id": "recommendation.gst_cashback", "domain": "recommendation", "release_level": "synthesis_support", "content": "Credit 100% of GST paid as non-withdrawable gameplay discount chips usable exclusively to pay contest entry fees."},
            {"id": "recommendation.rake_optimization", "domain": "recommendation", "release_level": "synthesis_support", "content": "Adjust platform rake from 8% to 11% on high-stakes VIP tables while maintaining low 5% rake on casual micro-tables."},
            {"id": "recommendation.tds_simplification", "domain": "recommendation", "release_level": "synthesis_support", "content": "Automate net-winnings TDS tax calculations at annual fiscal year-end/withdrawal to maximize active player bankroll."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.gaming-gst-pivot", root_label="Restructure real-money gaming platform economics under 28% GST.",
            branches=[
                {"id": "tax-incidence-impact", "label": "28% Face-Value GST Tax Burden & NGR", "conclusion": "Tax jumped from ₹8 Cr to ₹112 Cr/mo, threatening viability if fully absorbed as pure cash."},
                {"id": "player-liquidity-and-churn", "label": "Player Wallet Depletion & Table Matchmaking", "conclusion": "Direct tax deduction dropped player sessions from 14 to 4, collapsing liquidity."},
                {"id": "gameplay-credit-mechanics", "label": "Non-Withdrawable Bonus Credits & Rake Velocity", "conclusion": "GST cashback in gameplay chips preserves 88% of depositors and increases rake velocity by 34%."}
            ],
            diagnosis={"label": "Table Liquidity Collapse & Gameplay Credit Shield", "evidence": ["tax-incidence-impact", "player-liquidity-and-churn", "gameplay-credit-mechanics"], "conclusion": "Passing 28% GST killed player liquidity; refunding GST as non-withdrawable gameplay chips preserves table velocity, funded by targeted VIP rake adjustments."},
            recommendation={"label": "3-Pillar Gaming Tax & Liquidity Strategy", "evidence": ["diagnosis"], "conclusion": "Issue 100% GST refund as gameplay bonus chips, tier platform rake by table stakes, and streamline withdrawal TDS automation."},
            routes=[{"id": "tax-first", "sequence": ["tax-incidence-impact", "player-liquidity-and-churn", "gameplay-credit-mechanics", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from GST tax math to player liquidity velocity."}],
            recovery=["Ask candidate what happens to player bankrolls when 28% is deducted immediately on deposit.", "Clarify that players need table liquidity to keep playing.", "Redirect toward non-withdrawable gameplay bonus credits and rake optimization."]
        )
    )

    # Case 8: OTT Vernacular Tiering
    emit_case(
        school_dir="isb", slug="08-ott-vernacular-tiering", title="Regional OTT Streaming Churn", school_tag="ISB",
        category="pricing", industry="telecom_and_media", difficulty="intermediate",
        opening_context="Your client is a leading South Indian regional vernacular OTT streaming service with 5M paid subscribers. Annual subscriber churn is 58%, and customer acquisition cost via digital ads is exceeding customer lifetime value.",
        opening_objective="Diagnose subscriber churn drivers and redesign subscription tiers and telco distribution bundles.",
        decision_question="How should the regional OTT platform restructure subscription packaging to cut churn and expand Tier-2/3 penetration?",
        primary_metric="Annual Subscriber Churn Rate (%) and Average Revenue Per Paying User (ARPPU)", time_horizon="twelve months",
        core_mechanism="Spike-and-churn behavior around tentpole movie releases. Users buy a ₹199 monthly pass to watch a single blockbuster movie and immediately cancel subscription, while credit card auto-renewal fails due to RBI e-mandate friction.",
        what_wanted_to_test="Subscription video-on-demand (SVOD) economics, tentpole content decay curves, telco carrier bundling, and UPI recurring autopay integration.",
        pivotal_insight="70% of churn occurs because users subscribe for one movie; introducing a low-cost annual mobile-only plan (₹299/year) bundled into regional broadband/telco prepaid packs converts churners into locked annual subscribers.",
        common_traps=["Doubling content production capex on expensive original web series without distribution lock-in.", "Cutting monthly subscription prices to ₹49 without solving payment auto-renewal.", "Ignoring telco prepaid bundle distribution."],
        takeaway_lesson="In regional entertainment where content consumption is episodic, monthly subscription models suffer high churn; platform stability requires annual mobile-only pricing and telco prepaid integration.",
        suggested_readings=["knowledge_base/industries/07_telecom_and_media.md", "knowledge_base/case_types/pricing_strategy.md", "knowledge_base/methodology/04_data_gathering_and_notes.md"],
        facts=[
            {"id": "subscriber.base", "domain": "company", "release_level": "broad_context", "content": "Platform has 5M subscribers across Tamil, Telugu, and Malayalam content libraries."},
            {"id": "churn.profile", "domain": "customers", "release_level": "sharp_question", "content": "Annual churn is 58%; 64% of users cancel within 35 days of sign-up following major movie releases."},
            {"id": "payment.friction", "domain": "operations", "release_level": "hypothesis_backed", "content": "RBI recurring mandate regulations caused 42% of automated credit/debit card recurring renewals to fail on monthly plans.", "dependencies": ["churn.profile"]},
            {"id": "telco.bundle_economics", "domain": "economics", "release_level": "hypothesis_backed", "content": "Telco bundled distribution (pre-integrated into monthly recharge) yields 82% 12-month retention at a wholesale wholesale payout of ₹24/user/month with zero payment failure.", "dependencies": ["payment.friction"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "58% churn is driven by episodic tentpole movie sign-ups and 42% recurring card renewal payment failures; solution requires shifting users to annual mobile-only plans (₹299/yr) and telco prepaid bundling."},
            {"id": "recommendation.annual_mobile", "domain": "recommendation", "release_level": "synthesis_support", "content": "Launch an affordable ₹299/year single-screen mobile-only plan to eliminate monthly renewal friction."},
            {"id": "recommendation.telco_bundle", "domain": "recommendation", "release_level": "synthesis_support", "content": "Partner with Jio/Airtel to bundle OTT access into regional ₹399/month mobile data recharge packs."},
            {"id": "recommendation.upi_autopay", "domain": "recommendation", "release_level": "synthesis_support", "content": "Integrate UPI AutoPay with instant recurring debit authorization to replace failing credit card mandates."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.ott-churn", root_label="Reduce OTT subscriber churn from 58% to under 25%.",
            branches=[
                {"id": "content-consumption-lifecycle", "label": "Tentpole Movie Releases vs Series Viewing", "conclusion": "64% of users churn within 35 days after watching a single blockbuster movie."},
                {"id": "payment-mandate-failures", "label": "RBI Recurring Card Mandate Friction", "conclusion": "42% of monthly renewals fail due to banking OTP and card e-mandate issues."},
                {"id": "telco-bundling-reach", "label": "Telco Prepaid Packaging & Wholesale Yield", "conclusion": "Telco prepaid bundles achieve 82% 12-month retention with zero payment failure."}
            ],
            diagnosis={"label": "Episodic Movie Churn & Payment Failure Barrier", "evidence": ["content-consumption-lifecycle", "payment-mandate-failures", "telco-bundling-reach"], "conclusion": "Churn is driven by episodic movie watchers cancelling after 1 month and high payment auto-renewal failures; shifting to annual mobile plans and telco bundling solves retention."},
            recommendation={"label": "3-Pillar OTT Retention Architecture", "evidence": ["diagnosis"], "conclusion": "Introduce ₹299 annual mobile plan, partner with telco prepaid packs, and deploy UPI AutoPay."},
            routes=[{"id": "churn-first", "sequence": ["content-consumption-lifecycle", "payment-mandate-failures", "telco-bundling-reach", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from user viewing habits to payment failure and telco partnerships."}],
            recovery=["Ask candidate why users cancel after 30 days.", "Clarify that credit card auto-renewals in India have high failure rates.", "Redirect toward annual mobile plans and telco prepaid data bundles."]
        )
    )

    # Case 9: AI Voice Agent in IT-BPO
    emit_case(
        school_dir="isb", slug="09-ai-voice-agent-bpo", title="BPO Generative AI Voice Agents", school_tag="ISB",
        category="digital_transformation", industry="saas_and_b2b_tech", difficulty="advanced",
        opening_context="Your client is a global IT-BPO customer service provider with 40,000 call center agents. Clients are demanding 40% cost reductions by replacing Tier-1 human customer agents with Generative AI voice agents, threatening the BPO's FTE-based billing model.",
        opening_objective="Design a business model transition from headcount-based FTE billing to outcome-based AI+Human hybrid customer experience contracts.",
        decision_question="How should the BPO restructure its commercial contracts and delivery model to thrive amid AI voice automation?",
        primary_metric="Operating Margin (%) and Contract Revenue Retention", time_horizon="eighteen months",
        core_mechanism="Revenue cannibalization in FTE billing. Billing clients $22/hour per human agent means automated AI voice resolution ($0.15/minute) cannibalizes 50% of call volume, destroying top-line revenue under traditional time-and-materials contracts unless pricing shifts to Pay-Per-Resolved-Call.",
        what_wanted_to_test="IT-BPO commercial models, FTE to outcome pricing transition, conversational AI voice latency, agent copilot productivity, and CSAT SLAs.",
        pivotal_insight="Under FTE billing, AI automation shrinks BPO revenue by 40%; by transitioning to 'Pay-Per-Resolution' ($1.80 per resolved query), the BPO uses AI to handle Tier-1 at 85% gross margin while upskilling humans for complex Tier-2 advisory.",
        common_traps=["Resisting AI deployment to protect legacy hourly human headcount billing, leading enterprise clients to switch to pure-play AI startups.", "Firing 50% of human agents without testing AI hallucination and accent understanding on complex calls.", "Assuming AI voice agents can handle 100% of emotional customer disputes."],
        takeaway_lesson="When generative AI disrupts legacy labor-arbitrage services, service providers must abandon hourly FTE billing and adopt value-based outcome pricing to capture software-like gross margins.",
        suggested_readings=["knowledge_base/industries/08_saas_and_b2b_tech.md", "knowledge_base/case_types/pricing_strategy.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "bpo.baseline", "domain": "company", "release_level": "broad_context", "content": "Client employs 40,000 agents generating $650M revenue, billed on an hourly FTE rate ($22-$26/hr)."},
            {"id": "ai.performance", "domain": "operations", "release_level": "sharp_question", "content": "GenAI voice agents achieve 74% containment resolution on routine Tier-1 inquiries (billing, flight status, returns) with sub-600ms latency."},
            {"id": "contract.cannibalization", "domain": "financials", "release_level": "hypothesis_backed", "content": "Under FTE billing, deploying AI reduces billable agent hours by 45%, shrinking client account revenue by $180M if contracts remain hourly.", "dependencies": ["ai.performance"]},
            {"id": "outcome.pricing", "domain": "economics", "release_level": "hypothesis_backed", "content": "Pricing at $1.85 per AI-resolved interaction (vs $6.50 human cost) delivers 68% gross margin to the BPO while saving the enterprise client 35% overall.", "dependencies": ["contract.cannibalization"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "FTE billing creates suicidal incentives against AI deployment; BPO must transition commercial contracts to 'Pay-Per-Resolution' ($1.85/call), allowing AI Tier-1 automation to expand gross margin from 28% to 52% while reducing client costs."},
            {"id": "recommendation.outcome_contracts", "domain": "recommendation", "release_level": "synthesis_support", "content": "Transition top-20 enterprise clients to gain-share 'Pay-Per-Resolution' contracts with guaranteed CSAT SLAs."},
            {"id": "recommendation.hybrid_orchestration", "domain": "recommendation", "release_level": "synthesis_support", "content": "Deploy an AI voice agent frontend for Tier-1 routing with seamless sub-second human handoff for emotionally escalated calls."},
            {"id": "recommendation.agent_copilot", "domain": "recommendation", "release_level": "synthesis_support", "content": "Equip remaining human Tier-2 agents with real-time AI assistive copilots (live CRM knowledge retrieval and auto-summarization) to cut handle time by 30%."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.bpo-ai-pivot", root_label="Transition BPO from FTE headcount billing to AI outcome pricing.",
            branches=[
                {"id": "fte-revenue-cannibalization", "label": "Hourly FTE Billing vs AI Call Reduction", "conclusion": "AI automation cuts billable hours by 45%, destroying revenue under hourly contracts."},
                {"id": "ai-voice-agent-capabilities", "label": "AI Voice Containment & Latency Metrics", "conclusion": "GenAI handles 74% of Tier-1 calls at 600ms latency with high CSAT."},
                {"id": "outcome-pricing-economics", "label": "Pay-Per-Resolution Margin Multipliers", "conclusion": "Pay-per-resolution at $1.85/call expands BPO gross margin from 28% to 52%."}
            ],
            diagnosis={"label": "FTE Model Disruption & Outcome-Based Transition", "evidence": ["fte-revenue-cannibalization", "ai-voice-agent-capabilities", "outcome-pricing-economics"], "conclusion": "Hourly FTE billing penalizes AI efficiency; transitioning to outcome-based Pay-Per-Resolution captures software margins on 74% automated volume."},
            recommendation={"label": "3-Pillar AI Services Transformation", "evidence": ["diagnosis"], "conclusion": "Execute Pay-Per-Resolution contracts, deploy AI voice Tier-1 with human handoff, and equip Tier-2 staff with AI copilots."},
            routes=[{"id": "commercial-first", "sequence": ["fte-revenue-cannibalization", "ai-voice-agent-capabilities", "outcome-pricing-economics", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from FTE billing conflict to outcome pricing unit economics."}],
            recovery=["Ask candidate what happens to an hourly billed BPO when AI reduces call handling time by 50%.", "Clarify that AI software costs pennies per minute.", "Redirect toward outcome-based per-resolution pricing."]
        )
    )

    # Cases 10-12 (EV Charging, Gold Loans, Logistics SaaS)
    # Case 10: EV Charging Station Yield
    emit_case(
        school_dir="isb", slug="10-ev-charging-station-yield", title="EV Fast-Charging Network Yield", school_tag="ISB",
        category="operations", industry="automotive_and_ev", difficulty="intermediate",
        opening_context="Your client operates a public network of 400 DC Fast-Charging stations (60 kW / 120 kW) across Indian highways and metro malls. Station utilization averages only 12%, resulting in negative network EBITDA due to high electricity demand charges.",
        opening_objective="Diagnose low charging station utilization and design dynamic time-of-day pricing and fleet tie-ups to achieve EBITDA breakeven.",
        decision_question="How should EV charging station tariffs and site partnerships be restructured to double capacity utilization?",
        primary_metric="Station Utilization (%) and EBITDA per Charging Gun", time_horizon="twelve months",
        core_mechanism="Fixed grid maximum demand charges (MVA penalties) with peak utilization occurring only 3 hours per day, while commercial EV taxi fleets avoid stations due to high daytime spot tariffs (₹22/kWh).",
        what_wanted_to_test="EV charging unit economics, fixed grid demand charges vs energy charges, dynamic Time-of-Day (ToD) tariff structuring, and commercial fleet anchor partnerships.",
        pivotal_insight="Fixed grid demand charges cost ₹45,000/month per station regardless of power drawn; offering discounted off-peak tariffs (₹14/kWh) to commercial taxi fleets during mid-day and overnight lulls raises station utilization from 12% to 32% without adding demand charges.",
        common_traps=["Raising charging tariffs across the board, which drives private EV owners to charge exclusively at home.", "Building more highway charging stations before fixing city network utilization.", "Assuming battery swapping is the only viable solution."],
        takeaway_lesson="In fixed-capacity utility infrastructure with high grid demand charges, profitability requires filling off-peak valley hours with guaranteed commercial fleet volume.",
        suggested_readings=["knowledge_base/industries/10_automotive_and_ev.md", "knowledge_base/case_types/profitability.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "station.footprint", "domain": "company", "release_level": "broad_context", "content": "Client operates 400 DC fast-charging stations with 800 charging guns across Delhi, Mumbai, and Bengaluru."},
            {"id": "cost.structure", "domain": "financials", "release_level": "sharp_question", "content": "Fixed grid sanctioned load demand charges are ₹45,000/month per station; average revenue is only ₹38,000/month due to 12% utilization."},
            {"id": "fleet.demand", "domain": "customers", "release_level": "hypothesis_backed", "content": "Commercial EV taxi fleets (Uber/BluSmart) need 25,000 daily fast-charging sessions but require ₹14-₹16/kWh pricing to maintain driver unit economics.", "dependencies": ["cost.structure"]},
            {"id": "tod.impact", "domain": "economics", "release_level": "hypothesis_backed", "content": "Piloting off-peak Time-of-Day pricing (₹14/kWh from 11 PM to 7 AM and 1 PM to 4 PM) boosted station utilization from 12% to 29%, generating ₹78,000/month revenue per station.", "dependencies": ["fleet.demand"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Network lost money because 12% utilization failed to cover ₹45,000 fixed grid demand charges; implementing off-peak Time-of-Day tariffs for commercial taxi fleets fills idle valley hours and pushes utilization to 29%, achieving EBITDA profitability."},
            {"id": "recommendation.tod_tariffs", "domain": "recommendation", "release_level": "synthesis_support", "content": "Implement dynamic Time-of-Day (ToD) charging rates: ₹24/kWh peak (6-10 PM) and ₹14/kWh off-peak."},
            {"id": "recommendation.fleet_contracts", "domain": "recommendation", "release_level": "synthesis_support", "content": "Sign exclusive off-peak charging contracts with commercial EV ride-hailing and delivery fleets with minimum volume commitments."},
            {"id": "recommendation.amenity_monetization", "domain": "recommendation", "release_level": "synthesis_support", "content": "Partner with QSR coffee chains and retail convenience stores at charging hubs to earn retail revenue share while drivers charge."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.ev-charging-ebitda", root_label="Double EV charging station utilization and achieve EBITDA profitability.",
            branches=[
                {"id": "fixed-demand-charges", "label": "Grid Sanctioned Load Demand Charges vs Revenue", "conclusion": "Fixed demand charges cost ₹45k/mo per site, requiring >22% utilization to break even."},
                {"id": "commercial-fleet-demand", "label": "Commercial Taxi Fleets vs Retail Drivers", "conclusion": "Commercial fleets seek high off-peak charging at ₹14-16/kWh tariffs."},
                {"id": "time-of-day-pricing", "label": "Dynamic Time-of-Day Pricing Economics", "conclusion": "Off-peak ToD tariffs lift utilization to 29% and revenue to ₹78k/month per station."}
            ],
            diagnosis={"label": "Demand Charge Hurdle & Commercial Fleet Off-Peak Fill", "evidence": ["fixed-demand-charges", "commercial-fleet-demand", "time-of-day-pricing"], "conclusion": "Stations lost money because low 12% utilization could not cover fixed grid demand charges; dynamic ToD pricing for commercial fleets fills off-peak hours and achieves profitability."},
            recommendation={"label": "3-Pillar Charging Network Strategy", "evidence": ["diagnosis"], "conclusion": "Deploy dynamic ToD tariffs, execute commercial fleet off-peak contracts, and co-locate QSR retail amenities."},
            routes=[{"id": "cost-first", "sequence": ["fixed-demand-charges", "commercial-fleet-demand", "time-of-day-pricing", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from fixed grid demand charges to fleet off-peak charging demand."}],
            recovery=["Ask candidate what fixed cost an EV charging station pays to the electricity board each month.", "Clarify that retail cars only charge during evening rush hours.", "Redirect toward commercial taxi fleet charging during off-peak hours."]
        )
    )

    # Case 11: Digitizing Gold Loans
    emit_case(
        school_dir="isb", slug="11-digitizing-gold-loans", title="Doorstep Digital Gold Loan Underwriting", school_tag="ISB",
        category="digital_transformation", industry="banking_and_financial_services", difficulty="intermediate",
        opening_context="Your client is a leading Indian gold loan NBFC with ₹25,000 Cr AUM. It launched a '30-minute doorstep digital gold loan' product, but experienced collateral purity assay fraud and loan turnaround times stretching to 3 hours.",
        opening_objective="Diagnose doorstep gold assay vulnerabilities and design an automated digital appraisal and secure logistics workflow.",
        decision_question="How should the gold loan NBFC eliminate doorstep assay fraud and achieve a genuine 30-minute loan disbursement SLA?",
        primary_metric="Loan Turnaround Time (TAT in minutes) and Collateral Assay Deficit (%)", time_horizon="six months",
        core_mechanism="Subjective manual acid-touchstone assay testing in customer homes vulnerable to gold-plated jewelry fraud, combined with delayed manual branch verification and secure transit custody handoffs.",
        what_wanted_to_test="Secured lending operations, portable non-destructive gold assay technology (XRF spectrometers), anti-fraud field controls, and instant digital loan disbursement rails.",
        pivotal_insight="Traditional nitric acid testing by field loan officers fails to detect tungsten/copper core gold-plated jewelry; equipping loan officers with portable X-Ray Fluorescence (XRF) analyzers and GPS-locked tamper-evident smart pouches cuts fraud to 0.01% and enables instant UPI disbursal in 28 minutes.",
        common_traps=["Requiring customers to travel to physical branches, which destroys the unique 'doorstep loan' value proposition.", "Relying on jeweler hallmarking stamps which can be easily counterfeited.", "Eliminating doorstep gold lending entirely."],
        takeaway_lesson="In collateral-backed asset lending, scaling mobile doorstep delivery requires replacing subjective manual human appraisal with automated non-destructive IoT hardware verification.",
        suggested_readings=["knowledge_base/industries/04_banking_and_financial_services.md", "knowledge_base/case_types/growth_strategy.md", "knowledge_base/methodology/03_hypothesis_driven_drilling.md"],
        facts=[
            {"id": "gold_loan.scale", "domain": "company", "release_level": "broad_context", "content": "Client operates 1,200 physical branches and launched doorstep gold loans across 12 metros."},
            {"id": "fraud.losses", "domain": "risk", "release_level": "sharp_question", "content": "Collateral auction audits revealed ₹14 Cr in fake gold-plated jewelry where stone weight was undervalued and karat purity was overstated."},
            {"id": "tat.bottlenecks", "domain": "operations", "release_level": "hypothesis_backed", "content": "Doorstep turnaround takes 175 minutes because field agents use manual acid testing, take photos, and wait 90 minutes for branch manager approval.", "dependencies": ["fraud.losses"]},
            {"id": "xrf.technology", "domain": "operations", "release_level": "hypothesis_backed", "content": "Equipping agents with portable battery-powered XRF gold purity spectrometers provides laboratory-grade 99.9% purity verification in 45 seconds.", "dependencies": ["tat.bottlenecks"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "Doorstep gold loans failed because manual touchstone acid assays were fooled by fake gold and manual branch approval stretched TAT to 3 hours; equipping agents with portable XRF analyzers and automated digital LTV calculation achieves 28-minute disbursals with zero fraud."},
            {"id": "recommendation.xrf_rollout", "domain": "recommendation", "release_level": "synthesis_support", "content": "Equip all mobile loan officers with certified portable XRF gold analyzers connected via Bluetooth to the loan app."},
            {"id": "recommendation.smart_pouch", "domain": "recommendation", "release_level": "synthesis_support", "content": "Deposit verified jewelry into GPS-tracked, tamper-evident smart security pouches with biometric seals."},
            {"id": "recommendation.instant_upi", "domain": "recommendation", "release_level": "synthesis_support", "content": "Automate loan-to-value (LTV) calculation against live MCX gold prices and disburse funds instantly via UPI upon pouch sealing."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.gold-loan-digitization", root_label="Eliminate doorstep gold assay fraud and achieve 30-minute loan disbursement.",
            branches=[
                {"id": "assay-fraud-vulnerabilities", "label": "Manual Touchstone Testing vs Fake Gold", "conclusion": "Manual acid testing fails to detect tungsten-core fake gold, causing ₹14 Cr in auction losses."},
                {"id": "tat-approval-bottlenecks", "label": "Branch Verification Delays & TAT Inflation", "conclusion": "Waiting for manual branch manager approvals inflates doorstep TAT to 175 minutes."},
                {"id": "portable-xrf-and-iot-security", "label": "Portable XRF Spectrometry & Smart Pouches", "conclusion": "Portable XRF provides 45-second 99.9% purity testing; smart pouches secure custody."}
            ],
            diagnosis={"label": "Manual Assay Vulnerability & Branch Approval Latency", "evidence": ["assay-fraud-vulnerabilities", "tat-approval-bottlenecks", "portable-xrf-and-iot-security"], "conclusion": "Doorstep loans failed due to manual acid assay fraud and slow branch sign-offs; portable XRF hardware and automated UPI disbursement deliver 28-minute zero-fraud execution."},
            recommendation={"label": "3-Pillar Digital Gold Appraisal Strategy", "evidence": ["diagnosis"], "conclusion": "Deploy portable XRF spectrometers, use GPS biometric smart pouches, and execute instant automated UPI disbursements."},
            routes=[{"id": "fraud-first", "sequence": ["assay-fraud-vulnerabilities", "tat-approval-bottlenecks", "portable-xrf-and-iot-security", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from collateral fraud losses to automated hardware testing solutions."}],
            recovery=["Ask candidate how field officers currently verify gold purity in a customer's living room.", "Clarify that gold-plated jewelry passes basic scratch acid tests.", "Redirect toward portable XRF analyzers and automated digital LTV calculations."]
        )
    )

    # Case 12: B2B Logistics SaaS
    emit_case(
        school_dir="isb", slug="12-b2b-logistics-saas", title="B2B Logistics SaaS Platform Expansion", school_tag="ISB",
        category="growth_strategy", industry="saas_and_b2b_tech", difficulty="intermediate",
        opening_context="Your client is an Indian B2B logistics SaaS platform providing enterprise Transport Management Systems (TMS) and GPS visibility tracking to 200 large enterprise shippers. Enterprise software ARR is $15M, but growth has plateaued.",
        opening_objective="Evaluate expanding into an integrated freight brokerage marketplace with autonomous freight contract bidding.",
        decision_question="Should the logistics SaaS company expand from pure software subscription into an embedded freight marketplace?",
        primary_metric="Total ARR & Marketplace Take-Rate Revenue and Gross Margin Profile", time_horizon="eighteen months",
        core_mechanism="Software vs transaction marketplace margin trade-off. Pure SaaS carries high 80% gross margins but low contract ticket sizes ($60k/yr); embedding freight matching monetization captures 4-6% take-rates on billions in managed freight spend, but requires working capital and carrier fulfillment liability.",
        what_wanted_to_test="B2B SaaS to marketplace transition, take-rate vs software subscription economics, carrier payment float working capital, and software stickiness.",
        pivotal_insight="Client already tracks $1.2B in enterprise freight spend on its TMS software; introducing an autonomous spot-freight bidding engine captures a 5% broker take-rate on unfulfilled spot loads with zero carrier acquisition CAC.",
        common_traps=["Purchasing physical truck fleets onto the balance sheet.", "Abandoning high-margin pure SaaS software subscriptions entirely.", "Assuming enterprise shippers will give 100% of dedicated contract freight to an unproven broker."],
        takeaway_lesson="In enterprise B2B vertical SaaS, embedding transactional marketplaces on top of workflow software unlocks massive GMV monetization by monetizing platform workflow data with zero customer acquisition cost.",
        suggested_readings=["knowledge_base/industries/08_saas_and_b2b_tech.md", "knowledge_base/case_types/growth_strategy.md", "knowledge_base/methodology/01_preliminary_questions.md"],
        facts=[
            {"id": "saas.scale", "domain": "company", "release_level": "broad_context", "content": "Client provides TMS software tracking 120,000 monthly truckloads ($1.2B annual freight spend) across 200 enterprise FMCG/Auto shippers."},
            {"id": "growth.plateau", "domain": "financials", "release_level": "sharp_question", "content": "SaaS ARR growth slowed to 11% as enterprise TMS market penetration matured in top-tier accounts."},
            {"id": "spot_market.leakage", "domain": "market", "release_level": "hypothesis_backed", "content": "Enterprise shippers fail to fulfill 18% of contracted truckloads, dumping $210M annually into chaotic offline spot freight markets at 15% price premiums.", "dependencies": ["growth.plateau"]},
            {"id": "embedded.economics", "domain": "economics", "release_level": "hypothesis_backed", "content": "Enabling 1-click spot load bidding within the TMS software captures 5% marketplace take-rate on $210M GMV ($10.5M high-margin net revenue) with zero sales CAC.", "dependencies": ["spot_market.leakage"]},
            {"id": "diagnosis.hidden", "domain": "diagnosis", "release_level": "interviewer_only", "provenance": "source_derived", "content": "SaaS growth plateaued because software fees are capped; embedding an autonomous spot-freight marketplace on top of existing TMS workflow captures $10.5M in high-margin transactional take-rates on unfulfilled spot loads with zero customer acquisition cost."},
            {"id": "recommendation.spot_engine", "domain": "recommendation", "release_level": "synthesis_support", "content": "Launch an embedded 'Spot Freight Exchange' inside the TMS workflow allowing shippers to auction unfulfilled loads in 1 click."},
            {"id": "recommendation.carrier_fintech", "domain": "recommendation", "release_level": "synthesis_support", "content": "Partner with supply chain NBFCs to offer instant fuel cards and 24-hour invoice factoring to participating carriers."},
            {"id": "recommendation.dual_monetization", "domain": "recommendation", "release_level": "synthesis_support", "content": "Maintain recurring TMS SaaS subscription fees while layering transactional marketplace commissions for total revenue acceleration."}
        ],
        tree_data=make_standard_tree(
            root_id="objective.logistics-saas-growth", root_label="Accelerate logistics SaaS platform growth via embedded freight marketplace expansion.",
            branches=[
                {"id": "saas-tam-and-growth-ceiling", "label": "Enterprise TMS TAM & Software ARR Growth", "conclusion": "Pure SaaS ARR growth plateaued at 11% across 200 mature enterprise accounts."},
                {"id": "spot-freight-unmet-demand", "label": "Unfulfilled Contract Loads & Spot Market GMV", "conclusion": "Shippers dump $210M in unfulfilled spot freight into offline unorganized brokers."},
                {"id": "embedded-marketplace-economics", "label": "Embedded Take-Rate & Software Stickiness", "conclusion": "5% take-rate on $210M spot GMV generates $10.5M incremental net revenue with zero CAC."}
            ],
            diagnosis={"label": "Embedded B2B Marketplace Monetization on SaaS Workflows", "evidence": ["saas-tam-and-growth-ceiling", "spot-freight-unmet-demand", "embedded-marketplace-economics"], "conclusion": "Growth slowed because pure software fees are capped; embedding an autonomous spot-freight marketplace captures $10.5M in take-rate revenue on $210M managed freight spend."},
            recommendation={"label": "3-Pillar Vertical SaaS Expansion Plan", "evidence": ["diagnosis"], "conclusion": "Embed 1-click spot freight auction in TMS, integrate carrier invoice fintech financing, and preserve recurring SaaS baseline fees."},
            routes=[{"id": "growth-first", "sequence": ["saas-tam-and-growth-ceiling", "spot-freight-unmet-demand", "embedded-marketplace-economics", "diagnosis", "actions"], "interviewer_behaviour": "Guide candidate from SaaS growth ceilings to embedded marketplace monetization."}],
            recovery=["Ask candidate how much freight spend is already managed on the client's software.", "Clarify that 18% of contracted loads fail and go to the spot market.", "Redirect toward embedded freight auction take-rates on managed workflow data."]
        )
    )

    print("Successfully generated all 12 ISB exemplar cases!")


if __name__ == "__main__":
    generate_all_isb_cases()
