RESERVED_SLUGS = frozenset(
    {"admin", "api", "www", "app", "mail", "static", "media", "support", "status"}
)

MODULE_BOOKING = "booking"
MODULE_COMMISSIONS = "commissions"
MODULE_REPORTS = "reports"
MODULE_WHATSAPP = "notifications_whatsapp"
MODULE_KEYS = (MODULE_BOOKING, MODULE_COMMISSIONS, MODULE_REPORTS, MODULE_WHATSAPP)

VERTICALS = ("barbershop", "salon", "nails", "spa")
LANGUAGES = ("es", "en")

# Nombres de los parámetros de sesión que leen las políticas RLS.
DB_SETTING_TENANT = "app.current_tenant"
DB_SETTING_BYPASS = "app.bypass_rls"
