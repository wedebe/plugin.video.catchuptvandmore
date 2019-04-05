# -*- coding: utf-8 -*-
"""
    Catch-up TV & More
    Copyright (C) 2016  SylvainCecchetto

    This file is part of Catch-up TV & More.

    Catch-up TV & More is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    Catch-up TV & More is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with Catch-up TV & More; if not, write to the Free Software Foundation,
    Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

# The unicode_literals import only has
# an effect on Python 2.
# It makes string literals as unicode like in Python 3
from __future__ import unicode_literals

import xbmc

from codequick import Route, utils, storage


@Route.register
def add_item_to_favourites(plugin, item_id):
    """
    Callback function called when the user click
    on 'add item to favourite' from an item
    context menu
    """
    print('WANT TO ADD THE ITEM ', item_id, 'TO THE PLUGIN fAVOUTITES FOLDER')
    print('ListItem path: ' + xbmc.getInfoLabel('ListItem.Path'))

    # Ask the user if he wants to edit the label
    item_label = utils.keyboard('Choose_your_favorite_title', xbmc.getInfoLabel('ListItem.Label'))

    # If user aborded do not add this item to favourite
    if item_label == '':
        # TODO: Notify the user that the action aborded
        return False

    # Add this item to favourite db
    with storage.PersistentDict("favourites.pickle") as db:
        item_dict = {}

        item_dict['path'] = xbmc.getInfoLabel('ListItem.Path')
        item_dict['label'] = item_label
        item_dict['order'] = len(db)

        db[item_id] = item_dict
    return False


@Route.register
def rename_favourite_item(plugin, item_id):
    """
    Callback function called when the user click
    on 'rename' from a favourite item
    context menu
    """
    item_label = utils.keyboard('How_to_rename_your_item?', xbmc.getInfoLabel('ListItem.Label'))

    # If user aborded do not edit this item
    if item_label == '':
        return False
    with storage.PersistentDict("favourites.pickle") as db:
        db[item_id]['label'] = item_label
    xbmc.executebuiltin('XBMC.Container.Refresh()')
    return False


@Route.register
def remove_favourite_item(plugin, item_id):
    """
    Callback function called when the user click
    on 'remove' from a favourite item
    context menu
    """
    with storage.PersistentDict("favourites.pickle") as db:
        del db[item_id]
    xbmc.executebuiltin('XBMC.Container.Refresh()')
    return False


@Route.register
def move_favourite_item(plugin, direction, item_id):
    """
    Callback function called when the user click
    on 'Move up/down' from a favourite item
    context menu
    """
    if direction == 'down':
        offset = 1
    elif direction == 'up':
        offset = -1

    with storage.PersistentDict("favourites.pickle") as db:
        item_to_move_id = item_id
        item_to_move_order = db[item_id]['order']

        menu = []
        for item_id, item_dict in db.items():
            item = (
                item_dict['order'],
                item_id,
                item_dict
            )

            menu.append(item)
        menu = sorted(menu, key=lambda x: x[0])

        for k in range(0, len(menu)):
            item = menu[k]
            item_id = item[1]
            if item_to_move_id == item_id:
                item_to_swap = menu[k + offset]
                item_to_swap_order = item_to_swap[0]
                item_to_swap_id = item_to_swap[1]
                db[item_to_move_id]['order'] = item_to_swap_order
                db[item_to_swap_id]['order'] = item_to_move_order
                xbmc.executebuiltin('XBMC.Container.Refresh()')
                break

        return False
