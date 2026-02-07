from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('videos/', views.video_list, name='video_list'),
    path('videos/<int:pk>/', views.video_detail, name='video_detail'),
    path('tests/', views.test_list, name='test_list'),
    path('tests/<int:pk>/', views.test_detail, name='test_detail'),
    path('tests/<int:pk>/take/', views.test_take, name='test_take'),
    path('tests/<int:pk>/retake/', views.test_retake, name='test_retake'),
    path('tests/<int:pk>/pause/', views.test_pause, name='test_pause'),
    path('tests/<int:pk>/resume/', views.test_resume, name='test_resume'),
    path('tests/<int:pk>/update-time/', views.test_update_time, name='test_update_time'),
    path('test-results/<int:pk>/', views.test_result, name='test_result'),
    path('profile/', views.profile, name='profile'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('statistics/', views.statistics, name='statistics'),
    path('analytics/', views.analytics, name='analytics'),
    path('weekly-summary/', views.weekly_summary, name='weekly_summary'),
    path('monthly-report/', views.monthly_report, name='monthly_report'),
    path('export/excel/', views.export_to_excel, name='export_to_excel'),
    path('bookmark/toggle/', views.toggle_bookmark, name='toggle_bookmark'),
    path('export/results/', views.export_results, name='export_results'),
    path('video/<int:pk>/update-progress/', views.update_video_progress, name='update_video_progress'),
    path('video/<int:pk>/note/add/', views.add_video_note, name='add_video_note'),
    path('video/note/<int:note_id>/delete/', views.delete_video_note, name='delete_video_note'),
    path('video/<int:pk>/rate/', views.rate_video, name='rate_video'),
    path('video/<int:pk>/comment/add/', views.add_video_comment, name='add_video_comment'),
    path('video/comment/<int:comment_id>/delete/', views.delete_video_comment, name='delete_video_comment'),
    path('playlist/create/', views.create_playlist, name='create_playlist'),
    path('video/<int:pk>/playlist/add/', views.add_video_to_playlist, name='add_video_to_playlist'),
    path('video/<int:pk>/playlist/remove/', views.remove_video_from_playlist, name='remove_video_from_playlist'),
    path('video/<int:pk>/bookmark/add/', views.add_video_bookmark, name='add_video_bookmark'),
]

