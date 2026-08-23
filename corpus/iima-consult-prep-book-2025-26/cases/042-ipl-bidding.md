---
case_id: iima-2025-26-042
title: 'IPL Bidding'
content_kind: structured_source_case
runtime_readiness: needs_runtime_qa
layout_review: preliminary_passed
source_id: iima-consult-prep-book-2025-26
source_attribution: 'Consult Club, IIM Ahmedabad, IIMA Consult Prep Book 2025-26'
source_pdf_pages: 135-136
case_type: pricing
extraction_method: pdfplumber-positional-callout-reconstruction
extracted_on: 2026-08-22
format_version: structured-source-v2
candidate_visibility: opening_brief_only
---

# IPL Bidding

## Case at a glance

- **Case type:** Pricing
- **Source pages:** 135-136
- **Candidate sees initially:** the opening brief only.
- **Facilitator sees:** the ordered source turns and approach material below.

## Opening brief

Your client is an Indian Premier League (IPL) team that wishes to bid for Virat Kohli in this year’s IPL auction. They want your advice in the assessing the fair value at which Kohli should be acquired.

## Facilitator interview script

> Speaker labels are reconstructed from the source slide’s shaded interviewer callouts. `Source sequence` marks a turn that needs human speaker review before runtime approval.

<!-- Source PDF page 135, column 1 -->

### Turn 1 - Candidate

Can you tell me if the client is a specific team? How has the client performed recently and why are they interested in pursuing Kohli?

### Turn 2 - Interviewer

Assume that there is no sentimental reason for the team to acquire Kohli, nor vice versa. The client was at 7th position 2 years ago. They currently rank 5th out of 10 teams. The teams wants to make it to the finals this year. They believe that Kohli fits well with the team’s young core due to his leadership and can help their struggling batting line-up. Since we want to boost our chances of reaching the finals due to Kohli’s addition, I’m assuming there is a

### Turn 3 - Candidate

negligible chance of ending up lower than 5th. Do we have more data to validate this assumption?

### Turn 4 - Interviewer

5th You are right. Client’s chances of doing worse can be taken 0. Moreover, Probability of staying at is 30%, moving to 4th is 30%, ending up in 3rd place is 25%, being the finalist is 10%, and winning the IPL is 5%. Please tell me if there is any other information you need.

### Turn 5 - Candidate

I would like to understand the bidding process, what bearing does it have on the bid price of Kohli, and how many competitors are pursuing Kohli more aggressively than us.

### Turn 6 - Interviewer

Assume that we are only concerned with Kohli’s fair value, and the client will not bid more. Also, the other teams are rational and follow a similar approach to valuing players. There are no salary caps on bidding for more players. Why don’t you tell me how you plan on finding Kohli’s fair market value?

### Turn 7 - Candidate

Estimating the fair value will be tough using cost-based pricing as we cannot bifurcate cost between fixed and variable components. Similarly, competitor-based pricing isn’t optimal as we are not concerned about how much would other teams pay to acquire Kohli. Value-based method can be a viable framework to find Kohli’s fair bid price. Using this, we will assess the expected benefit we get after acquiring Kohli. The bid price has to be lower than that value.

### Turn 8 - Interviewer

Sounds good. How would you quantify the benefit client would accrue after acquiring Kohli?

### Turn 9 - Candidate

I would estimate the increase in team’s revenue after Kohli’s acquisition. This will be the upper limit of the bid price. Here, ending up at different ranks will impact the change in revenue, and I will find the expected value of such benefit using the probability data provided by you.

### Turn 10 - Interviewer

Seems like a good approach. What are the ways in which an IPL team generates revenue and how would Kohli’s acquisition affect them.

### Turn 11 - Candidate

The main sources of revenue are the share of media rights from BCCI, ticket sales, merchandize sales, brand sponsorships, and prize money. On an average, an IPL team can expect an income of Rs 200 Cr. I can see Kohli’s acquisition impacting media rights income. Some part of it can be taken as fixed, and some variable which depends on what is the final position at the end of IPL. Brand deals will generate more money if the team has superstars like Kohli. Prize money is proportional to the final position. More tickets and merchandize will be sold due to Kohli’s star power and fandom. May I know the exact revenue share per stream?

### Turn 12 - Interviewer

Sure. Media rights have the greatest share in revenue (40%), followed by brand sponsorships (25%), then prize money (15%), and then tickets and merchandize sales (10% each). An IPL team’s average annual revenue is indeed 200 Cr. I would now like you to calculate the impact on media rights and prize money first.

<!-- Source PDF page 135, column 2 -->

### Turn 13 - Candidate

I will assume 80% of the media rights to be fixed and 20% to be variable. To calculate change in media rights’ revenue after Kohli’s acquisition, we will only consider the increase in the variable component. I will assume that the increase in variable factor revenue distribution will be symmetric to the prize money revenue distribution. Variable revenue is expected to increase by 14.5% (calculated on the next page using probability and revenue share tables). This equals an increase of 3.28 Cr for media rights share and 4.35 Cr for prize money income.

### Turn 14 - Interviewer

This is good enough. Let’s move to brand endorsements and deals next.

### Turn 15 - Candidate

Sure. Considering the constraints teams face while endorsing a brand such as limited space on the team uniform, very little time to shoot advertisements, etc., there is very little scope to increase the number of deals as most teams are already operating after taking up as many deals as they could. Kohli’s image can help the client charge more per client due to his fandom and superstar status, increasing brand visibility.

### Turn 16 - Interviewer

Correct. We know that the last team Kohli belonged to was able to charge a premium of 10% on its brand deals compared to our client.

### Turn 17 - Candidate

In that case, the deal value would increase 10% if the client were to acquire Kohli, resulting in a net revenue increase of Rs 5 Cr

### Turn 18 - Interviewer

That’s good enough. What about revenue from tickets sales?

### Turn 19 - Candidate

Tickets sales over the year is (Average tickets sold per game)*(Average price of the ticked)*(Number of home games scheduled per season). I will assume the number of games to be the same as last year. Number of tickets sold is (Occupancy of the stadium)*(Total number of seats). We can assume occupancy to go up roughly by ~20%. The ticket price can also be sold at a premium. Do we have any information for these metrics?

### Turn 20 - Interviewer

You’re correct in assuming that number of home games played remains the same. However, client’s stadiums has 70% occupancy on an average. They expect it to be 77% in case Kohli joins the team. BCCI does not allow any team to increase the ticket price.

### Turn 21 - Candidate

In this case, average occupancy increases by (77%-70%)/70% = 10% leading to a symmetric 10% increase in ticket sales which is Rs 2 Cr.

### Turn 22 - Interviewer

Sounds reasonable. On to the merchandize sales now. Assume that the merchandize sales and tickets sales display high correlation when new players join the team.

### Turn 23 - Candidate

With this information, I can take the increase in merchandize revenue for the client to be 10%. This would lead to an increase of Rs 2 Cr. Summing up the increase in expected revenue’s values, we get a net benefit of Rs (3.28 + 4.35 + 5 + 2 + 2) Cr = Rs 16.63 Cr. This should be the upper limit of the bid that the client should place to acquire Kohli. A few points to consider are that we have not considered the possibility of star players making special demands such as better coaches, amenities, trainers, equipment, leave requests etc. which have a cost associated with them. This should be deducted from total revenue to find the net value of benefit that the team would get post-acquisition.

### Turn 24 - Interviewer

This sounds good enough. Let’s end the case here.

## Facilitator-only approach material

> Do not show this section to the candidate during a live interview. It contains the source’s approach sheet, recommendations, and observations.

<!-- Source PDF page 136, column 1 -->

Problem Your client is an Indian Premier League team that wishes to bid for Virat Statement

APPROACH/ FRAMEWORK Total Revenue (200 CASE FACTS

• No sentimental reason to buy Media Rights Share Brand deals Prize Money Kohli, find his intrinsic value (80 Cr; 40%) (50 Cr; 25%) (30 Cr; • Team finished 5th last year and will finish above that with Kohli +14.5% Increase Variable Fixed Revenue (16 Cr; 20%) (64 Cr; 80%) (4.35

No. of Value deals per deal

+14.5% +10% Increase in Revenue Increase in Revenue (2.32 Cr) (5 Cr)

INTERVIEWEE NOTES

• Ignore any budget constraints Net Increase in • Cost and competitor-based (16.63 pricing not relevant

• Value based pricing done by Calculating expected increase in variable revenue streams (prize money looking at potential increment in team revenues if Kohli is bought Team rank 1 2 3 4 5 6-10

Probability 5% 10% 25% 30% 30% 0%

(Return if Rank 1st)*(Probability of Being 1st) + (Return if Rank 2nd)*(Probability of Being 2nd) +…. Return if Rank 10th)*(Probability of Being 10th)

<!-- Source PDF page 136, column 2 -->

Kohli in this year’s IPL auction. Advise them on how much they should bid.

Cr) OBSERVATIONS

• The major revenue streams for a Tickets Sales Merchandise Sales sports team is usually – Cut of 15%) (20 Cr; 10%) (20 Cr; 10%) media rights, Cut of central sponsorship, Team sponsorship, Merchandise, Ticket Sales Ticket No. of in No. of • Media rights is often the major price/ Tickets games source of revenue for the league game sold Cr) and each of the teams

Seats in Occupancy stadium

+10% +10% Increase in Revenue Increase in Revenue (2 Cr) (2 Cr)

Revenue Cr)

& media rights) that are dependent on ending rank

Team rank 1 2 3 4 5 6 7-10

% of variable 25% 20% 15% 15% 10% 5% 2.5% revenue

5%*25% + 10%*20%.... + 14.5% 0%*2.5%

## Runtime QA status

- **Current state:** Structured source case. The source dialogue has been restored from slide callouts and reading order.
- **Before simulator use:** Convert this case into the stage-gated runtime template, explicitly map fact-release conditions, and review the scoring guidance.
- **Candidate safety:** Do not pass the approach material or complete script to the candidate-facing client.
