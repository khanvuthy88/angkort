# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Modules

This repo contains two Odoo 18 modules:

- **`e_menu`** — REST API-based e-menu system for multi-tenant shop management (products, orders, JWT auth)
- **`ica_web_responsive`** — Web UI theme with responsive design and dark mode support

## Running Tests

```bash
# Run e_menu module tests (Odoo HttpCase)
odoo-bin -d <database> --test-enable --test-tags=e_menu -i e_menu

# Run a single test class or method
odoo-bin -d <database> --test-enable --test-tags=/e_menu:TestApiRoutes.test_login

# Manual API test script (requires `requests` and a running Odoo server)
python e_menu/test_auth_api.py

# Import Postman collection for manual testing
# e_menu/Postman_Collection_e_menu_Controllers.json
# e_menu/Postman_Environment_e_menu_Controllers.json
```

Tests in `e_menu/tests/test_api_routes.py` use `@tagged("-at_install", "post_install")` and set up `database.secret` system parameter required for JWT.

## Dependencies

```bash
pip install PyJWT  # only non-standard Python dependency (see requirements.txt)
```

## Architecture

### e_menu: API & Auth

All API routes are under `/angkort/api/v1/`. Controllers live in `e_menu/controllers/api/`:

| File | Routes |
|---|---|
| `auth.py` | `POST /login`, `POST /refresh`, `POST /logout` |
| `shop.py` | CRUD on `/shop` and `/shop/<id>` |
| `product.py` | CRUD on `/shop/<id>/product`, attributes, variants, categories |
| `order.py` | `GET /my/order` |
| `utils.py` | `APIUtilsMixin` base class + decorators |

**Auth flow:** Login → JWT issued → hashed tokens stored in `res.user.token` → every protected request validates JWT *and* checks DB for revocation (token `active` flag). Auth method name for protected routes is `auth="angkit"`.

**Response envelope:**
```json
// Success
{"status": true, "message": "...", "data": {...}}
// Error
{"status": false, "message": "...", "error": "..."}
```

**Common controller decorators** (from `api/utils.py`):
- `@validate_auth` — enforces bearer token + sets `request.env.user`
- `@validate_input_data` — parses and validates JSON/form body
- `@paginate_results` — applies `page`/`page_size` (default 20, max 100)
- `@verify_ownership` — checks `owner_user_id` or `create_uid` against current user

### e_menu: Multi-Tenant Data Model

- `res.partner` is extended with `type='store'` to represent shops; has `owner_user_id`, `shop_bank_ids`, `shop_wifi_ids`, `shop_open_hour_ids`
- Products, attributes, and categories all carry a `shop_id` FK to keep them scoped to their shop
- `product.attribute` has a `UNIQUE(name, shop_id)` SQL constraint — duplicate attribute names are allowed across shops
- `ir.http` overrides `_bearer_authenticate()` and adds `_auth_method_angkit()` for custom JWT validation

### e_menu: Security

- Group `e_menu.group_merchant` gates write access to shop/product/partner records
- Model access rules in `security/ir.model.access.csv`
- `database.secret` system parameter **must be set** for JWT signing to work; startup will log an error if missing

### ica_web_responsive

Auto-installs alongside the `web` module. Injects SCSS variable overrides and JS into the backend/frontend/dark-mode asset bundles. Model `res.users.settings` is extended with a `homemenu_config` JSON field.
