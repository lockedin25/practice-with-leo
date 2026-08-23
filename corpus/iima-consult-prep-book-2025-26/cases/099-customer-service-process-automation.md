---
case_id: iima-2025-26-099
title: 'Customer Service Process Automation'
content_kind: structured_source_case
runtime_readiness: needs_runtime_qa
layout_review: preliminary_passed
source_id: iima-consult-prep-book-2025-26
source_attribution: 'Consult Club, IIM Ahmedabad, IIMA Consult Prep Book 2025-26'
source_pdf_pages: 273-274
case_type: unconventional
extraction_method: pdfplumber-positional-callout-reconstruction
extracted_on: 2026-08-22
format_version: structured-source-v2
candidate_visibility: opening_brief_only
---

# Customer Service Process Automation

## Case at a glance

- **Case type:** Unconventional
- **Source pages:** 273-274
- **Candidate sees initially:** the opening brief only.
- **Facilitator sees:** the ordered source turns and approach material below.

## Opening brief

Your client is a large e-commerce player based in India. They want to automate their customer service processes and want your support to identify which process to automate

## Facilitator interview script

> Speaker labels are reconstructed from the source slide’s shaded interviewer callouts. `Source sequence` marks a turn that needs human speaker review before runtime approval.

<!-- Source PDF page 273, column 1 -->

### Turn 1 - Candidate

Okay, I would first like to understand the objective behind automation- is it cost reduction, improve customer satisfaction or a mix of both?

### Turn 2 - Interviewer

Our primary goal is cost reduction without hurting CSAT.

### Turn 3 - Candidate

Great. I would like to understand our current contact channels and current volumes for the same.

### Turn 4 - Interviewer

We get roughly 12 million contacts a year out of which about 70% are after-sales. Channel mix is about 50% chat, 45% voice/human agent, and 5% via email.

### Turn 5 - Candidate

Got it, thank you. So, there are 45% contacts led by human intervention, which we can potentially automate. I would like to begin with customer journey, then deep-dive into how the client run their customer service process today and where the process could be automated. From there we’ll prioritize what to automate now vs. Later, with safeguards so CSAT doesn’t drop.

### Turn 6 - Interviewer

Sounds good

### Turn 7 - Candidate

Got it. I’ll start with mapping the customer journey end-to-end across four stages - pre-purchase, purchase, after-sales, and post-engagement. Pre-purchase: customers browse on app/web, see specs, delivery promises, and reviews; if info is missing, they open chat or call for availability, delivery date, or price. Purchase covers checkout and payment via UPI, cards, wallets, and a sizable COD share for Tier-2/3. After-sales includes order tracking, delivery reschedules, cancellations, returns and refunds, and warranty claims. Post-engagement covers feedback, loyalty points, and marketing consents. Since after-sales drives 70% of contacts, I’d like to drill deeper into those processes.

### Turn 8 - Interviewer

Yes, the rest of the processes are automated. Let’s deep dive into after-sales.

### Turn 9 - Candidate

Okay, I’d split it into two layers for handling the customer tickets. On the front end, we have customer-facing platforms - human-assisted like call centres and social media teams, and non-human like chatbots, IVRs, and in-app help sections. On the back end, we have operational processes like logistics tracking integration, warehouse coordination for returns, and seller refund approvals. Moving on to tickets categories, we can bucket these into order tracking and delivery updates, delivery rescheduling requests, returns and refunds, cancellations, and warranty or service claims. We can take a deeper look at each ticket type one by one, understand the current handling process, and then see if there’s automation potential without hurting CSAT

### Turn 10 - Interviewer

Yes, that sounds good. Go ahead..

### Turn 11 - Candidate

Starting with order tracking and delivery updates - I’m assuming we already have courier integration to show status in-app, but customers still contact us when the information is unclear or outdated?

### Turn 12 - Interviewer

Yes. We pull updates from our warehouse checkpoints, but about 15–20% of the time, the status is vague, so customers chat with our chat bots. The process of handling these queries is automated.

### Turn 13 - Candidate

Understood, so not much potential here. Moving on, how does delivery rescheduling requests work today?

### Turn 14 - Interviewer

Customers contact us, the agent notes the preferred date, and manually informs the courier partner.

<!-- Source PDF page 273, column 2 -->

### Turn 15 - Candidate

This is an easy win - we can let customers pick from a few available delivery dates in the chatbot itself, and the same bot can send a simple daily sheet to the courier partner by email or shared dashboard. That way, no agents are stuck relaying the same info hundreds of times. Moving on to returns and refunds. I’m assuming customers raise the return request online, and post checking and approval process, pickup is arranged.

### Turn 16 - Interviewer

Yes, additionally, refund approval happens after the warehouse confirms the returned item is okay.

### Turn 17 - Candidate

Got it. For returns from our own warehouses, we can make refunds auto-approve as soon as the item passes the warehouse check, without agent review. For seller orders, we can set a rule - if the value is under a certain price range, auto-approve; otherwise send to agents. This should free up time from low-value, low-risk cases..

### Turn 18 - Interviewer

Yes, makes sense. Let’s move directly to warranty claims since cancellations are mostly automated.

### Turn 19 - Candidate

Okay, I’m assuming these are complex because they involve brand or seller coordination?

### Turn 20 - Interviewer

Exactly. Customers often don’t have the invoice handy, or brands need images or videos before approval..

### Turn 21 - Candidate

Okay, I’d leave them with agents but enhance with automated intake forms, document upload, and knowledge base tools so agents work faster. Also, we can incorporate AI to read through these documents saving time.

### Turn 22 - Interviewer

Works. Now, how would you prioritize which processes to automate?

### Turn 23 - Candidate

For prioritization, we can use a 2 x 2 impact-feasibility matrix. The high-impact, high-feasibility ones to automate right away would be order tracking, delivery rescheduling, and simple refund triggers. The lower- feasibility but still valuable ones, like c warranty claims, can be planned for later. And as a quick win, we can add auto-suggestions in chat for “return” or “cancel” before the customer even reaches an agent.

### Turn 24 - Interviewer

Any safeguards to ensure CSAT doesn’t drop?

### Turn 25 - Candidate

To protect CSAT, we could always give customers an “escape hatch” - if they fail two or three bot attempts, they get routed straight to an agent. We could also use sentiment detection so that frustrated customers are directed to human agents immediately. To avoid large-scale issues, automation could first be piloted in select regions or categories. And throughout, NPS and CSAT could be tracked separately for automated versus human tickets, so cost savings don’t come at the expense of experience.

### Turn 26 - Interviewer

Sounds reasonable. Can you give me a quick guesstimate of the potential savings in terms of man-hours?

### Turn 27 - Candidate

Before I estimate savings, could you give me an approx. % split of these after-sales contacts by ticket type?

### Turn 28 - Interviewer

Sure. Order tracking is about 30%, delivery reschedules 15%, refund/ return triggers 10%, cancellations 25%, and warranty/service claims around 20%. Additionally, for estimation- you can assume a fully loaded cost rate of Rs. 400/hr.

### Turn 29 - Candidate

Alright. So, you have 12M contacts a year, 70% of which are after-sales; that’s 8.4M. Applying ticket type split: order tracking is 30%, so 2.52M; reschedules are 15%, so 1.26M; and refund triggers are 10%, so 0.84M. That’s 4.62M contacts we could automate. At an average handling time of 4 minutes, that’s 18.48M minutes, or about 308K man-hours. Assuming that we are able to automate 60% of that basis our recommendations, we save around 185K hours. At a fully loaded cost of ₹400/hour, that’s close to ₹74 million annually.

### Turn 30 - Interviewer

Sounds good. Let’s close the case here.

## Facilitator-only approach material

> Do not show this section to the candidate during a live interview. It contains the source’s approach sheet, recommendations, and observations.

<!-- Source PDF page 274, column 1 -->

Problem Your client is a large e-commerce player based in India. They want Statement automate?

CASE FACTS APPROACH/ FRAMEWORK

• Large Indian e-commerce player Customer-journey with 12M annual customer service contacts. Pre- Purchase Purchase

• Objective: Cost reduction without hurting CSAT. Front-end • 70% (8.4M) are after-sales queries. Issues handled at both front- • Current after-sales ticket types: end & back-end level order tracking (30%), delivery reschedules (15%), refund triggers Order tracking & Delivery (10%), cancellations (25%), Delivery updates rescheduling warranty/service claims (20%).

Prioritization Matrix

INTERVIEWEE NOTES • Approach: Map customer journey, deep dive into after-sales, split Automate into front-end vs. back-end, apply Quick Wins Automate two lenses (customer experience y & operational efficiency), prioritize t i l i b Order-tracking via impact-feasibility matrix i s a e • Deep dive into different type of F tickets to further understand which Plan for rescheduling De-prioritize process to automate medium-term Non-complex • Quick wins are high-volume, low- complexity processes with minimal human judgment. Impact

<!-- Source PDF page 274, column 2 -->

to automate its customer service processes - how should they decide which processes to

RECOMMENDATIONS

• Allocate Start by clarifying the primary objective of automation After-sales Post- Engagement (cost, efficiency, customer satisfaction) to guide prioritization.

• Map the entire customer journey to identify major contact drivers and Back-end touchpoints.

• Segment processes into front-end (customer-facing) and back-end Returns & (operations/support) for targeted Cancellations Warranty claims Refunds analysis.

Prioritization actions OBSERVATIONS

• It is important to break the problem Plan for medium- into logical stages of the customer Quick Wins term journey, then zoom into the biggest volume/cost driver. Chat-bot Complex • It was imperative to prioritize optimization cancellations solutions that are both technically doable and won’t harm the Delivery Auto-approve low Warranty claims customer experience. value refunds • Additionally, using available data to identify high-impact areas is crucial, refunds so your deep dive is focused where it matters.

## Runtime QA status

- **Current state:** Structured source case. The source dialogue has been restored from slide callouts and reading order.
- **Before simulator use:** Convert this case into the stage-gated runtime template, explicitly map fact-release conditions, and review the scoring guidance.
- **Candidate safety:** Do not pass the approach material or complete script to the candidate-facing client.
