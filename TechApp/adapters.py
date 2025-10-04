from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Auto-link social accounts to existing users by email.
        """
        # If this social account is already linked, do nothing
        if sociallogin.is_existing:
            return  

        # Get email from Google profile
        email = sociallogin.account.extra_data.get("email")
        if not email:
            return  

        try:
            # Look for a user with this email
            user = User.objects.get(email=email)
            # Connect the Google account to the existing user
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            # If no user exists, normal signup flow continues
            pass
