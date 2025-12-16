# File: urls.py
# Author: Anna LaPrade (alaprade@bu.edu),11/25/2025
# Description: the url patterns for the project app

from django.urls import path
from .views import *
from django.urls import path, include

# generic view for authentication/authorization
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path("", HomeView.as_view(), name="cafe_home"),
    path("profile/<int:pk>/", ShowCafeProfileView.as_view(), name="show_cafe_profile"),
    path("cafe/<int:pk>/", CafeDetailView.as_view(), name="show_cafe"),
    path('login/', CafeLoginView.as_view(), name='login'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('logout/', LogoutView.as_view(next_page='cafe_home'), name='logout'),
    path('visit/<int:pk>/', VisitDetailView.as_view(), name='visit_detail'),
    path('favorite-item/<int:pk>/', FavoriteItemDetailView.as_view(), name='favorite_item_detail'),
    path('cafes/new/', CafeCreateView.as_view(), name='create_cafe'),
    path('all_cafes/', AllCafesView.as_view(), name='all_cafes'),
    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('sticker/place/', PlaceStickerView.as_view(), name='place_sticker'),
    path('update-sticker/', UpdateStickerView.as_view(), name='update_sticker'),
    path('stickers/delete/', StickerDeleteView.as_view(), name='delete_sticker'),
    path('cafe/<int:cafe_pk>/add_visit/', VisitCreateView.as_view(), name='create_visit'),
    path('cafe/<int:cafe_pk>/log_visit/', LogCafeVisitView.as_view(), name='log_cafe_visit'),
    path('wishlist/add/', AddWishlistView.as_view(), name='add_to_wishlist'),
    path('cafe/<int:cafe_pk>/remove_wish/', RemoveFromWishlistView.as_view(), name='remove_from_wishlist'),
    path('cafe/<int:cafe_pk>/add_wish/', AddToWishlistView.as_view(), name='add_to_wishlist_direct'),
    path('visit/<int:pk>/update/', VisitUpdateView.as_view(), name='update_visit'),
    path('visit/<int:pk>/delete/', VisitDeleteView.as_view(), name='delete_visit'),
    path('stats/', CafeStatsView.as_view(), name='cafe_stats'), # 
    path('search/', CafeSearchView.as_view(), name='cafe_search'),
    path('profile/theme/<str:theme_name>/update/', update_theme_preference, name='update_theme_preference'),
    path('cafe/<int:pk>/edit/', CafeUpdateView.as_view(), name='update_cafe'),
    path('cafe/<int:pk>/delete/', CafeDeleteView.as_view(), name='delete_cafe'),
    
]