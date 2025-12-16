# File: forms.py -->
# Author: Anna LaPrade (alaprade@bu.edu), 11/27/2025 -->
# Description: forms for the project/cafe passport app -->
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import *
from django import forms
from django.forms import inlineformset_factory
from .models import Visit, VisitPhoto, FavoriteItem, ItemPhoto


# user sign up form
class SignUpForm(UserCreationForm):
    '''Sign up form for user/profile creation '''
    email = forms.EmailField(required=True)
    display_name = forms.CharField(max_length=255)
    home_city = forms.CharField(max_length=255)
    

    class Meta:
        '''asscoiated metadata'''
        model = User
        fields = ("username", "email", "password1", "password2", "display_name", "home_city")

    def save(self, commit=True):
        '''save the user and profile to db'''
        user = super().save(commit)
        profile = CafeProfile(
            user=user,
            display_name=self.cleaned_data['display_name'],
            home_city=self.cleaned_data['home_city']
        )
        if commit:
            profile.save()
        return user


# cafe creation form
class CafeForm(forms.ModelForm):
    '''A form to create new cafes'''
    add_to_wishlist = forms.BooleanField(
        required=False,
        initial=True, # checked by default
        label="Add to my wishlist"
    )
    
    new_tags = forms.CharField(
        max_length=255,
        required=False,
        help_text="<br>Comma-separated list of new tags"
    )

    google_rating = forms.FloatField(
        min_value=0.0,
        max_value=5.0,
        required=False,
        help_text="<br>Enter a rating between 0 and 5"
    )

    class Meta:
        '''assosciated metadata'''
        model = Cafe
        fields = ['name', 'address', 'google_rating', 'image', 'tags', 'new_tags', 'add_to_wishlist']
        widgets = {
            'tags': forms.CheckboxSelectMultiple,
            'image': forms.TextInput(attrs={
                'placeholder': 'Example: https://example.com/image.jpg'
            })
        }

    def save(self, commit=True):
        '''screating a new cafe + any new tags'''
        cafe = super().save(commit=False)
        if commit:
            cafe.save()
            self.save_m2m()
            # Handle new tags
            new_tags_str = self.cleaned_data.get('new_tags')
            if new_tags_str:
                tag_names = [t.strip() for t in new_tags_str.split(",") if t.strip()]
                for name in tag_names:
                    tag, created = Tag.objects.get_or_create(name=name)
                    cafe.tags.add(tag)
        return cafe
    

# visit creation form
class VisitForm(forms.ModelForm):
    '''A form to create new visits '''
    date_visited = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Visited"
    )
    user_rating = forms.FloatField(
        min_value=0.0,
        max_value=5.0,
        required=True,
        help_text="<br>Enter your rating (0 to 5)"
    )
    amount_spent = forms.FloatField(
        min_value=0.0,
        required=False,
        label="Amount Spent ($)"
    )

    class Meta:
        '''asscoiated metadata'''
        model = Visit
        fields = ['date_visited', 'user_rating', 'amount_spent', 'notes']


# visit photo creation form
class VisitPhotoForm(forms.ModelForm):
    '''form for each visit photo'''
    class Meta:
        model = VisitPhoto
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'placeholder': 'Optional photo caption'}),
        }
        labels = {
            'image': 'Upload Visit Photo',
        }

# item photo creation form
class ItemPhotoForm(forms.ModelForm):
    '''form for each item photo'''
    class Meta:
        model = ItemPhoto
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'placeholder': 'Optional item photo caption'}),
        }
        labels = {
            'image': 'Upload Item Photo',
        }

# item creation form
class FavoriteItemForm(forms.ModelForm):
    '''form for FavoriteItem (with nested ItemPhotos)'''
    class Meta:
        model = FavoriteItem
        fields = ['name', 'price', 'rating', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Lavender Latte'}),
            'price': forms.NumberInput(attrs={'placeholder': 'e.g., 5.50'}),
            'rating': forms.NumberInput(attrs={'placeholder': 'e.g., 4.5'}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes on the item'}),
        }


# formset factories to get the forms within forms
# creates the formset for Visit Photos (max 5 photos per visit)
VisitPhotoFormSet = inlineformset_factory(
    Visit, VisitPhoto, form=VisitPhotoForm, extra=1, max_num=5
)

# creates the formset for Favorite Item Photos (max 2 photos per item)
ItemPhotoFormSetFactory = inlineformset_factory(
    FavoriteItem, ItemPhoto, form=ItemPhotoForm, extra=1, max_num=2
)

# creates the formset for Favorite Items (max 3 items per visit)
FavoriteItemFormSet = inlineformset_factory(
    Visit, FavoriteItem, form=FavoriteItemForm, extra=1, max_num=3
)


# wishlist addition form
class WishlistAddForm(forms.Form):
    '''
    A form to allow users to add a cafe to their wishlist by searching 
    for an existing cafe or opting to create a new one.
    '''
    # the ForeignKey relationship represented by a ModelChoiceField
    # shows all existing Cafes in a dropdown/select box
    cafe_choice = forms.ModelChoiceField(
        queryset=Cafe.objects.all().order_by('name'), # fetch all cafes, ordered by name
        required=False,
        label="Select an existing Cafe:",
        help_text="Start typing the cafe name to search existing entries."
    )
    
    # a boolean field to trigger the new cafe form
    create_new_cafe = forms.BooleanField(
        required=False,
        label="Can't find it? Check here to add a brand new cafe."
    )

