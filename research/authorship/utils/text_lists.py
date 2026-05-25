from django.core.management.base import CommandError

from text_app.models.tbl_textlist import TblTextListDescription


def resolve_text_list(user, name_or_id: str) -> TblTextListDescription:
    """
    Resolve a text list by id or name.
    Resolution order:
      1. Exact integer id
      2. Exact name match (case-insensitive)
      3. icontains substring match
    Raises CommandError if the list is not found or multiple icontains matches exist.
    """
    # 1. Try integer id
    try:
        list_id = int(name_or_id)
        try:
            return TblTextListDescription.objects.get(id=list_id)
        except TblTextListDescription.DoesNotExist:
            raise CommandError(f"Text list with id={list_id} not found.")
    except ValueError:
        pass

    qs = TblTextListDescription.objects.filter(is_deleted=False)

    # 2. Exact name match
    exact = qs.filter(name__iexact=name_or_id).first()
    if exact:
        return exact

    # 3. icontains match
    matches = list(qs.filter(name__icontains=name_or_id).order_by("id"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(f"id={m.id} '{m.name}'" for m in matches)
        raise CommandError(
            f"Multiple text lists match '{name_or_id}': {names}. "
            "Use a more specific name or pass --list_id."
        )
    raise CommandError(
        f"No text list found matching '{name_or_id}'. "
        "Run load_authorship_demo or check the database."
    )
