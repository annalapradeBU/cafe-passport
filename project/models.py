# File: models.py
# Author: Anna LaPrade (alaprade@bu.edu), 11/24/2025
# Description: the models and their attributes for the project app

from django.db import models
from django.contrib.auth.models import User  # for authentication1
from django.core.validators import MinValueValidator, MaxValueValidator


# profile model for cafe passport
class CafeProfile(models.Model):
    '''Encapsulate the data of a CafeProfile by an user.'''

    # define the data attributed to this object 
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cafe_profile")
    #CharFeild for better performance 
    display_name = models.CharField(max_length=255)
    # specify a folder for organizational purposes
    profile_picture = models.ImageField(upload_to='cafe_profile_pictures/', blank=True, null=True)
    bio = models.TextField(blank=True)
    home_city = models.CharField(max_length=255)

    # all the theme preferences 
    theme_preference = models.CharField(
        max_length=50,
        default='default',
        # define all available choices for the user's theme settings 
        choices=[
            ('default', 'Default Theme 🎀'),
            ('dark', 'Midnight Theme 🌑'),
            ('forest', 'Forest Theme 🌿'),
            ('ocean', 'Ocean Theme 🌊'), 
            ('roastery', 'Roastery Theme ☕'), 
            ('lavender', 'Lavender Theme 🪻'),
            ('gothic', 'Gothic Theme 🖤'),
        ]
    )

    def __str__(self):
        ''' return a string representation of this model instance '''
        # display names might not be unique 
        return self.user.username
    
    def get_all_visits(self):
        """Return a QuerySet of Visits for this profile."""
        return Visit.objects.filter(profile=self).order_by('-date_visited')
    


class Tag(models.Model):
    '''Encapsulate the data of a Tag that can be used to help describe a cafe.'''

    # the many-to-many key apparently only needs to be on one side, I chose the cafe 
    # CharField to allow to make unique
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        ''' return a string representation of this model instance '''
        return self.name
    


class Cafe(models.Model):
    '''Encapsulate the data of a Cafe a user can create'''

    # define the data attributed to this object 
    # CharFeild for better performance
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    google_rating = models.FloatField(
        # restict ratings between 0 and 5
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0)
        ],
        blank=True,
        null=True
    )
    image= models.URLField(blank=True)
    # the many to many feild only needs to be on one of the models, relationship to tag
    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        ''' return a string representation of this model instance '''
        return self.name

   
class CafeWish(models.Model):
    '''Encapsulate the data of a Cafe wishlist associated with a user'''
    profile = models.ForeignKey(CafeProfile, on_delete=models.CASCADE)
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)
    visited = models.BooleanField(default=False)

    # make it so a cafe can be added to a single user's profile only once
    class Meta:
        unique_together = ('profile', 'cafe')

    def __str__(self):
        ''' return a string representation of this model instance '''
        return f"{self.profile.user.username}'s wishlist: {self.cafe.name}"
    
    #  checks if a Visit exists for this profile and cafe.
    @property
    def has_been_visited(self):
        '''
        dynamically checks if the profile has any recorded Visit to this cafe.
        '''
        # Check the Visit model for any entry matching the profile and cafe.
        return Visit.objects.filter(
            profile=self.profile,
            cafe=self.cafe
        ).exists()

    

class Visit(models.Model):
    '''encapsulate the data of a Visit associated with a Profile and a Cafe'''

    # define the data attributed to this object 
    profile = models.ForeignKey(CafeProfile, on_delete=models.CASCADE)
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE)
    date_visited = models.DateField()
    user_rating = models.FloatField()
    amount_spent = models.FloatField()
    notes = models.TextField(blank=True)

    def __str__(self):
        ''' return a string representation of this model instance '''
        return f"{self.profile} → {self.cafe} ({self.date_visited})"
    

class VisitPhoto(models.Model):
    '''encapsulate the data of a VisitPhoto associated with an Visit'''
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE)
    # specify a folder for organizational purposes
    image = models.ImageField(upload_to="visit_photos/")
    caption = models.TextField(blank=True)

    def __str__(self):
        ''' return a string representation of this model instance '''
        return f"Photo for {self.visit.cafe.name} on {self.visit.date_visited}"
    

class FavoriteItem(models.Model):
    '''encapsulate the data of a Favorite Item associated with a Visit'''

    # define the data attributed to this object
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    price = models.FloatField()
    rating = models.FloatField()
    description = models.TextField(blank=True)

    def __str__(self):
        ''' return a string representation of this model instance '''
        return self.name 
    

class ItemPhoto(models.Model):
    '''encapsulate the data of a ItemPhoto associated with a FavoriteItem'''
    favorite_item = models.ForeignKey(FavoriteItem, on_delete=models.CASCADE)
    # specify a folder for organizational purposes
    image = models.ImageField(upload_to="item_photos/")
    caption = models.TextField(blank=True)

    def __str__(self):
        ''' return a string representation of this model instance '''
        return f"Photo for {self.favorite_item.name}"
    

class Sticker(models.Model):
    '''encapsulate the data of a sticker associated with a Visit'''
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="stickers")
    
    type = models.ForeignKey('StickerType', on_delete=models.CASCADE, related_name="placed_stickers")
    
    x_position = models.FloatField()
    y_position = models.FloatField()
    rotation = models.FloatField()
    scale = models.FloatField()
    
    image =  models.ImageField(upload_to="stickers/", blank=True, null=True) 

    def __str__(self):
        '''string representation of this model'''
        return f"Sticker {self.type.name} on {self.visit}"



class StickerType(models.Model):
    '''define available sticker types that users can place'''
    name = models.CharField(max_length=255, unique=True) # used for lookup
    image = models.ImageField(upload_to="sticker_options/")

    def __str__(self):
        '''string representation of this model'''
        return self.name

