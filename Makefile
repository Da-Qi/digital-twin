.PHONY: dev dev-backend dev-frontend db-shell migrate lint

dev:
	docker compose up --build

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

db-shell:
	docker compose exec db psql -U dtadmin -d digitaltwin

migrate:
	docker compose exec backend alembic upgrade head

migrate-new:
	cd backend && alembic revision --autogenerate -m "$(msg)"

lint:
	cd backend && ruff check . && cd ../frontend && npm run lint

.PHONY: reset-db
reset-db:
	docker compose down -v && docker compose up -d db
	sleep 3 && docker compose exec backend alembic upgrade head
