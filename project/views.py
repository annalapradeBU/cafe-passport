# File: views.py
# Author: Anna LaPrade (alaprade@bu.edu), 11/24/2025
# Description: the views for the project (cafe passport) app

import json
import traceback

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView, UpdateView, DeleteView
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Avg, Count, F, Q, Exists, OuterRef
from django.db.models.functions import Coalesce
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import plotly
import plotly.offline
import plotly.graph_objs as go

from .models import *
from .forms import *


# view to show a user's cafe profile
class ShowCafeProfileView(LoginRequiredMixin, DetailView):
    ''' View that shows a user's cafe profile, including associated visits and wishlist '''
    model = CafeProfile
    template_name = "project/show_cafe_profile.html"
    context_object_name = "profile"
    login_url = reverse_lazy('login')


    # add additional context
    def get_context_data(self, **kwargs):
        '''Adds visit history and wishlist data to the profile page context'''
        context = super().get_context_data(**kwargs)
        profile = self.get_object()

        # get the related photos (if no visit photo, use a favorite item photo or the cafe photo)
        visits = profile.get_all_visits().prefetch_related(
        'visitphoto_set', 'favoriteitem_set__itemphoto_set', 'cafe'
    )

        # get visit photo
        visit_list = []
        for visit in visits:
            # if there's a visit photo, user that
            if visit.visitphoto_set.exists():
                image_url = visit.visitphoto_set.first().image.url

            # otherwise, use a favorite item photo
            elif visit.favoriteitem_set.exists() and visit.favoriteitem_set.first().itemphoto_set.exists():
                image_url = visit.favoriteitem_set.first().itemphoto_set.first().image.url
            
            # otherwise, use the cafe image
            elif visit.cafe.image:
                cafe_image = visit.cafe.image
                
                if isinstance(cafe_image, str):
                    image_url = cafe_image  
                else:
                    image_url = cafe_image.url

            # otherwise use defualt image
            else:
                image_url = 'https://img.freepik.com/premium-vector/cute-doodle-cup-coffee-saucer-isolated-white-background_361363-219.jpg'

            visit_list.append({
                'visit': visit,
                'image_url': image_url
            })

        context["visits"] = visit_list

        # define the subquery, dhecks if a Visit exists for the same cafe and profile
        has_visit = Visit.objects.filter(
            cafe=OuterRef('cafe'),
            profile=profile
        ).values('pk')
        
        # query the wishlist and use Exists to annotate the dynamic 'is_visited' field
        wishlist = CafeWish.objects.filter(profile=profile).annotate(
            is_visited=Exists(has_visit) 
        ).select_related("cafe")

        # assign the correctly annotated queryset to the context
        context["wishlist"] = wishlist

        return context
    
    def get_login_url(self):
        '''return the UR for this app's login page'''

        return reverse('login')
    

class CafeDetailView(DetailView):
    ''' displays a detailed view of a single cafe '''
    model = Cafe
    template_name = "project/show_cafe.html"
    context_object_name = "cafe"

    def get_context_data(self, **kwargs):
        '''adds visit and wishlist status for the logged-in user'''
        context = super().get_context_data(**kwargs)
        cafe = self.object

        # initialize user-specific context variables to safe defaults
        context['wishlist_item'] = None
        context['has_visited'] = False
        context['visits'] = []
        context['user_is_authenticated'] = self.request.user.is_authenticated

        # check if the user is logged in before accessing profile data 
        if self.request.user.is_authenticated:
            # safely get the profile object
            try:
                profile = self.request.user.cafe_profile
            except AttributeError:
                # handle case where user is logged in but doesn't have a cafe_profile
                return context

            # fetch Visits
            visits = Visit.objects.filter(cafe=cafe, profile=profile).prefetch_related(
                'visitphoto_set', 'favoriteitem_set__itemphoto_set'
            )
            
            # fetch Wishlist Item
            wishlist_item = CafeWish.objects.filter(
                profile=profile,
                cafe=cafe
            ).first()

            # set Ccntext variables for logged-in sser
            context['wishlist_item'] = wishlist_item
            context['has_visited'] = visits.exists()

            # build visit list 
            visit_list = []
            for visit in visits:
                # priority: visit photo > item photo > cafe image > default
                if visit.visitphoto_set.exists():
                    image_url = visit.visitphoto_set.first().image.url
                elif visit.favoriteitem_set.exists() and visit.favoriteitem_set.first().itemphoto_set.exists():
                    image_url = visit.favoriteitem_set.first().itemphoto_set.first().image.url
                elif cafe.image:
                    image_url = cafe.image
                else:
                    image_url = '/static/project/default_cafe.jpg'
                
                visit_list.append({
                    'visit': visit,
                    'image_url': image_url
                })
            
            context['visits'] = visit_list

        return context

    

class SignUpView(CreateView):
    ''' displays the user signup form and creates a new user'''
    form_class = SignUpForm
    template_name = 'project/signup.html'
    success_url = reverse_lazy('login')


class HomeView(TemplateView):
    '''displays the application home page'''
    template_name = "project/cafe_home.html"

class CafeLoginView(LoginView):
    '''displays the user login form '''
    template_name = 'project/login.html'

    def get_success_url(self):
        '''determines where the user is redirected after logging in'''
        next_url = self.get_redirect_url()
        if next_url:
            return next_url

        # if user has a profile, redirect there
        if hasattr(self.request.user, 'cafe_profile'):
            return reverse('show_cafe_profile', kwargs={'pk': self.request.user.cafe_profile.pk})

        # fallback: home page
        return reverse('cafe_home')
    

class VisitDetailView(LoginRequiredMixin, DetailView):
    ''' displays detailed information for a single visit belonging to the logged-in user '''
    model = Visit
    template_name = "project/visit_detail.html"
    context_object_name = "visit"

    def get_queryset(self):
        '''
        restricts the queryset so that users may only view their own visits.
        returns:
            QuerySet: A filtered queryset of Visit objects owned by the user.
        '''
        # make sure the user can only view their own visits
        profile = self.request.user.cafe_profile
        return Visit.objects.filter(profile=profile).prefetch_related(
            'visitphoto_set',
            'favoriteitem_set__itemphoto_set',
            'stickers'
        )
    
    def get_context_data(self, **kwargs):
        '''
        adds sticker type options to the visit detail context.

        returns:
            dict: The template context including available StickerType objects.
        '''
        context = super().get_context_data(**kwargs)
        context['sticker_types'] = StickerType.objects.all()  # create a StickerType model for options
        return context
    

    def get_login_url(self):
        '''return the URL for this app's login page'''

        return reverse('login')
    
    
class FavoriteItemDetailView(LoginRequiredMixin, DetailView):
    ''' displays detailed information for a user's favorite item'''
    model = FavoriteItem
    template_name = "project/favorite_item_detail.html"
    context_object_name = "item"

    def get_queryset(self):
        '''
        restricts the queryset so users may only view their own favorite items.

        returns:
            QuerySet: A filtered queryset of FavoriteItem objects.'''
        
        return FavoriteItem.objects.filter(
            visit__profile__user=self.request.user
        ).prefetch_related('itemphoto_set')
    

    def get_login_url(self):
        '''return the URL for this app's login page'''

        return reverse('login')
    
    

class CafeCreateView(LoginRequiredMixin, CreateView):
    ''' displays and processes the cafe creation form '''
    model = Cafe
    form_class = CafeForm
    template_name = 'project/create_cafe.html'

    def form_valid(self, form):
        '''
        saves the new cafe and optionally adds it to the user's wishlist.

        args:
            form (ModelForm): The validated cafe creation form.

        returns:
            HttpResponse: Redirect response after successful form submission.'''
        
        response = super().form_valid(form)

        # if checkbox was checked, create wishlist entry
        if form.cleaned_data.get("add_to_wishlist"):
            profile = self.request.user.cafe_profile
            CafeWish.objects.get_or_create(
                profile=profile,
                cafe=self.object
            )

        return response

    def get_success_url(self):
        '''return the url to direct user upon successful cafe creation'''
        return reverse("show_cafe", kwargs={"pk": self.object.pk})
    

    def get_login_url(self):
        '''return the URL for this app's login page'''

        return reverse('login')
    

class AllCafesView(ListView):
    ''' displays a list of all cafes available in the global database'''
    model = Cafe
    template_name = "project/all_cafes.html"
    context_object_name = "cafes"


class WishlistView(LoginRequiredMixin, ListView):
    '''displays the logged-in user's cafe wishlist'''
    model = CafeWish
    template_name = "project/wishlist.html"
    context_object_name = "wishes"

    def get_queryset(self):
        '''
        retrieves all wishlist items for the authenticated user

        returns:
            QuerySet: Filtered CafeWish objects belonging to the user's profile
        '''
        # ensure the user is authenticated and has a profile
        if not self.request.user.is_authenticated:
            return CafeWish.objects.none()
        
        try:
            profile = self.request.user.cafe_profile
        except CafeProfile.DoesNotExist:
            return CafeWish.objects.none()

        # get all CafeWish objects for the user and select the related Cafe object
        queryset = CafeWish.objects.filter(profile=profile).select_related('cafe')
        
        return queryset

    def get_context_data(self, **kwargs):
        '''
        adds metadata to indicate whether each wishlist cafe has been visited

        returns:
            dict: Updated template context with visit indicators
        '''
        context = super().get_context_data(**kwargs)
        
        if not self.request.user.is_authenticated:
             return context

        try:
            profile = self.request.user.cafe_profile
        except CafeProfile.DoesNotExist:
            # if no profile, we can't determine visits, so just return
            return context

        # get the IDs of all Cafes the user has visited
        visited_cafe_ids = Visit.objects.filter(profile=profile).values_list('cafe_id', flat=True)
        
        # create a set for fast lookup
        visited_set = set(visited_cafe_ids)

        # process the wishlist items (which are already in context['wishes'] as self.object_list)
        decorated_wishes = []
        for wish in context['wishes']:
            cafe = wish.cafe # access the related cafe object
            
            # check if this cafe's ID is in the set of visited IDs
            has_visited = cafe.pk in visited_set
            
            # decorate the wish object with the new context
            decorated_wishes.append({
                'wish': wish,
                'cafe': cafe,  # passing the cafe separately for easier template access
                'has_visited': has_visited,
            })
            
        context['wishes'] = decorated_wishes
        
        return context
    
    def get_login_url(self):
        '''return the UR for this app's login page'''

        return reverse('login')
    


@method_decorator(csrf_exempt, name='dispatch')
class PlaceStickerView(LoginRequiredMixin, View):
    '''handles AJAX requests for placing a sticker on a visit image'''
    def post(self, request, *args, **kwargs):
        '''
        Creates and saves a new Sticker object using data from the request

        returns:
            JsonResponse: Success or error status with sticker ID
        '''

        try:
            data = json.loads(request.body)

            visit_id = data.get("visit_id")
            sticker_type_name = data.get("sticker_type")
            
            # ensure x/y/rotation/scale are converted to float 
            # and default to 0.0 or 1.0 if the key is missing or None
            # The 'x' and 'y' keys *must* be sent by the frontend.
            x_position = float(data.get("x", 0.0))
            y_position = float(data.get("y", 0.0))
            rotation = float(data.get("rotation", 0.0))
            scale = float(data.get("scale", 1.0))

            visit = get_object_or_404(Visit, pk=visit_id)
            sticker_type_obj = get_object_or_404(StickerType, name=sticker_type_name)
            
            new_sticker = Sticker.objects.create(
                visit=visit,
                type=sticker_type_obj, 
                x_position=x_position,
                y_position=y_position,
                rotation=rotation,
                scale=scale,
                # populate the image field using the StickerType object's image
                image=sticker_type_obj.image 
            )

            # must return the ID for the frontend to track
            return JsonResponse({"status": "success", "id": new_sticker.id})
            
        except Exception as e:
            print(f"Error placing sticker: {e}. Data received: {data}")
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
        
    def get_login_url(self):
        '''return the UR for this app's login page'''

        return reverse('login')
    


@method_decorator(csrf_exempt, name='dispatch')
class UpdateStickerView(View):
    '''handles AJAX requests to update an existing sticker's position and scale'''
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            sticker_id = data.get("sticker_id")
            
            sticker = get_object_or_404(Sticker, pk=sticker_id)
            
            sticker.x_position = float(data.get("x"))
            sticker.y_position = float(data.get("y"))
            sticker.rotation = float(data.get("rotation"))
            sticker.scale = float(data.get("scale"))
            
            sticker.save() 
            
            return JsonResponse({"status": "success"})
            
        except Exception as e:
            print(f"Error updating sticker: {e}. Data received: {data}")
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class StickerDeleteView(View):
    '''processes AJAX requests to delete a sticker'''

    def post(self, request, *args, **kwargs):
        try:
            # load JSON data from the request body
            data = json.loads(request.body)
            sticker_id = data.get('sticker_id')
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON format.")

        if not sticker_id:
            return HttpResponseBadRequest("Missing sticker_id in request body.")

        try:
            # retrieve the sticker instance or return a 404 error
            sticker = get_object_or_404(Sticker, id=sticker_id)
            
            # perform the deletion
            sticker.delete()
            
            # return a successful response
            return JsonResponse({'status': 'success', 'message': f'Sticker {sticker_id} deleted.'})
            
        except Exception as e:
            # handle any exceptions during deletion
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        

class VisitCreateView(LoginRequiredMixin, CreateView):
    ''' handles creation of a new cafe visit with nested formsets '''
    model = Visit
    form_class = VisitForm
    template_name = 'project/create_visit.html'

    def dispatch(self, request, *args, **kwargs):
        '''loads the associated Cafe object before processing'''
        self.cafe = get_object_or_404(Cafe, pk=self.kwargs['cafe_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        '''builds and attaches nested formsets to the template context'''
        context = super().get_context_data(**kwargs)
        context['cafe'] = self.cafe
        
        if self.request.POST:
            # instantiate main formsets from POST data
            item_formset = FavoriteItemFormSet(self.request.POST, self.request.FILES, prefix='items')
            visit_photo_formset = VisitPhotoFormSet(self.request.POST, self.request.FILES, prefix='photos')

        else: 
            # instantiate empty main formsets
            item_formset = FavoriteItemFormSet(prefix='items')
            visit_photo_formset = VisitPhotoFormSet(prefix='photos')

        # handle nested formsets for RENDERED forms 
        for form in item_formset:
            if form.prefix != item_formset.empty_form.prefix:
                # form.prefix is like 'items-0' so this replacement produces 'item_photos-0'
                prefix = form.prefix.replace(item_formset.prefix, 'item_photos')
                form.nested_photo_formset = ItemPhotoFormSetFactory(
                    self.request.POST or None,
                    self.request.FILES or None,
                    instance=form.instance,
                    prefix=prefix
                )

        # handle nested formset for the EMPTY TEMPLATE form
        empty_item_form = item_formset.empty_form

        empty_prefix = f'item_photos-{item_formset.prefix}-__prefix__'

        empty_item_form.nested_photo_formset = ItemPhotoFormSetFactory(
            instance=None,
            prefix=empty_prefix
        )
            
        context['favorite_item_formset'] = item_formset
        context['visit_photo_formset'] = visit_photo_formset
        
        return context

    def form_valid(self, form):
        '''
        saves Visit, VisitPhotos, FavoriteItems, and nested ItemPhotos atomically

        returns:
            HttpResponse: Redirect on successful save
            '''
        
        context = self.get_context_data()
        visit_photo_formset = context['visit_photo_formset']
        favorite_item_formset = context['favorite_item_formset']

        # check if the main form and top-level formsets are valid
        if not form.is_valid() or not visit_photo_formset.is_valid() or not favorite_item_formset.is_valid():
             return self.render_to_response(self.get_context_data(form=form))

        # check if ALL NESTED formsets are valid
        all_nested_valid = True
        for item_form in favorite_item_formset.forms:
            # check only forms that are not marked for deletion and have a nested formset attached
            if not item_form.cleaned_data.get('DELETE', False) and hasattr(item_form, 'nested_photo_formset'):
                if not item_form.nested_photo_formset.is_valid():
                    all_nested_valid = False
                    # break early if one nested formset is invalid
                    break 
        
        if not all_nested_valid:
            messages.error(self.request, "Please correct the errors in the Favorite Item Photos.")
            # re-render to show nested errors attached to the forms
            return self.render_to_response(self.get_context_data(form=form))

        # if everything is valid, save in an atomic transaction
        with transaction.atomic():
            # save the main Visit object
            self.object = form.save(commit=False)
            self.object.profile = self.request.user.cafe_profile
            self.object.cafe = self.cafe
            self.object.save() # saves the Visit and generates its PK

            # save the Visit Photos formset
            visit_photo_formset.instance = self.object
            visit_photo_formset.save()

            # save the Favorite Items and their nested Item Photos
            for item_form in favorite_item_formset.forms:
                # check for forms submitted with data AND not marked for deletion
                if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE'):
                    
                    # save the FavoriteItem object first to get its PK
                    favorite_item = item_form.save(commit=False)
                    favorite_item.visit = self.object # Ensure FK is set
                    favorite_item.save()
                    
                    # save the nested Item Photos formset
                    if hasattr(item_form, 'nested_photo_formset'):
                        nested_photo_formset = item_form.nested_photo_formset
                        # Must update the instance of the nested formset before saving
                        nested_photo_formset.instance = favorite_item 
                        nested_photo_formset.save()
                
                # handle deletion for existing items
                elif item_form.cleaned_data and item_form.cleaned_data.get('DELETE'):
                    item_form.instance.delete()
        
        messages.success(self.request, f"Visit to {self.cafe.name} logged successfully!")
        return redirect(self.get_success_url())


    def get_success_url(self):
        '''return the url to redirect users to on successful visit creation'''
        return reverse("visit_detail", kwargs={"pk": self.object.pk})
    

    def get_login_url(self):
        '''return the URL for this app's login page'''

        return reverse('login')
    
    



class LogCafeVisitView(LoginRequiredMixin, View):
    '''Processes complex POST requests for dynamically logging visits with media'''
    
    def post(self, request, cafe_pk, *args, **kwargs):
        ''' saves Visit, VisitPhotos, FavoriteItems, and nested ItemPhotos using JSON + file uploads

        returns:
            JsonResponse: Success or failure response'''
        # enforces user login before access (from LoginRequiredMixin)
        
        try:
            # retrieve the Cafe instance
            cafe = get_object_or_404(Cafe, pk=cafe_pk)
            
            # extract and parse dynamic data
            dynamic_data_json = request.POST.get('dynamic_data')
            
            if not dynamic_data_json:
                return JsonResponse({"detail": "Missing 'dynamic_data' payload."}, status=400)
            
            dynamic_data = json.loads(dynamic_data_json)
            
            # use a transaction to ensure all related objects are saved, or none are.
            with transaction.atomic():
                # create the main Visit object
                new_visit = Visit.objects.create(
                    profile=request.user.cafe_profile,
                    cafe=cafe,
                    date_visited=request.POST.get('date_visited'),
                    user_rating=request.POST.get('user_rating'),
                    amount_spent=request.POST.get('amount_spent'),
                    notes=request.POST.get('notes'),
                )

                # process Visit Photos
                for photo_data in dynamic_data.get('visitPhotos', []):
                    file_key = photo_data.get('file_key')
                    caption = photo_data.get('caption')
                    
                    if file_key and file_key in request.FILES:
                        VisitPhoto.objects.create(
                            visit=new_visit,
                            image=request.FILES[file_key],
                            caption=caption
                        )

                # process Favorite Items (including nested Item Photos)
                for item_data in dynamic_data.get('favoriteItems', []):
                    # Ensure the item has a name before creating
                    if not item_data.get('name'):
                        continue 
                        
                    # create the FavoriteItem object
                    favorite_item = FavoriteItem.objects.create(
                        visit=new_visit,
                        name=item_data.get('name'),
                        price=item_data.get('price'), 
                        rating=item_data.get('rating'),
                        description=item_data.get('description')
                    )
                    
                    # process nested Item Photos
                    for item_photo_data in item_data.get('photos', []):
                        item_file_key = item_photo_data.get('file_key')
                        item_caption = item_photo_data.get('caption')
                        
                        if item_file_key and item_file_key in request.FILES:
                            ItemPhoto.objects.create(
                                favorite_item=favorite_item,
                                image=request.FILES[item_file_key],
                                caption=item_caption
                            )

            
                            
            # return final success response
            return JsonResponse({
                "success": True,
                "detail": "Visit logged successfully!",
                "redirect_url": reverse('visit_detail', kwargs={'pk': new_visit.pk})
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON format in 'dynamic_data' field."}, status=400)
        
        except IntegrityError as e:
            # catches database constraints
            print("Database Integrity Error:", str(e))
            return JsonResponse({"detail": f"A database error occurred (missing required data or constraint violation)."}, status=500)
            
        except Exception as e:
            # catches all other Python errors
            print("\n" + "="*50)
            print(f"CRITICAL SERVER ERROR in LogCafeVisitView: {e}")
            traceback.print_exc()
            print("="*50 + "\n")
            
            return JsonResponse({"detail": f"An internal server error occurred: {type(e).__name__} - {str(e)}"}, status=500)

    def get_login_url(self):
        '''return the UR for this app's login page'''

        return reverse('login')
    
    
    

class AddWishlistView(LoginRequiredMixin, TemplateView):
    '''a view to handle the logic for searching for a cafe or adding a new one 
    to the wishlist, handling two forms (search/select and create new).'''
 
    template_name = 'project/add_to_wishlist.html'
    login_url = reverse_lazy('login')

    # helper method to initialize forms
    def get_forms(self, data=None, files=None):
        '''Returns initialized instances of the two forms'''
        return {
            'add_form': WishlistAddForm(data),
            'new_cafe_form': CafeForm(data, files)
        }

    def get_context_data(self, **kwargs):
        '''Initial context for the GET request (or when re-rendering POST)'''
        context = super().get_context_data(**kwargs)
        
        if 'forms' not in kwargs:
            kwargs['forms'] = self.get_forms()
        
        context.update(kwargs['forms'])
        
        # determine if the new cafe form should be shown based on a flag passed
        show_new_cafe = kwargs.get('show_new_cafe_form', False) or (
             'name' in context['new_cafe_form'].data and not context['new_cafe_form'].is_valid()
        )
        context.setdefault('show_new_cafe_form', show_new_cafe) 
        
        return context

    def post(self, request, *args, **kwargs):
        '''Handles POST requests, checking two possible form submissions'''
        
        forms = self.get_forms(request.POST, request.FILES)
        add_form = forms['add_form']
        new_cafe_form = forms['new_cafe_form']
        
        # create new cafe 
        if 'name' in request.POST and 'new_cafe_submit' in request.POST: # added button name check for reliability
            
            if new_cafe_form.is_valid():
                with transaction.atomic():
                    new_cafe = new_cafe_form.save(commit=False)
                    new_cafe.save()
                    new_cafe_form.save_m2m() 
                    
                    if new_cafe_form.cleaned_data.get('add_to_wishlist'):
                        profile = request.user.cafe_profile
                        CafeWish.objects.create(profile=profile, cafe=new_cafe)

                messages.success(request, f"New cafe, {new_cafe.name}, created and added to wishlist.")
                return redirect('wishlist') 
            
            # if invalid, re-render and keep the new cafe form visible
            else:
                messages.error(request, "Please correct the errors in the New Cafe form.")
                return self.render_to_response(self.get_context_data(forms=forms, show_new_cafe_form=True))

        # add Selected Cafe (Identified by the presence of 'cafe_choice' in POST)
        elif 'cafe_choice' in request.POST and request.POST.get('cafe_choice') != '':
            
            # create a form only with the cafe_choice data
            single_field_form = WishlistAddForm({'cafe_choice': request.POST.get('cafe_choice')})
            
            if single_field_form.is_valid():
                cafe_choice = single_field_form.cleaned_data['cafe_choice']
                
                try:
                    profile = request.user.cafe_profile
                    if not CafeWish.objects.filter(profile=profile, cafe=cafe_choice).exists():
                        CafeWish.objects.create(profile=profile, cafe=cafe_choice)
                    
                    messages.success(request, f"Successfully added {cafe_choice.name} to your wishlist.")
                    return redirect('wishlist') 
                
                except Exception as e:
                    messages.error(request, f"Error adding cafe to wishlist: {e}")
                    # fall through to re-render with error message
            
            else:
                 messages.error(request, "Please select a cafe from the list.")


        # if the form failed validation or no action was clearly defined, re-render
        return self.render_to_response(self.get_context_data(forms=forms))

    def get_login_url(self):
        '''return the URL for this app's login page'''

        return reverse('login')
    


class RemoveFromWishlistView(LoginRequiredMixin, View):
    '''Handles removing a cafe from the user's wishlist'''
    
    def post(self, request, cafe_pk):
        # get the Cafe and the current user's Profile
        cafe = get_object_or_404(Cafe, pk=cafe_pk)
        profile = request.user.cafe_profile
        
        # attempt to find and delete the CafeWish object
        try:
            wish_item = CafeWish.objects.get(profile=profile, cafe=cafe)
            wish_item.delete()
            
            # send a success message to the user
            messages.success(request, f"Successfully removed {cafe.name} from your wishlist. 👋")
            
            # redirect back to the same cafe's detail page
            return redirect('show_cafe', pk=cafe_pk) 
            
        except CafeWish.DoesNotExist:
            messages.error(request, f"{cafe.name} was not found on your wishlist.")
            return redirect('show_cafe', pk=cafe_pk)


    def get_login_url(self):
        '''return the UR for this app's login page'''

        return reverse('login')
    
        

class AddToWishlistView(LoginRequiredMixin, View):
    '''Handles adding a cafe directly to the user's wishlist.'''
    
    def post(self, request, cafe_pk):
        # get the Cafe and the current user's Profile
        cafe = get_object_or_404(Cafe, pk=cafe_pk)
        profile = request.user.cafe_profile
        
        # check if it already exists before creating
        if not CafeWish.objects.filter(profile=profile, cafe=cafe).exists():
            CafeWish.objects.create(profile=profile, cafe=cafe)
            messages.success(request, f"Successfully added {cafe.name} to your wishlist! 💖")
        else:
            messages.info(request, f"{cafe.name} is already on your wishlist.")
            
        # redirect back to the same cafe's detail page
        return redirect('show_cafe', pk=cafe_pk)
    

    def get_login_url(self):
        '''return the UR for this app's login page'''

        return reverse('login')
    
    



class VisitUpdateView(LoginRequiredMixin, UpdateView):
    '''Handles updating an existing Visit, including related nested forms/formsets'''

    model = Visit
    
    form_class = VisitForm 
    template_name = 'project/update_visit.html' 
    context_object_name = 'visit'

    
    def test_func(self):
        '''Allows update only if the visit belongs to the current user's profile'''
        visit = self.get_object()
        return visit.profile == self.request.user.cafe_profile



    def get_context_data(self, **kwargs):
        '''get all the formset data needed '''
        context = super().get_context_data(**kwargs)
        visit = self.object 

        if self.request.POST:
            # re-instantiate main formsets from POST data
            item_formset = FavoriteItemFormSet(self.request.POST, self.request.FILES, instance=visit, prefix='items')
            visit_photo_formset = VisitPhotoFormSet(self.request.POST, self.request.FILES, instance=visit, prefix='photos')

        else: 
            # instantiate formsets with existing data (instance=visit)
            item_formset = FavoriteItemFormSet(instance=visit, prefix='items')
            visit_photo_formset = VisitPhotoFormSet(instance=visit, prefix='photos')
        
        # handle bested Formsets for RENDERED forms
        for form in item_formset:
            if form.instance.pk: # only try to attach if the item exists
                prefix = form.prefix.replace(item_formset.prefix, 'item_photos')
                form.nested_photo_formset = ItemPhotoFormSetFactory(
                    self.request.POST or None,
                    self.request.FILES or None,
                    instance=form.instance,
                    prefix=prefix
                )

        # -handle Nested Formset for the EMPTY TEMPLATE Form
        empty_item_form = item_formset.empty_form
        empty_prefix = f'item_photos-{item_formset.prefix}-__prefix__'

        empty_item_form.nested_photo_formset = ItemPhotoFormSetFactory(
            instance=None,
            prefix=empty_prefix
        )
            
        context['favorite_item_formset'] = item_formset
        context['visit_photo_formset'] = visit_photo_formset
        
        return context

    def form_valid(self, form):
        '''validate the form and update the object'''
        context = self.get_context_data()
        visit_photo_formset = context['visit_photo_formset']
        favorite_item_formset = context['favorite_item_formset']

        # check if the main form and top-level formsets are valid
        if not form.is_valid() or not visit_photo_formset.is_valid() or not favorite_item_formset.is_valid():
             return self.render_to_response(self.get_context_data(form=form))

        # check if ALL NESTED formsets are valid
        all_nested_valid = True
        for item_form in favorite_item_formset.forms:
            # check only forms that are not marked for deletion and have a nested formset attached
            if not item_form.cleaned_data.get('DELETE', False) and hasattr(item_form, 'nested_photo_formset'):
                if not item_form.nested_photo_formset.is_valid():
                    all_nested_valid = False
                    break 
        
        if not all_nested_valid:
            messages.error(self.request, "Please correct the errors in the Favorite Item Photos.")
            return self.render_to_response(self.get_context_data(form=form))

        # if everything is valid, save in an atomic transaction
        with transaction.atomic():
            # save the main Visit object
            self.object = form.save() 

            # save the Visit Photos formset
            visit_photo_formset.save()

            # save the Favorite Items and their nested Item Photos
            for item_form in favorite_item_formset.forms:
                # check for forms submitted with data AND not marked for deletion
                if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE'):
                    
                    # save or update the FavoriteItem object
                    favorite_item = item_form.save(commit=False)
                    favorite_item.visit = self.object 
                    favorite_item.save()
                    
                    # save the Nested Item Photos formset
                    if hasattr(item_form, 'nested_photo_formset'):
                        nested_photo_formset = item_form.nested_photo_formset
                        nested_photo_formset.instance = favorite_item 
                        nested_photo_formset.save()
                
                # handle deletion for existing items
                elif item_form.cleaned_data and item_form.cleaned_data.get('DELETE'):
                    if item_form.instance.pk:
                        item_form.instance.delete()
        
        messages.success(self.request, f"Visit to {self.object.cafe.name} updated successfully!")
        return redirect(self.get_success_url())

    def get_success_url(self):
        '''redirect users on sucessul update'''
        return reverse("visit_detail", kwargs={"pk": self.object.pk})
    

    def get_login_url(self):
        '''return the UR for this app's login page'''

        return reverse('login')
    


class VisitDeleteView(LoginRequiredMixin, DeleteView):
    '''Handles deleting an existing Visit'''
    model = Visit
    template_name = 'project/delete_visit.html' 
    context_object_name = 'visit'
    
    # URL to redirect to after successful deletion (e.g., the user's profile page)
    success_url = reverse_lazy('cafe_home') 

    def test_func(self):
        """Allows deletion only if the visit belongs to the current user's profile."""
        visit = self.get_object()
        return visit.profile == self.request.user.cafe_profile

    # override delete method to add message
    def form_valid(self, form):
        '''validate form and add a success message for deletion'''
        # store info before deleting
        cafe_name = self.object.cafe.name
        
        # call the parent delete method
        response = super().form_valid(form)
        
        # add a success message
        messages.success(self.request, f"Visit to {cafe_name} successfully deleted. 🗑️")
        
        return response
    

    def get_login_url(self):
        '''return the URL for this app's login page'''

        return reverse('login')
    
    





class CafeStatsView(LoginRequiredMixin, TemplateView):
    '''Displays various statistics about the user's cafe visits, wishlist, 
    spending, and favorite items, including a Plotly chart for tags'''
    
    template_name = "project/cafe_stats.html"
    
    def get_context_data(self, **kwargs):
        '''get wishlist/visits/tag data'''
        context = super().get_context_data(**kwargs)
        profile = self.request.user.cafe_profile

        
        # all visits for the user
        visits = Visit.objects.filter(profile=profile)
        # all wishlist items for the user
        wishlist_items = CafeWish.objects.filter(profile=profile)
        # all favorited items for the user (via their visits)
        favorite_items = FavoriteItem.objects.filter(visit__profile=profile)

        # Wishlist Statistics
        total_wishlist = wishlist_items.count()
        # find all cafes the user has visited
        visited_cafes_in_wishlist = CafeWish.objects.filter(
            profile=profile,
            cafe__in=visits.values('cafe') # filter by cafes that have a visit entry
        ).count()
        
        unvisited_wishlist_count = total_wishlist - visited_cafes_in_wishlist
        
        # calculate percentage (handle division by zero)
        percent_visited_wishlist = (visited_cafes_in_wishlist / total_wishlist) * 100 \
                                   if total_wishlist > 0 else 0

        # Visit & Spending Statistics
        
        total_visits = visits.count()
    
        # aggregate on the Visit queryset
        visit_aggregates = visits.aggregate(
            avg_money_spent=Coalesce(Avg('amount_spent'), 0.0),
            avg_visit_rating=Coalesce(Avg('user_rating'), 0.0)
        )
        
        # Item Statistics

        # aggregate on the FavoriteItem queryset
        item_aggregates = favorite_items.aggregate(
            avg_item_cost=Coalesce(Avg('price'), 0.0),
            avg_item_rating=Coalesce(Avg('rating'), 0.0),
            total_items=Count('id')
        )

        # Most Common Tags/ Plotly Chart Generation

        # get the IDs of cafes the user has actually visited
        visited_cafe_ids = visits.values('cafe_id').distinct()
        
        # find the tags associated with those visited cafes, count them
        tag_counts = Cafe.objects.filter(
            pk__in=visited_cafe_ids
        ).values(
            'tags__name'
        ).annotate(
            count=Count('id', distinct=True)
        ).filter(
            tags__name__isnull=False
        ).order_by('-count')

        # generate Plotly Pie Chart
        if tag_counts.exists():
            labels = [t['tags__name'] for t in tag_counts]
            values = [t['count'] for t in tag_counts]
            
            # create Plotly figure object
            fig = go.Figure(data=[go.Pie(
                labels=labels, 
                values=values,
                hole=0.4,
                hoverinfo='label+percent+value',
                textinfo='percent',
                automargin=True
            )])
            
            # update layout for styling
            fig.update_layout(
                title='', # title is handled in the template card
                showlegend=True,
                legend=dict(orientation="h"),
                margin=dict(t=10, b=0, l=0, r=0)
            )

            
            
            # convert Plotly figure to HTML div element
            graph_div_tags = plotly.offline.plot(fig, auto_open=False, output_type="div")
        else:
            graph_div_tags = "<p class='text-center text-muted mt-5'>No tag data available yet. Add tags to your visited cafes!</p>"


        context['total_wishlist_cafes'] = total_wishlist
        context['visited_wishlist_count'] = visited_cafes_in_wishlist
        context['unvisited_wishlist_count'] = unvisited_wishlist_count
        context['percent_visited_wishlist'] = round(percent_visited_wishlist, 1)

        context['total_visits'] = total_visits
        context['avg_money_spent'] = round(visit_aggregates['avg_money_spent'], 2)
        context['avg_visit_rating'] = round(visit_aggregates['avg_visit_rating'], 1)
        
        context['avg_item_cost'] = round(item_aggregates['avg_item_cost'], 2)
        context['avg_item_rating'] = round(item_aggregates['avg_item_rating'], 1)
        context['total_favorite_items'] = item_aggregates['total_items']
        
        context['most_common_tags'] = tag_counts[:5] # for the simple list
        context['tag_chart_html'] = graph_div_tags # for the Plotly chart
        
        return context


    def get_login_url(self):
        '''return the URL for this app's login page'''

        return reverse('login')
    
    


class CafeSearchView(ListView):
    '''Handles searching for Cafes by name/address and filtering by tags'''
    
    model = Cafe
    template_name = "project/cafe_search.html"
    context_object_name = "cafes"
    paginate_by = 10 

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('tags') # optimize query
        
        # get the text query
        query = self.request.GET.get('q')
        
        # get the selected tag IDs
        selected_tags = self.request.GET.getlist('tags') 

        # apply Text Search 
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |          
                Q(address__icontains=query)        
            ).distinct() # use distinct() to avoid duplicates from text matches

        # apply Tag Filtering (AND/Intersection logic) 
        if selected_tags:
            # Filter queryset to only include Cafes that have ALL selected tags
            for tag_id in selected_tags:
                queryset = queryset.filter(tags__pk=tag_id) 

        return queryset.distinct() # Final distinct call in case initial queryset was unfiltered

    def get_context_data(self, **kwargs):
        '''get the tag data/query data to display it back to user'''
        context = super().get_context_data(**kwargs)
        
        # pass data needed for the template
        context['search_query'] = self.request.GET.get('q', '')
        
        # pass all tags for the checkboxes
        context['all_tags'] = Tag.objects.all().order_by('name')
        
        # Pass the list of tags that were selected by the user to maintain state
        # Convert the list of string IDs to integers for easier comparison in template
        selected_tag_ids = [int(tag_id) for tag_id in self.request.GET.getlist('tags')]
        context['selected_tags'] = selected_tag_ids
        context['selected_tag_objs'] = Tag.objects.filter(pk__in=selected_tag_ids)

        return context
    



@login_required
@require_POST
def update_theme_preference(request, theme_name):
    '''saves the user's selected theme to their CafeProfile'''
    
    # list of allowed themes to prevent injection
    allowed_themes = ['default', 'dark', 'forest', 'ocean', 'roastery', 'lavender', 'gothic']
    
    if theme_name not in allowed_themes:
        return HttpResponseBadRequest("Invalid theme name.")

    try:
        profile = request.user.cafe_profile
        profile.theme_preference = theme_name
        profile.save()
        
        # return a success JSON response for the fetch call
        return JsonResponse({'status': 'success', 'theme': theme_name})
    except Exception as e:
        # handle cases where profile doesn't exist or database error occurs
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    

# cafe update/edit view
class CafeUpdateView(LoginRequiredMixin, UpdateView):
    ''' allows authenticated users to update an existing Cafe '''

    model = Cafe
    form_class = CafeForm 
    template_name = 'project/create_cafe.html' # reuse the creation template for editing
    context_object_name = 'cafe'

    def get_success_url(self):
        '''redirects to the updated cafe's detail page'''
        # redirect back to the cafe detail page after a successful update
        messages.success(self.request, f"Cafe '{self.object.name}' updated successfully.")
        return reverse('show_cafe', kwargs={'pk': self.object.pk})

    def get_login_url(self):
        '''returns the login URL'''
        return reverse('login')
    
# cafe delete view
class CafeDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView): # add UserPassesTestMixin
    ''' Allows only staff/superusers to delete a Cafe '''
    model = Cafe
    template_name = 'project/delete_cafe.html' 
    context_object_name = 'cafe'
    success_url = reverse_lazy('all_cafes') 

    # test function to check user privileges 
    def test_func(self):
        '''
        Restricts deletion access to staff or superusers.

        Returns:
            bool: True if user is authorized.
        '''
        return self.request.user.is_staff or self.request.user.is_superuser

    # handles the case where the test_func fails
    def handle_no_permission(self):
        '''Handles unauthorized delete attempts'''
        messages.error(self.request, "You do not have permission to delete cafes.")
        return redirect(reverse('show_cafe', kwargs={'pk': self.kwargs['pk']}))

    def form_valid(self, form):
        '''adds a success message after deleting a cafe'''
        messages.success(self.request, f"Cafe '{self.get_object().name}' deleted successfully.")
        return super().form_valid(form)

    def get_login_url(self):
        '''returns the login URL'''
        return reverse('login')