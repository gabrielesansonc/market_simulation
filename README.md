# Market Simulation Project

## Why I built this
I started this project because I realized I did not actually understand how markets price things.

I wanted to understand:
- how prices are formed when people have different beliefs
- how uncertainty changes market behavior
- how an exchange can make money

So this repo became a learning sandbox for market microstructure in a simple 2-outcome setup.

## What this simulates
This is a two-outcome prediction market (Polymarket/Kalshi style logic):
- Outcome `A` happens
- Outcome `B` happens (`B` = "not A")

Each person has a belief about the probability of `A`, then submits one order (`bid` or `ask`) on `A` or `B`.
Orders arrive over time, move around visually, and can match if prices cross.

When a match happens, the simulation tracks:
- matched trade details
- implied probabilities (midpoint style from book quotes)
- exchange profit (captured spread in this model)

## Market intuition (assumptions + math)
This section is the "how and why" behind the simulation for learning purposes.

### Core assumptions
- Two mutually exclusive outcomes:
  - `A` happens
  - `B` happens (`B = not A`)
- Each participant places one order of fixed size `1`.
- Orders are either:
  - `bid` (wants to buy)
  - `ask` (wants to sell)
- Matching only occurs when prices cross:
  - `bid >= ask`
- Every order must stay on the floor for at least a short minimum time before it can match (in the web app).
- Exchange profit is modeled as captured spread per matched trade:
  - `profit += (bid_price - ask_price) * qty`

### Belief model
- There is a base population probability for `A`: `y`.
- Individual beliefs are sampled around `y` with disagreement level `bettor_std`.
- To keep probabilities valid in `(0, 1)` without hard clipping normal draws, the simulator uses a logit-normal style sampling approach:
  - sample in logit space
  - map back with sigmoid

### Order prices
- For each arriving participant:
  - choose outcome (`A` or `B`)
  - choose side (`bid` or `ask`)
  - derive fair value from sampled belief
- In this current web configuration, spread parameters are fixed to `0`, so bids/asks are centered directly on beliefs.

### Implied probability from the book
Using last unmatched best quotes:

- `midA = (bestBidA + bestAskA) / 2`
- `midB = (bestBidB + bestAskB) / 2`

Normalized version:

- `P(A) = midA / (midA + midB)`
- `P(B) = midB / (midA + midB)`

Current visual app display is unnormalized:

- `P(A) = midA`
- `P(B) = midB`

This is intentional so you can see raw quote pressure independently on each side.

### Interpretation for students
- If `bestBidA` and `bestAskA` move up, market willingness to pay for `A` is rising.
- If `bestBidB` and `bestAskB` move up, market willingness to pay for `B` is rising.
- Wider bid/ask gaps mean more uncertainty or less immediate agreement.
- Faster order arrival (higher speed setting) produces more rapid quote updates and more market motion.

## Project structure
- `market_simulation.py`
  - Python proof-of-concept implementation.
  - Contains the core simulation and matching logic in the language I am most familiar with.
  - Useful for clean logic, inspection, and reproducible experiments.

- `usage_demo.ipynb`
  - Notebook proof-of-concept for running and inspecting simulation outputs step by step.
  - Good for debugging assumptions and understanding intermediate results.

- `market_visualizer.html`
  - "Vibe code" animated web version of the Python simulation.
  - Interactive controls, live arrivals, movement, matching animations, live implied probabilities, and exchange profit.
  - Built for intuition and visual understanding.

- `run_visualizer.py`
  - Simple local server launcher for the HTML app.

## How to run
### Animated web app
```bash
python3 run_visualizer.py
```
Then open:
`http://127.0.0.1:8000/market_visualizer.html`

### Python logic
```bash
python3 market_simulation.py
```

### Notebook
Open `usage_demo.ipynb` in Jupyter Lab/Notebook and run cells.

## Notes
- The Python and HTML versions are aligned conceptually, but the HTML is optimized for interactivity and animation.
- The goal is learning and intuition, not production trading execution.
