from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using a dynamic key.
    Usage: {{ my_dict|get_item:my_key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def file_exists(field_file):
    """
    Return True only when a FileField/ImageField has a valid storage object
    and the underlying file exists in storage.
    """
    try:
        if not field_file:
            return False
        storage = getattr(field_file, 'storage', None)
        name = getattr(field_file, 'name', '')
        if not storage or not name:
            return False
        try:
            return storage.exists(name)
        except Exception:
            # Some storage backends (e.g., Cloudinary) may not support exists().
            # Fall back to URL availability when possible.
            try:
                return bool(getattr(field_file, 'url', None))
            except Exception:
                return False
    except Exception:
        return False
