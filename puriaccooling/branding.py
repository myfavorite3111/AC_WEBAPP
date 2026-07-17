import os


def _brand_env(name, default):
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


APP_BRANDING = {
    "COMPANY_NAME": _brand_env("DEMO_COMPANY_NAME", "Demo AC Company"),
    "APP_NAME": _brand_env("DEMO_APP_NAME", "Air Conditioning Services ERP"),
    "TAGLINE": _brand_env("DEMO_COMPANY_TAGLINE", "HVAC service, installation, and maintenance management"),
    "DOMAIN": _brand_env("DEMO_PUBLIC_DOMAIN", "demo-ac.local"),
    "CONTACT_EMAIL": _brand_env("DEMO_CONTACT_EMAIL", "demo@example.com"),
    "CONTACT_PHONE": _brand_env("DEMO_CONTACT_PHONE", "+91 90000 00000"),
    "LOGO_TEXT": _brand_env("DEMO_LOGO_TEXT", "AC"),
    "BRAND_YEAR": _brand_env("DEMO_BRAND_YEAR", "2026"),
}
