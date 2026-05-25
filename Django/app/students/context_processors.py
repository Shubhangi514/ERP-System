def user_role(request):
    """Inject the current user's role into every template context safely."""
    role = None
    is_principal = False

    if request.user.is_authenticated:
        if request.user.is_superuser:
            role = 'principal'
            is_principal = True
        else:
            try:
                role = request.user.profile.role
                is_principal = (role == 'principal')
            except Exception:
                role = 'student'

    return {
        'user_role': role,
        'is_principal': is_principal,
    }
