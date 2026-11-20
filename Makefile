# One command: make fight
# Windows without make: run the three commands under `fight` by hand.

.PHONY: fight up down keys dashboard test clean

fight: .env up
	uv run fight.py

.env:
	uv run fight.py init-env

up: .env
	docker compose up -d
	uv run fight.py wait-otari

down:
	docker compose down

keys: .env
	uv run fight.py keys

dashboard:
	@echo "http://localhost:8000  (sign in with the admin key: make keys)"

test:
	uv run --group dev pytest -q

clean: down
	docker compose down -v
	rm -f fight-card.md fight-card.json fight-log.jsonl
