from .branding import APP_BRANDING


def branding(request):
    return {"BRAND": APP_BRANDING}
