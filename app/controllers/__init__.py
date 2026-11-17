from app.controllers.assets import bp as assets_bp
from app.controllers.audit import bp as audit_bp
from app.controllers.categories import bp as categories_bp
from app.controllers.incidents import bp as incidents_bp
from app.controllers.stats import bp as stats_bp
from app.controllers.users import bp as users_bp

ALL_BLUEPRINTS = [users_bp, categories_bp, assets_bp, incidents_bp, audit_bp, stats_bp]
