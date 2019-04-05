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
import importlib

from codequick import Route, Resolver, Listitem, run, Script, utils, storage
import urlquick
import xbmcplugin
import xbmc
import xbmcgui

import resources.lib.skeleton as sk
from resources.lib.labels import LABELS
from resources.lib import common
import resources.lib.cq_utils as cqu
from resources.lib import vpn
import resources.lib.favourites as fav


def get_sorted_menu(plugin, menu_id):
    # The current menu to build contains
    # all the items present in the 'menu_id'
    # dictionnary of the skeleton.py file
    current_menu = eval('sk.' + menu_id.upper())

    # Notify user for the new M3U Live TV feature
    if menu_id == "live_tv" and \
            cqu.get_kodi_version() >= 18 and \
            plugin.setting.get_boolean('show_live_tv_m3u_info'):

        r = xbmcgui.Dialog().yesno(
            plugin.localize(LABELS['Information']),
            plugin.localize(30605),
            plugin.localize(30606)
        )
        if not r:
            plugin.setting['show_live_tv_m3u_info'] = False

    # First, we have to sort the current menu items
    # according to each item order and we have
    # to hide each disabled item
    menu = []
    for item_id, item_infos in current_menu.items():

        add_item = True

        # If the item is enable
        if not Script.setting.get_boolean(item_id):
            add_item = False

        # If the desired language is not avaible
        if 'available_languages' in item_infos:
            desired_language = Script.setting[item_id + '.language']
            if desired_language not in item_infos['available_languages']:
                add_item = False

        if add_item:
            # Get order value in settings file
            item_order = Script.setting.get_int(item_id + '.order')

            item = (
                item_order,
                item_id,
                item_infos
            )

            menu.append(item)

    # We sort the menu according to the item_order values
    return sorted(menu, key=lambda x: x[0])


def add_context_menus_to_item(
        plugin, item, index, item_id, menu_id, menu_len):

    # Move up
    if index > 0:
        item.context.script(
            move_item,
            plugin.localize(LABELS['Move up']),
            direction='up',
            item_id=item_id,
            menu_id=menu_id)

    # Move down
    if index < menu_len - 1:
        item.context.script(
            move_item,
            plugin.localize(LABELS['Move down']),
            direction='down',
            item_id=item_id,
            menu_id=menu_id)

    # Hide
    item.context.script(
        hide_item,
        plugin.localize(LABELS['Hide']),
        item_id=item_id)

    # Connect/Disconnect VPN
    with storage.PersistentDict('vpn') as db:
        vpn_label = plugin.localize(LABELS['Connect VPN'])
        if 'status' in db:
            if db['status'] == 'connected':
                vpn_label = plugin.localize(LABELS['Disconnect VPN'])
        else:
            db['status'] = 'disconnected'
            db.flush()

        item.context.script(
            vpn.vpn_item_callback,
            vpn_label)

    # Add to plugin favourites
    item.context.script(
        fav.add_item_to_favourites,
        'add_item_to_favourites',
        item_id=item_id)

    return


@Route.register
def root(plugin):
    """
    root is the entry point
    of Catch-up TV & More
    """
    # First menu to build is the root menu
    # (see ROOT dictionnary in skeleton.py)

    # TEMPO (waiting for the CodeQuick update)
    plugin.cache_to_disc = True

    return generic_menu(plugin, 'ROOT')


@Route.register
def generic_menu(plugin, menu_id, item_module=None, item_dict=None):
    """
    Build a generic addon menu
    with all not hidden items
    """

    # TEMPO (waiting for the CodeQuick update)
    plugin.cache_to_disc = True

    menu = get_sorted_menu(plugin, menu_id)

    if not menu:
        # If the selected menu is empty just reload the current menu
        yield False

    for index, (item_order,
                item_id,
                item_infos
                ) in enumerate(menu):

        item = Listitem()

        add_context_menus_to_item(
            plugin, item, index, item_id, menu_id, len(menu))

        if item_id in LABELS:
            label = LABELS[item_id]
            if isinstance(label, int):
                label = plugin.localize(label)
            item.label = label
        else:
            item.label = item_id

        # Get item path of icon and fanart
        if 'thumb' in item_infos:
            item.art["thumb"] = common.get_item_media_path(
                item_infos['thumb'])

        if 'fanart' in item_infos:
            item.art["fanart"] = common.get_item_media_path(
                item_infos['fanart'])

        # If this item requires a module to work, get
        # the module path to be loaded
        item.params['item_module'] = item_infos.get('module')

        # Get the next action to trigger if this
        # item will be selected by the user
        item.set_callback(
            eval(item_infos['callback']),
            item_id,
            item_dict=cqu.item2dict(item))

        yield item


@Route.register
def tv_guide_menu(plugin, menu_id, item_module=None, item_dict=None):

    # TEMPO (waiting for the CodeQuick update)
    plugin.cache_to_disc = True

    # Move up and move down action only work with this sort method
    plugin.add_sort_methods(xbmcplugin.SORT_METHOD_UNSORTED)

    menu = get_sorted_menu(plugin, menu_id)
    channels_id = []
    for index, (channel_order,
                channel_id,
                channel_infos
                ) in enumerate(menu):
        channels_id.append(channel_id)

    # Load the graber module accroding to the country
    # (e.g. resources.lib.channels.tv_guides.fr_live)
    tv_guide_module_path = 'resources.lib.channels.tv_guides.' + menu_id
    tv_guide_module = importlib.import_module(tv_guide_module_path)

    # For each channel grab the current program according to the current time
    tv_guide = tv_guide_module.grab_tv_guide(channels_id)

    for index, (channel_order,
                channel_id,
                channel_infos
                ) in enumerate(menu):

        item = Listitem()

        add_context_menus_to_item(
            plugin, item, index, channel_id, menu_id, len(menu))

        label = LABELS[channel_id]
        if isinstance(label, int):
            label = plugin.localize(label)
        item.label = label

        # Get item path of icon and fanart
        if 'thumb' in channel_infos:
            item.art["thumb"] = common.get_item_media_path(
                channel_infos['thumb'])

        if 'fanart' in channel_infos:
            item.art["fanart"] = common.get_item_media_path(
                channel_infos['fanart'])

        # If this item requires a module to work, get
        # the module path to be loaded
        item.params['item_module'] = channel_infos.get('module')

        # If we have program infos from the grabber
        if channel_id in tv_guide:
            guide_infos = tv_guide[channel_id]

            if 'title' in guide_infos:
                item.label = item.label + ' — ' + guide_infos['title']

            item.info['originaltitle'] = guide_infos.get('originaltitle')

            # e.g Divertissement, Documentaire, Film, ...
            item.info['genre'] = guide_infos.get('genre')

            plot = []

            if 'specific_genre' in guide_infos:
                if 'genre' not in guide_infos:
                    item.info['genre'] = guide_infos['specific_genre']
                elif guide_infos.get('genre') in guide_infos['specific_genre']:
                    item.info['genre'] = guide_infos['specific_genre']
                else:
                    plot.append(guide_infos['specific_genre'])

            # start_time and stop_time must be a string
            if 'start_time' in guide_infos and 'stop_time' in guide_infos:
                plot.append(guide_infos['start_time'] + ' - ' + guide_infos['stop_time'])
            elif 'start_time' in guide_infos:
                plot.append(guide_infos['start_time'])

            if 'subtitle' in guide_infos:
                plot.append(guide_infos['subtitle'])

            if 'plot' in guide_infos:
                plot.append(guide_infos['plot'])

            item.info['plot'] = '\n'.join(plot)

            item.info['episode'] = guide_infos.get('episode')
            item.info['season'] = guide_infos.get('season')
            item.info["rating"] = guide_infos.get('rating')
            item.info["duration"] = guide_infos.get('duration')

            if 'fanart' in guide_infos:
                item.art["fanart"] = guide_infos['fanart']

            if 'thumb' in guide_infos:
                item.art["thumb"] = guide_infos['thumb']

        # Get the next action to trigger if this
        # item will be selected by the user
        item.set_callback(
            eval(channel_infos['callback']),
            channel_id,
            item_dict=cqu.item2dict(item))

        yield item


@Route.register
def replay_bridge(plugin, item_id, item_module, item_dict={}):
    """
    replay_bridge is the bridge between the
    addon.py file and each channel modules files.
    Because each time the user enter in a new
    menu level the PLUGIN.run() function is
    executed.
    So we have to load on the fly the corresponding
    module of the channel.
    """
    # TEMPO (waiting for the CodeQuick update)
    plugin.cache_to_disc = True

    # Let's go to the module file ...
    item_module = importlib.import_module(item_module)
    return item_module.replay_entry(plugin, item_id)


@Route.register
def website_bridge(plugin, item_id, item_module, item_dict={}):
    """
    Like replay_bridge
    """

    # TEMPO (waiting for the CodeQuick update)
    plugin.cache_to_disc = True

    # Let's go to the module file ...
    item_module = importlib.import_module(item_module)
    return item_module.website_entry(plugin, item_id)


@Route.register
def multi_live_bridge(plugin, item_id, item_module, item_dict={}):
    """
    Like replay_bridge
    """

    # TEMPO (waiting for the CodeQuick update)
    plugin.cache_to_disc = True

    # Let's go to the module file ...
    item_module = importlib.import_module(item_module)
    return item_module.multi_live_entry(plugin, item_id)


@Resolver.register
def live_bridge(plugin, item_id, item_module, item_dict={}):
    """
    Like replay_bridge
    """

    # TEMPO (waiting for the CodeQuick update)
    plugin.cache_to_disc = True

    # Let's go to the module file ...
    item_module = importlib.import_module(item_module)
    return item_module.live_entry(plugin, item_id, item_dict)




@Route.register
def clear_cache(plugin):
    # Callback function of clear cache setting button
    urlquick.cache_cleanup(-1)
    Script.notify(plugin.localize(30371), '')
    return False


@Route.register
def move_item(plugin, direction, item_id, menu_id):
    # Callback function of move item conext menu
    if direction == 'down':
        offset = 1
    elif direction == 'up':
        offset = -1

    item_to_move_id = item_id
    item_to_move_order = plugin.setting.get_int(item_to_move_id + '.order')

    menu = get_sorted_menu(plugin, menu_id)

    for k in range(0, len(menu)):
        item = menu[k]
        item_id = item[1]
        if item_to_move_id == item_id:
            item_to_swap = menu[k + offset]
            item_to_swap_order = item_to_swap[0]
            item_to_swap_id = item_to_swap[1]
            plugin.setting[item_to_move_id + '.order'] = item_to_swap_order
            plugin.setting[item_to_swap_id + '.order'] = item_to_move_order
            xbmc.executebuiltin('XBMC.Container.Refresh()')
            break

    return False


@Route.register
def hide_item(plugin, item_id):
    # Callback function of hide item context menu
    if plugin.setting.get_boolean('show_hidden_items_information'):
        xbmcgui.Dialog().ok(
            plugin.localize(LABELS['Information']),
            plugin.localize(
                LABELS['To re-enable hidden items go to the plugin settings']))
        plugin.setting['show_hidden_items_information'] = False

    plugin.setting[item_id] = False
    xbmc.executebuiltin('XBMC.Container.Refresh()')
    return False


@Route.register
def vpn_import_setting(plugin):
    # Callback function of OpenVPN import config file setting button
    vpn.import_ovpn()
    return False


@Route.register
def vpn_delete_setting(plugin):
    # Callback function of OpenVPN delete config file setting button
    vpn.delete_ovpn()
    return False


@Route.register
def vpn_connectdisconnect_setting(plugin):
    # Callback function of OpenVPN connect/disconnect setting button
    return vpn.vpn_item_callback(plugin)


@Route.register
def favourites(plugin, item_id, item_module, item_dict={}):
    """
    Callback function called when the user enter in the
    favourites folder
    """
    print('BUILD FAVOURITES LIST')

    # Get sorted items
    sorted_menu = []
    with storage.PersistentDict("favourites.pickle") as db:
        menu = []
        for item_id, item_dict in db.items():
            item = (
                item_dict['order'],
                item_id,
                item_dict
            )

            menu.append(item)

        # We sort the menu according to the item_order values
        sorted_menu = sorted(menu, key=lambda x: x[0])

    # Add each item in the listing
    for index, (item_order,
                item_id,
                item_dict
                ) in enumerate(sorted_menu):


        item = Listitem()

        print('\tCURRENT ITEM label: ', item_dict['label'])
        print('\tCURRENT ITEM id: ', item_id)
        print('\tCURRENT ITEM URL: ', item_dict['path'])
        print('\tCURRENT ITEM order: ', str(item_dict['order']))


        item.label = item_dict['label']
        item_callback = cqu.get_callback_in_url(item_dict['path'])
        item_module = cqu.get_module_in_url(item_dict['path'])
        print('\tCURRENT ITEM callback: ', item_callback)
        print('\tCURRENT ITEM module: ', item_module)

        # Rename
        item.context.script(
            fav.rename_favourite_item,
            'rename',
            item_id=item_id)

        # Remove
        item.context.script(
            fav.remove_favourite_item,
            'remove',
            item_id=item_id)

        # Move up
        if item_dict['order'] > 0:
            item.context.script(
                fav.move_favourite_item,
                plugin.localize(LABELS['Move up']),
                direction='up',
                item_id=item_id)

        # Move down
        if item_dict['order'] < len(db) - 1:
            item.context.script(
                fav.move_favourite_item,
                plugin.localize(LABELS['Move down']),
                direction='down',
                item_id=item_id)

        item.set_callback(
            eval(item_callback),
            item_id)

        yield item


def main():
    """
    Before calling run() function of
    codequick, we need to check if there
    is any module to load on the fly
    """
    cqu.import_needed_module()

    """
    Then we let CodeQuick check for
    functions to register and call
    the correct function according to
    the Kodi URL
    """
    run()


if __name__ == '__main__':
    main()
