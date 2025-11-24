

def has_any_model_permission(user, app_label, model_name):
    """Return True if user has any permission for the specified model."""
    
    actions = ["view", "add", "change", "delete"]
    return any( user.has_perm( f"{app_label}.{action}_{model_name}" ) for action in actions )

