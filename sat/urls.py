from django.urls import path
from core import views

app_name = 'sat'

urlpatterns = [
    path('', views.sat_home, name='sat_home'),
    path('bookmarks/', views.sat_bookmarks, name='sat_bookmarks'),
    path('bookmarks/clear/', views.sat_clear_bookmarks, name='sat_clear_bookmarks'),
    path('dashboard/', views.sat_dashboard, name='sat_dashboard'),
    path('statistics/', views.sat_statistics, name='sat_statistics'),
    path('<str:subject>/', views.sat_subject, name='sat_subject'),
    path('resource/<int:pk>/progress/', views.sat_update_progress, name='sat_update_progress'),
    path('resource/<int:pk>/bookmark/', views.sat_toggle_bookmark, name='sat_toggle_bookmark'),
    path('resource/<int:pk>/note/add/', views.sat_add_note, name='sat_add_note'),
    path('resource/<int:pk>/pdf/', views.sat_pdf_viewer, name='sat_pdf_viewer'),
    path('resource/<int:pk>/pdf/stream/', views.sat_pdf_stream, name='sat_pdf_stream'),
    path('note/<int:note_id>/delete/', views.sat_delete_note, name='sat_delete_note'),
]
