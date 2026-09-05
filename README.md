# Xbench

**Measuring the Mandate of Heaven.** Seven days of firsthand opinion on X about frontier AI models and the coding harnesses people run them in.

Live: https://nicodunks.github.io/xbench/
Repo: https://github.com/nicodunks/xbench

## Setup

The page is static. Run it locally with:

```bash
python3 -m http.server 4173
```

and open `http://127.0.0.1:4173/`. Everything the page shows comes from `index.html`, `xbench.css`, `swiss.css`, `xbench.js` and two JSON files under `data/labels-v2/`: `public-summary.json` (every chart) and `public-evidence.json` (every counted post, with its reason and a link back to X).

The pipeline pulls posts from the official X API, labels every post with a language model working from [`AGENT_CLASSIFICATION_PROMPT.md`](AGENT_CLASSIFICATION_PROMPT.md), has a reviewer re-read the flagged ones, and aggregates with `build_release_v2.py`. The raw corpus stays in `data/private/`, which is ignored. Every label for every post is public by id, so any number on the page can be audited. To run a collection day or a labeling pass, see [`X_API_GUIDE.md`](X_API_GUIDE.md) and [`AGENT_LABELING_GUIDE.md`](AGENT_LABELING_GUIDE.md). Contributions go through [CONTRIBUTING.md](CONTRIBUTING.md); the most useful one is a disputed label with the post link. MIT for the code, post texts belong to their authors, see [LICENSE](LICENSE).

The write-up below is the original post, reproduced as written.

---

# Xbench: Twitter Vibes as an AI Eval

## Maybe attention is all you need for evals too

Today's AI evals no longer reflect how frontier users feel about the models.

Revenue and adoption are probably the most valuable real world evals right now, but I believe that both are lagging indicators of a much fuzzier and more important measure that we call the twitter vibe, or “the mandate of heaven”.

I attempt to measure this with Xbench.

According to Xbench -- Codex is dominating Claude Code, Astra has the highest model sentiment, GLM 5.3 Flash tops model preferences, GPT 5.6 Sol over-engineers, and people really don't like Opus 5.

People think Fable 5.1 is brilliant, but they are too mad at Anthropic to really admit it.

See Xbench here:

https://nicodunks.github.io/xbench/

## The Eval Problem:

It’s clear to everyone on twitter that the AI industry has a serious eval problem. Gemini is accused of benchmaxxing, no eval measures how frustrating Opus 5 is to use, AA panics to update their evals, and GPT-6-Astra does not report on many of the go-to evals of yesterday.

Update! AA just released an update, moving Astra up to the #2 spot. It is now sits equidistant between Fable 5.1 and Muse Spark 1.3... which...

Astra launched and according to its model card, it is another Mythos preview moment. It solves ARC-AGI-3 and ExploitBench...

Without going too deep here, you should assume self-reported evals to be very rigorous, a little skewed, and completely insufficient.

That is why we need other, different ways to capture the obvious gap we all feel between a model card and what we experience every day as users on the frontier.

I suggest we measure the twitter vibe, or the mandate of heaven.

## Prior Examples of the Mandate of Heaven

We can tell when the vibe shifts. If you’re deep enough on twitter it’s visceral. We felt it late Summer 2024 with Sonnet 3.5 and Cursor for code, and in late Spring 2025 with Claude Code. It usually takes 6-12 months for impacts on adoption and ARR to land, while other companies sometime grow revenue and valuation faster.

The trend continues now, but in OpenAI’s favor. About 6 months ago OpenAI recaptured the Mandate of Heaven with GPT 5.5-5.6 and Codex. Most of those in the know switched to Codex a while ago.

Today, Twitter rallies against Claudish, unforced communication blunders, infra instability, what looks like tokenmaxxing, and more at Anthropic.

Corporate America is still talking about Cowork, but by new year Codex will be all the rage. I predict OAI revenue will surpass Ant's by March '27 if things stay this way any longer (but what do i I know).

## Xbench Experiment and Methodology:

I built XBENCH to see if we could measure the Mandate of Heaven. It’s far from perfect – heavily limited by both my personal budget on x-api calls and the ceiling of whatever rigor one can really get to in a day and a half of building and writing – but I believe it reflects the truth on twitter.

I polled all mentions of thirteen LLM models (details on which towards the bottom) and the top 5 coding agent harnesses. I sampled ~13% of them, which pulled 23,275 posts/replies/quotes from 14,454 twitter users over the last 7 days.

I then had Fable 5.1 fan out dozens of Sonnet 5 subagents in parallel to analyze every single message, not relying on brittle key word matching or any pre-baked code, but actually reasoning over every single message. We logged all messages, but only counted messages that communicated a first hand user experience towards metrics.

Claude filtered out anything vague, promotional messages, second hand reviews and stories, and bots. Qualifying messages were assigned a preference between positive, mixed, negative or not expressed. And every message that mentioned multiple models or harnesses was reasoned over to determine if there was a clear stated preference or even an explicit mention of switching usage from one model or harness to another.

## Xbench Findings:

Xbench's findings seemed to resonate strongly with today’s twitter vibes. See below for a bulleted list of call outs and judge for yourself.

Codex is kicking butt rn.

- GPT-6 Astra after one day has the highest sentiment of all 13 models (+64%, n 110) and the top model intelligence score (+76 on 71 posts).
- Opus 5 is extremely disliked. It is the least preferred model of the 13, scores worst on personality (-65), and is the only model that scores net negative.
- People prefer Codex to Claude Code 121:60 (67%) and people are clearly switching to Codex. 29 people switched to Codex while only 9 switched to Claude Code.
- The biggest advantage Codex has over Claude code is on limits and quota, where Codex wins 41 to 13; Claude Code's limits sentiment is -64 against Codex's -31.
- People really like Grok Bot. It wins head to head preference against Codex & Claude 46:20.
- Price is the biggest factor in winning on preferences for models (at least within the frontier). GLM 5.3 Flash sits at #1st place on preferences.
- GPT 5.6 Sol beats Opus 5 in preference 25:14 (64%)
- Fable 5.1 is admired for its intelligence, but complaints about token consumption and price hold it back towards the bottom of the preference ladder.
- Fable 5.1 beats Opus 5 20:9 and beats Sol 17:10 in direct comparisons
- What people dislike most about GPT 5.6 Sol is that it over-engineers and is hard to steer.
- Filtering for English barely moves results, and what movement there is actually favors the Chinese OSS models

Below are findings that I believe are either a bit inaccurate or are probably explained away due to other biases and limitations

- Fable 5.1 is the second worst preference score, and is lower than GLM 5.3 Flash on stated intelligence differences. Fable 5 and 5.1 are obviously smarter.
- Codex's worst dimension is reliability at -52, and most of those posts are from the September 3 outage. Codex is generally very performant and reliable.
- Kimi K3 remains suspiciously high on explicit preferences and sentiment. I suspect there is a SF vs non SF twitter divide here, some paying for influence, or maybe just too little sample size.
- Grok Bot beats Claude Code 25:8 (76%) and Codex 21:12, taking 8 direct switchers from Claude Code and 5 from Codex.

## Issues and limitations

### 1) Bad vibes towards Anthropic, and tailwinds for OSS

Another issue, to really overgeneralize and state it plainly, is that people on twitter are very upset with Anthropic right now and that carries over to how they publicly discuss their models and products.

The opposite is true towards open source models. There is a secular trend towards open source, and all things relatively equal an open source or underdog model will peform much better on Xbench.

### 2) Twitter is owned by SpaceX and leans very pro-Elon.

There’s two trillion dollars of SpaceX stock making its weight felt on twitter. While I root for Elon, It’s hard to take Gavin Baker seriously when he’s on a book tour calling Grok Bot another “Claude Code moment”.

I feel that the love for Grok 4.6 and Grok Build is mostly legitimate, but the Grok Bot heat feels possibly a bit manufactured.

## Where this goes and how to improve things:

- I only used ~$150 in x-api costs to pull data over the prior 7 days. $100-$200 a day + the last 30 days would be a far more robust signal. I would expect some directional change in my results, and way more meaningful confidence intervals. Evals aren't cheap though.
- I should rank the intensity of sentiment and let that impact weighting.
- Not all twitter signal is created equally – in fact, I will possibly explore making this SF only (sorry NYC). Unfortunately, twitter posts mostly do not contain location data. To do this, we must read against every author, and that is $0.01 a read. I would probably need to 100-200x my costs to make this robust and statistically significant using only SF.
- I would like to include more models – Deepseek would be fun to include, and I would predict it would rank towards the top of Xbench if OpenCode is any signal.
- I feel i got pretty deep in <36 hours, but with a full week this would be far more rigorous.

## Models and harnesses compared:

The thirteen models are Claude Fable 5.1, Claude Opus 5, GPT-6 Astra, GPT-5.6 Sol, GPT-5.6 Luna, Muse Spark 1.3, Muse Spark 1.2, Gemini 3.8 Flash, Gemini 3.7 Flash, Grok 4.6, GLM 5.3, GLM 5.3 Flash, and Kimi K3. The harnesses are Claude Code, Codex, and Grok Bot, with OpenCode and Pi collected but left off the page because their samples were too thin.

## Link to Xbench

https://nicodunks.github.io/xbench/

Originally posted on X: https://x.com/nicochristie/status/2096284789766819924
