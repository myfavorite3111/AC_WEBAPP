from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as account_views


urlpatterns = [

    path('admin/', admin.site.urls),

    path('login/', account_views.login_view, name='login'),
    path('solutions/support/', account_views.login_view, name='legacy_demo_login'),

    path('', include('public.urls')),

    path('dashboard/', account_views.dashboard, name='dashboard'),

    path('add-manager/', account_views.add_manager, name='add_manager'),

    path('logout/', account_views.logout_view, name='logout'),

    path('customers/', include('customers.urls')),

    path('projects/', include('projects.urls')),

    path('store/', include('store.urls')),

    path('boq/', include('boq.urls')),

    path('material-issue/', include('material_issue.urls')),

    path('service/', include('service.urls')),

    path('amc/', include('amc.urls')),

    path('reports/', include('reports.urls')),
    path('training/', include('training.urls')),
    path("complaints/", include("complaints.urls")),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
