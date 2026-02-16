# readme_for_future_llm

This file is for future coding agents/LLMs.  
Goal: load this first, then make changes safely without breaking the simulation.

## Project intent
This repo is a learning simulation of a 2-outcome prediction market.
- Outcomes: `A` or `B` (`B = not A`)
- User wants intuition for:
  - pricing
  - uncertainty
  - exchange profit mechanics

There are 2 implementations:
- `market_simulation.py`: Python proof-of-concept logic
- `market_visualizer.html`: interactive animated web app (main UX)

`usage_demo.ipynb` is a notebook proof-of-concept around Python logic.

## Current source of truth for UX
The web app is `market_visualizer.html` and is currently the most feature-rich.
Use `run_visualizer.py` to run locally.

## Runtime model in web app
### Market generation
- No pre-generated list anymore.
- Offers are generated live, one per tick, from **current slider values**.
- This allows real-time parameter changes while running.

### Randomness
- Seed input was removed from UI.
- Start uses a random seed each run:
  - `seed = Math.floor(Math.random() * 0xffffffff)`

### Matching
- Orders are stored in book:
  - `state.book.A.bid`, `state.book.A.ask`
  - `state.book.B.bid`, `state.book.B.ask`
- Match condition:
  - best mature bid >= best mature ask
- Important: minimum residence time enforced:
  - `state.minResidenceMs = 1500`
  - orders cannot match before this age on floor.

### Implied probabilities
- Computed from unmatched best quotes (midpoint-based).
- Current displayed values are **unnormalized**:
  - `P(A) = midA`
  - `P(B) = midB`
- Normalized equations are documented in `README.md`.

### Exchange profit
- In web app, exchange profit is captured spread:
  - `profit += (bid_price - ask_price) * qty`
- Displayed with `$`.

## Animation/rendering stack
- `PixiJS` for rendering
- `GSAP` for animation/timelines
- A single shared market field canvas (not 4 separate visible lanes)
- Invisible walking zones by group:
  - `A_ask`, `A_bid`, `B_ask`, `B_bid`

### Current avatar state
- Static emoji was replaced with a Pixi vector “walking avatar”.
- Walking cycle is generated procedurally (arms/legs/head bob), tied to movement distance.
- This was done because emoji looked pixelated on mobile.

### Speed coupling
Speed slider currently controls:
1. Interarrival interval (inverted mapping):
   - higher slider => faster arrivals
2. Walking speed:
   - proportional to arrival rate (`offers/sec`)
   - minimum walking speed tuned to half of previous baseline
3. Match spread-pop animation timing:
   - slower slider => slower/longer spread animation
   - faster slider => faster/shorter spread animation

## Charting
- In-page canvas line chart (no external chart library).
- Red line: A, Blue line: B.
- Latest point is intentionally placed around **2/3** chart width (not right edge).
- End labels show latest percentages (`A xx.x%`, `B xx.x%`).

## UI assumptions/decisions
- Number of offers default: `100`
- `offers_std` hidden/fixed to `0`
- spread controls hidden/fixed to `0`
- probability slider: `0..1`
- disagreement (`bettor_std`) slider: `0..0.5`
- Speed label includes a blank line hack for vertical alignment with other controls.

## Known fragile areas (edit carefully)
1. `updateWanderMovement`:
   - must define `nowMs` before using it
   - this previously broke all movement/matching when incorrect
2. Matching flow:
   - if you move/remove `tryMatchAll(nowMs)`, ensure minimum residence logic still applies
3. Speed mapping:
   - multiple behaviors depend on same slider (arrivals, walk speed, match timing)
4. Canvas resize:
   - chart and Pixi surfaces both have resize hooks

## Files and responsibilities
- `market_visualizer.html`
  - Everything front-end: HTML/CSS/JS in one file
- `market_simulation.py`
  - Python simulation API and matching logic
  - includes bounded probability sampling (logit/sigmoid)
- `README.md`
  - user-facing explanation and market intuition/math
- `run_visualizer.py`
  - local static server helper

## Quick local run
```bash
python3 run_visualizer.py
```
Open:
`http://127.0.0.1:8000/market_visualizer.html`

## If adding features
Recommended workflow:
1. Change one subsystem at a time (UI, generation, matching, animation, chart).
2. Verify:
   - people move
   - matches happen
   - spread pops
   - chart updates
   - profit updates
3. Keep existing behavior unless user explicitly requests a model change.

## User preference patterns from history
- Prefers rapid visual iteration and immediate UX feedback.
- Wants simple wording for controls/tooltips.
- Wants market formulas documented in README (not cluttering UI).
- Strongly dislikes regressions in movement/matching animations.
