# ===== Настройки =====
COMPOSE = docker compose
WEB = $(COMPOSE) exec web
MANAGE = $(WEB) python manage.py

# ===== Базовые операции =====
up:
	$(COMPOSE) up -d

build:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart web nginx

logs:
	$(COMPOSE) logs -f --tail=200 web

logs-nginx:
	$(COMPOSE) logs -f --tail=200 nginx

ps:
	$(COMPOSE) ps

# ===== Django =====
migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

superuser:
	$(MANAGE) createsuperuser

collectstatic:
	$(MANAGE) collectstatic --noinput

shell:
	$(MANAGE) shell

# ===== Удобные комбо-команды =====
# Обновил ТОЛЬКО код/шаблоны/стили (без зависимостей)
update-code:
	$(COMPOSE) restart web
	$(MAKE) collectstatic
	$(COMPOSE) restart nginx

# Обновил базы данных/миграции
update-db:
	$(MAKE) makemigrations
	$(MAKE) migrate

# Полное обновление сайта (часто достаточно для деплоя)
update:
	$(COMPOSE) pull
	$(COMPOSE) up -d --build
	$(MAKE) migrate
	$(MAKE) collectstatic
	$(COMPOSE) restart nginx

# Если изменил зависимости в pyproject.toml
update-deps:
	$(COMPOSE) up -d --build web
	$(MAKE) migrate
	$(MAKE) collectstatic
	$(COMPOSE) restart nginx

# Быстрый доступ внутрь контейнеров
sh-web:
	$(COMPOSE) exec web sh

sh-nginx:
	$(COMPOSE) exec nginx sh
