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
