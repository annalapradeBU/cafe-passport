#<!-- File: context_processors.py -->
#<!-- Author: Anna LaPrade (alaprade@bu.edu), 12/05/2025 -->
#<!-- Description: proceeses theme context to allow themes to be user specific for the project (cafe passport) app -->


def user_theme_processor(request):
    '''
    adds the current user's theme preference to the template context.
    '''
    if request.user.is_authenticated:
        # check if the user has a linked CafeProfile
        try:
            profile = request.user.cafe_profile
            # return the theme preference from the database
            return {'user_theme': profile.theme_preference}
        except Exception:
            # handle case where user is authenticated but profile is missing
            return {'user_theme': 'default'}
    
    # return default theme for anonymous users
    return {'user_theme': 'default'}