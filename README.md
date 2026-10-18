# Lead Scoring and Prioritizing App for HVAC Businesses



Overview

I built a lead scoring application designed primarily for HVAC businesses, which takes customer inquiries and prioritizes them based on problem severity and description of the issue at hand, provided by the customer. The app uses an AI layer to interpret inquiries and order them by importance, to help businesses determine which customers need their attention first. For example, an AC unit that has stopped working would be prioritized over a routine checkup.

How it works

This application retrieves customer inquiries, interprets the problem description of each, generates a quick summary of the situation at hand, and assigns a score out of 100 based on urgency. The leads are ranked by score, with higher numbers being placed above lower numbers. 

Limitations and Realizations

- This was my first real-world project, and at the time, I had not done proper market research and was mainly unaware of the competition. Lead scoring and management exist and are common within powerhouse CRM platforms like HubSpot and ServiceTitan. Nonetheless, this was a fun project and it taught me a lesson about how vital market research is to validating an idea. I reached out to local businesses and I repeatedly encountered similar existing solutions, which made this project proof that good ideas and competition can coexist. Now, when exploring new ideas, I make sure I contact businesses and identify my competition as a part of my software development process.
- This application relies heavily on a single AI model to interpret inquiries for their problem urgency, determine how they should be ranked, and condense each description into a summary for the user. I have learned that since AI models can return different results each time they are tested on the same data, those results may vary in accuracy. Although I created a prompt to guide the internal AI model my application uses, prompting alone cannot eliminate all possibilities of inaccuracy by the AI. This realization prompted me to use mathematical rules and logic for interpreting input as much as possible in future projects, to improve consistency.
