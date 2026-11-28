# SPDX-License-Identifier: AGPL-3.0-or-later
"""Items in play (Zephyrex RPG, 2026-11-28, for the operator's story checks; split with Zephyrex
VTT: the wiki keeps an item's existence and whereabouts, the VTT its rules effect, its sheet gear
and where it is drawn on a scene).

- An ItemInstance's location_id is where it lies; an EntityInventory row is who carries it now (de
  facto); owner_person_id is whose it is (de jure). Taking, spending and dropping never change the
  owner.
- An instance owned by a person with no carry row and no location (a sheet's gear made before the
  VTT read EntityInventory) counts as carried by its owner; the first take, spend or drop that
  touches it writes the carry row.
- What a holder carries of an instance is the carry row's quantity, which these moves keep equal
  to the instance's own: a partial move splits the instance.
- A stackable item (stack_size above 1) merges into the stack of the same item and owner already
  carried by the taker, or already lying at the place it is dropped.

Each runs as the requester: the framework's EDIT on the rows is the guard (the campaign's GM).
"""

from typing import Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel as PlainModel
from pydantic import Field

# Holders that leave an item free to take: it lies in or on them (a place, a chest).
OPEN_HOLDERS = ("location", "item")


class ItemHere(PlainModel):
    item_instance_id: str
    item_id: Optional[str]
    name: str
    kind: Optional[str]
    quantity: int
    owner_person_id: Optional[str]
    held_by: Optional[dict[str, str]] = Field(None, description="{type, id} of the record carrying it, if any")


class ItemsAt(PlainModel):
    items: list[ItemHere]


class ItemsCarried(PlainModel):
    items: dict[str, list[ItemHere]] = Field(..., description="Each person asked for: what they carry")


class ItemTaken(PlainModel):
    item_instance_id: str = Field(..., description="The instance the person now carries (a merged stack's, when it merged)")
    taken: int
    left: int = Field(..., description="How many stayed where it was")


class ItemSpent(PlainModel):
    item_instance_id: str
    spent: int
    left: int = Field(..., description="How many the person still carries of it (0: the instance is gone)")


class ItemDropped(PlainModel):
    item_instance_id: str = Field(..., description="The instance now lying there (a merged stack's, when it merged)")
    dropped: int
    location_id: str


def _managers(model_registry: Any, requester_id: str) -> tuple[Any, Any, Any, Any]:
    from zephyrex.extensions.rpg_core.BLL_RPGCore import _manager  # type: ignore[import-not-found]
    from zephyrex.extensions.genealogy.BLL_Genealogy import PersonManager
    from zephyrex.extensions.world_inventory.BLL_WorldInventory import (  # type: ignore[import-not-found]
        EntityInventoryManager,
        ItemInstanceManager,
        ItemManager,
    )

    return (
        _manager(model_registry, requester_id, ItemInstanceManager),
        _manager(model_registry, requester_id, EntityInventoryManager),
        _manager(model_registry, requester_id, ItemManager),
        _manager(model_registry, requester_id, PersonManager),
    )


def _live(manager: Any, filters: Optional[list[Any]] = None, **kwargs: Any) -> list[Any]:
    """A list's rows without soft-deleted ones, whoever reads (ROOT's reads include them)."""
    from zephyrex.extensions.rpg_core.BLL_RPGCore import _listed  # type: ignore[import-not-found]

    return _listed(manager, filters, **kwargs)


def _one(manager: Any, row_id: Any) -> Any:
    """A row by id, 404 when it is soft-deleted too (a get as ROOT answers a tombstone)."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    rows = _live(manager, [FieldComparison(manager.Model, "id", "in", [str(row_id)])])
    if not rows:
        raise HTTPException(status_code=404, detail=f"{manager.Model.__name__} not found")
    return rows[0]


def _quantity(value: Any) -> int:
    return int(value) if value else 1


def _wanted(quantity: Optional[int], have: int, verb: str) -> int:
    if quantity is None:
        return have
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
        raise HTTPException(status_code=422, detail="quantity is a whole number from 1")
    if quantity > have:
        raise HTTPException(status_code=422, detail=f"Only {have} to {verb}")
    return quantity


def _holding(holdings: Any, instance_id: str) -> Optional[Any]:
    rows = _live(holdings, item_instance_id=instance_id)
    return rows[0] if rows else None


def _carried_by(instance: Any, holding: Optional[Any], person_id: str) -> Optional[int]:
    """How many of ``instance`` the person carries, or none when they don't carry it."""
    if holding is not None:
        if holding.target_entity_type == "person" and str(holding.target_entity_id) == person_id:
            return _quantity(holding.quantity)
        return None
    if str(instance.owner_person_id or "") == person_id and not instance.location_id:
        return _quantity(instance.quantity)
    return None


def _stackable(items: Any, item_id: Optional[str]) -> bool:
    if not item_id:
        return False
    try:
        return _quantity(_one(items, item_id).stack_size) > 1
    except HTTPException:
        return False


def _shown(instance: Any, items: Any, holding: Optional[Any]) -> ItemHere:
    name, kind = "", None
    if instance.item_id:
        try:
            item = _one(items, instance.item_id)
            name, kind = str(item.name or ""), item.kind
        except HTTPException:
            pass
    held = {"type": str(holding.target_entity_type), "id": str(holding.target_entity_id)} if holding is not None else None
    amount = _quantity(holding.quantity) if holding is not None else _quantity(instance.quantity)
    return ItemHere(
        item_instance_id=str(instance.id), item_id=instance.item_id, name=name, kind=kind, quantity=amount, owner_person_id=instance.owner_person_id, held_by=held
    )


def items_at(model_registry: Any, requester_id: str, location_id: str, include_inside: bool = False) -> ItemsAt:
    """What lies at a place, nobody carrying it: instances whose location_id is the place (or, with
    include_inside, a place inside it) and no one holds, and those the place itself holds."""
    from zephyrex.extensions.rpg_core.BLL_RPGCore import _manager  # type: ignore[import-not-found]
    from zephyrex.extensions.world_spatial.BLL_WorldSpatial import LocationManager  # type: ignore[import-not-found]
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    instances, holdings, items, _people = _managers(model_registry, requester_id)
    places = _manager(model_registry, requester_id, LocationManager)
    _one(places, location_id)
    wanted = [location_id]
    if include_inside:
        frontier = [location_id]
        while frontier:
            children = [str(row.id) for row in _live(places, [FieldComparison(places.Model, "parent_id", "in", frontier)]) if str(row.id) not in wanted]
            wanted.extend(children)
            frontier = children
    lying = _live(instances, [FieldComparison(instances.Model, "location_id", "in", wanted)])
    held_here = _live(holdings, [FieldComparison(holdings.Model, "target_entity_id", "in", wanted)])
    shown: dict[str, ItemHere] = {}
    for instance in lying:
        holding = _holding(holdings, str(instance.id))
        if holding is None or holding.target_entity_type in OPEN_HOLDERS:
            shown[str(instance.id)] = _shown(instance, items, holding)
    for holding in held_here:
        if holding.target_entity_type != "location" or str(holding.item_instance_id) in shown:
            continue
        try:
            instance = _one(instances, holding.item_instance_id)
        except HTTPException:
            continue
        shown[str(instance.id)] = _shown(instance, items, holding)
    return ItemsAt(items=sorted(shown.values(), key=lambda one: (one.name.casefold(), one.item_instance_id)))


def items_carried(model_registry: Any, requester_id: str, person_ids: list[str]) -> ItemsCarried:
    """What each person carries: their carry rows, and what they own that nothing holds and lies
    nowhere (gear from before carry rows)."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    wanted = sorted({str(one).strip() for one in person_ids if str(one).strip()})
    if len(wanted) > 100:
        raise HTTPException(status_code=422, detail="At most 100 people")
    instances, holdings, items, people = _managers(model_registry, requester_id)
    if not wanted:
        return ItemsCarried(items={})
    visible = {str(row.id) for row in _live(people, [FieldComparison(people.Model, "id", "in", wanted)])}
    found: dict[str, list[ItemHere]] = {one: [] for one in wanted if one in visible}
    rows = [row for row in _live(holdings, [FieldComparison(holdings.Model, "target_entity_id", "in", sorted(visible))]) if row.target_entity_type == "person"] if visible else []
    for holding in rows:
        try:
            instance = _one(instances, holding.item_instance_id)
        except HTTPException:
            continue
        found[str(holding.target_entity_id)].append(_shown(instance, items, holding))
    owned = _live(instances, [FieldComparison(instances.Model, "owner_person_id", "in", sorted(visible))]) if visible else []
    for instance in owned:
        if instance.location_id or _holding(holdings, str(instance.id)) is not None:
            continue
        found[str(instance.owner_person_id)].append(_shown(instance, items, None))
    for one in found.values():
        one.sort(key=lambda item: (item.name.casefold(), item.item_instance_id))
    return ItemsCarried(items=found)


def _split(instances: Any, instance: Any, amount: int) -> Any:
    """``amount`` of ``instance`` as an instance of its own (the original keeps the rest)."""
    return instances.create(item_id=instance.item_id, owner_person_id=instance.owner_person_id, quantity=amount, durability=instance.durability)


def take_item(model_registry: Any, requester_id: str, person_id: str, item_instance_id: str, quantity: Optional[int] = None) -> ItemTaken:
    """The person picks up an item lying somewhere (or in a place or container holding it): all of
    it, or ``quantity`` split off its stack. Refused (409) when another person or an organisation
    carries it; the owner never changes."""
    instances, holdings, items, people = _managers(model_registry, requester_id)
    _one(people, person_id)
    instance = _one(instances, item_instance_id)
    holding = _holding(holdings, item_instance_id)
    if _carried_by(instance, holding, person_id) is not None:
        # Already theirs to hand: nothing moves.
        return ItemTaken(item_instance_id=item_instance_id, taken=0, left=0)
    if holding is not None and holding.target_entity_type not in OPEN_HOLDERS:
        raise HTTPException(status_code=409, detail=f"Carried by a {holding.target_entity_type}: not lying free to take")
    if holding is None and _carried_by(instance, None, str(instance.owner_person_id or "")) is not None and str(instance.owner_person_id) != person_id:
        raise HTTPException(status_code=409, detail="Carried by its owner: not lying free to take")
    have = _quantity(holding.quantity) if holding is not None else _quantity(instance.quantity)
    amount = _wanted(quantity, have, "take")
    left = have - amount
    if left:
        instances.update(id=item_instance_id, quantity=left)
        if holding is not None:
            holdings.update(id=str(holding.id), quantity=left)
        moving = _split(instances, instance, amount)
    else:
        if holding is not None:
            holdings.delete(id=str(holding.id))
        moving = instances.update(id=item_instance_id, location_id=None) if instance.location_id else instance
    # A stack of the same item and owner the person already carries takes it in.
    if _stackable(items, instance.item_id):
        for row in _live(holdings, target_entity_type="person", target_entity_id=person_id):
            if str(row.item_instance_id) == str(moving.id):
                continue
            try:
                stack = _one(instances, row.item_instance_id)
            except HTTPException:
                continue
            if str(stack.item_id) == str(instance.item_id) and str(stack.owner_person_id or "") == str(instance.owner_person_id or ""):
                total = _quantity(row.quantity) + amount
                instances.update(id=str(stack.id), quantity=total)
                holdings.update(id=str(row.id), quantity=total)
                instances.delete(id=str(moving.id))
                return ItemTaken(item_instance_id=str(stack.id), taken=amount, left=left)
    if moving.location_id:
        moving = instances.update(id=str(moving.id), location_id=None)
    holdings.create(item_instance_id=str(moving.id), target_entity_type="person", target_entity_id=person_id, quantity=amount)
    return ItemTaken(item_instance_id=str(moving.id), taken=amount, left=left)


def _carried_or_refused(instances: Any, holdings: Any, person_id: str, item_instance_id: str) -> tuple[Any, Optional[Any], int]:
    instance = _one(instances, item_instance_id)
    holding = _holding(holdings, item_instance_id)
    have = _carried_by(instance, holding, person_id)
    if have is None:
        raise HTTPException(status_code=409, detail="They don't carry it")
    return instance, holding, have


def spend_item(model_registry: Any, requester_id: str, person_id: str, item_instance_id: str, quantity: int = 1) -> ItemSpent:
    """The person uses up ``quantity`` of an item they carry (a potion drunk, an arrow loosed): at 0
    the carry row and the instance are removed."""
    instances, holdings, _items, people = _managers(model_registry, requester_id)
    _one(people, person_id)
    instance, holding, have = _carried_or_refused(instances, holdings, person_id, item_instance_id)
    amount = _wanted(quantity, have, "spend")
    left = have - amount
    if left:
        instances.update(id=item_instance_id, quantity=left)
        if holding is not None:
            holdings.update(id=str(holding.id), quantity=left)
    else:
        if holding is not None:
            holdings.delete(id=str(holding.id))
        instances.delete(id=str(instance.id))
    return ItemSpent(item_instance_id=item_instance_id, spent=amount, left=left)


def drop_item(
    model_registry: Any, requester_id: str, person_id: str, item_instance_id: str, quantity: Optional[int] = None, location_id: Optional[str] = None
) -> ItemDropped:
    """The person puts down an item they carry, all of it or ``quantity``, at ``location_id`` or
    where they are (422 when neither is known); the owner never changes."""
    from zephyrex.extensions.rpg_core.BLL_RPGCore import _manager  # type: ignore[import-not-found]
    from zephyrex.extensions.world_spatial.BLL_WorldSpatial import LocationManager  # type: ignore[import-not-found]

    instances, holdings, items, people = _managers(model_registry, requester_id)
    person = _one(people, person_id)
    place = location_id or getattr(person, "location_id", None)
    if not place:
        raise HTTPException(status_code=422, detail="Name the place: they are nowhere")
    _one(_manager(model_registry, requester_id, LocationManager), place)
    instance, holding, have = _carried_or_refused(instances, holdings, person_id, item_instance_id)
    amount = _wanted(quantity, have, "drop")
    left = have - amount
    if left:
        instances.update(id=item_instance_id, quantity=left)
        if holding is not None:
            holdings.update(id=str(holding.id), quantity=left)
        else:
            holdings.create(item_instance_id=item_instance_id, target_entity_type="person", target_entity_id=person_id, quantity=left)
        moving = _split(instances, instance, amount)
    else:
        if holding is not None:
            holdings.delete(id=str(holding.id))
        moving = instance
    # A stack of the same item and owner already lying free there takes it in.
    if _stackable(items, instance.item_id):
        for stack in _live(instances, location_id=place):
            if str(stack.id) == str(moving.id) or str(stack.item_id) != str(instance.item_id) or str(stack.owner_person_id or "") != str(instance.owner_person_id or ""):
                continue
            if _holding(holdings, str(stack.id)) is not None:
                continue
            instances.update(id=str(stack.id), quantity=_quantity(stack.quantity) + amount)
            instances.delete(id=str(moving.id))
            return ItemDropped(item_instance_id=str(stack.id), dropped=amount, location_id=place)
    instances.update(id=str(moving.id), location_id=place)
    return ItemDropped(item_instance_id=str(moving.id), dropped=amount, location_id=place)


class ItemGiven(PlainModel):
    item_instance_id: str = Field(..., description="The instance the person now owns and carries (their stack's, when it merged)")
    quantity: int = Field(..., description="How many of it they carry now")


def give_item(model_registry: Any, requester_id: str, person_id: str, item_id: str, quantity: int = 1) -> ItemGiven:
    """``quantity`` of a kind of item made for the person, theirs and carried by them (Zephyrex RPG,
    2026-11-28: pregens and the party carried nothing; the VTT builder grants starting equipment,
    the vault a person's `carries:`). A stackable item merges into the stack of it they own and
    carry."""
    instances, holdings, items, people = _managers(model_registry, requester_id)
    _one(people, person_id)
    item = _one(items, item_id)
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
        raise HTTPException(status_code=422, detail="quantity is a whole number from 1")
    amount = quantity
    if _quantity(item.stack_size) > 1:
        for row in _live(holdings, target_entity_type="person", target_entity_id=person_id):
            try:
                stack = _one(instances, row.item_instance_id)
            except HTTPException:
                continue
            if str(stack.item_id) == str(item_id) and str(stack.owner_person_id or "") == person_id:
                total = _quantity(row.quantity) + amount
                instances.update(id=str(stack.id), quantity=total)
                holdings.update(id=str(row.id), quantity=total)
                return ItemGiven(item_instance_id=str(stack.id), quantity=total)
    made = instances.create(item_id=item_id, owner_person_id=person_id, quantity=amount)
    holdings.create(item_instance_id=str(made.id), target_entity_type="person", target_entity_id=person_id, quantity=amount)
    return ItemGiven(item_instance_id=str(made.id), quantity=amount)
